-- One row per calendar day from 2016-01-01 to 2018-12-31 (covers every Olist date).
-- Built with a cross-join number generator because Redshift's generate_series
-- runs only on the leader node and cannot be used to create tables.

with digits as (
    select 0 as d union all select 1 union all select 2 union all select 3
    union all select 4 union all select 5 union all select 6 union all select 7
    union all select 8 union all select 9
),

numbers as (
    select ones.d + tens.d * 10 + hundreds.d * 100 + thousands.d * 1000 as n
    from digits as ones
    cross join digits as tens
    cross join digits as hundreds
    cross join digits as thousands
),

days as (
    select dateadd(day, n, '2016-01-01'::date)::date as date_day
    from numbers
    where dateadd(day, n, '2016-01-01'::date) <= '2018-12-31'::date
)

select
    date_day,
    extract(year from date_day)::integer                  as year,
    extract(quarter from date_day)::integer               as quarter,
    extract(month from date_day)::integer                 as month,
    trim(to_char(date_day, 'Month'))                      as month_name,
    to_char(date_day, 'YYYY-MM')                          as year_month,
    extract(dow from date_day)::integer                   as day_of_week,   -- 0 = Sunday
    trim(to_char(date_day, 'Day'))                        as day_name,
    extract(dow from date_day) in (0, 6)                  as is_weekend
from days
