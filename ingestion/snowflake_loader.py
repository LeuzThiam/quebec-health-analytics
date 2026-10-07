"""Chargement idempotent des fichiers validés vers Snowflake."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

import snowflake.connector

from config import SnowflakeSettings
from download import DownloadedFile


SOURCE_SYSTEM = "MSSS"
SOURCE_DATASET = "EMERGENCY_HOURLY"


def load_emergency_file(file: DownloadedFile, settings: SnowflakeSettings) -> str:
    """Charge un fichier une seule fois et journalise le résultat dans AUDIT."""
    run_id = str(uuid4())
    batch_id = f"EMERG_{file.sha256.upper()}"
    database = settings.database
    stage = f"@{database}.RAW.HEALTH_SOURCE_FILES"
    table = f"{database}.RAW.URGENCES_HORAIRES_RAW"
    audit_table = f"{database}.AUDIT.INGESTION_RUN"

    connection_parameters = dict(
        account=settings.account,
        user=settings.user,
        authenticator=settings.authenticator,
        warehouse=settings.warehouse,
        database=database,
        role=settings.role,
    )
    if settings.password:
        connection_parameters["password"] = settings.password
    connection = snowflake.connector.connect(**connection_parameters)
    connection.autocommit(False)
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"SELECT COUNT(*) FROM {audit_table} "
            "WHERE SOURCE_DATASET = %s AND SOURCE_SHA256 = %s AND STATUS = 'SUCCESS'",
            (SOURCE_DATASET, file.sha256),
        )
        if cursor.fetchone()[0] > 0:
            connection.rollback()
            return "SKIPPED_ALREADY_LOADED"

        cursor.execute(
            f"INSERT INTO {audit_table} "
            "(RUN_ID, BATCH_ID, SOURCE_SYSTEM, SOURCE_DATASET, SOURCE_FILE, "
            "SOURCE_SHA256, STARTED_AT, ROWS_RECEIVED, STATUS) "
            "SELECT %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), %s, 'RUNNING'",
            (
                run_id,
                batch_id,
                SOURCE_SYSTEM,
                SOURCE_DATASET,
                file.path.name,
                file.sha256,
                file.row_count,
            ),
        )

        current_sha256 = hashlib.sha256(file.path.read_bytes()).hexdigest()
        if current_sha256 != file.sha256:
            raise RuntimeError("Le fichier a changé après sa validation.")

        file_uri = file.path.resolve().as_posix().replace("'", "''")
        staged_directory = f"{stage}/{file.sha256}"
        staged_file = f"{staged_directory}/{file.path.name}"
        quoted_staged_file = staged_file.replace("'", "''")
        cursor.execute(
            f"PUT 'file://{file_uri}' {staged_directory} "
            "AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        )

        # Le lot est déterministe. Un nouvel essai remplace donc un éventuel lot
        # incomplet au lieu d'ajouter une deuxième copie des mêmes observations.
        cursor.execute(f"DELETE FROM {table} WHERE BATCH_ID = %s", (batch_id,))

        modified_at = (file.modified_at or datetime.now(timezone.utc)).isoformat()
        copy_sql = f"""
            COPY INTO {table} (
                RSS, REGION, NOM_ETABLISSEMENT, NOM_INSTALLATION,
                NO_PERMIS_INSTALLATION, NOMBRE_DE_CIVIERES_FONCTIONNELLES,
                NOMBRE_DE_CIVIERES_OCCUPEES,
                NOMBRE_DE_PATIENTS_SUR_CIVIERE_PLUS_DE_24_HEURES,
                NOMBRE_DE_PATIENTS_SUR_CIVIERE_PLUS_DE_48_HEURES,
                NOMBRE_TOTAL_DE_PATIENTS_PRESENTS_A_LURGENCE,
                NOMBRE_TOTAL_DE_PATIENTS_EN_ATTENTE_DE_PEC,
                DMS_SUR_CIVIERE, DMS_AMBULATOIRE, DMS_SUR_CIVIERE_HORAIRE,
                DMS_AMBULATOIRE_HORAIRE, HEURE_EXTRACTION_IMAGE, MISE_A_JOUR,
                SOURCE_FILE, BATCH_ID, FILE_MODIFIED_AT
            )
            FROM (
                SELECT $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                       $12, $13, $14, $15, $16, $17,
                       METADATA$FILENAME, '{batch_id}',
                       TO_TIMESTAMP_TZ('{modified_at}')
                FROM '{quoted_staged_file}'
            )
            FILE_FORMAT = (FORMAT_NAME = '{database}.RAW.CSV_URGENCES_CP1252')
            ON_ERROR = 'ABORT_STATEMENT'
            FORCE = TRUE
        """
        cursor.execute(copy_sql)
        copy_result = cursor.fetchone()
        rows_loaded = int(copy_result[3])

        cursor.execute(
            f"UPDATE {audit_table} SET COMPLETED_AT = CURRENT_TIMESTAMP(), "
            "ROWS_LOADED = %s, ROWS_REJECTED = %s, STATUS = 'SUCCESS' "
            "WHERE RUN_ID = %s",
            (rows_loaded, file.row_count - rows_loaded, run_id),
        )
        connection.commit()
        return batch_id
    except Exception as error:
        connection.rollback()
        try:
            cursor.execute(
                f"INSERT INTO {audit_table} "
                "(RUN_ID, BATCH_ID, SOURCE_SYSTEM, SOURCE_DATASET, SOURCE_FILE, "
                "SOURCE_SHA256, STARTED_AT, COMPLETED_AT, ROWS_RECEIVED, "
                "STATUS, ERROR_MESSAGE) "
                "SELECT %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP(), "
                "CURRENT_TIMESTAMP(), %s, 'FAILED', %s",
                (
                    run_id,
                    batch_id,
                    SOURCE_SYSTEM,
                    SOURCE_DATASET,
                    file.path.name,
                    file.sha256,
                    file.row_count,
                    str(error)[:5000],
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
        raise
    finally:
        connection.close()
