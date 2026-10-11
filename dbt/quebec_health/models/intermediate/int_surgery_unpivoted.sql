-- Une ligne par période, région, délai et spécialité.
select
    financial_period,
    wait_bucket,
    region_code,
    specialty_code,
    replace(initcap(replace(specialty_code, '_', ' ')), 'Orl', 'ORL')
        as specialty_name,
    patients_waiting,
    batch_id,
    loaded_at
from {{ ref('stg_surgery_waitlist') }}
unpivot include nulls (
    patients_waiting for specialty_code in (
        chirurgie_generale,
        chirurgie_orthopedique,
        chirurgie_plastique,
        chirurgie_vasculaire,
        neurochirurgie,
        obstetrique_gynecologie,
        ophtalmologie,
        orl_chirurgie_cervico_faciale,
        urologie,
        autres
    )
)
