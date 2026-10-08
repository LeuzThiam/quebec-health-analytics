"""Point d'entrée de l'ingestion des estimations de population."""

from __future__ import annotations

import argparse
from pathlib import Path

from population_download import download_file, validate_file


DEFAULT_FILE = Path("data/incoming/population_quebec.csv")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Préparer les estimations de population de Statistique Canada."
    )
    parser.add_argument("--file", type=Path, help="Valider un fichier normalisé existant.")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Valider le fichier sans effectuer de chargement Snowflake.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    source_file = args.file or DEFAULT_FILE
    source_url = "local"
    modified_at = None

    if args.file is None:
        source_file, source_url, modified_at = download_file(source_file)

    validated_file = validate_file(source_file, source_url, modified_at)
    print(f"Fichier : {validated_file.path}")
    print(f"Lignes : {validated_file.row_count}")
    print(f"SHA-256 : {validated_file.sha256}")
    print("Validation terminée, aucun chargement Snowflake effectué.")


if __name__ == "__main__":
    main()

