select
    nullif(trim(rss), '') as rss_code,
    nullif(trim(region), '') as region,
    nullif(trim(nom_etablissement), '') as nom_etablissement,
    nullif(trim(nom_installation), '') as nom_installation,
    nullif(trim(no_permis_installation), '') as no_permis_installation,
    try_to_number(nullif(trim(nombre_de_civieres_fonctionnelles), '')) as nombre_civieres_fonctionnelles,
    try_to_number(nullif(trim(nombre_de_civieres_occupees), '')) as nombre_civieres_occupees,
    try_to_number(nullif(trim(nombre_de_patients_sur_civiere_plus_de_24_heures), '')) as nombre_patients_civiere_plus_24h,
    try_to_number(nullif(trim(nombre_de_patients_sur_civiere_plus_de_48_heures), '')) as nombre_patients_civiere_plus_48h,
    try_to_number(nullif(trim(nombre_total_de_patients_presents_a_lurgence), '')) as nombre_patients_presents,
    try_to_number(nullif(trim(nombre_total_de_patients_en_attente_de_pec), '')) as nombre_patients_attente_pec,
    try_to_decimal(nullif(trim(dms_sur_civiere), ''), 18, 6) as dms_civiere_heures,
    try_to_decimal(nullif(trim(dms_ambulatoire), ''), 18, 6) as dms_ambulatoire_heures,
    try_to_time(nullif(trim(dms_sur_civiere_horaire), '')) as dms_civiere_affichage,
    try_to_time(nullif(trim(dms_ambulatoire_horaire), '')) as dms_ambulatoire_affichage,
    try_to_time(nullif(trim(heure_extraction_image), '')) as heure_extraction,
    try_to_timestamp_ntz(nullif(trim(mise_a_jour), '')) as date_heure_mise_a_jour,
    case
        when upper(trim(nom_installation)) in ('ENSEMBLE DU QUÉBEC', 'TOTAL PROVINCIAL') then 'PROVINCIAL'
        when upper(trim(nom_installation)) = 'TOTAL RÉGIONAL' then 'REGIONAL'
        else 'INSTALLATION'
    end as niveau_agregation,
    source_file,
    loaded_at
from {{ source('raw', 'urgences_horaires') }}
