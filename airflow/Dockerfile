FROM astrocrpublic.azurecr.io/runtime:3.4-1

# Install dbt in its own virtual environment so its dependencies never
# conflict with Airflow's. The DAG calls /usr/local/airflow/dbt_venv/bin/dbt.
# Pinned to dbt Core v1 to match the local development setup.
RUN python -m venv dbt_venv && \
    dbt_venv/bin/pip install --no-cache-dir "dbt-core>=1.12,<2.0" "dbt-redshift>=1.11,<2.0"
