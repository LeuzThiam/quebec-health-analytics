"""Téléchargement et normalisation des projections de population ISQ/MSSS."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

import pandas as pd

from download import HTTP_HEADERS


SOURCE_URL = (
    "https://www.donneesquebec.ca/recherche/dataset/"
    "911a70f1-1053-4f4a-9c3b-529de857bb16/resource/"
    "05c3c53d-db97-4bc3-8221-d8af47b4b93e/download/"
    "estimationprojectionuniquedonneesouvertes.csv"
)
IDENTIFIER_COLUMNS = (
    "NiveauGeographique",
    "CodeTerritoire",
    "Territoire",
    "Annee",
    "TypeDonnees",
    "Statut",
    "Sexe",
)
AGE_COLUMNS = (
    "TousLesAges",
    "MoinsUnAn",
    *(str(age) for age in range(1, 90)),
    "90ansOuPlus",
)
EXPECTED_COLUMNS = IDENTIFIER_COLUMNS + AGE_COLUMNS
OUTPUT_COLUMNS = (
    "geography_level",
    "territory_code",
    "territory_name",
    "reference_year",
    "data_type",
    "status",
    "sex",
    "age_label",
    "population",
)
EXPECTED_REGION_CODES = {f"{code:02d}" for code in range(1, 19)}
EXPECTED_YEARS = set(range(2001, 2052))


@dataclass(frozen=True)
class ComparablePopulationFile:
    path: Path
    source_url: str
    sha256: str
    modified_at: datetime | None
    row_count: int


def _validate_source(data: pd.DataFrame) -> None:
    if tuple(data.columns) != EXPECTED_COLUMNS:
        raise ValueError("Le schéma de la source de population ISQ/MSSS a changé.")
    if data.empty:
        raise ValueError("Le fichier de population ISQ/MSSS est vide.")

    grain = ["NiveauGeographique", "CodeTerritoire", "Annee", "Sexe"]
    if data[list(IDENTIFIER_COLUMNS[:5]) + ["Sexe"]].eq("").any().any():
        raise ValueError("Une dimension obligatoire de la source est vide.")
    if data.duplicated(grain).any():
        raise ValueError("La source contient des doublons à sa granularité métier.")

    years = pd.to_numeric(data["Annee"], errors="coerce")
    if years.isna().any() or set(years.astype(int)) != EXPECTED_YEARS:
        raise ValueError("La période 2001-2051 de la source est incomplète.")
    if set(data["Sexe"]) != {"Masculin", "Féminin", "Total"}:
        raise ValueError("Le domaine du sexe a changé dans la source.")
    if set(data["TypeDonnees"]) != {"Estimation", "Projection"}:
        raise ValueError("Le domaine du type de données a changé dans la source.")

    measures = data[list(AGE_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    if measures.isna().any().any() or (measures < 0).any().any():
        raise ValueError("Une valeur de population est absente, invalide ou négative.")
    if not measures[list(AGE_COLUMNS[1:])].sum(axis=1).eq(
        measures["TousLesAges"]
    ).all():
        raise ValueError("La somme des âges ne correspond pas à TousLesAges.")

    regions = data.loc[data["NiveauGeographique"] == "RSS", "CodeTerritoire"]
    if set(regions) != EXPECTED_REGION_CODES:
        raise ValueError("La source ne contient pas exactement les 18 RSS attendues.")


def _normalise_source(source_path: Path, destination: Path) -> Path:
    data = pd.read_csv(
        source_path,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )
    _validate_source(data)

    regions = data.loc[data["NiveauGeographique"] == "RSS"].copy()
    normalised = regions.melt(
        id_vars=list(IDENTIFIER_COLUMNS),
        value_vars=list(AGE_COLUMNS),
        var_name="age_label",
        value_name="population",
    ).rename(
        columns={
            "NiveauGeographique": "geography_level",
            "CodeTerritoire": "territory_code",
            "Territoire": "territory_name",
            "Annee": "reference_year",
            "TypeDonnees": "data_type",
            "Statut": "status",
            "Sexe": "sex",
        }
    )
    normalised = normalised.loc[:, OUTPUT_COLUMNS]
    normalised.to_csv(destination, index=False, encoding="utf-8")
    return destination


def download_file(destination: Path) -> tuple[Path, str, datetime | None]:
    """Télécharge la source officielle et produit un fichier RSS normalisé immuable."""
    request = Request(SOURCE_URL, headers=HTTP_HEADERS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    token = uuid4().hex
    source_path = destination.with_name(f".{destination.stem}.{token}.source.csv")
    normalised_path = destination.with_name(f".{destination.stem}.{token}.csv")

    try:
        with urlopen(request, timeout=120) as response, source_path.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
            last_modified = response.headers.get("Last-Modified")

        _normalise_source(source_path, normalised_path)
        content_sha256 = hashlib.sha256(normalised_path.read_bytes()).hexdigest()
        immutable_path = destination.with_name(
            f"{destination.stem}_{content_sha256[:16]}{destination.suffix}"
        )
        normalised_path.replace(immutable_path)
    finally:
        source_path.unlink(missing_ok=True)
        normalised_path.unlink(missing_ok=True)

    modified_at = parsedate_to_datetime(last_modified) if last_modified else None
    return immutable_path, SOURCE_URL, modified_at


def validate_file(
    path: Path,
    source_url: str = "local",
    modified_at: datetime | None = None,
) -> ComparablePopulationFile:
    """Valide le fichier RSS long avant son chargement dans Snowflake."""
    content = path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()
    data = pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)

    if tuple(data.columns) != OUTPUT_COLUMNS:
        raise ValueError("Le schéma normalisé de population ISQ/MSSS est inattendu.")
    if data.empty:
        raise ValueError("Le fichier normalisé de population est vide.")

    grain = ["territory_code", "reference_year", "sex", "age_label"]
    if data.duplicated(grain).any():
        raise ValueError("Le fichier normalisé contient des doublons.")
    if set(data["territory_code"]) != EXPECTED_REGION_CODES:
        raise ValueError("Le fichier normalisé ne contient pas les 18 RSS.")
    if set(pd.to_numeric(data["reference_year"]).astype(int)) != EXPECTED_YEARS:
        raise ValueError("Le fichier normalisé ne couvre pas 2001-2051.")
    if set(data["age_label"]) != set(AGE_COLUMNS):
        raise ValueError("Le domaine des âges du fichier normalisé est incomplet.")

    population = pd.to_numeric(data["population"], errors="coerce")
    if population.isna().any() or (population < 0).any():
        raise ValueError("Une population normalisée est invalide ou négative.")

    expected_rows = 18 * len(EXPECTED_YEARS) * 3 * len(AGE_COLUMNS)
    if len(data) != expected_rows:
        raise ValueError(f"Nombre de lignes inattendu : {len(data)}/{expected_rows}.")

    return ComparablePopulationFile(
        path=path,
        source_url=source_url,
        sha256=sha256,
        modified_at=modified_at,
        row_count=len(data),
    )
