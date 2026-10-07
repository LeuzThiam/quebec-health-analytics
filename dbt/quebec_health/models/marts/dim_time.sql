-- Une ligne par minute afin de supporter les snapshots horaires et leurs variations.
with minutes as (
    select dateadd(minute, seq4(), '00:00:00'::time) as time_value
    from table(generator(rowcount => 1440))
)

select
    hour(time_value) * 100 + minute(time_value) as time_key,
    time_value,
    hour(time_value) as hour_number,
    minute(time_value) as minute_number,
    case
        when hour(time_value) < 6 then 'NUIT'
        when hour(time_value) < 12 then 'MATIN'
        when hour(time_value) < 18 then 'APRES_MIDI'
        else 'SOIREE'
    end as time_of_day
from minutes

