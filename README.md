
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
