with source as (
    select * from {{ source('olist', 'order_payments') }}
)

select
    order_id || '-' || payment_sequential          as order_payment_key,
    order_id,
    cast(payment_sequential as integer)            as payment_sequential,
    payment_type,
    cast(payment_installments as integer)          as payment_installments,
    cast(payment_value as decimal(12, 2))          as payment_value
from source
