select
    date_key,
    facility_key,
    count(*) as duplicate_count
from {{ ref('agg_emergency_daily') }}
group by date_key, facility_key
having count(*) > 1

