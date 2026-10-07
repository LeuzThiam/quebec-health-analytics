-- Les groupes 48 h+ et 24 h+ sont inclus dans le nombre de patients sur civière.
select *
from {{ ref('fct_urgences_horaires') }}
where nombre_patients_civiere_plus_48h > nombre_patients_civiere_plus_24h
   or nombre_patients_civiere_plus_24h > nombre_civieres_occupees

