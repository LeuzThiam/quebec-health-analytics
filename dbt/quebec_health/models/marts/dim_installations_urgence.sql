select
    no_permis_installation as installation_id,
    nom_installation,
    nom_etablissement,
    etablissement_code,
    rss_code,
    region,
    municipalite_code,
    municipalite_nom,
    rls_code,
    rls_nom,
    ruis_code,
    ruis_nom,
    longitude,
    latitude
from {{ ref('int_urgences_enrichies') }}
qualify row_number() over (
    partition by no_permis_installation
    order by date_heure_mise_a_jour desc, loaded_at desc
) = 1
