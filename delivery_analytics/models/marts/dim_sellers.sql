-- Current version of each seller, read from the SCD Type 2 snapshot.
-- Full history (including closed-out versions) lives in snapshots.snap_sellers.

select
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state,
    dbt_valid_from      as valid_from
from {{ ref('snap_sellers') }}
where dbt_valid_to is null
