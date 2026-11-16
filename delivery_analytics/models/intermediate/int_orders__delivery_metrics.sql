-- One row per order with delivery performance metrics.
-- Definitions (used by every downstream model, the dashboard and the stats tests):
--   is_delivered    : order_status = 'delivered' and a customer delivery timestamp exists
--   is_late         : delivered DATE > estimated delivery DATE (dates, not timestamps)
--   delay_days      : delivered date - estimated date (positive = late, negative = early)
--   days_to_deliver : purchase date -> delivered date
--   dispatch_days   : order approval -> handoff to carrier, in fractional days
-- Metrics are NULL for orders that were not delivered, so they never skew averages.

with orders as (
    select * from {{ ref('stg_olist__orders') }}
),

item_totals as (
    select
        order_id,
        count(*)            as item_count,
        sum(item_price)     as items_value,
        sum(freight_value)  as freight_value
    from {{ ref('stg_olist__order_items') }}
    group by order_id
),

dated as (
    select
        orders.*,
        trunc(order_purchased_at)            as purchase_date,
        trunc(order_delivered_customer_at)   as delivered_date,
        trunc(order_estimated_delivery_at)   as estimated_delivery_date,
        (order_status = 'delivered'
            and order_delivered_customer_at is not null) as is_delivered
    from orders
)

select
    dated.order_id,
    dated.customer_id,
    dated.order_status,
    dated.order_purchased_at,
    dated.order_approved_at,
    dated.order_delivered_carrier_at,
    dated.order_delivered_customer_at,
    dated.order_estimated_delivery_at,
    dated.purchase_date,
    dated.delivered_date,
    dated.estimated_delivery_date,
    dated.is_delivered,

    case when dated.is_delivered
         then dated.delivered_date > dated.estimated_delivery_date
    end                                                            as is_late,

    case when dated.is_delivered
         then datediff(day, dated.estimated_delivery_date, dated.delivered_date)
    end                                                            as delay_days,

    case when dated.is_delivered
         then datediff(day, dated.purchase_date, dated.delivered_date)
    end                                                            as days_to_deliver,

    case when dated.order_approved_at is not null
          and dated.order_delivered_carrier_at is not null
         then datediff(hour, dated.order_approved_at, dated.order_delivered_carrier_at) / 24.0
    end                                                            as dispatch_days,

    coalesce(item_totals.item_count, 0)                            as item_count,
    coalesce(item_totals.items_value, 0)                           as items_value,
    coalesce(item_totals.freight_value, 0)                         as freight_value

from dated
left join item_totals
    on dated.order_id = item_totals.order_id
