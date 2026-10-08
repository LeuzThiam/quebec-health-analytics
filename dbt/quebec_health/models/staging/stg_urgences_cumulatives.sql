select
    nullif(trim(annee), '') as annee_financiere,
    try_to_number(nullif(trim(cumul_periode), '')) as cumul_periode,
    nullif(trim(rss), '') as rss_code,
    nullif(trim(region), '') as region,
    nullif(trim(nom_etablissement), '') as nom_etablissement,
    nullif(trim(nom_installation), '') as nom_installation,
    nullif(trim(no_permis_installation), '') as no_permis_installation,
    case
        when lower(trim(nom_installation)) = 'total provincial' then 'PROVINCIAL'
        when lower(trim(nom_installation)) = 'total régional' then 'REGIONAL'
        when lower(trim(nom_installation)) = 'total établissement' then 'ETABLISSEMENT'
        else 'INSTALLATION'
    end as niveau_agregation,
    try_to_number(nb_visites_total) as nb_visites_total,
    try_to_number(nb_usagers_75ans_et_plus_total) as nb_usagers_75ans_et_plus_total,
    try_to_number(nb_usagers_sante_mentale_total) as nb_usagers_sante_mentale_total,
    try_to_decimal(dms_total, 18, 6) as dms_total_heures,
    try_to_number(nb_usagers_pec_total) as nb_usagers_pec_total,
    try_to_decimal(delai_pec_total, 18, 6) as delai_pec_total_heures,
    try_to_number(nb_visites_ambulatoire) as nb_visites_ambulatoire,
    try_to_number(nb_usagers_75ans_et_plus_amb) as nb_usagers_75ans_et_plus_ambulatoire,
    try_to_number(nb_usagers_sante_mentale_amb) as nb_usagers_sante_mentale_ambulatoire,
    try_to_decimal(dms_ambulatoire, 18, 6) as dms_ambulatoire_heures,
    try_to_number(nb_usagers_pec_ambulatoire) as nb_usagers_pec_ambulatoire,
    try_to_decimal(delai_pec_ambulatoire, 18, 6) as delai_pec_ambulatoire_heures,
    try_to_number(nb_visites_sur_civiere) as nb_visites_sur_civiere,
    try_to_number(nb_usagers_sur_civiere_plus_24h) as nb_usagers_sur_civiere_plus_24h,
    try_to_number(nb_usagers_sur_civiere_plus_48h) as nb_usagers_sur_civiere_plus_48h,
    try_to_decimal(dms_sur_civiere, 18, 6) as dms_sur_civiere_heures,
    try_to_number(nb_usagers_pec_sur_civiere) as nb_usagers_pec_sur_civiere,
    try_to_decimal(delai_pec_sur_civiere, 18, 6) as delai_pec_sur_civiere_heures,
    try_to_number(nb_usagers_75ans_et_plus_civ) as nb_usagers_75ans_et_plus_civiere,
    try_to_number(nb_usagers_sante_mentale_civ) as nb_usagers_sante_mentale_civiere,
    source_file,
    batch_id,
    file_modified_at,
    loaded_at
from {{ source('raw', 'urgences_cumulatives') }}
