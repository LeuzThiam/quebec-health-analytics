{{
    config(
        materialized='incremental',
        unique_key='emergency_snapshot_key',
        incremental_strategy='merge',
        on_schema_change='sync_all_columns',
        cluster_by=['snapshot_at']
    )
}}

with snapshots as (
    select *
    from {{ ref('int_urgences_enrichies') }}
    where snapshot_at is not null
    {% if is_incremental() %}
        -- Le watermark technique inclut aussi les corrections et backfills arrivés tardivement.
        and loaded_at >= dateadd(
            hour,
            -1,
            (select coalesce(max(loaded_at), '1900-01-01'::timestamp_tz) from {{ this }})
        )
    {% endif %}
)

select
    md5(concat_ws('|', no_permis_installation, snapshot_at::varchar)) as emergency_snapshot_key,
    md5(no_permis_installation) as facility_key,
    md5(coalesce(rss_code, region)) as region_key,
    to_number(to_char(snapshot_at::date, 'YYYYMMDD')) as date_key,
    hour(snapshot_at) * 100 + minute(snapshot_at) as time_key,
    snapshot_at,
    no_permis_installation as installation_id,
    nombre_civieres_fonctionnelles,
    nombre_civieres_occupees,
    nombre_patients_civiere_plus_24h,
    nombre_patients_civiere_plus_48h,
    nombre_patients_presents,
    nombre_patients_attente_pec,
    dms_civiere_heures,
    dms_ambulatoire_heures,
    taux_occupation_pct,
    niveau_occupation,
    source_file,
    loaded_at
from snapshots
