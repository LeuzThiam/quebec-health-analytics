USE ROLE ACCOUNTADMIN;

CREATE WAREHOUSE IF NOT EXISTS HEALTH_ELT_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse ELT de la plateforme Quebec Health Analytics';

CREATE DATABASE IF NOT EXISTS QUEBEC_HEALTH_DWH
    COMMENT = 'Plateforme analytique des donnees de sante du Quebec';

CREATE SCHEMA IF NOT EXISTS QUEBEC_HEALTH_DWH.RAW
    COMMENT = 'Donnees sources conservees au plus pres du format publie';

CREATE SCHEMA IF NOT EXISTS QUEBEC_HEALTH_DWH.STAGING
    COMMENT = 'Normalisation technique des donnees sources';

CREATE SCHEMA IF NOT EXISTS QUEBEC_HEALTH_DWH.INTERMEDIATE
    COMMENT = 'Regles et assemblages intermediaires';

CREATE SCHEMA IF NOT EXISTS QUEBEC_HEALTH_DWH.MARTS
    COMMENT = 'Modeles destines aux usages analytiques';

CREATE SCHEMA IF NOT EXISTS QUEBEC_HEALTH_DWH.AUDIT
    COMMENT = 'Tracabilite des executions et controles';
