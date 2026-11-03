
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="MCP Security Gateway")

DOWNSTREAM_URL = os.getenv(
    "DOWNSTREAM_URL", "http://127.0.0.1:8001/mcp"
)

# Demo credentials only; replace with proper token validation in production.
TOKENS = {
    "admin-token": "admin",
    "viewer-token": "viewer",
}


def rpc_error(request_id, code, message):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


@app.post("/mcp")
async def mcp_gateway(request: Request):
    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(
            rpc_error(None, -32700, "Parse error"),
            status_code=400,
        )

    if not isinstance(payload, dict):
        return JSONResponse(
            rpc_error(None, -32600, "Invalid Request"),
            status_code=400,
        )

    request_id = payload.get("id")
    method = payload.get("method")

    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    role = TOKENS.get(token) if scheme.lower() == "bearer" else None
    if method == "tools/call" and role is None:
        return JSONResponse(
            rpc_error(
                request_id,
                -32001,
                "Authentication required",
            ),
            status_code=401,
        )

    if method == "tools/call":
        params = payload.get("params")
        if not isinstance(params, dict):
            return JSONResponse(
                rpc_error(request_id, -32602, "Invalid params"),
                status_code=400,
            )

        tool_name = params.get("name")
        if not isinstance(tool_name, str):
            return JSONResponse(
                rpc_error(request_id, -32602, "Invalid tool name"),
                status_code=400,
            )

        if tool_name.startswith("admin_") and role != "admin":
            return JSONResponse(
                rpc_error(
                    request_id,
                    -32001,
                    "Unauthorized Tool Call",
                ),
                status_code=403,
            )

    # Forward permitted requests to the downstream MCP server.
    headers = {
        "content-type": "application/json",
    }

    # Preserve relevant MCP transport headers.
    for name in ("accept", "mcp-session-id", "mcp-protocol-version"):
        value = request.headers.get(name)
        if value:
            headers[name] = value

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            upstream = await client.post(
                DOWNSTREAM_URL,
                json=payload,
                headers=headers,
            )
    except httpx.RequestError:
        return JSONResponse(
            rpc_error(request_id, -32000, "Downstream unavailable"),
            status_code=502,
        )

    response_headers = {}
    for name in ("content-type", "mcp-session-id"):
        if name in upstream.headers:
            response_headers[name] = upstream.headers[name]

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )
