
import asyncio
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(title="Mock LLM Provider")


class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 512


@app.post("/generate")
async def generate(request: GenerateRequest):
    prompt = request.prompt.lower()

    # Identify whether this is the backup provider.
    is_backup = os.getenv("MOCK_PROVIDER") == "backup"

    # Simulate HTTP 429 only for the primary provider.
    if "simulate_429" in prompt and not is_backup:
        raise HTTPException(
            status_code=429,
            detail="Provider rate limit exceeded",
        )

    # Simulate a 4-second delay only for the primary.
    if "simulate_timeout" in prompt and not is_backup:
        await asyncio.sleep(4)

    return {
        "text": f"Mock response to: {request.prompt}",
        "tokens_used": min(request.max_tokens, 100),
    }
