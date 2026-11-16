with source as (
    select * from {{ source('olist', 'customers') }}
)

select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,   -- kept as text to preserve leading zeros
    customer_city,
    upper(customer_state)       as customer_state
from source
