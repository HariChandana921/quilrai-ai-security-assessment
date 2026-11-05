
# QuilrAI AI Security Assessment

## Task 1: Secure MCP Server

This project implements a Python Model Context Protocol (MCP) server with customer lookup and mock refund functionality.

## Features

- Customer record lookup
- Mock refund processing
- Pydantic input validation
- Customer ID format validation
- Refund amount and reason validation
- Error handling for invalid requests
- Automated unit and MCP integration tests

## Technologies

- Python 3.14
- MCP Python SDK 1.x
- Pydantic
- Pytest
- Pytest-asyncio

## Installation

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the MCP Server

```bash
python task1_mcp_server/server.py
```

The server uses stdio transport and is intended to communicate with an MCP client.

## Run Unit Tests

```bash
python -m pytest task1_mcp_server/test_server.py -v
```

## Run Integration Tests

```bash
python task1_mcp_server/test_mcp_client.py
```

## Implemented MCP Tools

### get_customer_record
Retrieves a mock customer record using a validated customer ID.

### trigger_refund
Processes a mock refund request after validating the customer ID, refund amount, and reason.

No real payment transaction is performed.

## Testing

The implementation has passed nine unit tests and MCP client integration checks, including invalid input and unknown-tool handling.


---

## Task 2: MCP Security Gateway Proxy

This project implements a Python-based Model Context Protocol (MCP) Security Gateway that acts as a reverse proxy between an AI agent client and a downstream MCP server. It provides role-based authorization, secure tool filtering, and JSON-RPC request forwarding.

## Features

- Bearer token authentication
- Role-based access control (Admin and Viewer)
- Administrative tool authorization
- JSON-RPC 2.0 request validation
- Transparent forwarding of permitted MCP requests
- Unauthorized tool execution prevention
- HTTP 401 and 403 error handling
- Downstream server failure handling (HTTP 502)
- Automated security and integration tests

## Technologies

- Python 3.14
- FastAPI
- HTTPX
- Uvicorn
- Pytest
- JSON-RPC 2.0

## Installation

Install the required dependencies from the project root:

```bash
python -m pip install -r requirements.txt
```

## Running the Mock MCP Server

```bash
python -m uvicorn task2_mcp_gateway.mock_server:app --host 127.0.0.1 --port 8001
```

## Running the MCP Security Gateway

Open another terminal and run:

```bash
python -m uvicorn task2_mcp_gateway.gateway:app --host 127.0.0.1 --port 8000
```

## Authorization Rules

| User Role | Tool | Expected Response |
|---|---|---|
| Viewer | get_customer_record | 200 OK |
| Viewer | admin_delete_customer | 403 Forbidden |
| Admin | admin_delete_customer | 200 OK |
| Missing authentication | tools/call | 401 Unauthorized |
| Invalid token | tools/call | 401 Unauthorized |

Administrative tools are identified by the `admin_` prefix. Only users with the admin role can execute these tools.

## Testing

Run the automated tests:

```bash
python -m pytest task2_mcp_gateway/test_gateway.py -v
```

### Test Results

All six automated tests passed successfully.

- Viewer cannot execute administrative tools
- Admin can execute administrative tools
- Viewer can access permitted tools
- Missing authentication is rejected
- Invalid authentication tokens are rejected
- Downstream server failures are handled

**Result: 6 passed.**

## Security Implementation

The gateway validates incoming JSON-RPC requests and checks authorization before forwarding tool execution requests to the downstream server.

Unauthorized administrative calls are blocked at the gateway, preventing their execution by the downstream server.

For demonstration purposes, the implementation uses predefined authentication tokens. Production deployments should use secure token validation and appropriate secret management.


# Task 3: Real-Time Streaming PII Guardrail

## Overview

This project implements a real-time streaming PII (Personally Identifiable Information) guardrail using Python, FastAPI, and HTTPX.

The gateway acts as a security layer between a client and a downstream Large Language Model (LLM). It receives streaming responses from the LLM, detects sensitive information, and redacts it before forwarding the content to the client.

The implementation focuses on preventing sensitive information from leaking even when PII is split across multiple streaming chunks.

## Objectives

- Implement an asynchronous FastAPI gateway for LLM responses.
- Support real-time Server-Sent Events (SSE).
- Detect and redact sensitive information.
- Prevent PII leakage across chunk boundaries.
- Preserve non-sensitive response content.
- Handle upstream errors and connection failures.
- Validate functionality using automated tests.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application development |
| FastAPI | API gateway |
| HTTPX | Asynchronous communication with the downstream LLM |
| Uvicorn | ASGI server |
| Regular Expressions | PII detection and redaction |
| SSE | Real-time response streaming |
| Pytest | Automated testing |

## Project Structure

```text
task3_streaming_guardrail/
├── gateway.py
├── mock_llm.py
├── test_gateway.py
└── README.md
```

**File descriptions:**

- `gateway.py`: Implements the streaming gateway, PII detection, redaction, and SSE responses.
- `mock_llm.py`: Simulates an LLM that produces streaming responses containing test PII.
- `test_gateway.py`: Contains automated tests for endpoint behavior, PII redaction, and error handling.
- `README.md`: Documents the implementation, setup, and testing procedure.

## Architecture

```text
             Client
                |
                | POST /generate
                v
       FastAPI PII Gateway
                |
                | HTTPX Async Request
                v
          Mock LLM Server
                |
                | Streaming SSE Events
                v
       Streaming PII Guardrail
                |
                | Incremental buffering
                | PII detection
                | Sensitive data redaction
                v
          Safe SSE Events
                |
                v
             Client
```

## PII Detection

The gateway detects and redacts the following categories:

| PII Type | Example | Redacted Output |
|---|---|---|
| Email address | alice@example.com | [REDACTED] |
| Social Security Number | 123-45-6789 | [REDACTED] |
| Credit card number | 4111 1111 1111 1111 | [REDACTED] |

The gateway replaces detected sensitive values with `[REDACTED]`.

## Real-Time Streaming Implementation

Unlike an approach that buffers the entire LLM response, this implementation processes incoming content incrementally.

The gateway maintains a pending buffer for text that may contain incomplete sensitive information.

The processing workflow is:

1. Receive an SSE event from the downstream LLM.
2. Extract the generated text from the event.
3. Append the content to the pending buffer.
4. Identify portions of text that can be safely released.
5. Apply PII redaction before forwarding content.
6. Retain potentially incomplete sensitive values until they can be processed safely.
7. Send the final SSE completion event.

A maximum pending-buffer limit is used to avoid unbounded buffering. If the pending content exceeds the configured threshold, the implementation replaces it with a redaction marker.

This approach supports incremental delivery while protecting the tested PII patterns across chunk boundaries.

## Installation and Setup

### 1. Navigate to the project root

```bash
cd quilrai-ai-security-assessment
```

### 2. Activate the virtual environment

On macOS or Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

The application uses two local servers.

### Terminal 1: Start the Mock LLM

```bash
python -m uvicorn task3_streaming_guardrail.mock_llm:app --host 127.0.0.1 --port 8001
```

### Terminal 2: Start the PII Gateway

```bash
python -m uvicorn task3_streaming_guardrail.gateway:app --host 127.0.0.1 --port 8000
```

### Terminal 3: Test the Streaming Endpoint

```bash
curl -N --no-buffer -X POST http://127.0.0.1:8000/generate
```

The endpoint returns SSE events with detected PII replaced by `[REDACTED]`.

## Testing

Run the Task 3 tests from the repository root:

```bash
python -m pytest task3_streaming_guardrail/test_gateway.py -v --import-mode=importlib
```

Run the complete assessment test suite:

```bash
python -m pytest -v --import-mode=importlib
```

### Test Coverage

The automated tests cover:

- Gateway application initialization
- POST endpoint registration
- Rejection of unsupported GET requests
- Email redaction
- SSN redaction across chunks
- Credit card redaction
- Preservation of safe text
- Upstream HTTP errors
- Downstream connection failures

### Test Results

During local verification, the complete assessment test suite produced:

```text
24 passed in 0.33s
```

All 24 collected tests passed in this run.

## Real-Time Streaming Verification

Streaming behavior was also tested using a local mock LLM with delayed output.

The observed results were:

| Event | Approximate Arrival Time |
|---|---|
| First safe content | 0.02 seconds |
| Additional redacted content | 10.03 seconds |
| SSE completion marker | 12.03 seconds |

These results demonstrate that the gateway can deliver initial safe content before the downstream LLM completes its response.

The test also showed that email addresses, SSNs, and credit card numbers in the sample response were redacted.

## Error Handling

The gateway handles downstream communication failures and upstream HTTP errors.

It is designed to avoid exposing sensitive internal error details to the client.

Because a streaming response may already have started when an error occurs, errors encountered during streaming are communicated within the SSE response rather than by changing the HTTP status code after headers have been sent.

## Security Considerations

The implementation includes the following security measures:

- Redaction before client delivery
- Protection against tested cross-chunk PII patterns
- Incremental buffering of potentially sensitive content
- Maximum pending-buffer threshold
- Asynchronous resource cleanup
- Disabled response caching through `Cache-Control: no-cache`
- `X-Content-Type-Options: nosniff`

### Limitations

PII detection is based on regular expressions and may not identify every possible sensitive-data format.

The buffering strategy may introduce latency when the gateway cannot yet determine whether incoming content is safe.

Additional production improvements could include more comprehensive PII detection, stricter input validation, structured logging without sensitive content, and broader adversarial testing.

## Conclusion

Task 3 demonstrates a real-time streaming security gateway that redacts supported PII patterns before delivering LLM-generated content to clients.

The solution combines asynchronous communication, SSE streaming, incremental buffering, regular-expression-based redaction, and automated testing.

Local verification demonstrated incremental delivery, successful redaction of the tested sensitive information, and passing automated tests.


---

## Task 4: Multi-Model Router with Rate Limiting

### Overview

This task implements a FastAPI-based model routing gateway with
primary and backup LLM providers, tenant-specific rate limiting,
and automatic provider failover.

### Features

- Primary model routing for normal requests.
- Automatic backup routing when the primary returns HTTP 429.
- Backup routing when the primary exceeds its 3-second timeout.
- SQLite-backed, per-tenant sliding-window rate limiting.
- A limit of 50,000 reserved tokens per 60-second window.
- Atomic token reservations to protect against concurrent requests.
- Estimated input-token and maximum output-token accounting.
- Standardized error responses without exposing internal provider details.

### Architecture

Client
  |
  v
FastAPI Model Router (Port 8000)
  |
  +-- API Key / Tenant Identification
  |
  +-- SQLite Rate Limiter
  |      |
  |      +-- 60-second sliding window
  |      +-- 50,000-token reservation limit
  |
  +-- Primary LLM (Port 8001)
  |      |
  |      +-- Success -> Return response
  |      +-- HTTP 429 / Timeout -> Backup
  |
  +-- Backup LLM (Port 8002)
         |
         +-- Success -> Return response
         +-- Failure -> Sanitized gateway error

### Installation

From the repository root:

```bash
python -m pip install -r requirements.txt
```

### Running the Services

Open three separate terminals.

Primary provider:

```bash
python -m uvicorn task4_model_router.mock_models:app --port 8001
```

Backup provider:

```bash
MOCK_PROVIDER=backup python -m uvicorn task4_model_router.mock_models:app --port 8002
```

Model router:

```bash
python -m uvicorn task4_model_router.router:app --port 8000
```

### Example Request

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tenant-demo" \
  -d '{"prompt":"Hello AI","max_tokens":100}'
```

### Testing

Run Task 4 tests:

```bash
python -m pytest task4_model_router/test_router.py -v --import-mode=importlib
```

Run all assessment tests:

```bash
python -m pytest -v --import-mode=importlib
```

### Test Coverage

- Token limit enforcement
- Tenant isolation
- Sliding-window expiration
- Concurrent token reservations
- Primary provider success
- HTTP 429 fallback
- Primary timeout fallback
- Sanitized upstream errors
- Input-token accounting

### Implementation Notes

Input tokens are estimated using approximately four characters
per token. This is an approximation rather than an exact tokenizer.

The router reserves estimated input tokens plus the maximum
requested output tokens before sending a request.

A production implementation should use model-specific tokenizers,
reconcile reservations against actual provider usage, and define
how failed requests affect token accounting.

SQLite database files are excluded from Git.
```
