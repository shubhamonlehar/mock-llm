from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import fixture_service
from app.services.fixture_service import FixtureService

router = APIRouter(prefix="/openai/v1")


@router.post("/chat/completions")
async def chat_completions(
    payload: dict[str, Any],
    request: Request,
    service: FixtureService = Depends(fixture_service),
) -> dict[str, Any]:
    return await service.chat_completion(payload, dict(request.headers))


@router.get("/models")
async def models(
    request: Request,
    service: FixtureService = Depends(fixture_service),
) -> dict[str, Any]:
    return await service.models(dict(request.headers))
