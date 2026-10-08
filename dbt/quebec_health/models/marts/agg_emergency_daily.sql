with daily_snapshots as (
    select
        date_key,
        facility_key,
        region_key,
        snapshot_at,
        date_trunc('hour', snapshot_at) as snapshot_hour,
        nombre_civieres_fonctionnelles,
        nombre_civieres_occupees,
        nombre_patients_civiere_plus_24h,
        nombre_patients_civiere_plus_48h,
        nombre_patients_presents,
        nombre_patients_attente_pec,
        taux_occupation_pct
    from {{ ref('fct_urgences_horaires') }}
)

select
    date_key,
    facility_key,
    region_key,
    min(snapshot_at) as first_snapshot_at,
    max(snapshot_at) as last_snapshot_at,
    count(*) as snapshot_count,
    count(distinct snapshot_hour) as observed_hours,
    round(avg(taux_occupation_pct), 2) as avg_occupancy_rate_pct,
    max(taux_occupation_pct) as max_occupancy_rate_pct,
    count(distinct case when taux_occupation_pct > 100 then snapshot_hour end) as hours_over_100_pct,
    count(distinct case when taux_occupation_pct > 120 then snapshot_hour end) as hours_over_120_pct,
    count(distinct case when taux_occupation_pct > 150 then snapshot_hour end) as hours_over_150_pct,
    max_by(nombre_civieres_fonctionnelles, snapshot_at) as functional_stretchers_latest,
    max_by(nombre_civieres_occupees, snapshot_at) as occupied_stretchers_latest,
    max_by(nombre_patients_civiere_plus_24h, snapshot_at) as patients_24h_plus_latest,
    max_by(nombre_patients_civiere_plus_48h, snapshot_at) as patients_48h_plus_latest,
    max_by(nombre_patients_presents, snapshot_at) as patients_present_latest,
    max_by(nombre_patients_attente_pec, snapshot_at) as patients_waiting_latest
from daily_snapshots
group by date_key, facility_key, region_key

