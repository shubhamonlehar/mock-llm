from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config.settings import get_settings
from app.repositories.fixtures import FixtureRepository


def export_fixtures(output_dir: Path | str = "fixtures") -> int:
    settings = get_settings()
    repository = FixtureRepository(settings.sqlite_path)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    count = 0
    for fixture in repository.all():
        payload = {
            "request_hash": fixture.request_hash,
            "model": fixture.model,
            "request": fixture.request,
            "response": fixture.response,
        }
        path = destination / f"{fixture.request_hash}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Export SQLite fixtures to JSON files.")
    parser.add_argument("--output-dir", default="fixtures")
    args = parser.parse_args()
    count = export_fixtures(args.output_dir)
    print(f"Exported {count} fixtures.")


if __name__ == "__main__":
    main()
