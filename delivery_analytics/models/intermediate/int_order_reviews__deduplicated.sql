-- One review per order, sourced from the DynamoDB export.
-- The raw data has duplicate review_ids and some orders with several reviews.
-- Rule: keep the most recently answered review (then most recently created,
-- then review_id as a final tie-breaker so the result is deterministic).

with reviews as (
    select * from {{ ref('stg_dynamodb__order_reviews') }}
),

ranked as (
    select
        reviews.*,
        row_number() over (
            partition by order_id
            order by review_answered_at desc nulls last,
                     review_created_at desc nulls last,
                     review_id
        ) as review_rank
    from reviews
)

select
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_created_at,
    review_answered_at
from ranked
where review_rank = 1
