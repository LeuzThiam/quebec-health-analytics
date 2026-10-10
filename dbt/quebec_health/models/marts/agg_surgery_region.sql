with surgery_by_region as (
    select
        fact.financial_period,
        2000 + try_to_number(left(fact.financial_period, 2)) as financial_year_start,
        fact.region_key,
        sum(coalesce(fact.patients_waiting, 0)) as patients_waiting,
        sum(case when bucket.display_order = 1 then coalesce(fact.patients_waiting, 0) else 0 end)
            as patients_waiting_0_6_months,
        sum(case when bucket.display_order = 2 then coalesce(fact.patients_waiting, 0) else 0 end)
            as patients_waiting_6_12_months,
        sum(case when bucket.display_order = 3 then coalesce(fact.patients_waiting, 0) else 0 end)
            as patients_waiting_over_12_months
    from {{ ref('fct_surgery_waitlist') }} as fact
    inner join {{ ref('dim_wait_bucket') }} as bucket
        on fact.wait_bucket_key = bucket.wait_bucket_key
    group by fact.financial_period, fact.region_key
),

matched_population as (
    select
        surgery.*,
        population.reference_year as population_reference_year,
        population.population,
        row_number() over (
            partition by surgery.financial_period, surgery.region_key
            order by population.reference_year desc
        ) as population_rank
    from surgery_by_region as surgery
    left join {{ ref('int_population_region_annual') }} as population
        on surgery.region_key = population.region_key
       and population.reference_year <= surgery.financial_year_start
)

select
    md5(concat_ws('|', financial_period, region_key)) as surgery_region_period_key,
    financial_period,
    financial_year_start,
    region_key,
    population_reference_year,
    population,
    patients_waiting,
    patients_waiting_0_6_months,
    patients_waiting_6_12_months,
    patients_waiting_over_12_months,
    round(
        100.0 * patients_waiting_over_12_months / nullif(patients_waiting, 0),
        2
    ) as share_waiting_over_12_months_pct,
    round(100000.0 * patients_waiting / nullif(population, 0), 2)
        as patients_waiting_per_100k
from matched_population
where population_rank = 1
