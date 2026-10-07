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
    password: str | None = None
    authenticator: str = "externalbrowser"
    warehouse: str = "HEALTH_ELT_WH"
    database: str = "QUEBEC_HEALTH_DWH"
    role: str = "QUEBEC_HEALTH_INGESTION"

    @classmethod
    def from_environment(cls) -> "SnowflakeSettings":
        required = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Variables Snowflake manquantes : " + ", ".join(missing)
            )

        password = os.getenv("SNOWFLAKE_PASSWORD") or None
        authenticator = os.getenv("SNOWFLAKE_AUTHENTICATOR") or (
            "snowflake" if password else "externalbrowser"
        )
        settings = cls(
            account=required["account"],
            user=required["user"],
            password=password,
            authenticator=authenticator,
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "HEALTH_ELT_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "QUEBEC_HEALTH_DWH"),
            role=os.getenv("SNOWFLAKE_ROLE", "QUEBEC_HEALTH_INGESTION"),
        )
        for value in (settings.warehouse, settings.database, settings.role):
            if not _IDENTIFIER_PATTERN.fullmatch(value):
                raise ValueError(f"Identifiant Snowflake invalide : {value}")
        if settings.authenticator == "snowflake" and not settings.password:
            raise RuntimeError("SNOWFLAKE_PASSWORD est requis avec authenticator=snowflake.")
        return settings
