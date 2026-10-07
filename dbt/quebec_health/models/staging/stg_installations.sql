select
    nullif(trim(instal_cod), '') as installation_code,
    nullif(trim(instal_nom), '') as installation_nom,
    nullif(trim(etab_code), '') as etablissement_code,
    nullif(trim(etab_nom), '') as etablissement_nom,
    nullif(trim(rss_code), '') as rss_code,
    nullif(trim(rss_nom), '') as rss_nom,
    nullif(trim(mun_code), '') as municipalite_code,
    nullif(trim(mun_nom), '') as municipalite_nom,
    nullif(trim(rls_code), '') as rls_code,
    nullif(trim(rls_nom), '') as rls_nom,
    nullif(trim(ruis_code), '') as ruis_code,
    nullif(trim(ruis_nom), '') as ruis_nom,
    try_to_decimal(nullif(trim(longitude), ''), 12, 8) as longitude,
    try_to_decimal(nullif(trim(latitude), ''), 12, 8) as latitude,
    try_to_date(nullif(trim(date_maj), '')) as date_mise_a_jour,
    source_file,
    loaded_at
from {{ source('raw', 'installations') }}
