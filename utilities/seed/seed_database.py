"""
Seed the database with mock datasets for testing purposes.

Usage:
    python utilities/seed_database.py
    python utilities/seed_database.py --count 500
    python utilities/seed_database.py --count 2000 --prefix test
"""
import argparse
import os
import sys

# Ensure the project root is on the path when running from a subdirectory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from application import create_app
from application import database
from test.mock_objects import MockObjects


def main():
    project_name = os.environ.get("COMPOSE_PROJECT_NAME", "")
    if "prod" in project_name.lower():
        print(f"ERROR: Refusing to seed a production database (COMPOSE_PROJECT_NAME='{project_name}').")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Seed the database with mock datasets.")
    parser.add_argument("--count", type=int, default=10, help="Number of datasets to generate (default: 10)")
    parser.add_argument("--prefix", type=str, default="seed", help="Prefix for dataset IDs (default: seed)")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        mock = MockObjects(database.db_session)
        print(f"Seeding {args.count} datasets with prefix '{args.prefix}'...")
        mock.generate_datasets(number=args.count, dataset_id_prefix=args.prefix)
        print("Done.")


if __name__ == "__main__":
    main()
