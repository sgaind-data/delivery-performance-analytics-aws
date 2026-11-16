-- One row per product, with an English category name.
-- A few Portuguese categories have no translation; they fall back to the Portuguese
-- name, and products with no category at all are labeled 'unknown'.

with products as (
    select * from {{ ref('stg_olist__products') }}
),

translation as (
    select * from {{ ref('stg_olist__product_category_translation') }}
)

select
    products.product_id,
    products.product_category_name                         as category_name_pt,
    coalesce(translation.product_category_name_english,
             products.product_category_name,
             'unknown')                                    as category_name,
    products.product_weight_g,
    products.product_length_cm,
    products.product_height_cm,
    products.product_width_cm,
    products.product_photos_qty
from products
left join translation
    on products.product_category_name = translation.product_category_name
