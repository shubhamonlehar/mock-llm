from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from app.config.settings import Settings


class GroqProvider:
    name = "groq"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = httpx.AsyncClient(base_url=settings.groq_base_url.rstrip("/"), timeout=120)

    async def chat_completion(self, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        return await self._post("/chat/completions", payload, headers)

    async def models(self, headers: dict[str, str]) -> dict[str, Any]:
        return await self._get("/models", headers)

    async def close(self) -> None:
        await self.client.aclose()

    async def _post(self, path: str, payload: dict[str, Any], incoming_headers: dict[str, str]) -> dict[str, Any]:
        response = await self.client.post(path, json=payload, headers=self._headers(incoming_headers))
        return self._json_or_error(response)

    async def _get(self, path: str, incoming_headers: dict[str, str]) -> dict[str, Any]:
        response = await self.client.get(path, headers=self._headers(incoming_headers))
        return self._json_or_error(response)

    def _headers(self, incoming_headers: dict[str, str]) -> dict[str, str]:
        headers = {"content-type": "application/json"}
        if self.settings.groq_api_key:
            headers["authorization"] = f"Bearer {self.settings.groq_api_key}"
        elif authorization := incoming_headers.get("authorization"):
            headers["authorization"] = authorization
        return headers

    @staticmethod
    def _json_or_error(response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError:
            body = {"error": response.text}
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=body)
        return body
