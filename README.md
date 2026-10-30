
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
