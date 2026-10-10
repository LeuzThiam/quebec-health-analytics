select
    md5(concat_ws('|', fact.financial_period, fact.specialty_key)) as surgery_specialty_period_key,
    fact.financial_period,
    fact.specialty_key,
    sum(coalesce(fact.patients_waiting, 0)) as patients_waiting,
    sum(case when bucket.display_order = 1 then coalesce(fact.patients_waiting, 0) else 0 end)
        as patients_waiting_0_6_months,
    sum(case when bucket.display_order = 2 then coalesce(fact.patients_waiting, 0) else 0 end)
        as patients_waiting_6_12_months,
    sum(case when bucket.display_order = 3 then coalesce(fact.patients_waiting, 0) else 0 end)
        as patients_waiting_over_12_months,
    round(
        100.0
        * sum(case when bucket.display_order = 3 then coalesce(fact.patients_waiting, 0) else 0 end)
        / nullif(sum(coalesce(fact.patients_waiting, 0)), 0),
        2
    ) as share_waiting_over_12_months_pct
from {{ ref('fct_surgery_waitlist') }} as fact
inner join {{ ref('dim_wait_bucket') }} as bucket
    on fact.wait_bucket_key = bucket.wait_bucket_key
group by fact.financial_period, fact.specialty_key
