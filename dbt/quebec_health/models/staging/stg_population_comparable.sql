-- Typage de la source ISQ/MSSS; les libellés originaux restent disponibles en RAW.
select
    md5(concat_ws(
        '|',
        trim(territory_code),
        trim(reference_year),
        trim(sex),
        trim(age_label)
    )) as population_comparable_key,
    trim(geography_level) as geography_level,
    lpad(trim(territory_code), 2, '0') as region_code,
    trim(territory_name) as territory_name,
    try_to_number(reference_year) as reference_year,
    case trim(data_type)
        when 'Estimation' then 'ESTIMATE'
        when 'Projection' then 'PROJECTION'
    end as data_type,
    nullif(trim(status), '') as publication_status,
    case trim(sex)
        when 'Total' then 'TOTAL'
        when 'Masculin' then 'MALE'
        when 'Féminin' then 'FEMALE'
    end as sex_code,
    trim(age_label) as age_label,
    try_to_number(population) as population,
    source_file,
    batch_id,
    file_modified_at,
    loaded_at
from {{ source('raw', 'population_comparable') }}
