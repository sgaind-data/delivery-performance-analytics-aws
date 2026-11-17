"""
export_dashboard_data.py  —  Milestone 7: data extracts for Tableau Public.

Tableau Public cannot connect to Redshift, so this script exports two CSVs from
the dbt marts, plus the headline KPIs computed in Python so the dashboard's
numbers can be checked against an independent calculation.

Writes:
  dashboard/tableau_orders.csv         one row per DELIVERED order
  dashboard/tableau_seller_orders.csv  one row per delivered order x seller
  results/dashboard_kpis.csv           headline KPIs (on-time %, avg delay, freight per order)

Run from the repo root with the project venv active and DBT_REDSHIFT_PASSWORD set:
    python analysis/export_dashboard_data.py

Definitions (from int_orders__delivery_metrics):
  - Scope: delivered orders (status 'delivered' with a delivery date)
  - is_late: delivered DATE > estimated delivery DATE   (exported as 1/0)
  - delay_days: delivered date - estimated date (positive = late)
  - freight per order: total freight_value across an order's items
"""

import os
from pathlib import Path

import pandas as pd
import redshift_connector

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = REPO_ROOT / "dashboard"
RESULTS_DIR = REPO_ROOT / "results"
DASHBOARD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

ORDERS_SQL = """
select
    f.order_id,
    f.purchase_date,
    d.year_month                          as purchase_year_month,
    f.promised_delivery_date,
    f.actual_delivery_date,
    c.customer_state,
    c.customer_city,
    case when f.is_late then 1 else 0 end as is_late,
    f.delay_days,
    f.days_to_deliver,
    f.dispatch_days,
    f.order_item_count,
    f.order_items_value,
    f.order_freight_value,
    f.review_score
from marts.fact_orders as f
join marts.dim_customers as c on f.customer_id = c.customer_id
join marts.dim_date      as d on f.purchase_date = d.date_day
where f.is_first_item_in_order
  and f.is_delivered
"""

SELLER_ORDERS_SQL = """
select
    f.order_id,
    f.seller_id,
    s.seller_state,
    s.seller_city,
    c.customer_state,
    case when f.is_late then 1 else 0 end as is_late,
    f.delay_days,
    f.dispatch_days,
    count(*)                              as seller_item_count,
    sum(f.item_price)                     as seller_items_value,
    sum(f.freight_value)                  as seller_freight_value
from marts.fact_orders as f
join marts.dim_sellers   as s on f.seller_id = s.seller_id
join marts.dim_customers as c on f.customer_id = c.customer_id
where f.is_delivered
group by 1, 2, 3, 4, 5, 6, 7, 8
"""


def query(conn, sql: str) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetch_dataframe()


def main() -> None:
    conn = redshift_connector.connect(
        host="olist-wg.387265682464.us-east-2.redshift-serverless.amazonaws.com",
        port=5439,
        database="dev",
        user="sarika_admin",
        password=os.environ["DBT_REDSHIFT_PASSWORD"],
        ssl=True,
    )
    orders = query(conn, ORDERS_SQL)
    seller_orders = query(conn, SELLER_ORDERS_SQL)
    conn.close()

    orders.to_csv(DASHBOARD_DIR / "tableau_orders.csv", index=False)
    seller_orders.to_csv(DASHBOARD_DIR / "tableau_seller_orders.csv", index=False)
    print(f"tableau_orders.csv:        {len(orders):,} rows")
    print(f"tableau_seller_orders.csv: {len(seller_orders):,} rows")

    # Headline KPIs, computed independently of Tableau
    late = orders["is_late"].astype(int)
    kpis = pd.DataFrame(
        [
            {"kpi": "delivered_orders", "value": len(orders)},
            {"kpi": "late_orders", "value": int(late.sum())},
            {"kpi": "on_time_rate_pct", "value": round((1 - late.mean()) * 100, 4)},
            {"kpi": "avg_delay_days_late_orders",
             "value": round(orders.loc[late == 1, "delay_days"].astype(float).mean(), 4)},
            {"kpi": "median_delay_days_late_orders",
             "value": float(orders.loc[late == 1, "delay_days"].astype(float).median())},
            {"kpi": "avg_freight_per_order_brl",
             "value": round(orders["order_freight_value"].astype(float).mean(), 4)},
            {"kpi": "freight_pct_of_items_value",
             "value": round(orders["order_freight_value"].astype(float).sum()
                            / orders["order_items_value"].astype(float).sum() * 100, 4)},
        ]
    )
    kpis.to_csv(RESULTS_DIR / "dashboard_kpis.csv", index=False)
    print("\nHeadline KPIs (check these against Tableau):")
    print(kpis.to_string(index=False))


if __name__ == "__main__":
    main()
