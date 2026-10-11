select
    md5(concat_ws('|', snapshot_at, rss_code)) as emergency_region_snapshot_key,
    snapshot_at,
    md5(rss_code) as region_key,
    nombre_installations,
    installations_avec_capacite,
    installations_en_surcapacite,
    nombre_civieres_fonctionnelles,
    nombre_civieres_occupees,
    nombre_patients_civiere_plus_24h,
    nombre_patients_civiere_plus_48h,
    nombre_patients_presents,
    nombre_patients_attente_pec,
    taux_occupation_pct,
    dms_civiere_moyenne_heures,
    dms_ambulatoire_moyenne_heures,
    case when taux_occupation_pct is not null then taux_occupation_pct > 100 end
        as is_over_100_pct,
    case when taux_occupation_pct is not null then taux_occupation_pct > 120 end
        as is_over_120_pct,
    case when taux_occupation_pct is not null then taux_occupation_pct > 150 end
        as is_over_150_pct
from {{ ref('mart_urgences_regionales') }}
where rss_code is not null
