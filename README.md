# Québec Health Analytics Platform

Plateforme de données destinée à analyser la pression sur les urgences, l'accès aux chirurgies et les différences régionales du système de santé québécois.

## État actuel

Le projet dispose maintenant d'un premier pipeline analytique fonctionnel à partir de deux jeux de données officiels du MSSS :

- la situation horaire dans les urgences;
- le référentiel M02 des installations.

Les notebooks valident la structure des fichiers, leur qualité et la relation entre les numéros de permis des installations. Snowflake assure ensuite la transformation des données selon les couches `RAW`, `STAGING`, `INTERMEDIATE` et `MARTS`.

La couche analytique contient une dimension des installations, une table de faits des urgences horaires et un mart régional. Les requêtes du tableau de bord présentent les indicateurs globaux, le classement des régions et les installations qui demandent une attention prioritaire.

L'environnement Snowflake de développement utilise la base `QUEBEC_HEALTH_DWH` et un warehouse `X-SMALL` configuré pour s'arrêter automatiquement après 60 secondes d'inactivité.

## Exécuter les notebooks

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m jupyter lab
```

Les fichiers téléchargés sont conservés localement dans `data/exploration` et ne sont pas versionnés.

## Automatisation locale

L'ingestion horaire s'exécute depuis Windows, car le serveur source du MSSS refuse les téléchargements provenant des runners GitHub. La configuration Snowflake est enregistrée hors du dépôt et le mot de passe est chiffré par Windows pour l'utilisateur courant.

Initialisation unique :

```powershell
.\automation\run_hourly_pipeline.ps1 -Initialize
```

Exécution complète de l'ingestion et des transformations dbt :

```powershell
.\automation\run_hourly_pipeline.ps1
```

Les journaux d'exécution sont conservés dans `%LOCALAPPDATA%\QuebecHealthAnalytics\logs`.
