# Québec Health Analytics Platform

Plateforme ELT consacrée à l'analyse de la pression sur les urgences, des délais d'accès aux chirurgies et des différences régionales du système de santé québécois.

## Périmètre

Le projet intègre cinq jeux de données publics :

- situation horaire des urgences du MSSS;
- données cumulatives des urgences;
- listes d'attente en chirurgie;
- référentiel des installations du réseau de la santé;
- population par région de santé de Statistique Canada;
- estimations et projections de population comparables de l'ISQ/MSSS,
  diffusées par Données Québec sous licence CC-BY 4.0.

Les données sont institutionnelles et agrégées. Le projet ne contient aucun renseignement médical personnel.

## Architecture

```text
Sources publiques
      ↓
Ingestion et validation Python
      ↓
Snowflake RAW et journal d'audit
      ↓
dbt STAGING → INTERMEDIATE → MARTS
      ↓
Power BI
```

Python télécharge et valide les fichiers, calcule une empreinte SHA-256 et charge les nouvelles versions dans Snowflake. Le mécanisme d'idempotence empêche le rechargement d'un fichier déjà traité.

dbt normalise les données, applique les règles métier et construit un modèle dimensionnel comprenant notamment les faits d'urgences, de chirurgie et de population. Les marts produisent des indicateurs provinciaux, régionaux et par habitant destinés à Power BI.

## Technologies

- Python, Pandas et Jupyter Notebook
- Snowflake
- dbt Core et dbt-snowflake
- SQL
- Power BI
- Git, GitHub et GitHub Actions

## Modèle analytique

Les principaux objets de la couche `MARTS` sont :

- `FCT_URGENCES_HORAIRES` et `FCT_URGENCES_CUMULATIVES`;
- `FCT_SURGERY_WAITLIST`;
- `FCT_POPULATION_ANNUAL`;
- les dimensions de date, heure, région, installation, spécialité et délai;
- les agrégats quotidiens, régionaux, chirurgicaux et démographiques.

Les tests dbt contrôlent les clés, les relations, les valeurs obligatoires, la granularité et la cohérence des mesures. Un modèle de supervision expose également la fraîcheur des cinq sources.

## Tableau de bord

Le rapport Power BI, conservé localement pour éviter de publier un fichier
binaire contenant des données mises en cache, présente actuellement :

- une vue provinciale de la pression sur les urgences;
- une comparaison des taux d'occupation par région;
- une analyse des listes d'attente en chirurgie.

## Installation locale

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Les données téléchargées sont conservées dans `data/` et ne sont pas versionnées.

## Exécution dbt

Les paramètres Snowflake sont fournis par des variables d'environnement. Aucun secret n'est conservé dans le dépôt.

```powershell
.\venv\Scripts\dbt.exe debug `
    --project-dir .\dbt\quebec_health `
    --profiles-dir .\dbt\quebec_health

.\venv\Scripts\dbt.exe build `
    --project-dir .\dbt\quebec_health `
    --profiles-dir .\dbt\quebec_health
```

## Automatisation horaire

L'ingestion des urgences horaires et les transformations dbt peuvent être lancées depuis Windows :

```powershell
.\automation\run_hourly_pipeline.ps1
```

Initialisation de la configuration locale sécurisée :

```powershell
.\automation\run_hourly_pipeline.ps1 -Initialize
```

Installation de la tâche planifiée pour une session Windows sans mot de passe :

```powershell
.\automation\run_hourly_pipeline.ps1 -InstallScheduledTask -RunOnlyWhenLoggedOn
```

Les journaux d'exécution sont enregistrés dans `%LOCALAPPDATA%\QuebecHealthAnalytics\logs`.

### Exécution dans GitHub Actions

La CI valide la syntaxe Python et PowerShell ainsi que le projet dbt à chaque pull request concernée. Elle ne charge aucune donnée et n'utilise aucun secret de production.

### Limite de couverture

Le MSSS ne publie que l'état courant des urgences, sans historique : une heure non capturée est définitivement perdue. La tâche Windows s'exécute à `HH:45`, empêche les exécutions concurrentes et reprend dès que possible après une indisponibilité. Un ordinateur éteint pendant plusieurs heures crée néanmoins un trou de couverture.

## Méthode de développement

Le développement suit un flux Git structuré : branche fonctionnelle, pull request vers `develop`, contrôles automatisés, puis publication planifiée vers `main`. Les changements ne sont pas développés directement sur la branche de production.
