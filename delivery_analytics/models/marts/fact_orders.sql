-- Fact table at ORDER-ITEM grain: one row per item in an order.
-- Item-level measures: item_price, freight_value.
-- Order-level attributes (delivery dates, is_late, delay_days, review_score) repeat on
-- every item of the same order. For order-level KPIs, count distinct order_id or filter
-- on is_first_item_in_order = true.
-- Orders with no items (canceled/unavailable) are not in this table.

with items as (
    select * from {{ ref('stg_olist__order_items') }}
),

orders as (
    select * from {{ ref('int_orders__delivery_metrics') }}
),

reviews as (
    select order_id, review_score
    from {{ ref('int_order_reviews__deduplicated') }}
)

select
    -- keys
    items.order_item_key,
    items.order_id,
    items.order_item_number,
    (items.order_item_number = 1)              as is_first_item_in_order,
    orders.customer_id,
    items.product_id,
    items.seller_id,

    -- order status and dates (promised vs actual)
    orders.order_status,
    orders.purchase_date,
    orders.estimated_delivery_date              as promised_delivery_date,
    orders.delivered_date                       as actual_delivery_date,
    trunc(orders.order_delivered_carrier_at)    as carrier_handoff_date,
    items.shipping_limit_at,

    -- delivery performance (order level)
    orders.is_delivered,
    orders.is_late,
    orders.delay_days,
    orders.days_to_deliver,
    orders.dispatch_days,

    -- item-level measures
    items.item_price,
    items.freight_value,

    -- order-level totals (repeat per item; use with distinct order_id)
    orders.item_count                           as order_item_count,
    orders.items_value                          as order_items_value,
    orders.freight_value                        as order_freight_value,

    -- customer review (order level)
    reviews.review_score

from items
inner join orders
    on items.order_id = orders.order_id
left join reviews
    on items.order_id = reviews.order_id
