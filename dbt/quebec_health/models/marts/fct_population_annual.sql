select
    md5(concat_ws(
        '|',
        reference_year,
        region_code,
        age_group,
        sex_code
    )) as population_annual_key,
    reference_year,
    md5(region_code) as region_key,
    md5(age_group) as age_group_key,
    md5(sex_code) as sex_key,
    peer_group_code,
    population,
    status,
    source_file,
    batch_id,
    file_modified_at,
    loaded_at
from {{ ref('stg_population_health_region') }}

