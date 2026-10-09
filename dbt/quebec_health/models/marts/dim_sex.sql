select
    md5(sex_code) as sex_key,
    sex_code,
    sex_label
from {{ ref('stg_population_health_region') }}
qualify row_number() over (
    partition by sex_code
    order by sex_label
) = 1

