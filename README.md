# Québec Health Analytics Platform

Plateforme de données destinée à analyser la pression sur les urgences, l'accès aux chirurgies et les différences régionales du système de santé québécois.

## État actuel

Le projet est dans sa phase d'exploration des sources. Deux jeux de données officiels du MSSS sont actuellement étudiés :

- la situation horaire dans les urgences;
- le référentiel M02 des installations.

Les notebooks valident la structure des fichiers, leur qualité et la relation entre les numéros de permis des installations.

## Exécuter les notebooks

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m jupyter lab
```

Les fichiers téléchargés sont conservés localement dans `data/exploration` et ne sont pas versionnés.
