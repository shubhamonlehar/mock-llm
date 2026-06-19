from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.repositories.fixtures import FixtureRepository
from app.utils.hashing import generate_request_hash


def test_record_mode_saves_fixture(client_factory, sample_payload) -> None:
    client, provider, db_path = client_factory(mode="record")

    response = client.post("/openai/v1/chat/completions", json=sample_payload)

    assert response.status_code == 200
    assert provider.calls == 1
    fixture = FixtureRepository(db_path).get(generate_request_hash(sample_payload))
    assert fixture is not None
    assert fixture.response == response.json()


def test_replay_mode_returns_fixture(client_factory, sample_payload) -> None:
    client, provider, db_path = client_factory(mode="replay")
    repository = FixtureRepository(db_path)
    expected = {"choices": [{"message": {"content": "saved"}}]}
    repository.upsert(
        request_hash=generate_request_hash(sample_payload),
        provider="groq",
        model="llama-test",
        request=sample_payload,
        response=expected,
    )
    client.app.state.fixture_service.startup()

    response = client.post("/openai/v1/chat/completions", json=sample_payload)

    assert response.status_code == 200
    assert response.json() == expected
    assert provider.calls == 0


def test_regular_mode_returns_cached_fixture_without_calling_groq(client_factory, sample_payload) -> None:
    client, provider, db_path = client_factory(mode="regular")
    expected = {"choices": [{"message": {"content": "cached"}}]}
    FixtureRepository(db_path).upsert(
        request_hash=generate_request_hash(sample_payload),
        provider="groq",
        model="llama-test",
        request=sample_payload,
        response=expected,
    )
    client.app.state.fixture_service.startup()

    response = client.post("/openai/v1/chat/completions", json=sample_payload)

    assert response.status_code == 200
    assert response.json() == expected
    assert provider.calls == 0


def test_regular_mode_records_fixture_on_cache_miss(client_factory, sample_payload) -> None:
    client, provider, db_path = client_factory(mode="regular")

    response = client.post("/openai/v1/chat/completions", json=sample_payload)
    cached_response = client.post("/openai/v1/chat/completions", json=sample_payload)

    assert response.status_code == 200
    assert cached_response.status_code == 200
    assert cached_response.json() == response.json()
    assert provider.calls == 1
    fixture = FixtureRepository(db_path).get(generate_request_hash(sample_payload))
    assert fixture is not None
    assert fixture.response == response.json()


def test_replay_mode_does_not_call_groq(client_factory, sample_payload) -> None:
    client, provider, db_path = client_factory(mode="replay")
    FixtureRepository(db_path).upsert(
        request_hash=generate_request_hash(sample_payload),
        provider="groq",
        model="llama-test",
        request=sample_payload,
        response={"ok": True},
    )
    client.app.state.fixture_service.startup()

    client.post("/openai/v1/chat/completions", json=sample_payload)

    assert provider.calls == 0


def test_missing_fixture_returns_404(client_factory, sample_payload) -> None:
    client, provider, _ = client_factory(mode="replay")

    response = client.post("/openai/v1/chat/completions", json=sample_payload)

    assert response.status_code == 404
    assert response.json() == {"error": "fixture_not_found"}
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_concurrent_requests_work(app_factory, sample_payload) -> None:
    app, provider, _ = app_factory(mode="record")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        responses = await asyncio.gather(
            *[client.post("/openai/v1/chat/completions", json={**sample_payload, "temperature": index}) for index in range(10)]
        )

    assert all(response.status_code == 200 for response in responses)
    assert provider.calls == 10


def test_sqlite_persistence_works(tmp_path, sample_payload) -> None:
    db_path = tmp_path / "fixtures.db"
    repository = FixtureRepository(db_path)
    request_hash = generate_request_hash(sample_payload)
    repository.upsert(
        request_hash=request_hash,
        provider="groq",
        model="llama-test",
        request=sample_payload,
        response={"persisted": True},
    )

    fresh_repository = FixtureRepository(db_path)

    assert fresh_repository.get(request_hash).response == {"persisted": True}


def test_admin_apis(client_factory, sample_payload) -> None:
    client, _, db_path = client_factory(mode="replay")
    request_hash = generate_request_hash(sample_payload)
    FixtureRepository(db_path).upsert(
        request_hash=request_hash,
        provider="groq",
        model="llama-test",
        request=sample_payload,
        response={"admin": True},
    )

    stats = client.get("/admin/stats")
    lookup = client.get(f"/admin/fixture/{request_hash}")
    search = client.get("/admin/fixtures", params={"model": "llama-test"})

    assert stats.status_code == 200
    assert stats.json()["fixture_count"] == 1
    assert lookup.status_code == 200
    assert search.status_code == 200
    assert search.json()["items"][0]["request_hash"] == request_hash


def test_models_replay_returns_local_models_without_calling_groq(client_factory, sample_payload) -> None:
    client, provider, db_path = client_factory(mode="replay")
    FixtureRepository(db_path).upsert(
        request_hash=generate_request_hash(sample_payload),
        provider="groq",
        model="llama-test",
        request=sample_payload,
        response={"ok": True},
    )

    response = client.get("/openai/v1/models")

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "llama-test"
    assert provider.model_calls == 0


def test_models_record_forwards_to_provider(client_factory) -> None:
    client, provider, _ = client_factory(mode="record")

    response = client.get("/openai/v1/models")

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "llama-test"
    assert provider.model_calls == 1


def test_admin_export_returns_all_fixtures(client_factory, sample_payload) -> None:
    client, _, db_path = client_factory(mode="replay")
    FixtureRepository(db_path).upsert(
        request_hash=generate_request_hash(sample_payload),
        provider="groq",
        model="llama-test",
        request=sample_payload,
        response={"export": True},
    )

    response = client.get("/admin/export")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["fixtures"][0]["response"] == {"export": True}
    assert "attachment" in response.headers["content-disposition"]


def test_clear_fixtures_deletes_db_and_cache(client_factory, sample_payload) -> None:
    client, _, db_path = client_factory(mode="replay")
    request_hash = generate_request_hash(sample_payload)
    FixtureRepository(db_path).upsert(
        request_hash=request_hash,
        provider="groq",
        model="llama-test",
        request=sample_payload,
        response={"ok": True},
    )
    client.app.state.fixture_service.startup()

    response = client.delete("/admin/fixtures")

    assert response.status_code == 200
    assert response.json() == {"deleted_count": 1, "cache_cleared": True}
    assert FixtureRepository(db_path).count() == 0
    assert client.app.state.fixture_service._hash_cache == {}
