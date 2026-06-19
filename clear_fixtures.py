from __future__ import annotations

import argparse

import httpx

from app.config.settings import get_settings
from app.repositories.fixtures import FixtureRepository


def clear_fixtures() -> int:
    settings = get_settings()
    repository = FixtureRepository(settings.sqlite_path)
    return repository.clear()


def clear_running_proxy(proxy_url: str) -> dict[str, object]:
    response = httpx.delete(f"{proxy_url.rstrip('/')}/admin/fixtures", timeout=10)
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Clear all recorded fixtures.")
    parser.add_argument(
        "--proxy-url",
        help="Clear via a running proxy so both SQLite data and in-memory cache are reset.",
    )
    args = parser.parse_args()

    if args.proxy_url:
        result = clear_running_proxy(args.proxy_url)
        print(f"Deleted {result['deleted_count']} fixtures. Cache cleared: {result['cache_cleared']}.")
        return

    deleted_count = clear_fixtures()
    print(f"Deleted {deleted_count} fixtures. Restart the proxy to clear its in-memory cache.")


if __name__ == "__main__":
    main()
