-- 04_load_dynamodb_export.sql
-- Loads the DynamoDB export of olist_order_reviews (DynamoDB JSON, gzipped) from S3
-- into Redshift, then validates it against the original CSV load.
--
-- DynamoDB JSON wraps every value in a type descriptor, e.g.
--   {"Item": {"order_id": {"S": "abc"}, "review_score": {"N": "5"}}}
-- The JSONPaths file (s3://sarika-olist-raw-2026/config/dynamodb_reviews_jsonpaths.json)
-- maps each typed value to a column. Attributes missing from an item (e.g. empty
-- comments, which were omitted in DynamoDB) load as NULL.

-- 1. Landing table (all text, like the rest of the raw layer)
create table if not exists raw_olist.dynamodb_order_reviews (
  order_id                varchar(256),
  review_id               varchar(256),
  review_score            varchar(256),
  review_comment_title    varchar(1024),
  review_comment_message  varchar(65535),
  review_creation_date    varchar(256),
  review_answer_timestamp varchar(256)
);

-- 2. Load the export (re-runnable: clears the table first)
truncate raw_olist.dynamodb_order_reviews;

copy raw_olist.dynamodb_order_reviews
from 's3://sarika-olist-raw-2026/dynamodb-export/AWSDynamoDB/01794864615460-a4353b59/data/'
iam_role default
format as json 's3://sarika-olist-raw-2026/config/dynamodb_reviews_jsonpaths.json'
gzip
acceptinvchars;

-- 3. Validate: row counts, distinct orders and average score from both paths
select 'csv' as load_path,
       count(*) as row_count,
       count(distinct order_id) as distinct_orders,
       round(avg(review_score::float), 4) as avg_score
from raw_olist.order_reviews
union all
select 'dynamodb',
       count(*),
       count(distinct order_id),
       round(avg(review_score::float), 4)
from raw_olist.dynamodb_order_reviews;

-- 4. Validate: reviews that are missing from either side or whose score differs
--    (expected result: 0)
select count(*) as mismatched_reviews
from raw_olist.order_reviews as csv
full outer join raw_olist.dynamodb_order_reviews as ddb
    on csv.order_id = ddb.order_id
   and csv.review_id = ddb.review_id
where csv.order_id is null
   or ddb.order_id is null
   or csv.review_score <> ddb.review_score;
