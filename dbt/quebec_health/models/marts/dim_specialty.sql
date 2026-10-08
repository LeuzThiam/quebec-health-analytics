select
    md5(specialty_code) as specialty_key,
    specialty_code,
    specialty_name
from {{ ref('int_surgery_unpivoted') }}
qualify row_number() over (
    partition by specialty_code
    order by specialty_name
) = 1
