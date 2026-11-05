
# QuilrAI AI Security Assessment

This repository contains four Python implementations developed for the QuilrAI AI Security Assessment. The tasks cover MCP server development, tool-level access control, streaming PII protection, and model routing with rate limiting.

## Project Structure

| Folder | Description |
| --- | --- |
| `task1_mcp_server/` | MCP server with customer lookup and mock refund tools |
| `task2_mcp_gateway/` | MCP security gateway with role-based access control |
| `task3_streaming_guardrail/` | Streaming gateway for detecting and redacting PII |
| `task4_model_router/` | Model router with rate limiting and provider fallback |

## Setup

Create a virtual environment and install the dependencies from the project root.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Run each task separately because several services use the same ports.

## Task 1: Secure MCP Server

Implemented an MCP server with two tools:

- `get_customer_record`: Retrieves mock customer information using a validated customer ID.
- `trigger_refund`: Validates the customer ID, refund amount, and reason before simulating a refund.

Pydantic handles input validation. No real customer database or payment system is involved.

### Run

```bash
python task1_mcp_server/server.py
```

The server uses stdio transport and communicates with an MCP client.

### Tests

```bash
python -m pytest task1_mcp_server/test_server.py -v
python task1_mcp_server/test_mcp_client.py
```

## Task 2: MCP Security Gateway

Built a gateway that checks authentication and authorization before forwarding MCP requests to a downstream server.

The gateway supports two roles:

- `viewer`: Can access permitted tools but cannot execute administrative operations.
- `admin`: Can access administrative tools, including tools with the `admin_` prefix.

Requests are validated before forwarding. Missing or invalid authentication is rejected, and downstream errors are handled by the gateway.

### Run

Start the mock server:

```bash
python -m uvicorn task2_mcp_gateway.mock_server:app --port 8001
```

Start the gateway in another terminal:

```bash
python -m uvicorn task2_mcp_gateway.gateway:app --port 8000
```

### Tests

```bash
python -m pytest task2_mcp_gateway/test_gateway.py -v --import-mode=importlib
```

The implementation uses predefined tokens for local testing rather than a production authentication provider.

## Task 3: Streaming PII Guardrail

Developed a FastAPI gateway that processes streamed LLM responses and removes supported sensitive information before sending content to the client.

The current implementation detects:

- Email addresses
- US Social Security numbers
- Credit card number patterns

PII may be split across multiple streaming chunks. To handle this, the gateway temporarily buffers potentially incomplete sensitive values, applies redaction, and forwards safe content as it becomes available.

The gateway uses Server-Sent Events (SSE) and asynchronous HTTP requests.

### Run

Start the mock LLM:

```bash
python -m uvicorn task3_streaming_guardrail.mock_llm:app --port 8001
```

Start the streaming gateway in another terminal:

```bash
python -m uvicorn task3_streaming_guardrail.gateway:app --port 8000
```

### Tests

```bash
python -m pytest task3_streaming_guardrail/test_gateway.py -v --import-mode=importlib
```

### Streaming Verification

During local testing:

| Event | Approximate Time |
| --- | --- |
| First safe response | 0.02 seconds |
| Additional redacted content | 10.03 seconds |
| Stream completion | 12.03 seconds |

The gateway delivered safe content before the upstream response finished.

The detector uses regular expressions, so it is limited to supported PII patterns. Buffering may also introduce some delay when incoming text cannot yet be classified as safe.

## Task 4: Multi-Model Router with Rate Limiting

Implemented a model router that forwards requests to a primary provider and switches to a backup provider when necessary.

The router includes:

- Primary and backup mock model providers
- Automatic fallback on HTTP 429 responses
- Automatic fallback after a three-second primary timeout
- Per-tenant rate limiting using SQLite
- A 60-second sliding window
- A limit of 50,000 reserved tokens per tenant
- Atomic reservations for concurrent requests
- Sanitized error responses

Tenants are identified using the `X-API-Key` request header.

### Run

Start the primary provider:

```bash
python -m uvicorn task4_model_router.mock_models:app --port 8001
```

Start the backup provider in another terminal:

```bash
MOCK_PROVIDER=backup python -m uvicorn task4_model_router.mock_models:app --port 8002
```

Start the router in a third terminal:

```bash
python -m uvicorn task4_model_router.router:app --port 8000
```

### Example Request

```bash
curl -sS -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-demo" \
  -d '{"prompt":"Hello AI","max_tokens":100}'
```

### Tests

```bash
python -m pytest task4_model_router/test_router.py -v --import-mode=importlib
```

The tests cover rate limiting, tenant isolation, concurrent requests, sliding-window expiration, provider fallback, and error handling.

### Token Accounting

Input tokens are estimated using approximately four characters per token.

The router reserves estimated input tokens and the maximum requested output tokens before forwarding the request.

This is an approximation. Production usage would require model-specific token counting and reconciliation with actual token consumption.

SQLite database files are excluded from Git because they contain local runtime state.

## Running All Tests

From the repository root:

```bash
python -m pytest -q --import-mode=importlib
```

Latest local test result:

```text
33 passed
```

## Implementation Notes

All four tasks use mock data or mock model providers.

The implementations focus on demonstrating input validation, authorization, PII redaction, tenant rate limiting, and provider failover.

Additional security hardening, monitoring, and integration work would be needed before using these services in a production environment.
