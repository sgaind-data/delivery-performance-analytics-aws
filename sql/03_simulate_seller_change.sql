-- 03_simulate_seller_change.sql
-- Demonstrates the SCD Type 2 snapshot (snap_sellers).
-- The Olist data is static, so this simulates ONE seller relocating to another city
-- within the same state (SP). The seller's state is unchanged, so state-level
-- analysis is not affected. After running this, `dbt build --select snap_sellers+`
-- closes the old version (dbt_valid_to set) and inserts a new current version.

-- Step 1 (Redshift Query Editor): relocate one SP seller to the city of Sao Paulo
update raw_olist.sellers
set seller_city = 'sao paulo',
    seller_zip_code_prefix = '01310'
where seller_id = (
    select min(seller_id)
    from raw_olist.sellers
    where seller_state = 'SP'
      and seller_city <> 'sao paulo'
);

-- Step 2 (Terminal): dbt build --select snap_sellers+

-- Step 3 (Redshift Query Editor): show every seller with more than one version
select seller_id,
       seller_city,
       seller_zip_code_prefix,
       seller_state,
       dbt_valid_from,
       dbt_valid_to
from snapshots.snap_sellers
where seller_id in (
    select seller_id
    from snapshots.snap_sellers
    group by seller_id
    having count(*) > 1
)
order by seller_id, dbt_valid_from;
