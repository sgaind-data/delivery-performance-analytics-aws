"""
export_marts.py  -  Snapshot every mart table to local CSV before AWS teardown.

After Redshift is deleted, future analysis (e.g. new case-study questions) can run
locally with pandas on these files. Output: data/marts/<table>.csv (git-ignored,
because data/ is in .gitignore; regenerate by rebuilding the pipeline).

Run from the repo root with the venv active and DBT_REDSHIFT_PASSWORD set:
    python analysis/export_marts.py
"""

import os
from pathlib import Path

import redshift_connector

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "data" / "marts"
OUT.mkdir(parents=True, exist_ok=True)

TABLES = [
    "marts.fact_orders",
    "marts.dim_customers",
    "marts.dim_products",
    "marts.dim_sellers",
    "marts.dim_date",
    "snapshots.snap_sellers",
]

conn = redshift_connector.connect(
    host="olist-wg.387265682464.us-east-2.redshift-serverless.amazonaws.com",
    port=5439,
    database="dev",
    user="sarika_admin",
    password=os.environ["DBT_REDSHIFT_PASSWORD"],
    ssl=True,
)
for table in TABLES:
    cur = conn.cursor()
    cur.execute(f"select * from {table}")
    df = cur.fetch_dataframe()
    path = OUT / f"{table.split('.')[1]}.csv"
    df.to_csv(path, index=False)
    print(f"{table:<26} {len(df):>8,} rows -> {path.relative_to(REPO)}")
conn.close()
