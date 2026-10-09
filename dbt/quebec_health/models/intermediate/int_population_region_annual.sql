-- Population totale annuelle, sans double comptage des groupes d'âge ou du sexe.
select
    md5(concat_ws('|', reference_year, region_code)) as population_region_annual_key,
    reference_year,
    md5(region_code) as region_key,
    population,
    status,
    batch_id,
    loaded_at
from {{ ref('stg_population_health_region') }}
where age_group = 'Total, tous les âges'
  and sex_code = 'TOTAL'

