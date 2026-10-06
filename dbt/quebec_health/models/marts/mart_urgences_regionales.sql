select
    date_heure_mise_a_jour as snapshot_at,
    rss_code,
    region,
    count(*) as nombre_installations,
    count_if(taux_occupation_pct is not null) as installations_avec_capacite,
    count_if(taux_occupation_pct > 100) as installations_en_surcapacite,
    sum(nombre_civieres_fonctionnelles) as nombre_civieres_fonctionnelles,
    sum(nombre_civieres_occupees) as nombre_civieres_occupees,
    sum(nombre_patients_civiere_plus_24h) as nombre_patients_civiere_plus_24h,
    sum(nombre_patients_civiere_plus_48h) as nombre_patients_civiere_plus_48h,
    sum(nombre_patients_presents) as nombre_patients_presents,
    sum(nombre_patients_attente_pec) as nombre_patients_attente_pec,
    round(
        100.0 * sum(nombre_civieres_occupees) / nullif(sum(nombre_civieres_fonctionnelles), 0),
        2
    ) as taux_occupation_pct,
    round(avg(dms_civiere_heures), 2) as dms_civiere_moyenne_heures,
    round(avg(dms_ambulatoire_heures), 2) as dms_ambulatoire_moyenne_heures
from {{ ref('int_urgences_enrichies') }}
group by date_heure_mise_a_jour, rss_code, region
