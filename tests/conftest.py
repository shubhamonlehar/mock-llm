from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.main import create_app
from app.services.fixture_service import FixtureService


class FakeProvider:
    name = "groq"

    def __init__(self) -> None:
        self.calls = 0
        self.model_calls = 0

    async def chat_completion(self, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        self.calls += 1
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "model": payload.get("model", "llama-test"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "fixture response"}}],
        }

    async def models(self, headers: dict[str, str]) -> dict[str, Any]:
        self.model_calls += 1
        return {"object": "list", "data": [{"id": "llama-test", "object": "model"}]}

    async def close(self) -> None:
        return None


@pytest.fixture
def sample_payload() -> dict[str, Any]:
    return {
        "model": "llama-test",
        "messages": [{"role": "user", "content": "Parse this resume"}],
        "temperature": 0,
    }


@pytest.fixture
def app_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def build(mode: str = "replay", provider: FakeProvider | None = None, db_name: str = "fixtures.db"):
        db_path = tmp_path / db_name
        monkeypatch.setenv("PROXY_MODE", mode)
        monkeypatch.setenv("SQLITE_PATH", str(db_path))
        monkeypatch.setenv("CACHE_ENABLED", "true")
        from app.config.settings import get_settings

        get_settings.cache_clear()
        app = create_app()
        fake_provider = provider or FakeProvider()
        settings = Settings(PROXY_MODE=mode, SQLITE_PATH=db_path, CACHE_ENABLED=True)
        app.state.settings = settings
        app.state.fixture_service = FixtureService(settings, provider=fake_provider)
        app.state.fixture_service.startup()
        return app, fake_provider, db_path

    return build


@pytest.fixture
def client_factory(app_factory):
    def build(*args, **kwargs):
        app, provider, db_path = app_factory(*args, **kwargs)
        return TestClient(app), provider, db_path

    return build
