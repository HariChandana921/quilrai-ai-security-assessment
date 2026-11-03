from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock MCP Server")

TOOLS = [
    {
        "name": "get_customer_record",
        "description": "Retrieve a mock customer record.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "admin_delete_customer",
        "description": "Simulate an administrative deletion.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"}
            },
            "required": ["customer_id"]
        }
    }
]


@app.post("/mcp")
async def handle_mcp(request: Request):
    body = await request.json()
    method = body.get("method")
    request_id = body.get("id")

    if method == "tools/list":
        result = {"tools": TOOLS}

    elif method == "tools/call":
        params = body.get("params", {})
        tool_name = params.get("name")

        if tool_name not in [tool["name"] for tool in TOOLS]:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": "Tool not found"
                }
            })

        result = {
            "content": [
                {
                    "type": "text",
                    "text": f"Mock execution of {tool_name}"
                }
            ]
        }

    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": "Method not found"
            }
        })

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }
