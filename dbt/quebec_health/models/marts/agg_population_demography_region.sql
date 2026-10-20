-- Indicateurs démographiques annuels destinés à l'analyse régionale.
with regional_population as (
    select
        region_code,
        reference_year,
        data_type,
        max(case when age_label = 'TousLesAges' then population end) as population_total,
        sum(case
            when try_to_number(age_label) >= 65 or age_label = '90ansOuPlus'
                then population
            else 0
        end) as population_65_plus
    from {{ ref('stg_population_comparable') }}
    where sex_code = 'TOTAL'
    group by region_code, reference_year, data_type
),

with_growth as (
    select
        *,
        lag(population_total) over (
            partition by region_code
            order by reference_year
        ) as previous_year_population
    from regional_population
)

select
    md5(concat_ws('|', crosswalk.region_code, population.reference_year))
        as population_demography_region_key,
    crosswalk.region_key,
    crosswalk.region_code,
    coalesce(crosswalk.msss_region_name, crosswalk.population_region_name)
        as region_name,
    crosswalk.match_status,
    population.reference_year,
    population.data_type,
    population.population_total,
    population.population_65_plus,
    round(
        100.0 * population.population_65_plus
        / nullif(population.population_total, 0),
        2
    ) as share_65_plus_pct,
    round(
        100.0 * (population.population_total - population.previous_year_population)
        / nullif(population.previous_year_population, 0),
        2
    ) as population_growth_pct
from with_growth as population
inner join {{ ref('region_crosswalk') }} as crosswalk
    on population.region_code = crosswalk.population_region_code
