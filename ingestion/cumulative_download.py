"""Téléchargement et validation du fichier cumulatif des urgences."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

import pandas as pd

from download import HTTP_HEADERS


DATASET_ID = "b7e297c3-ff0f-4e11-bc0f-2add3cffdd76"
CKAN_API_URL = (
    "https://www.donneesquebec.ca/recherche/api/3/action/package_show"
    f"?id={DATASET_ID}"
)

EXPECTED_COLUMNS = (
    "annee",
    "cumul_periode",
    "rss",
    "region",
    "nom_etablissement",
    "nom_installation",
    "no_permis_installation",
    "nb_visites_total",
    "nb_usagers_75ans_et_plus_total",
    "nb_usagers_sante_mentale_total",
    "dms_total",
    "nb_usagers_pec_total",
    "delai_pec_total",
    "nb_visites_ambulatoire",
    "nb_usagers_75ans_et_plus_amb",
    "nb_usagers_sante_mentale_amb",
    "dms_ambulatoire",
    "nb_usagers_pec_ambulatoire",
    "delai_pec_ambulatoire",
    "nb_visites_sur_civiere",
    "nb_usagers_sur_civiere_plus_24h",
    "nb_usagers_sur_civiere_plus_48h",
    "dms_sur_civiere",
    "nb_usagers_pec_sur_civiere",
    "delai_pec_sur_civiere",
    "nb_usagers_75ans_et_plus_civ",
    "nb_usagers_sante_mentale_civ",
)


@dataclass(frozen=True)
class CumulativeFile:
    path: Path
    source_url: str
    sha256: str
    modified_at: datetime | None
    row_count: int


def discover_resource_url() -> str:
    """Retourne l'URL CSV de la ressource cumulative officielle."""
    request = Request(CKAN_API_URL, headers=HTTP_HEADERS)
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    for resource in payload["result"]["resources"]:
        if resource.get("format", "").upper() == "CSV":
            return resource["url"]
    raise RuntimeError("Ressource CSV cumulative des urgences introuvable.")


def download_file(destination: Path) -> tuple[Path, str, datetime | None]:
    """Télécharge une copie immuable identifiée par son empreinte SHA-256."""
    source_url = discover_resource_url()
    request = Request(
        source_url,
        headers={**HTTP_HEADERS, "Referer": "https://www.msss.gouv.qc.ca/"},
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_name(
        f".{destination.stem}.{uuid4().hex}{destination.suffix}.part"
    )

    with urlopen(request, timeout=60) as response:
        content = response.read()
        last_modified = response.headers.get("Last-Modified")

    if not content:
        raise ValueError("Le fichier cumulatif téléchargé est vide.")

    sha256 = hashlib.sha256(content).hexdigest()
    immutable_path = destination.with_name(
        f"{destination.stem}_{sha256[:16]}{destination.suffix}"
    )
    try:
        temporary_path.write_bytes(content)
        temporary_path.replace(immutable_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    modified_at = parsedate_to_datetime(last_modified) if last_modified else None
    return immutable_path, source_url, modified_at


def validate_file(
    path: Path,
    source_url: str = "local",
    modified_at: datetime | None = None,
) -> CumulativeFile:
    """Valide le schéma, le contenu et la granularité métier du fichier."""
    content = path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()
    data = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    data.columns = data.columns.str.strip()

    if tuple(data.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            "Schéma cumulatif inattendu. "
            f"Attendu : {list(EXPECTED_COLUMNS)}; reçu : {list(data.columns)}"
        )
    if data.empty:
        raise ValueError("Le fichier cumulatif ne contient aucune ligne.")
    if data["annee"].isna().any() or data["cumul_periode"].isna().any():
        raise ValueError("Une année financière ou une période cumulative est absente.")

    grain = [
        "annee",
        "cumul_periode",
        "rss",
        "region",
        "nom_etablissement",
        "nom_installation",
        "no_permis_installation",
    ]
    if data.fillna("").duplicated(grain).any():
        raise ValueError("La granularité métier cumulative contient des doublons.")

    return CumulativeFile(
        path=path,
        source_url=source_url,
        sha256=sha256,
        modified_at=modified_at,
        row_count=len(data),
    )
