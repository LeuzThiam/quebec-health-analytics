select *
from {{ ref('fct_urgences_cumulatives') }}
where coalesce(nb_visites_total, 0) < 0
   or coalesce(nb_visites_ambulatoire, 0) < 0
   or coalesce(nb_visites_sur_civiere, 0) < 0
   or coalesce(nb_usagers_sur_civiere_plus_24h, 0) < 0
   or coalesce(nb_usagers_sur_civiere_plus_48h, 0) < 0
