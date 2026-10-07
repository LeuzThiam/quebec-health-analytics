-- Les mesures opérationnelles publiées ne doivent jamais être négatives.
select *
from {{ ref('fct_urgences_horaires') }}
where nombre_civieres_fonctionnelles < 0
   or nombre_civieres_occupees < 0
   or nombre_patients_civiere_plus_24h < 0
   or nombre_patients_civiere_plus_48h < 0
   or nombre_patients_presents < 0
   or nombre_patients_attente_pec < 0
