-- Calendrier partagé par les faits du Data Warehouse.
with dates as (
    select dateadd(day, seq4(), '2020-01-01'::date) as date_day
    from table(generator(rowcount => 15000))
)

select
    to_number(to_char(date_day, 'YYYYMMDD')) as date_key,
    date_day,
    year(date_day) as year_number,
    quarter(date_day) as quarter_number,
    month(date_day) as month_number,
    monthname(date_day) as month_name,
    weekofyear(date_day) as week_number,
    day(date_day) as day_number,
    dayname(date_day) as day_name,
    dayofweekiso(date_day) in (6, 7) as is_weekend,
    case when month(date_day) >= 4 then year(date_day) + 1 else year(date_day) end as fiscal_year,
    mod(month(date_day) - 4 + 12, 12) + 1 as fiscal_period
from dates

