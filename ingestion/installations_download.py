"""Validation du référentiel des installations de santé."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


EXPECTED_COLUMNS = (
    "INSTAL_COD",
    "INSTAL_NOM",
    "INSTAL_N_1",
    "ETAB_CODE",
    "ETAB_NOM",
    "ETAB_NOM_A",
    "RSS_CODE",
    "RSS_NOM",
    "ADRESSE",
    "CASE_POST",
    "CODE_POSTA",
    "MUN_CODE",
    "MUN_NOM",
    "CLSC_CODE",
    "CLSC_NOM",
    "MRC_CODE",
    "MRC_NOM",
    "RLS_CODE",
    "RLS_NOM",
    "RUIS_CODE",
    "RUIS_NOM",
    "STATUT_COD",
    "MD_CONS_CO",
    "MD_FINAN_C",
    "DESIGN_MIN",
    "INSTANCE",
    "DATE_INCOR",
    "DATE_OUVER",
    "LONGITUDE",
    "LATITUDE",
    "CHPSY",
    "CHSGS",
    "CHSLD",
    "CLSC",
    "CPEJ",
    "CRDITED",
    "CRDPA",
    "CRDPM",
    "CRDPV",
    "CRDPL",
    "CRJDA",
    "CRMDA",
    "CRD",
    "DATE_MAJ",
)


@dataclass(frozen=True)
class InstallationsFile:
    path: Path
    sha256: str
    row_count: int


def validate_file(path: Path) -> InstallationsFile:
    """Valide le schéma exact et l'unicité du code d'installation.

    Le chargement Snowflake associe les colonnes par position : tout écart
    d'en-tête doit donc être refusé avant le chargement.
    """
    content = path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()
    data = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    data.columns = data.columns.str.strip()

    if tuple(data.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            "Schéma des installations inattendu. "
            f"Attendu : {list(EXPECTED_COLUMNS)}; reçu : {list(data.columns)}"
        )
    if data.empty:
        raise ValueError("Le fichier des installations ne contient aucune ligne.")

    codes = data["INSTAL_COD"].str.strip()
    if codes.eq("").any():
        raise ValueError("Un code d'installation (INSTAL_COD) est absent.")
    if codes.duplicated().any():
        raise ValueError("Le code d'installation (INSTAL_COD) contient des doublons.")

    return InstallationsFile(path=path, sha256=sha256, row_count=len(data))
