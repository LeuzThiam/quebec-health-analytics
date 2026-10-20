-- Une ligne retournée indique une mesure démographique impossible ou très improbable.
select *
from {{ ref('agg_population_demography_region') }}
where population_total < 0
   or population_65_plus < 0
   or population_65_plus > population_total
   or share_65_plus_pct not between 0 and 100
   or population_growth_pct not between -50 and 100
