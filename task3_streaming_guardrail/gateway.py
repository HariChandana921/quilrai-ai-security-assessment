
import json
import os
import re

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="Streaming PII Guardrail")

LLM_URL = os.getenv(
    "LLM_URL",
    "http://127.0.0.1:8001/generate",
)

# Detect email addresses, SSNs, and credit card numbers.
EMAIL = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD = re.compile(r"\b\d(?:[ -]?\d){15}\b")

PII = re.compile(
    f"(?:{EMAIL.pattern})|(?:{SSN.pattern})|(?:{CARD.pattern})"
)

# Characters that may form part of a sensitive value.
CANDIDATE = set(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789._%+@- "
)

MAX_PENDING = 4096


def redact(text: str) -> str:
    """Replace recognized PII with a redaction marker."""
    return PII.sub("[REDACTED]", text)


def make_event(text: str) -> str:
    """Create a Server-Sent Event."""
    event = {
        "choices": [
            {
                "delta": {
                    "content": text
                }
            }
        ]
    }
    return f"data: {json.dumps(event)}\n\n"


def split_safe(text: str, final: bool = False):
    """
    Retain unfinished candidate text so sensitive values
    split across upstream chunks are not released early.
    """
    if final:
        return redact(text), ""

    last = -1

    for index, char in enumerate(text):
        if char not in CANDIDATE:
            last = index

    if last < 0:
        return "", text

    safe = text[:last + 1]
    pending = text[last + 1:]

    return redact(safe), pending


@app.post("/generate")
async def generate():
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, read=30.0)
    )
    upstream = None

    try:
        # Connect before starting the streaming response.
        request = client.build_request("POST", LLM_URL)
        upstream = await client.send(request, stream=True)

        if upstream.status_code != 200:
            await upstream.aclose()
            await client.aclose()

            return JSONResponse(
                {"error": "Upstream LLM error"},
                status_code=502,
            )

    except httpx.RequestError:
        if upstream is not None:
            await upstream.aclose()

        await client.aclose()

        return JSONResponse(
            {"error": "Downstream unavailable"},
            status_code=502,
        )

    async def safe_stream():
        pending = ""

        try:
            async for line in upstream.aiter_lines():
                if not line.startswith("data: "):
                    continue

                data = line[6:].strip()

                if data == "[DONE]":
                    break

                try:
                    event = json.loads(data)
                    content = (
                        event["choices"][0]["delta"]
                        .get("content", "")
                    )

                except (
                    ValueError,
                    KeyError,
                    IndexError,
                    TypeError,
                ):
                    continue

                if not isinstance(content, str):
                    continue

                pending += content

                safe, pending = split_safe(pending)

                if safe:
                    yield make_event(safe)

                # Fail closed if the pending buffer is too large.
                if len(pending) > MAX_PENDING:
                    pending = ""
                    yield make_event("[REDACTED]")

            if pending:
                yield make_event(redact(pending))

        except httpx.RequestError:
            # Once streaming begins, the HTTP status cannot
            # be changed to 502.
            yield make_event(
                "[ERROR: Downstream unavailable]"
            )

        finally:
            await upstream.aclose()
            await client.aclose()

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        safe_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )
