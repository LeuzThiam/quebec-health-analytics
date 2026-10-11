-- Le MSSS reste prioritaire; StatCan complète les régions absentes des urgences.
with region_candidates as (
    select
        rss_code as region_code,
        region as region_name,
        1 as source_priority,
        snapshot_at as effective_at
    from {{ ref('int_urgences_enrichies') }}
    where rss_code is not null

    union all

    select
        region_code,
        health_region_name as region_name,
        2 as source_priority,
        to_timestamp_ntz(reference_year || '-07-01') as effective_at
    from {{ ref('stg_population_health_region') }}
    where region_code is not null
)

select
    md5(region_code) as region_key,
    region_code,
    region_name
from region_candidates
qualify row_number() over (
    partition by region_code
    order by source_priority, effective_at desc
) = 1
