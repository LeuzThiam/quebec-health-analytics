select
    md5(wait_bucket) as wait_bucket_key,
    wait_bucket,
    case wait_bucket
        when '0 à 6 mois' then 1
        when '6 à 12 mois' then 2
        when 'Plus d''1 an' then 3
        else 99
    end as display_order
from {{ ref('stg_surgery_waitlist') }}
qualify row_number() over (
    partition by wait_bucket
    order by wait_bucket
) = 1
