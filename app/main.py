from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.admin import router as admin_router
from app.api.openai import router as openai_router
from app.config.settings import get_settings
from app.services.fixture_service import FixtureNotFoundError, FixtureService
from app.storage.database import init_db
from app.utils.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    init_db(settings.sqlite_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.fixture_service.startup()
        yield
        await app.state.fixture_service.shutdown()

    app = FastAPI(title="Groq Recording & Replay Proxy", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.fixture_service = FixtureService(settings)

    @app.exception_handler(FixtureNotFoundError)
    async def fixture_not_found(_: Request, exc: FixtureNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": "fixture_not_found"})

    app.include_router(openai_router)
    app.include_router(admin_router)
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
