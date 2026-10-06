select
    date_heure_mise_a_jour as snapshot_at,
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
from {{ ref('int_urgences_enrichies') }}
