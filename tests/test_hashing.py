from __future__ import annotations

from app.utils.hashing import generate_request_hash


def test_hash_generation_is_deterministic() -> None:
    payload_a = {"model": "x", "messages": [{"content": "hello", "role": "user"}], "temperature": 0}
    payload_b = {"temperature": 0, "messages": [{"role": "user", "content": "hello"}], "model": "x"}

    assert generate_request_hash(payload_a) == generate_request_hash(payload_b)
