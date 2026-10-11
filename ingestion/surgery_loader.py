"""Chargement idempotent des listes d'attente en chirurgie vers Snowflake."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

import snowflake.connector

from config import SnowflakeSettings
from surgery_download import SurgeryFile


SOURCE_SYSTEM = "MSSS"
SOURCE_DATASET = "SURGERY_WAITLIST"


def load_surgery_file(file: SurgeryFile, settings: SnowflakeSettings) -> str:
    """Remplace le snapshot RAW et journalise le chargement."""
    run_id = str(uuid4())
    batch_id = f"SURGERY_{file.sha256.upper()}"
    database = settings.database
    stage = f"@{database}.RAW.HEALTH_SOURCE_FILES"
    table = f"{database}.RAW.SURGERY_WAITLIST_RAW"
    audit_table = f"{database}.AUDIT.INGESTION_RUN"

    parameters = dict(
        account=settings.account,
        user=settings.user,
        authenticator=settings.authenticator,
        warehouse=settings.warehouse,
        database=database,
        role=settings.role,
    )
    if settings.password:
        parameters["password"] = settings.password

    connection = snowflake.connector.connect(**parameters)
    connection.autocommit(False)
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"SELECT COUNT(*) FROM {audit_table} "
            "WHERE SOURCE_DATASET = %s AND SOURCE_SHA256 = %s AND STATUS = 'SUCCESS' "
            f"AND EXISTS (SELECT 1 FROM {table} WHERE BATCH_ID = %s)",
            (SOURCE_DATASET, file.sha256, batch_id),
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

        if hashlib.sha256(file.path.read_bytes()).hexdigest() != file.sha256:
            raise RuntimeError("Le fichier a changé après sa validation.")

        file_uri = file.path.resolve().as_posix().replace("'", "''")
        staged_directory = f"{stage}/{file.sha256}"
        staged_file = f"{staged_directory}/{file.path.name}".replace("'", "''")
        cursor.execute(
            f"PUT 'file://{file_uri}' {staged_directory} "
            "AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        )
        cursor.execute(f"DELETE FROM {table}")

        modified_at = (file.modified_at or datetime.now(timezone.utc)).isoformat()
        raw_columns = (
            "PERIODE_ATTENTE, DELAI_ATTENTE, REGION, CHIRURGIE_GENERALE, "
            "CHIRURGIE_ORTHOPEDIQUE, CHIRURGIE_PLASTIQUE, CHIRURGIE_VASCULAIRE, "
            "NEUROCHIRURGIE, OBSTETRIQUE_GYNECOLOGIE, OPHTALMOLOGIE, "
            "ORL_CHIRURGIE_CERVICO_FACIALE, UROLOGIE, AUTRES, TOTAL"
        )
        source_fields = ", ".join(f"${index}" for index in range(1, 15))
        cursor.execute(
            f"""
            COPY INTO {table} (
                {raw_columns}, SOURCE_FILE, BATCH_ID, FILE_MODIFIED_AT
            )
            FROM (
                SELECT {source_fields}, METADATA$FILENAME, '{batch_id}',
                       TO_TIMESTAMP_TZ('{modified_at}')
                FROM '{staged_file}'
            )
            FILE_FORMAT = (FORMAT_NAME = '{database}.RAW.CSV_SURGERY_UTF8')
            ON_ERROR = 'ABORT_STATEMENT'
            FORCE = TRUE
            """
        )
        rows_loaded = int(cursor.fetchone()[3])
        if rows_loaded != file.row_count:
            raise RuntimeError(
                f"Nombre de lignes chargé inattendu : {rows_loaded}/{file.row_count}."
            )

        cursor.execute(
            f"UPDATE {audit_table} SET COMPLETED_AT = CURRENT_TIMESTAMP(), "
            "ROWS_LOADED = %s, ROWS_REJECTED = 0, STATUS = 'SUCCESS' "
            "WHERE RUN_ID = %s",
            (rows_loaded, run_id),
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
