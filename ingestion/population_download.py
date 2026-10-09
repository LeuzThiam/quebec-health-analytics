"""Téléchargement et normalisation des estimations de population québécoises."""

from __future__ import annotations

import hashlib
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

import pandas as pd

from download import HTTP_HEADERS


SOURCE_URL = "https://www150.statcan.gc.ca/n1/fr/tbl/csv/17100157-fra.zip"
SOURCE_MEMBER = "17100157.csv"
REGION_DGUID_PATTERN = re.compile(r"^24\d{2}-[A-I]$")
OUTPUT_COLUMNS = (
    "reference_year",
    "health_region_name",
    "health_region_code",
    "peer_group_code",
    "age_group",
    "sex",
    "unit_of_measure",
    "scalar_factor",
    "value",
    "status",
    "decimals",
)


@dataclass(frozen=True)
class PopulationFile:
    path: Path
    source_url: str
    sha256: str
    modified_at: datetime | None
    row_count: int


def _download_archive(destination: Path) -> tuple[Path, datetime | None]:
    request = Request(SOURCE_URL, headers=HTTP_HEADERS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_name(f".{destination.name}.{uuid4().hex}.part")

    try:
        with urlopen(request, timeout=120) as response, temporary_path.open("wb") as output:
            while block := response.read(1024 * 1024):
                output.write(block)
            last_modified = response.headers.get("Last-Modified")
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)

    modified_at = parsedate_to_datetime(last_modified) if last_modified else None
    return destination, modified_at


def _normalise_archive(archive_path: Path, destination: Path) -> Path:
    temporary_path = destination.with_name(
        f".{destination.stem}.{uuid4().hex}{destination.suffix}.part"
    )
    first_chunk = True

    try:
        with zipfile.ZipFile(archive_path) as archive, archive.open(SOURCE_MEMBER) as source:
            for chunk in pd.read_csv(
                source,
                encoding="utf-8-sig",
                sep=";",
                dtype=str,
                chunksize=200_000,
            ):
                selected = chunk.loc[
                    chunk["DGUID"].str.match(REGION_DGUID_PATTERN, na=False)
                ].copy()
                if selected.empty:
                    continue

                normalised = pd.DataFrame(
                    {
                        "reference_year": selected.iloc[:, 0],
                        "health_region_name": selected["GÉO"],
                        "health_region_code": selected["DGUID"].str[:4],
                        "peer_group_code": selected["DGUID"].str[-1],
                        "age_group": selected["Groupe d'âge"],
                        "sex": selected["Genre"],
                        "unit_of_measure": selected["UNITÉ DE MESURE"],
                        "scalar_factor": selected["FACTEUR SCALAIRE"],
                        "value": selected["VALEUR"],
                        "status": selected["STATUS"],
                        "decimals": selected["DÉCIMALES"],
                    }
                )
                normalised.to_csv(
                    temporary_path,
                    mode="w" if first_chunk else "a",
                    header=first_chunk,
                    index=False,
                    encoding="utf-8",
                )
                first_chunk = False

        if first_chunk:
            raise ValueError("Aucune région sociosanitaire du Québec n'a été trouvée.")
        temporary_path.replace(destination)
        return destination
    finally:
        temporary_path.unlink(missing_ok=True)


def download_file(destination: Path) -> tuple[Path, str, datetime | None]:
    """Télécharge le cube StatCan et conserve seulement les régions du Québec."""
    archive_path = destination.with_suffix(".zip")
    archive_path, modified_at = _download_archive(archive_path)
    normalised_path = _normalise_archive(archive_path, destination)
    return normalised_path, SOURCE_URL, modified_at


def validate_file(
    path: Path,
    source_url: str = "local",
    modified_at: datetime | None = None,
) -> PopulationFile:
    """Valide le schéma et la granularité du fichier normalisé."""
    content = path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()
    data = pd.read_csv(path, encoding="utf-8", dtype=str)

    if tuple(data.columns) != OUTPUT_COLUMNS:
        raise ValueError(
            "Schéma population inattendu. "
            f"Attendu : {list(OUTPUT_COLUMNS)}; reçu : {list(data.columns)}"
        )
    if data.empty:
        raise ValueError("Le fichier de population ne contient aucune ligne.")

    required = [
        "reference_year",
        "health_region_name",
        "health_region_code",
        "peer_group_code",
        "age_group",
        "sex",
        "value",
    ]
    if data[required].isna().any().any():
        raise ValueError("Une dimension ou une mesure obligatoire est absente.")

    grain = ["reference_year", "health_region_code", "age_group", "sex"]
    if data.duplicated(grain).any():
        raise ValueError("La granularité population contient des doublons.")
    if data["health_region_code"].nunique() != 18:
        raise ValueError("Le fichier ne contient pas les 18 régions du Québec.")
    if set(data["sex"].unique()) != {"Total - genre", "Hommes+", "Femmes+"}:
        raise ValueError("Les catégories de genre StatCan ont changé.")

    values = pd.to_numeric(data["value"], errors="coerce")
    if values.isna().any() or (values < 0).any():
        raise ValueError("Une valeur de population est absente, invalide ou négative.")

    expected_rows = (
        data["reference_year"].nunique()
        * data["health_region_code"].nunique()
        * data["age_group"].nunique()
        * data["sex"].nunique()
    )
    if len(data) != expected_rows:
        raise ValueError("Le cube population normalisé est incomplet.")

    return PopulationFile(
        path=path,
        source_url=source_url,
        sha256=sha256,
        modified_at=modified_at,
        row_count=len(data),
    )

