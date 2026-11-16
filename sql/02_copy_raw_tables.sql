-- 02_copy_raw_tables.sql
-- Loads the 9 Olist CSVs from S3 into raw_olist using COPY.
-- Authentication uses the namespace's default IAM role (no keys in code).
-- Run 01_create_raw_tables.sql first.

copy raw_olist.orders from 's3://sarika-olist-raw-2026/raw/olist_orders_dataset.csv'
iam_role default csv ignoreheader 1 emptyasnull blanksasnull acceptinvchars;

copy raw_olist.customers from 's3://sarika-olist-raw-2026/raw/olist_customers_dataset.csv'
iam_role default csv ignoreheader 1 emptyasnull blanksasnull acceptinvchars;

copy raw_olist.geolocation from 's3://sarika-olist-raw-2026/raw/olist_geolocation_dataset.csv'
iam_role default csv ignoreheader 1 emptyasnull blanksasnull acceptinvchars;

copy raw_olist.order_items from 's3://sarika-olist-raw-2026/raw/olist_order_items_dataset.csv'
iam_role default csv ignoreheader 1 emptyasnull blanksasnull acceptinvchars;

copy raw_olist.order_payments from 's3://sarika-olist-raw-2026/raw/olist_order_payments_dataset.csv'
iam_role default csv ignoreheader 1 emptyasnull blanksasnull acceptinvchars;

copy raw_olist.order_reviews from 's3://sarika-olist-raw-2026/raw/olist_order_reviews_dataset.csv'
iam_role default csv ignoreheader 1 emptyasnull blanksasnull acceptinvchars;

copy raw_olist.products from 's3://sarika-olist-raw-2026/raw/olist_products_dataset.csv'
iam_role default csv ignoreheader 1 emptyasnull blanksasnull acceptinvchars;

copy raw_olist.sellers from 's3://sarika-olist-raw-2026/raw/olist_sellers_dataset.csv'
iam_role default csv ignoreheader 1 emptyasnull blanksasnull acceptinvchars;

copy raw_olist.product_category_translation from 's3://sarika-olist-raw-2026/raw/product_category_name_translation.csv'
iam_role default csv ignoreheader 1 emptyasnull blanksasnull acceptinvchars;

-- Row count check (all 9 matched the published counts on 2026-11-16)
select 'customers' as table_name, count(*) as row_count from raw_olist.customers
union all select 'geolocation', count(*) from raw_olist.geolocation
union all select 'order_items', count(*) from raw_olist.order_items
union all select 'order_payments', count(*) from raw_olist.order_payments
union all select 'order_reviews', count(*) from raw_olist.order_reviews
union all select 'orders', count(*) from raw_olist.orders
union all select 'products', count(*) from raw_olist.products
union all select 'sellers', count(*) from raw_olist.sellers
union all select 'product_category_translation', count(*) from raw_olist.product_category_translation
order by table_name;
