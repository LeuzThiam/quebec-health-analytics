select
    md5(age_group) as age_group_key,
    age_group as age_group_label,
    case
        when age_group = 'Total, tous les âges' then 'TOTAL'
        when age_group = 'Moins d''un an'
          or regexp_like(age_group, '^[0-9]+ ans?$') then 'SINGLE_YEAR'
        else 'STANDARD_GROUP'
    end as aggregation_level,
    case
        when age_group = 'Total, tous les âges' then null
        when age_group = 'Moins d''un an' then 0
        else try_to_number(regexp_substr(age_group, '[0-9]+', 1, 1))
    end as age_start,
    case
        when age_group = 'Total, tous les âges' then null
        when age_group = 'Moins d''un an' then 0
        when age_group = '90 ans et plus' then null
        when regexp_like(age_group, '^[0-9]+ ans?$')
            then try_to_number(regexp_substr(age_group, '[0-9]+', 1, 1))
        else try_to_number(regexp_substr(age_group, '[0-9]+', 1, 2))
    end as age_end
from {{ ref('stg_population_health_region') }}
qualify row_number() over (
    partition by age_group
    order by age_group
) = 1

