"""Téléchargement et validation des listes d'attente en chirurgie."""

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
    "https://www.msss.gouv.qc.ca/professionnels/statistiques/documents/"
    "chirurgie/Chirurgie_ListeAttente.csv"
)
EXPECTED_COLUMNS = (
    "PeriodeAttente",
    "Delais_d'attente",
    "Region",
    "Chirurgie_generale",
    "Chirurgie_orthopedique",
    "Chirurgie_plastique",
    "Chirurgie_vasculaire",
    "Neurochirurgie",
    "Obstetrique_et_gynecologie",
    "Ophtalmologie",
    "ORL_chirurgie_cervico_faciale",
    "Urologie",
    "Autres",
    "Total",
)
SPECIALTY_COLUMNS = EXPECTED_COLUMNS[3:-1]


@dataclass(frozen=True)
class SurgeryFile:
    path: Path
    source_url: str
    sha256: str
    modified_at: datetime | None
    row_count: int


def download_file(destination: Path) -> tuple[Path, str, datetime | None]:
    """Télécharge une copie immuable du fichier officiel."""
    request = Request(SOURCE_URL, headers=HTTP_HEADERS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_name(
        f".{destination.stem}.{uuid4().hex}{destination.suffix}.part"
    )

    with urlopen(request, timeout=60) as response:
        content = response.read()
        last_modified = response.headers.get("Last-Modified")

    if not content:
        raise ValueError("Le fichier de chirurgie téléchargé est vide.")

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
    return immutable_path, SOURCE_URL, modified_at


def validate_file(
    path: Path,
    source_url: str = "local",
    modified_at: datetime | None = None,
) -> SurgeryFile:
    """Valide le schéma, la granularité et les totaux publiés."""
    content = path.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()
    data = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    data.columns = data.columns.str.strip()

    if tuple(data.columns) != EXPECTED_COLUMNS:
        raise ValueError(
            "Schéma chirurgie inattendu. "
            f"Attendu : {list(EXPECTED_COLUMNS)}; reçu : {list(data.columns)}"
        )
    if data.empty:
        raise ValueError("Le fichier de chirurgie ne contient aucune ligne.")

    grain = ["PeriodeAttente", "Delais_d'attente", "Region"]
    if data[grain].isna().any().any():
        raise ValueError("La période, le délai ou la région est absent.")
    if data.duplicated(grain).any():
        raise ValueError("La granularité métier chirurgie contient des doublons.")

    measures = data[list(SPECIALTY_COLUMNS) + ["Total"]].apply(
        pd.to_numeric,
        errors="coerce",
    )
    invalid_values = data[list(SPECIALTY_COLUMNS) + ["Total"]].notna() & measures.isna()
    if invalid_values.any().any():
        raise ValueError("Une mesure de chirurgie n'est pas numérique.")
    if (measures.fillna(0) < 0).any().any():
        raise ValueError("Une mesure de chirurgie est négative.")
    if not measures[list(SPECIALTY_COLUMNS)].fillna(0).sum(axis=1).eq(measures["Total"]).all():
        raise ValueError("Au moins un total ne correspond pas aux spécialités.")

    return SurgeryFile(
        path=path,
        source_url=source_url,
        sha256=sha256,
        modified_at=modified_at,
        row_count=len(data),
    )
