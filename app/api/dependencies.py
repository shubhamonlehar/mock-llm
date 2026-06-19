from __future__ import annotations

from fastapi import Request

from app.services.fixture_service import FixtureService


def fixture_service(request: Request) -> FixtureService:
    return request.app.state.fixture_service
