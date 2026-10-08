"""Chargement idempotent du fichier cumulatif vers Snowflake."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

import snowflake.connector

from config import SnowflakeSettings
from cumulative_download import CumulativeFile


SOURCE_SYSTEM = "MSSS"
SOURCE_DATASET = "EMERGENCY_CUMULATIVE"


def load_cumulative_file(file: CumulativeFile, settings: SnowflakeSettings) -> str:
    """Charge le fichier une seule fois et journalise le lot dans AUDIT."""
    run_id = str(uuid4())
    batch_id = f"EMERG_CUMUL_{file.sha256.upper()}"
    database = settings.database
    stage = f"@{database}.RAW.HEALTH_SOURCE_FILES"
    table = f"{database}.RAW.URGENCES_CUMULATIVES_RAW"
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
        # La ressource cumulative republie un instantané complet. Une nouvelle
        # version remplace donc le contenu précédent afin qu'une correction du
        # MSSS ne duplique pas une granularité métier sous un autre lot.
        cursor.execute(f"DELETE FROM {table}")

        modified_at = (file.modified_at or datetime.now(timezone.utc)).isoformat()
        raw_columns = ", ".join(column.upper() for column in (
            "annee", "cumul_periode", "rss", "region", "nom_etablissement",
            "nom_installation", "no_permis_installation", "nb_visites_total",
            "nb_usagers_75ans_et_plus_total", "nb_usagers_sante_mentale_total",
            "dms_total", "nb_usagers_pec_total", "delai_pec_total",
            "nb_visites_ambulatoire", "nb_usagers_75ans_et_plus_amb",
            "nb_usagers_sante_mentale_amb", "dms_ambulatoire",
            "nb_usagers_pec_ambulatoire", "delai_pec_ambulatoire",
            "nb_visites_sur_civiere", "nb_usagers_sur_civiere_plus_24h",
            "nb_usagers_sur_civiere_plus_48h", "dms_sur_civiere",
            "nb_usagers_pec_sur_civiere", "delai_pec_sur_civiere",
            "nb_usagers_75ans_et_plus_civ", "nb_usagers_sante_mentale_civ",
        ))
        source_fields = ", ".join(f"${index}" for index in range(1, 28))
        copy_sql = f"""
            COPY INTO {table} (
                {raw_columns}, SOURCE_FILE, BATCH_ID, FILE_MODIFIED_AT
            )
            FROM (
                SELECT {source_fields}, METADATA$FILENAME, '{batch_id}',
                       TO_TIMESTAMP_TZ('{modified_at}')
                FROM '{staged_file}'
            )
            FILE_FORMAT = (FORMAT_NAME = '{database}.RAW.CSV_URGENCES_CUMUL_UTF8')
            ON_ERROR = 'ABORT_STATEMENT'
            FORCE = TRUE
        """
        cursor.execute(copy_sql)
        rows_loaded = int(cursor.fetchone()[3])

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
