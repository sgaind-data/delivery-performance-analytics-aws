with source as (
    select * from {{ source('olist', 'products') }}
)

-- Olist stores numeric product attributes as decimals in text (e.g. '40.0'),
-- so they are cast through float before integer.
select
    product_id,
    product_category_name,
    cast(cast(product_name_lenght as float) as integer)        as product_name_length,
    cast(cast(product_description_lenght as float) as integer) as product_description_length,
    cast(cast(product_photos_qty as float) as integer)         as product_photos_qty,
    cast(cast(product_weight_g as float) as integer)           as product_weight_g,
    cast(cast(product_length_cm as float) as integer)          as product_length_cm,
    cast(cast(product_height_cm as float) as integer)          as product_height_cm,
    cast(cast(product_width_cm as float) as integer)           as product_width_cm
from source
