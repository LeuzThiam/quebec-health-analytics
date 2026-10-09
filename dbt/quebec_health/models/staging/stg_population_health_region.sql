select
    try_to_number(reference_year) as reference_year,
    trim(health_region_name) as health_region_name,
    right(trim(health_region_code), 2) as region_code,
    trim(peer_group_code) as peer_group_code,
    trim(age_group) as age_group,
    case trim(sex)
        when 'Total - genre' then 'TOTAL'
        when 'Hommes+' then 'MALE'
        when 'Femmes+' then 'FEMALE'
    end as sex_code,
    trim(sex) as sex_label,
    try_to_number(value) as population,
    nullif(trim(status), '') as status,
    source_file,
    batch_id,
    file_modified_at,
    loaded_at
from {{ source('raw', 'population_health_region') }}

