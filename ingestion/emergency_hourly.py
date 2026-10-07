"""Point d'entrée du pipeline horaire des urgences du Québec."""

from __future__ import annotations

import argparse
from pathlib import Path

from config import SnowflakeSettings
from download import download_file, validate_file
from snowflake_loader import load_emergency_file


DEFAULT_FILE = Path("data/incoming/urgences_horaires.csv")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingérer le fichier horaire des urgences.")
    parser.add_argument("--file", type=Path, help="Utiliser un fichier local existant.")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Valider le fichier sans effectuer de chargement Snowflake.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    source_url = "local"
    source_file = args.file or DEFAULT_FILE

    if args.file is None:
        source_file, source_url, modified_at = download_file(source_file)
    else:
        modified_at = None

    validated_file = validate_file(source_file, source_url, modified_at)

    print(f"Fichier : {validated_file.path}")
    print(f"Lignes : {validated_file.row_count}")
    print(f"SHA-256 : {validated_file.sha256}")

    if args.validate_only:
        print("Validation terminée, aucun chargement Snowflake effectué.")
        return

    batch_id = load_emergency_file(validated_file, SnowflakeSettings.from_environment())
    print(f"Résultat du chargement : {batch_id}")


if __name__ == "__main__":
    main()
