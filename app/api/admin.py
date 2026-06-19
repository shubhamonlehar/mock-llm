from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import fixture_service
from app.services.fixture_service import FixtureService

router = APIRouter(prefix="/admin")


@router.get("/stats")
async def stats(service: FixtureService = Depends(fixture_service)) -> dict[str, object]:
    return {
        "mode": service.settings.proxy_mode,
        "fixture_count": service.fixture_count(),
    }


@router.get("/fixture/{request_hash}")
async def fixture(request_hash: str, service: FixtureService = Depends(fixture_service)) -> dict[str, object]:
    stored = service.get_fixture(request_hash)
    if stored is None:
        raise HTTPException(status_code=404, detail={"error": "fixture_not_found"})
    return {
        "request_hash": stored.request_hash,
        "provider": stored.provider,
        "model": stored.model,
        "created_at": stored.created_at,
        "request": stored.request,
        "response": stored.response,
    }


@router.get("/fixtures")
async def fixtures(
    model: str | None = None,
    date: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: FixtureService = Depends(fixture_service),
) -> dict[str, object]:
    results = service.search_fixtures(model=model, date=date, limit=limit, offset=offset)
    return {
        "items": [
            {
                "request_hash": item.request_hash,
                "provider": item.provider,
                "model": item.model,
                "created_at": item.created_at,
                "request": item.request,
                "response": item.response,
            }
            for item in results
        ],
        "limit": limit,
        "offset": offset,
    }


@router.delete("/fixtures")
async def clear_fixtures(service: FixtureService = Depends(fixture_service)) -> dict[str, object]:
    deleted_count = service.clear_fixtures()
    return {
        "deleted_count": deleted_count,
        "cache_cleared": True,
    }
