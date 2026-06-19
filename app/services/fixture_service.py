from __future__ import annotations

import logging
import time
from typing import Any

from app.config.settings import Settings
from app.providers.base import LLMProvider
from app.providers.groq import GroqProvider
from app.repositories.fixtures import Fixture, FixtureRepository
from app.utils.hashing import generate_request_hash
from app.utils.logging import log_structured

logger = logging.getLogger(__name__)


class FixtureNotFoundError(Exception):
    def __init__(self, request_hash: str) -> None:
        super().__init__("fixture_not_found")
        self.request_hash = request_hash


class FixtureService:
    def __init__(self, settings: Settings, provider: LLMProvider | None = None) -> None:
        self.settings = settings
        self.repository = FixtureRepository(settings.sqlite_path)
        self.provider = provider or GroqProvider(settings)
        self._hash_cache: dict[str, bool] = {}

    def startup(self) -> None:
        if self.settings.cache_enabled:
            self._hash_cache = {request_hash: True for request_hash in self.repository.list_hashes()}

    async def shutdown(self) -> None:
        await self.provider.close()

    async def chat_completion(self, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        request_hash = generate_request_hash(payload)
        model = payload.get("model")
        if self.settings.proxy_mode == "record":
            return await self._record(payload, headers, request_hash, str(model) if model else None)
        if self.settings.proxy_mode == "regular":
            fixture = self._get_fixture_for_replay(request_hash)
            if fixture is not None:
                self._log_replay(request_hash, fixture_found=True)
                return fixture.response
            self._log_replay(request_hash, fixture_found=False)
            return await self._record(payload, headers, request_hash, str(model) if model else None)
        return self._replay(request_hash)

    async def models(self, headers: dict[str, str]) -> dict[str, Any]:
        if self.settings.proxy_mode == "replay":
            fixtures = self.repository.search(limit=500, offset=0)
            model_ids = sorted({fixture.model for fixture in fixtures if fixture.model})
            return {
                "object": "list",
                "data": [
                    {
                        "id": model,
                        "object": "model",
                        "created": 0,
                        "owned_by": self.settings.provider,
                    }
                    for model in model_ids
                ],
            }
        return await self.provider.models(headers)

    def get_fixture(self, request_hash: str) -> Fixture | None:
        return self.repository.get(request_hash)

    def search_fixtures(
        self,
        *,
        model: str | None,
        date: str | None,
        limit: int,
        offset: int,
    ) -> list[Fixture]:
        return self.repository.search(model=model, date=date, limit=limit, offset=offset)

    def all_fixtures(self) -> list[Fixture]:
        return self.repository.all()

    def fixture_count(self) -> int:
        return self.repository.count()

    def clear_fixtures(self) -> int:
        deleted_count = self.repository.clear()
        self._hash_cache.clear()
        return deleted_count

    async def _record(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
        request_hash: str,
        model: str | None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        response = await self.provider.chat_completion(payload, headers)
        self.repository.upsert(
            request_hash=request_hash,
            provider=self.provider.name,
            model=model,
            request=payload,
            response=response,
        )
        if self.settings.cache_enabled:
            self._hash_cache[request_hash] = True
        latency_ms = int((time.perf_counter() - started) * 1000)
        log_structured(
            logger,
            "recorded fixture",
            mode=self.settings.proxy_mode,
            request_hash=request_hash,
            model=model,
            latency_ms=latency_ms,
        )
        return response

    def _replay(self, request_hash: str) -> dict[str, Any]:
        fixture = self._get_fixture_for_replay(request_hash)
        self._log_replay(request_hash, fixture_found=fixture is not None)
        if fixture is None:
            raise FixtureNotFoundError(request_hash)
        return fixture.response

    def _get_fixture_for_replay(self, request_hash: str) -> Fixture | None:
        if self.settings.cache_enabled and request_hash not in self._hash_cache:
            return None
        fixture = self.repository.get(request_hash)
        if fixture is None and self.settings.cache_enabled:
            self._hash_cache.pop(request_hash, None)
        return fixture

    def _log_replay(self, request_hash: str, *, fixture_found: bool) -> None:
        log_structured(
            logger,
            "replayed fixture",
            mode=self.settings.proxy_mode,
            request_hash=request_hash,
            fixture_found=fixture_found,
        )
