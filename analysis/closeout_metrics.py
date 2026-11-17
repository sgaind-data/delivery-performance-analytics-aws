"""
closeout_metrics.py  -  Final verified numbers for the resume and the BA case study.

Every number is computed here from the dbt marts in Redshift (or read from saved
outputs / dbt artifacts), and each query's result is saved to results/closeout/.

Run from the repo root with the venv active, AFTER a fresh `dbt build` (so the dbt
artifacts in delivery_analytics/target/ describe the current project):

    set -a; source airflow/.env; set +a
    (cd delivery_analytics && dbt build)
    python analysis/closeout_metrics.py

Definitions (from int_orders__delivery_metrics, matching the case-study rules):
  - Scope: order_status = 'delivered' AND a customer delivery timestamp exists (is_delivered)
  - On-time: delivered DATE <= estimated delivery DATE (dates, not timestamps)
  - Delay (days): delivered date - estimated date, reported for late orders only
  - Freight % of order value: SUM(freight_value) / SUM(price)
  - State: customer_state unless stated otherwise
  - One row per order: fact_orders filtered to is_first_item_in_order
"""

import json
import os
from pathlib import Path

import pandas as pd
import redshift_connector

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results" / "closeout"
OUT.mkdir(parents=True, exist_ok=True)
DBT_TARGET = REPO / "delivery_analytics" / "target"

# Delivered orders, one row per order, with customer state.
ORDERS = """
    select f.*, c.customer_state, c.customer_unique_id
    from marts.fact_orders f
    join marts.dim_customers c on f.customer_id = c.customer_id
    where f.is_first_item_in_order and f.is_delivered
"""

QUERIES = {
    # ---------- Request A1: fact table row counts (all statuses) ----------
    "a1_fact_row_counts": """
        select count(distinct order_id) as orders_in_fact,
               count(*)                 as order_items_in_fact
        from marts.fact_orders
    """,

    # ---------- Request B1: scope ----------
    "b1_scope": f"""
        with o as ({ORDERS})
        select count(*)                            as delivered_orders,
               count(distinct customer_unique_id)  as distinct_customers,
               min(purchase_date)                  as min_purchase_date,
               max(purchase_date)                  as max_purchase_date
        from o
    """,
    "b1_scope_sellers": """
        select count(distinct seller_id) as distinct_sellers_delivered
        from marts.fact_orders
        where is_delivered
    """,
    "b1_exclusions_by_status": """
        select order_status,
               count(*) as orders,
               sum(case when order_delivered_customer_at is null then 1 else 0 end)
                   as missing_delivery_date
        from staging.stg_olist__orders
        group by order_status
        order by orders desc
    """,
    "b1_delivered_orders_without_items": """
        select count(*) as delivered_orders_without_items
        from intermediate.int_orders__delivery_metrics m
        where m.is_delivered
          and not exists (select 1 from marts.fact_orders f where f.order_id = m.order_id)
    """,

    # ---------- Request A3 / B2: on-time and delay ----------
    "b2_on_time_and_delay": f"""
        with o as ({ORDERS})
        select count(*)                                              as delivered_orders,
               sum(case when is_late then 1 else 0 end)              as late_orders,
               round(100.0 * sum(case when is_late then 0 else 1 end) / count(*), 4)
                                                                     as on_time_pct,
               round(avg(case when is_late then delay_days::float end), 4)
                                                                     as avg_delay_days_late,
               median(case when is_late then delay_days end)         as median_delay_days_late
        from o
    """,

    # ---------- Request B3: on-time by customer state ----------
    "b3_on_time_by_state": f"""
        with o as ({ORDERS})
        select customer_state,
               count(*)                                   as delivered_orders,
               sum(case when is_late then 1 else 0 end)   as late_orders,
               round(100.0 * sum(case when is_late then 0 else 1 end) / count(*), 2)
                                                          as on_time_pct,
               case when count(*) < 100 then 'LOW-VOLUME' else '' end as volume_flag
        from o
        group by customer_state
        order by on_time_pct asc, delivered_orders desc
    """,

    # ---------- Request A6: driver analysis ----------
    # Which states contribute the most late orders (share of all late orders)?
    "a6_late_share_by_state": f"""
        with o as ({ORDERS}),
        s as (
            select customer_state,
                   count(*) as delivered_orders,
                   sum(case when is_late then 1 else 0 end) as late_orders
            from o group by customer_state
        )
        select customer_state, delivered_orders, late_orders,
               round(100.0 * late_orders / delivered_orders, 2)            as late_rate_pct,
               round(100.0 * late_orders / sum(late_orders) over (), 2)   as share_of_all_late_pct,
               round(100.0 * delivered_orders / sum(delivered_orders) over (), 2)
                                                                          as share_of_all_orders_pct
        from s
        order by late_orders desc
    """,
    # Same-state vs cross-state shipping (seller state vs customer state).
    "a6_late_by_shipping_route": f"""
        with o as ({ORDERS}),
        route as (
            select f.order_id,
                   max(case when s.seller_state <> c.customer_state then 1 else 0 end) as cross_state
            from marts.fact_orders f
            join marts.dim_sellers s   on f.seller_id = s.seller_id
            join marts.dim_customers c on f.customer_id = c.customer_id
            where f.is_delivered
            group by f.order_id
        )
        select case when r.cross_state = 1 then 'cross-state' else 'same-state' end as route,
               count(*)                                            as delivered_orders,
               sum(case when o.is_late then 1 else 0 end)          as late_orders,
               round(100.0 * sum(case when o.is_late then 1 else 0 end) / count(*), 2)
                                                                   as late_rate_pct,
               round(avg(o.days_to_deliver::float), 2)             as avg_days_to_deliver
        from o join route r on o.order_id = r.order_id
        group by 1
        order by 1
    """,
    # Seller dispatch speed (approval -> carrier handoff) vs lateness.
    "a6_late_by_dispatch_speed": f"""
        with o as ({ORDERS})
        select case
                 when dispatch_days is null then 'unknown'
                 when dispatch_days <= 1 then '0-1 days'
                 when dispatch_days <= 3 then '1-3 days'
                 when dispatch_days <= 7 then '3-7 days'
                 else '7+ days'
               end                                                  as dispatch_bucket,
               count(*)                                             as delivered_orders,
               round(100.0 * sum(case when is_late then 1 else 0 end) / count(*), 2)
                                                                    as late_rate_pct
        from o
        group by 1
        order by 1
    """,
    # Lateness by purchase month (seasonality / peak periods).
    "a6_late_by_purchase_month": f"""
        with o as ({ORDERS})
        select to_char(purchase_date, 'YYYY-MM')                    as purchase_month,
               count(*)                                             as delivered_orders,
               round(100.0 * sum(case when is_late then 1 else 0 end) / count(*), 2)
                                                                    as late_rate_pct
        from o
        group by 1
        order by 1
    """,
    # Seller location: share of sellers vs share of worst sellers handled in Python.
    "a6_sellers_by_state": """
        select seller_state, count(*) as sellers
        from marts.dim_sellers
        group by seller_state
        order by sellers desc
    """,

    # ---------- Request B4: freight ----------
    "b4_freight_overall": f"""
        with o as ({ORDERS})
        select round(avg(order_freight_value::float), 4)                       as avg_freight_per_order,
               round(100.0 * sum(order_freight_value) / sum(order_items_value), 4)
                                                                               as freight_pct_of_value_aggregate,
               round(100.0 * avg(order_freight_value::float
                                 / nullif(order_items_value::float, 0)), 4)    as freight_pct_of_value_avg_per_order
        from o
    """,
    "b4_freight_by_state": f"""
        with o as ({ORDERS})
        select customer_state,
               count(*)                                                         as delivered_orders,
               round(avg(order_freight_value::float), 2)                        as avg_freight_per_order,
               round(100.0 * sum(order_freight_value) / sum(order_items_value), 2)
                                                                                as freight_pct_of_value
        from o
        group by customer_state
        order by avg_freight_per_order desc
    """,

    # ---------- Request B5: sellers ----------
    "b5_seller_performance": """
        with so as (
            select distinct f.seller_id, f.order_id, f.is_late, f.dispatch_days
            from marts.fact_orders f
            where f.is_delivered
        ),
        s as (
            select seller_id,
                   count(distinct order_id)                                   as delivered_orders,
                   sum(case when is_late then 1 else 0 end)                   as late_orders,
                   round(100.0 * sum(case when is_late then 0 else 1 end) / count(*), 2)
                                                                              as on_time_pct,
                   round(avg(dispatch_days::float), 2)                        as avg_dispatch_days
            from so
            group by seller_id
        )
        select s.*, d.seller_state
        from s join marts.dim_sellers d on s.seller_id = d.seller_id
        order by on_time_pct asc, delivered_orders desc, s.seller_id
    """,

    # ---------- Request B6: reviews ----------
    "b6_reviews_by_status": f"""
        with o as ({ORDERS})
        select case when is_late then 'late' else 'on-time' end     as delivery_status,
               count(*)                                             as delivered_orders,
               count(review_score)                                  as orders_with_review,
               round(avg(review_score::float), 4)                   as avg_review_score,
               round(100.0 * sum(case when review_score <= 2 then 1 else 0 end)
                     / count(review_score), 2)                      as pct_1_2_star
        from o
        group by 1
        order by 1
    """,

    # ---------- Request B10: carrier fields ----------
    "b10_carrier_columns": """
        select table_schema, table_name, column_name
        from information_schema.columns
        where (column_name ilike '%carrier%' or column_name ilike '%shipping%'
               or column_name ilike '%logistic%' or column_name ilike '%courier%')
          and table_schema in ('raw_olist', 'staging', 'intermediate', 'marts', 'snapshots')
        order by table_schema, table_name, column_name
    """,
}


def dbt_facts() -> dict:
    """Model, test and status counts from the dbt artifacts of the last dbt build."""
    manifest = json.loads((DBT_TARGET / "manifest.json").read_text())
    run_results = json.loads((DBT_TARGET / "run_results.json").read_text())

    nodes = manifest["nodes"].values()
    models = [n for n in nodes if n["resource_type"] == "model"]
    by_layer: dict = {}
    for m in models:
        layer = m["fqn"][1] if len(m["fqn"]) > 2 else "root"
        by_layer[layer] = by_layer.get(layer, 0) + 1
    tests = [n for n in nodes if n["resource_type"] == "test"]
    snapshots = [n for n in nodes if n["resource_type"] == "snapshot"]

    statuses: dict = {}
    for r in run_results["results"]:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1

    return {
        "models_total": len(models),
        "models_by_layer": by_layer,
        "model_names": sorted(m["name"] for m in models),
        "tests_total": len(tests),
        "tests_generic": sum(1 for t in tests if t.get("test_metadata")),
        "tests_singular": sum(1 for t in tests if not t.get("test_metadata")),
        "snapshots": [s["name"] for s in snapshots],
        "sources": len(manifest["sources"]),
        "last_build_command": run_results["args"].get("which"),
        "last_build_generated_at": run_results["metadata"]["generated_at"],
        "last_build_elapsed_seconds": round(run_results["elapsed_time"], 2),
        "last_build_status_counts": statuses,
    }


def main() -> None:
    conn = redshift_connector.connect(
        host="olist-wg.387265682464.us-east-2.redshift-serverless.amazonaws.com",
        port=5439,
        database="dev",
        user="sarika_admin",
        password=os.environ["DBT_REDSHIFT_PASSWORD"],
        ssl=True,
    )
    pd.set_option("display.width", 200)
    pd.set_option("display.max_rows", 200)
    report = []

    for name, sql in QUERIES.items():
        cur = conn.cursor()
        cur.execute(sql)
        df = cur.fetch_dataframe()
        df.to_csv(OUT / f"{name}.csv", index=False)
        report.append(f"\n===== {name} =====\n{df.to_string(index=False)}")

        if name == "b5_seller_performance":
            eligible = df[df["delivered_orders"] >= 20]
            eligible.to_csv(OUT / "b5_sellers_20plus.csv", index=False)
            worst = eligible.head(10)
            worst.to_csv(OUT / "b5_worst10_sellers_20plus.csv", index=False)
            report.append(
                f"\n===== b5_summary =====\n"
                f"sellers_with_20plus_delivered_orders: {len(eligible)}\n"
                f"10 worst by on-time % (ties broken by more orders):\n"
                f"{worst.to_string(index=False)}\n"
                f"seller_state of the 10 worst: "
                f"{worst['seller_state'].value_counts().to_dict()}"
            )
            # Dispatch speed vs on-time across all eligible sellers.
            corr = eligible[["avg_dispatch_days", "on_time_pct"]].astype(float).corr().iloc[0, 1]
            report.append(f"corr(avg_dispatch_days, on_time_pct) across 20+ sellers: {corr:.4f}")
    conn.close()

    facts = dbt_facts()
    (OUT / "dbt_facts.json").write_text(json.dumps(facts, indent=2))
    report.append(f"\n===== dbt_facts =====\n{json.dumps(facts, indent=2)}")

    stats_path = REPO / "results" / "stats_results.csv"
    report.append(f"\n===== stats_results.csv (Milestone 6) =====\n{pd.read_csv(stats_path).to_string(index=False)}")

    text = "\n".join(report)
    (OUT / "closeout_output.txt").write_text(text)
    print(text)
    print(f"\nSaved all outputs to {OUT}")


if __name__ == "__main__":
    main()
