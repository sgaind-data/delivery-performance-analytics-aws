"""
Daily dbt pipeline for the Delivery Performance Analytics project.

Runs inside the local Astro (Airflow 3) environment:
  dbt_debug -> dbt_build -> dbt_docs_generate

- dbt_debug          checks the Redshift connection (--connection) before doing any work
- dbt_build          runs every model, the SCD2 snapshot and all tests in dependency order
- dbt_docs_generate  refreshes the documentation and lineage graph

dbt runs from its own virtual environment (see Dockerfile), against the dbt project
mounted at /usr/local/airflow/dbt (see docker-compose.override.yml), using the
profile in /usr/local/airflow/include. The Redshift password comes from the
DBT_REDSHIFT_PASSWORD variable in airflow/.env.
"""

from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

DBT_BIN = "/usr/local/airflow/dbt_venv/bin/dbt"
DBT_PROJECT_DIR = "/usr/local/airflow/dbt"
DBT_PROFILES_DIR = "/usr/local/airflow/include"
DBT_FLAGS = f"--project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROFILES_DIR}"

default_args = {
    "owner": "sarika",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="delivery_analytics_dbt_daily",
    description="Daily dbt build and docs for the Olist delivery analytics star schema on Redshift Serverless",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["dbt", "redshift", "delivery-analytics"],
) as dag:

    # --connection tests only the Redshift connection. A full `dbt debug` also
    # checks for git, which is not installed in the Airflow image (and not needed).
    dbt_debug = BashOperator(
        task_id="dbt_debug",
        bash_command=f"{DBT_BIN} debug --connection {DBT_FLAGS}",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"{DBT_BIN} build {DBT_FLAGS}",
    )

    dbt_docs_generate = BashOperator(
        task_id="dbt_docs_generate",
        bash_command=f"{DBT_BIN} docs generate {DBT_FLAGS}",
    )

    dbt_debug >> dbt_build >> dbt_docs_generate
