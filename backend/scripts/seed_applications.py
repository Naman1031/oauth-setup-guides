"""Load seed_data/guides/*.json into the `applications` table.

Usage (from backend/, with DATABASE_URL set in .env):
    python -m scripts.seed_applications            # validate and write
    python -m scripts.seed_applications --dry-run  # validate only, write nothing
"""

import argparse
import sys

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.seeding import SeedError, load_seed_records, seed_applications


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="validate the seed files without touching the database")
    args = parser.parse_args()

    settings = get_settings()
    try:
        records = load_seed_records(settings.seed_data_dir)
    except SeedError as error:
        print(f"Seed files are invalid; nothing was written.\n{error}", file=sys.stderr)
        return 1

    print(f"Validated {len(records)} guide(s): {', '.join(r.slug for r in records)}")
    if args.dry_run:
        return 0

    with get_session_factory()() as db:
        result = seed_applications(db, records)
    print(f"Inserted: {', '.join(result.inserted) or 'none'}")
    print(f"Updated:  {', '.join(result.updated) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
