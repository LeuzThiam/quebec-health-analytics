-- Correspondance explicite des codes RSS; aucune jointure n'est faite sur un nom.
with msss_regions as (
    select
        rss_code as msss_region_code,
        region as msss_region_name
    from {{ ref('int_urgences_enrichies') }}
    where rss_code is not null
    qualify row_number() over (
        partition by rss_code
        order by snapshot_at desc
    ) = 1
),

population_regions as (
    select
        region_code as population_region_code,
        territory_name as population_region_name
    from {{ ref('stg_population_comparable') }}
    where region_code is not null
    qualify row_number() over (
        partition by region_code
        order by reference_year desc
    ) = 1
)

select
    md5(coalesce(msss.msss_region_code, population.population_region_code)) as region_key,
    coalesce(msss.msss_region_code, population.population_region_code) as region_code,
    msss.msss_region_code,
    msss.msss_region_name,
    population.population_region_code,
    population.population_region_name,
    case
        when msss.msss_region_code is not null
            and population.population_region_code is not null then 'MATCHED'
        when msss.msss_region_code is not null then 'MSSS_ONLY'
        else 'POPULATION_ONLY'
    end as match_status
from msss_regions as msss
full outer join population_regions as population
    on msss.msss_region_code = population.population_region_code
