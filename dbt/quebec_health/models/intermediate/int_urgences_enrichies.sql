with urgences as (
    select
        *,
        round(
            100.0 * nombre_civieres_occupees / nullif(nombre_civieres_fonctionnelles, 0),
            2
        ) as taux_occupation_pct
    from {{ ref('stg_urgences_horaires') }}
    where niveau_agregation = 'INSTALLATION'
)

select
    urgence.date_heure_mise_a_jour,
    urgence.heure_extraction,
    coalesce(
        timestamp_ntz_from_parts(urgence.date_heure_mise_a_jour::date, urgence.heure_extraction),
        urgence.date_heure_mise_a_jour
    ) as snapshot_at,
    urgence.rss_code,
    urgence.region,
    urgence.no_permis_installation,
    urgence.nom_installation,
    urgence.nom_etablissement,
    installation.etablissement_code,
    installation.municipalite_code,
    installation.municipalite_nom,
    installation.rls_code,
    installation.rls_nom,
    installation.ruis_code,
    installation.ruis_nom,
    installation.longitude,
    installation.latitude,
    urgence.nombre_civieres_fonctionnelles,
    urgence.nombre_civieres_occupees,
    urgence.nombre_patients_civiere_plus_24h,
    urgence.nombre_patients_civiere_plus_48h,
    urgence.nombre_patients_presents,
    urgence.nombre_patients_attente_pec,
    urgence.dms_civiere_heures,
    urgence.dms_ambulatoire_heures,
    urgence.taux_occupation_pct,
    case
        when urgence.taux_occupation_pct is null then 'NON_CALCULABLE'
        when urgence.taux_occupation_pct > 100 then 'SURCAPACITE'
        when urgence.taux_occupation_pct >= 90 then 'ELEVE'
        else 'NORMAL'
    end as niveau_occupation,
    urgence.source_file,
    urgence.loaded_at
from urgences as urgence
left join {{ ref('stg_installations') }} as installation
    on urgence.no_permis_installation = installation.installation_code
