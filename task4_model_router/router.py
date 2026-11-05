import math
import asyncio
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


TOKEN_LIMIT = 50_000
WINDOW_SECONDS = 60
PRIMARY_TIMEOUT = 3.0

DB_PATH = os.getenv(
    "RATE_LIMIT_DB",
    str(Path(__file__).with_name("rate_limits.db")),
)
PRIMARY_URL = os.getenv(
    "PRIMARY_MODEL_URL", "http://127.0.0.1:8001/generate"
)
BACKUP_URL = os.getenv(
    "BACKUP_MODEL_URL", "http://127.0.0.1:8002/generate"
)


def initialize_database():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_key TEXT NOT NULL,
                tokens INTEGER NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_tenant_time
            ON token_usage (tenant_key, created_at)
        """)


def reserve_tokens(tenant_key: str, tokens: int) -> bool:
    now = time.time()

    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute("BEGIN IMMEDIATE")

        # Evict expired records from all tenants.
        conn.execute(
            "DELETE FROM token_usage WHERE created_at <= ?",
            (now - WINDOW_SECONDS,),
        )

        used = conn.execute(
            """
            SELECT COALESCE(SUM(tokens), 0)
            FROM token_usage
            WHERE tenant_key = ?
            """,
            (tenant_key,),
        ).fetchone()[0]

        if used + tokens > TOKEN_LIMIT:
            return False

        conn.execute(
            """
            INSERT INTO token_usage
                (tenant_key, tokens, created_at)
            VALUES (?, ?, ?)
            """,
            (tenant_key, tokens, now),
        )

    return True


class CompletionRequest(BaseModel):
    prompt: str = Field(min_length=1)
    max_tokens: int = Field(default=512, ge=1, le=50_000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Task 4 - Resilient LLM Gateway",
    lifespan=lifespan,
)


async def call_model(
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    timeout: float,
):
    response = await client.post(
        url,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()



@app.post("/generate")
async def generate(
    request: CompletionRequest,
    x_api_key: str = Header(min_length=1),
):
    # Estimate input tokens (approximately 4 characters/token).
    # Reserve both estimated input and maximum output tokens.
    # Production systems should use a model-specific tokenizer.
    input_tokens = max(1, math.ceil(len(request.prompt) / 4))
    total_tokens = input_tokens + request.max_tokens

    reserved = await asyncio.to_thread(
        reserve_tokens, x_api_key, total_tokens
    )

    if not reserved:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Tenant token limit exceeded",
            },
        )


    payload = request.model_dump()

    async with httpx.AsyncClient() as client:
        try:
            result = await call_model(
                client, PRIMARY_URL, payload, PRIMARY_TIMEOUT
            )
            return {"provider": "primary", "result": result}

        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError):
                if exc.response.status_code != 429:
                    raise HTTPException(
                        status_code=502,
                        detail={
                            "error": "UPSTREAM_ERROR",
                            "message": "Primary model request failed",
                        },
                    ) from None

        except (httpx.RequestError, ValueError):
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "UPSTREAM_ERROR",
                    "message": "Primary model request failed",
                },
            ) from None

        try:
            result = await call_model(
                client, BACKUP_URL, payload, PRIMARY_TIMEOUT
            )
            return {"provider": "backup", "result": result}

        except (httpx.RequestError, httpx.HTTPStatusError, ValueError):
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "ALL_PROVIDERS_FAILED",
                    "message": "Model providers are unavailable",
                },
            ) from None
