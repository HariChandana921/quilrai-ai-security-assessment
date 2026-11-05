
import asyncio
import sqlite3
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from task4_model_router import router


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_rate_limits.db")
    monkeypatch.setattr(router, "DB_PATH", db_path)
    router.initialize_database()
    return db_path


def test_token_limit(isolated_db):
    assert router.reserve_tokens("tenant-a", 30000)
    assert router.reserve_tokens("tenant-a", 20000)
    assert not router.reserve_tokens("tenant-a", 1)


def test_tenant_isolation(isolated_db):
    assert router.reserve_tokens("tenant-a", 50000)
    assert not router.reserve_tokens("tenant-a", 1)
    assert router.reserve_tokens("tenant-b", 100)


def test_sliding_window_expiration(isolated_db):
    assert router.reserve_tokens("tenant-a", 50000)

    with sqlite3.connect(isolated_db) as conn:
        conn.execute(
            "UPDATE token_usage SET created_at = ?",
            (time.time() - 61,),
        )

    assert router.reserve_tokens("tenant-a", 50000)

    with sqlite3.connect(isolated_db) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM token_usage"
        ).fetchone()[0]

    assert count == 1


def test_concurrent_reservations(isolated_db):
    async def run_test():
        results = await asyncio.gather(
            *(
                asyncio.to_thread(
                    router.reserve_tokens,
                    "tenant-concurrent",
                    10000,
                )
                for _ in range(10)
            )
        )
        return results

    results = asyncio.run(run_test())

    assert results.count(True) == 5
    assert results.count(False) == 5


def test_primary_success(isolated_db, monkeypatch):
    async def fake_call(client, url, payload, timeout):
        return {"text": "Primary response"}

    monkeypatch.setattr(router, "call_model", fake_call)

    with TestClient(router.app) as client:
        response = client.post(
            "/generate",
            headers={"X-API-Key": "tenant-primary"},
            json={"prompt": "Hello", "max_tokens": 100},
        )

    assert response.status_code == 200
    assert response.json()["provider"] == "primary"


def test_fallback_on_429(isolated_db, monkeypatch):
    async def fake_call(client, url, payload, timeout):
        if url == router.PRIMARY_URL:
            request = httpx.Request("POST", url)
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError(
                "Rate limited",
                request=request,
                response=response,
            )
        return {"text": "Backup response"}

    monkeypatch.setattr(router, "call_model", fake_call)

    with TestClient(router.app) as client:
        response = client.post(
            "/generate",
            headers={"X-API-Key": "tenant-fallback"},
            json={"prompt": "Hello", "max_tokens": 100},
        )

    assert response.status_code == 200
    assert response.json()["provider"] == "backup"


def test_fallback_on_timeout(isolated_db, monkeypatch):
    async def fake_call(client, url, payload, timeout):
        if url == router.PRIMARY_URL:
            raise httpx.ReadTimeout("Simulated timeout")
        return {"text": "Backup response"}

    monkeypatch.setattr(router, "call_model", fake_call)

    with TestClient(router.app) as client:
        response = client.post(
            "/generate",
            headers={"X-API-Key": "tenant-timeout"},
            json={"prompt": "Hello", "max_tokens": 100},
        )

    assert response.status_code == 200
    assert response.json()["provider"] == "backup"


def test_sanitized_upstream_error(isolated_db, monkeypatch):
    async def fake_call(client, url, payload, timeout):
        request = httpx.Request("POST", url)
        response = httpx.Response(500, request=request)
        raise httpx.HTTPStatusError(
            "Sensitive internal provider information",
            request=request,
            response=response,
        )

    monkeypatch.setattr(router, "call_model", fake_call)

    with TestClient(router.app) as client:
        response = client.post(
            "/generate",
            headers={"X-API-Key": "tenant-error"},
            json={"prompt": "Hello", "max_tokens": 100},
        )

    assert response.status_code == 502
    assert response.json()["detail"]["error"] == "UPSTREAM_ERROR"
    assert "Sensitive internal" not in response.text


def test_input_tokens_count_toward_limit(isolated_db, monkeypatch):
    async def fake_call(client, url, payload, timeout):
        return {"text": "OK"}

    monkeypatch.setattr(router, "call_model", fake_call)

    with TestClient(router.app) as client:
        response = client.post(
            "/generate",
            headers={"X-API-Key": "tenant-input-test"},
            json={
                "prompt": "A" * 400,
                "max_tokens": 49950,
            },
        )

    # 400 characters ≈ 100 input tokens.
    # 49,950 + 100 = 50,050, exceeding the limit.
    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "RATE_LIMIT_EXCEEDED"
