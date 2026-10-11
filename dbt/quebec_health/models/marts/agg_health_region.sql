-- Portrait régional courant pour la consommation analytique et Power BI.
with latest_population as (
    select
        region_key,
        reference_year as population_reference_year,
        population
    from {{ ref('int_population_region_annual') }}
    qualify row_number() over (
        partition by region_key
        order by reference_year desc
    ) = 1
),

latest_surgery as (
    select
        region_key,
        financial_period as surgery_financial_period,
        patients_waiting,
        patients_waiting_0_6_months,
        patients_waiting_6_12_months,
        patients_waiting_over_12_months,
        share_waiting_over_12_months_pct,
        patients_waiting_per_100k
    from {{ ref('agg_surgery_region') }}
    qualify row_number() over (
        partition by region_key
        order by financial_period desc
    ) = 1
),

latest_emergency as (
    select
        region_key,
        snapshot_at as emergency_snapshot_at,
        nombre_installations,
        installations_en_surcapacite,
        nombre_civieres_fonctionnelles,
        nombre_civieres_occupees,
        nombre_patients_presents,
        nombre_patients_attente_pec,
        taux_occupation_pct,
        dms_civiere_moyenne_heures,
        dms_ambulatoire_moyenne_heures,
        is_over_100_pct,
        is_over_120_pct,
        is_over_150_pct
    from {{ ref('agg_emergency_region') }}
    qualify row_number() over (
        partition by region_key
        order by snapshot_at desc
    ) = 1
)

select
    region.region_key,
    region.region_code,
    region.region_name,
    population.population_reference_year,
    population.population,
    surgery.surgery_financial_period,
    surgery.patients_waiting,
    surgery.patients_waiting_0_6_months,
    surgery.patients_waiting_6_12_months,
    surgery.patients_waiting_over_12_months,
    surgery.share_waiting_over_12_months_pct,
    surgery.patients_waiting_per_100k,
    emergency.emergency_snapshot_at,
    emergency.nombre_installations,
    emergency.installations_en_surcapacite,
    emergency.nombre_civieres_fonctionnelles,
    emergency.nombre_civieres_occupees,
    emergency.nombre_patients_presents,
    emergency.nombre_patients_attente_pec,
    emergency.taux_occupation_pct,
    emergency.dms_civiere_moyenne_heures,
    emergency.dms_ambulatoire_moyenne_heures,
    emergency.is_over_100_pct,
    emergency.is_over_120_pct,
    emergency.is_over_150_pct
from {{ ref('dim_region') }} as region
left join latest_population as population
    on region.region_key = population.region_key
left join latest_surgery as surgery
    on region.region_key = surgery.region_key
left join latest_emergency as emergency
    on region.region_key = emergency.region_key
