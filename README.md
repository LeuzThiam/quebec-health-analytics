# Québec Health Analytics Platform

Plateforme de données destinée à analyser la pression sur les urgences, l'accès aux chirurgies et les différences régionales du système de santé québécois.

## État actuel

Le projet dispose maintenant d'un pipeline analytique fonctionnel à partir de trois jeux de données officiels du MSSS :

- la situation horaire dans les urgences;
- l'historique cumulatif des urgences par période financière;
- le référentiel M02 des installations.

Les notebooks valident la structure des fichiers, leur qualité et la relation entre les numéros de permis des installations. Snowflake assure ensuite la transformation des données selon les couches `RAW`, `STAGING`, `INTERMEDIATE` et `MARTS`.

La couche analytique contient une dimension des installations, une table de faits des urgences horaires, une table de faits cumulative et un mart régional. Elle permet d'analyser la pression actuelle ainsi que son évolution sur plusieurs années financières.

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

Installation unique de l'exécution automatique toutes les heures :

```powershell
.\automation\run_hourly_pipeline.ps1 -InstallScheduledTask
```

Windows demande alors le mot de passe du compte local afin d'autoriser l'exécution même lorsque la session est fermée. Ce mot de passe est transmis uniquement au Planificateur de tâches Windows et n'est pas enregistré dans le projet.

Pour un compte Windows sans mot de passe, installer plutôt la tâche en mode session ouverte :

```powershell
.\automation\run_hourly_pipeline.ps1 -InstallScheduledTask -RunOnlyWhenLoggedOn
```

Dans ce mode, aucun mot de passe Windows n'est demandé. La tâche s'exécute uniquement lorsque l'utilisateur est connecté.

Exécution complète de l'ingestion et des transformations dbt :

```powershell
.\automation\run_hourly_pipeline.ps1
```

Les journaux d'exécution sont conservés dans `%LOCALAPPDATA%\QuebecHealthAnalytics\logs`.

Le fichier cumulatif évolue par période financière et reste volontairement séparé de la tâche horaire. Son ingestion se lance au besoin avec :

```powershell
.\venv\Scripts\python.exe .\ingestion\emergency_cumulative.py
```
