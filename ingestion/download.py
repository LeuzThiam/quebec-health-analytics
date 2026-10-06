"""Téléchargement et validation des fichiers publics de Données Québec."""

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


DATASET_ID = "d4541afe-9391-44bf-a78f-dae3c9cf1217"
CKAN_API_URL = (
    "https://www.donneesquebec.ca/recherche/api/3/action/package_show"
    f"?id={DATASET_ID}"
)

EXPECTED_COLUMNS = (
    "RSS",
    "Region",
    "Nom_etablissement",
    "Nom_installation",
    "No_permis_installation",
    "Nombre_de_civieres_fonctionnelles",
    "Nombre_de_civieres_occupees",
    "Nombre_de_patients_sur_civiere_plus_de_24_heures",
    "Nombre_de_patients_sur_civiere_plus_de_48_heures",
    "Nombre_total_de_patients_presents_a_lurgence",
    "Nombre_total_de_patients_en_attente_de_PEC",
    "DMS_sur_civiere",
    "DMS_ambulatoire",
    "DMS_sur_civiere_horaire",
    "DMS_ambulatoire_horaire",
    "Heure_de_l'extraction_(image)",
    "Mise_a_jour",
)


@dataclass(frozen=True)
class DownloadedFile:
    path: Path
    source_url: str
    sha256: str
    modified_at: datetime | None
    row_count: int


def discover_resource_url() -> str:
    """Retourne l'URL du fichier horaire comprenant les personnes présentes."""
    request = Request(CKAN_API_URL, headers={"User-Agent": "quebec-health-analytics/1.0"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    resources = payload["result"]["resources"]
    for resource in resources:
        name = resource.get("name", "").lower()
        url = resource.get("url", "")
        if resource.get("format", "").upper() == "CSV" and (
            "personnes présentes" in name or "nbpers" in url.lower()
        ):
            return url
    raise RuntimeError("Ressource CSV des personnes présentes introuvable.")


def download_file(destination: Path) -> tuple[Path, str, datetime | None]:
    """Télécharge atomiquement le fichier officiel vers le chemin demandé."""
    source_url = discover_resource_url()
    request = Request(source_url, headers={"User-Agent": "quebec-health-analytics/1.0"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_name(
        f".{destination.stem}.{uuid4().hex}{destination.suffix}.part"
    )

    with urlopen(request, timeout=60) as response:
        content = response.read()
        last_modified = response.headers.get("Last-Modified")

    if not content:
        raise ValueError("Le fichier téléchargé est vide.")
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
) -> DownloadedFile:
    """Valide l'encodage, le schéma minimal et le contenu du fichier."""
    content = path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()
    data = pd.read_csv(path, encoding="cp1252", dtype=str)
    data.columns = data.columns.str.strip()

    actual_columns = tuple(data.columns)
    if actual_columns != EXPECTED_COLUMNS:
        raise ValueError(
            "Ordre ou noms de colonnes inattendus. "
            f"Attendu : {list(EXPECTED_COLUMNS)}; reçu : {list(actual_columns)}"
        )
    if data.empty:
        raise ValueError("Le fichier ne contient aucune ligne.")
    if data["No_permis_installation"].dropna().str.strip().eq("").all():
        raise ValueError("Aucun numéro de permis d'installation valide.")

    return DownloadedFile(
        path=path,
        source_url=source_url,
        sha256=sha256,
        modified_at=modified_at,
        row_count=len(data),
    )
