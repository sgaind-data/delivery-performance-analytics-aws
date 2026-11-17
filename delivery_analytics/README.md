# delivery_analytics (dbt project)

dbt Core 1.12 project (dbt-redshift adapter) that turns the raw Olist tables in Redshift Serverless into a tested star schema. See the [main README](../README.md) for the full architecture and findings.

| Layer | Models | Materialization | Purpose |
| --- | --- | --- | --- |
| `models/staging` | 9 | view | One model per raw table: rename and cast the all-text raw layer |
| `models/intermediate` | 2 | view | `int_orders__delivery_metrics` (single definition of on-time, delay, dispatch) and `int_order_reviews__deduplicated` (one review per order, from the DynamoDB copy) |
| `models/marts` | 5 | table | Star schema: `fact_orders` (order-item grain), `dim_customers`, `dim_products`, `dim_sellers`, `dim_date` |
| `snapshots` | 1 | snapshot | `snap_sellers`: SCD Type 2 seller history (check strategy on zip, city, state) |

- **Tests:** 90 (89 generic: unique, not_null, relationships, accepted_values; 1 singular: `tests/assert_dynamodb_reviews_match_csv.sql`).
- **Schemas:** `macros/generate_schema_name.sql` writes to clean schema names (`staging`, `intermediate`, `marts`, `snapshots`).
- **Connection:** a `profiles.yml` outside the repo, with the password read from the `DBT_REDSHIFT_PASSWORD` environment variable.

```bash
dbt build             # models, snapshot and all tests in dependency order
dbt docs generate     # documentation and lineage graph (static copy in ../docs/index.html)
```
