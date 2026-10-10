-- Vue informative : elle surveille les sources sans provoquer d'échec de pipeline.
with freshness_policy as (
    select 'urgences_horaires' as source_name, 6 as warning_after_hours, 12 as stale_after_hours
    union all select 'urgences_cumulatives', 36, 72
    union all select 'installations', 720, 1440
    union all select 'surgery_waitlist', 1080, 2160
    union all select 'population_health_region', 8760, 17520
),

source_activity as (
    select
        'urgences_horaires' as source_name,
        max(loaded_at) as last_loaded_at,
        count(*) as row_count
    from {{ source('raw', 'urgences_horaires') }}

    union all

    select 'urgences_cumulatives', max(loaded_at), count(*)
    from {{ source('raw', 'urgences_cumulatives') }}

    union all

    select 'installations', max(loaded_at), count(*)
    from {{ source('raw', 'installations') }}

    union all

    select 'surgery_waitlist', max(loaded_at), count(*)
    from {{ source('raw', 'surgery_waitlist') }}

    union all

    select 'population_health_region', max(loaded_at), count(*)
    from {{ source('raw', 'population_health_region') }}
),

evaluated as (
    select
        policy.source_name,
        activity.last_loaded_at,
        activity.row_count,
        round(
            datediff('second', activity.last_loaded_at, current_timestamp()) / 3600.0,
            2
        ) as age_hours,
        policy.warning_after_hours,
        policy.stale_after_hours
    from freshness_policy as policy
    left join source_activity as activity
        on policy.source_name = activity.source_name
)

select
    source_name,
    last_loaded_at,
    row_count,
    age_hours,
    warning_after_hours,
    stale_after_hours,
    case
        when last_loaded_at is null or row_count = 0 then 'MISSING'
        when current_timestamp() >= dateadd('hour', stale_after_hours, last_loaded_at)
            then 'STALE'
        when current_timestamp() >= dateadd('hour', warning_after_hours, last_loaded_at)
            then 'WARNING'
        else 'FRESH'
    end as freshness_status,
    current_timestamp() as evaluated_at
from evaluated
