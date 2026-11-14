"""Point d'entrée de l'ingestion du référentiel des installations de santé."""

from __future__ import annotations

import argparse
from pathlib import Path

from config import SnowflakeSettings
from installations_download import validate_file
from installations_loader import load_installations_file


DEFAULT_FILE = Path("data/exploration/installations.csv")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingérer le référentiel des installations de santé."
    )
    parser.add_argument(
        "--file",
        type=Path,
        help=f"Fichier CSV local à ingérer (par défaut : {DEFAULT_FILE}).",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Valider le fichier sans effectuer de chargement Snowflake.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    source_file = args.file or DEFAULT_FILE

    validated_file = validate_file(source_file)
    print(f"Fichier : {validated_file.path}")
    print(f"Lignes : {validated_file.row_count}")
    print(f"SHA-256 : {validated_file.sha256}")

    if args.validate_only:
        print("Validation terminée, aucun chargement Snowflake effectué.")
        return

    batch_id = load_installations_file(
        validated_file,
        SnowflakeSettings.from_environment(),
    )
    print(f"Résultat du chargement : {batch_id}")


if __name__ == "__main__":
    main()
