from __future__ import annotations

import pytest
import httpx
from fastapi import HTTPException

from app.config.settings import Settings
from app.providers.groq import GroqProvider


@pytest.mark.asyncio
async def test_groq_provider_chat_completion_uses_incoming_header_when_api_key_missing(tmp_path) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["authorization"] = request.headers.get("authorization")
        seen["body"] = request.read().decode()
        return httpx.Response(200, json={"ok": True})

    provider = GroqProvider(
        Settings(
            SQLITE_PATH=tmp_path / "fixtures.db",
            GROQ_BASE_URL="https://groq.test/openai/v1",
            GROQ_API_KEY=None,
        )
    )
    provider.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://groq.test/openai/v1")

    response = await provider.chat_completion({"model": "llama-test"}, {"authorization": "Bearer incoming"})
    await provider.close()

    assert response == {"ok": True}
    assert seen["url"] == "https://groq.test/openai/v1/chat/completions"
    assert seen["authorization"] == "Bearer incoming"
    assert '"model":"llama-test"' in str(seen["body"]).replace(" ", "")


@pytest.mark.asyncio
async def test_groq_provider_models_uses_api_key_when_header_missing(tmp_path) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, json={"data": []})

    provider = GroqProvider(
        Settings(
            SQLITE_PATH=tmp_path / "fixtures.db",
            GROQ_BASE_URL="https://groq.test/openai/v1",
            GROQ_API_KEY="test-key",
        )
    )
    provider.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://groq.test/openai/v1")

    response = await provider.models({})
    await provider.close()

    assert response == {"data": []}
    assert seen["authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_groq_provider_prefers_api_key_over_incoming_header(tmp_path) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, json={"ok": True})

    provider = GroqProvider(
        Settings(
            SQLITE_PATH=tmp_path / "fixtures.db",
            GROQ_BASE_URL="https://groq.test/openai/v1",
            GROQ_API_KEY="default-key",
        )
    )
    provider.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://groq.test/openai/v1")

    response = await provider.chat_completion({"model": "llama-test"}, {"authorization": "Bearer incoming"})
    await provider.close()

    assert response == {"ok": True}
    assert seen["authorization"] == "Bearer default-key"


def test_groq_provider_json_or_error_handles_non_json_error() -> None:
    response = httpx.Response(503, text="service unavailable")

    with pytest.raises(HTTPException) as exc_info:
        GroqProvider._json_or_error(response)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {"error": "service unavailable"}
