-- 01_create_raw_tables.sql
-- Creates the raw landing schema for the Olist dataset in Redshift Serverless.
-- All columns are stored as text exactly as they arrive in the CSVs;
-- type casting happens later in dbt staging models.
-- Note: "raw" is a reserved word in Redshift, so the schema is named raw_olist.

create schema if not exists raw_olist;

create table raw_olist.customers (
  customer_id varchar(256), customer_unique_id varchar(256),
  customer_zip_code_prefix varchar(256), customer_city varchar(256),
  customer_state varchar(256));

create table raw_olist.geolocation (
  geolocation_zip_code_prefix varchar(256), geolocation_lat varchar(256),
  geolocation_lng varchar(256), geolocation_city varchar(256),
  geolocation_state varchar(256));

create table raw_olist.order_items (
  order_id varchar(256), order_item_id varchar(256), product_id varchar(256),
  seller_id varchar(256), shipping_limit_date varchar(256),
  price varchar(256), freight_value varchar(256));

create table raw_olist.order_payments (
  order_id varchar(256), payment_sequential varchar(256),
  payment_type varchar(256), payment_installments varchar(256),
  payment_value varchar(256));

create table raw_olist.order_reviews (
  review_id varchar(256), order_id varchar(256), review_score varchar(256),
  review_comment_title varchar(1024), review_comment_message varchar(65535),
  review_creation_date varchar(256), review_answer_timestamp varchar(256));

create table raw_olist.orders (
  order_id varchar(256), customer_id varchar(256), order_status varchar(256),
  order_purchase_timestamp varchar(256), order_approved_at varchar(256),
  order_delivered_carrier_date varchar(256),
  order_delivered_customer_date varchar(256),
  order_estimated_delivery_date varchar(256));

create table raw_olist.products (
  product_id varchar(256), product_category_name varchar(256),
  product_name_lenght varchar(256), product_description_lenght varchar(256),
  product_photos_qty varchar(256), product_weight_g varchar(256),
  product_length_cm varchar(256), product_height_cm varchar(256),
  product_width_cm varchar(256));

create table raw_olist.sellers (
  seller_id varchar(256), seller_zip_code_prefix varchar(256),
  seller_city varchar(256), seller_state varchar(256));

create table raw_olist.product_category_translation (
  product_category_name varchar(256),
  product_category_name_english varchar(256));
