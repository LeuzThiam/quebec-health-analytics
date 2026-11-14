{{ config(severity='warn') }}

-- Rend visibles les territoires présents dans une seule des deux sources.
select *
from {{ ref('region_crosswalk') }}
where match_status <> 'MATCHED'
