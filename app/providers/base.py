from __future__ import annotations

from typing import Any, Protocol


class LLMProvider(Protocol):
    name: str

    async def chat_completion(self, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        ...

    async def models(self, headers: dict[str, str]) -> dict[str, Any]:
        ...

    async def close(self) -> None:
        ...
