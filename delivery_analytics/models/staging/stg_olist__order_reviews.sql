with source as (
    select * from {{ source('olist', 'order_reviews') }}
)

-- Note: review_id is NOT unique in the raw data, and some orders have more than
-- one review. De-duplication to one review per order happens in the intermediate layer.
select
    review_id,
    order_id,
    cast(review_score as integer)                  as review_score,
    review_comment_title,
    review_comment_message,
    cast(review_creation_date as timestamp)        as review_created_at,
    cast(review_answer_timestamp as timestamp)     as review_answered_at
from source
