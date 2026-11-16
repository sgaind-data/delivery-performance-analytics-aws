-- Singular test: the DynamoDB round trip must not lose, add or change any review.
-- Returns every review that is missing from either copy or whose score differs.
-- The test passes when this query returns zero rows.

select
    coalesce(csv.order_id, ddb.order_id)    as order_id,
    coalesce(csv.review_id, ddb.review_id)  as review_id,
    csv.review_score                        as csv_review_score,
    ddb.review_score                        as dynamodb_review_score
from {{ ref('stg_olist__order_reviews') }} as csv
full outer join {{ ref('stg_dynamodb__order_reviews') }} as ddb
    on csv.order_id = ddb.order_id
   and csv.review_id = ddb.review_id
where csv.order_id is null
   or ddb.order_id is null
   or csv.review_score <> ddb.review_score
