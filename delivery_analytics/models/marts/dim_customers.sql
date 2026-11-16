-- One row per order-level customer_id (Olist issues a new customer_id per order;
-- customer_unique_id identifies the real person).

select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
from {{ ref('stg_olist__customers') }}
