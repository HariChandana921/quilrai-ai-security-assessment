
import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI(title="Mock LLM Provider")


@app.post("/generate")
async def generate():
    async def stream_response():
        chunks = [
            "Hello! Contact me at john.",
            "doe@example.com for more information. ",
            "My SSN is 123-",
            "45-6789 and my card number is ",
            "4111 1111 1111 1111. ",
            "Thank you!"
        ]

        for chunk in chunks:
            data = {
                "choices": [
                    {"delta": {"content": chunk}}
                ]
            }

            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(2)

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )
