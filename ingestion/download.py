"""Téléchargement et validation des fichiers publics de Données Québec."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
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

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/csv,application/octet-stream;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.7",
}


@dataclass(frozen=True)
class DownloadedFile:
    path: Path
    source_url: str
    sha256: str
    modified_at: datetime | None
    row_count: int


def discover_resource() -> tuple[str, str]:
    """Retourne l'identifiant CKAN et l'URL du fichier horaire attendu."""
    request = Request(CKAN_API_URL, headers=HTTP_HEADERS)
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    resources = payload["result"]["resources"]
    for resource in resources:
        name = resource.get("name", "").lower()
        url = resource.get("url", "")
        if resource.get("format", "").upper() == "CSV" and (
            "personnes présentes" in name or "nbpers" in url.lower()
        ):
            return resource["id"], url
    raise RuntimeError("Ressource CSV des personnes présentes introuvable.")


def download_file(destination: Path) -> tuple[Path, str, datetime | None]:
    """Télécharge atomiquement le fichier officiel vers le chemin demandé."""
    resource_id, source_url = discover_resource()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_name(
        f".{destination.stem}.{uuid4().hex}{destination.suffix}.part"
    )

    request = Request(
        source_url,
        headers={**HTTP_HEADERS, "Referer": "https://www.msss.gouv.qc.ca/"},
    )
    try:
        response = urlopen(request, timeout=60)
        downloaded_from = source_url
    except HTTPError as error:
        if error.code != 403:
            raise
        downloaded_from = (
            "https://www.donneesquebec.ca/recherche/datastore/dump/"
            f"{resource_id}?format=csv"
        )
        response = urlopen(
            Request(downloaded_from, headers=HTTP_HEADERS), timeout=60
        )

    with response:
        content = response.read()
        last_modified = response.headers.get("Last-Modified")

    if downloaded_from != source_url:
        # CKAN ajoute une colonne technique `_id`. On reconstruit ici le CSV
        # exact attendu par Snowflake avant de calculer son hash et de le charger.
        datastore_data = pd.read_csv(
            BytesIO(content), encoding="utf-8-sig", dtype=str
        )
        datastore_data.columns = datastore_data.columns.str.strip()
        datastore_data = datastore_data.drop(columns=["_id"], errors="raise")
        if tuple(datastore_data.columns) != EXPECTED_COLUMNS:
            raise ValueError("Schéma inattendu dans l'export DataStore.")
        content = datastore_data.to_csv(index=False).encode("cp1252")

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
    return immutable_path, downloaded_from, modified_at


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
