with source as (
    select * from {{ source('olist', 'sellers') }}
)

select
    seller_id,
    seller_zip_code_prefix,     -- kept as text to preserve leading zeros
    seller_city,
    upper(seller_state)         as seller_state
from source
