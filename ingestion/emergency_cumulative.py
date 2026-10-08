"""Point d'entrée de l'ingestion cumulative des urgences du Québec."""

from __future__ import annotations

import argparse
from pathlib import Path

from config import SnowflakeSettings
from cumulative_download import download_file, validate_file
from cumulative_loader import load_cumulative_file


DEFAULT_FILE = Path("data/incoming/urgences_cumulatives.csv")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingérer le fichier cumulatif des urgences."
    )
    parser.add_argument("--file", type=Path, help="Utiliser un fichier local existant.")
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

    if args.validate_only:
        print("Validation terminée, aucun chargement Snowflake effectué.")
        return

    batch_id = load_cumulative_file(
        validated_file,
        SnowflakeSettings.from_environment(),
    )
    print(f"Résultat du chargement : {batch_id}")


if __name__ == "__main__":
    main()
