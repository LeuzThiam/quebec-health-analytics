"""Configuration du pipeline d'ingestion à partir des variables d'environnement."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


_IDENTIFIER_PATTERN = re.compile(r"^[A-Z][A-Z0-9_$]*$")


@dataclass(frozen=True)
class SnowflakeSettings:
    account: str
    user: str
    password: str
    warehouse: str = "HEALTH_ELT_WH"
    database: str = "QUEBEC_HEALTH_DWH"
    role: str = "QUEBEC_HEALTH_INGESTION"

    @classmethod
    def from_environment(cls) -> "SnowflakeSettings":
        required = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Variables Snowflake manquantes : " + ", ".join(missing)
            )

        settings = cls(
            account=required["account"],
            user=required["user"],
            password=required["password"],
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "HEALTH_ELT_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "QUEBEC_HEALTH_DWH"),
            role=os.getenv("SNOWFLAKE_ROLE", "QUEBEC_HEALTH_INGESTION"),
        )
        for value in (settings.warehouse, settings.database, settings.role):
            if not _IDENTIFIER_PATTERN.fullmatch(value):
                raise ValueError(f"Identifiant Snowflake invalide : {value}")
        return settings
