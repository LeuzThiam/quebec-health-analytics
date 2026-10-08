select
    md5(concat_ws(
        '|',
        financial_period,
        region_code,
        wait_bucket,
        specialty_code
    )) as surgery_waitlist_key,
    financial_period,
    md5(regexp_replace(region_code, '^RSS', '')) as region_key,
    md5(specialty_code) as specialty_key,
    md5(wait_bucket) as wait_bucket_key,
    patients_waiting,
    batch_id,
    loaded_at
from {{ ref('int_surgery_unpivoted') }}
