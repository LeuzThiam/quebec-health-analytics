"""Chargement idempotent des fichiers validés vers Snowflake."""

from __future__ import annotations

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
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    batch_id = f"EMERG_{timestamp}_{file.sha256[:8].upper()}"
    database = settings.database
    stage = f"@{database}.RAW.HEALTH_SOURCE_FILES"
    table = f"{database}.RAW.URGENCES_HORAIRES_RAW"
    audit_table = f"{database}.AUDIT.INGESTION_RUN"

    connection = snowflake.connector.connect(
        account=settings.account,
        user=settings.user,
        password=settings.password,
        warehouse=settings.warehouse,
        database=database,
        role=settings.role,
    )
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"SELECT COUNT(*) FROM {audit_table} "
            "WHERE SOURCE_DATASET = %s AND SOURCE_SHA256 = %s AND STATUS = 'SUCCESS'",
            (SOURCE_DATASET, file.sha256),
        )
        if cursor.fetchone()[0] > 0:
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

        file_uri = file.path.resolve().as_posix().replace("'", "''")
        cursor.execute(f"PUT 'file://{file_uri}' {stage} AUTO_COMPRESS=FALSE OVERWRITE=TRUE")

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
                FROM {stage}/{file.path.name}
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
                f"UPDATE {audit_table} SET COMPLETED_AT = CURRENT_TIMESTAMP(), "
                "STATUS = 'FAILED', ERROR_MESSAGE = %s WHERE RUN_ID = %s",
                (str(error)[:5000], run_id),
            )
            connection.commit()
        except Exception:
            connection.rollback()
        raise
    finally:
        connection.close()
