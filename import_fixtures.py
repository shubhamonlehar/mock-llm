from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config.settings import get_settings
from app.repositories.fixtures import FixtureRepository


def import_fixtures(input_dir: Path | str = "fixtures", provider: str = "groq") -> int:
    settings = get_settings()
    repository = FixtureRepository(settings.sqlite_path)
    source = Path(input_dir)
    count = 0

    for path in sorted(source.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        repository.upsert(
            request_hash=payload["request_hash"],
            provider=payload.get("provider", provider),
            model=payload.get("model"),
            request=payload["request"],
            response=payload["response"],
        )
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Import exported JSON fixtures into SQLite.")
    parser.add_argument("--input-dir", default="fixtures")
    parser.add_argument("--provider", default="groq")
    args = parser.parse_args()
    count = import_fixtures(args.input_dir, args.provider)
    print(f"Imported {count} fixtures.")


if __name__ == "__main__":
    main()
