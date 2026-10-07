-- Dimension région conforme, réutilisable par les futurs domaines chirurgie et population.
select
    md5(coalesce(rss_code, region)) as region_key,
    rss_code as region_code,
    region as region_name
from {{ ref('int_urgences_enrichies') }}
where coalesce(rss_code, region) is not null
qualify row_number() over (
    partition by md5(coalesce(rss_code, region))
    order by snapshot_at desc, loaded_at desc
) = 1
