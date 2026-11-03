
import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from task2_mcp_gateway.gateway import app

client = TestClient(app)

URL = "/mcp"


def make_request(tool):
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": {
                "customer_id": "CUST-12345"
            },
        },
    }


@pytest.fixture
def mock_downstream():
    response = httpx.Response(
        200,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "Mock execution"
                    }
                ]
            },
        },
        request=httpx.Request(
            "POST",
            "http://127.0.0.1:8001/mcp"
        ),
    )

    with patch(
        "task2_mcp_gateway.gateway.httpx.AsyncClient.post",
        new_callable=AsyncMock,
    ) as mock_post:
        mock_post.return_value = response
        yield mock_post


# TEST 1: Viewer cannot execute admin tools
def test_viewer_cannot_delete_customer(mock_downstream):
    response = client.post(
        URL,
        json=make_request("admin_delete_customer"),
        headers={
            "Authorization": "Bearer viewer-token"
        },
    )

    assert response.status_code == 403
    assert (
        response.json()["error"]["message"]
        == "Unauthorized Tool Call"
    )
    mock_downstream.assert_not_awaited()


# TEST 2: Admin can execute admin tools
def test_admin_can_delete_customer(mock_downstream):
    response = client.post(
        URL,
        json=make_request("admin_delete_customer"),
        headers={
            "Authorization": "Bearer admin-token"
        },
    )

    assert response.status_code == 200
    mock_downstream.assert_awaited_once()


# TEST 3: Viewer can access read-only tools
def test_viewer_can_read_customer(mock_downstream):
    response = client.post(
        URL,
        json=make_request("get_customer_record"),
        headers={
            "Authorization": "Bearer viewer-token"
        },
    )

    assert response.status_code == 200
    mock_downstream.assert_awaited_once()


# TEST 4: Missing authentication
def test_missing_authentication(mock_downstream):
    response = client.post(
        URL,
        json=make_request("get_customer_record"),
    )

    assert response.status_code == 401
    assert (
        response.json()["error"]["message"]
        == "Authentication required"
    )
    mock_downstream.assert_not_awaited()


# TEST 5: Invalid authentication token
def test_invalid_token(mock_downstream):
    response = client.post(
        URL,
        json=make_request("get_customer_record"),
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401
    mock_downstream.assert_not_awaited()


# TEST 6: Downstream server unavailable
def test_downstream_unavailable():
    with patch(
        "task2_mcp_gateway.gateway.httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError(
            "Connection failed"
        ),
    ):
        response = client.post(
            URL,
            json=make_request("get_customer_record"),
            headers={
                "Authorization": "Bearer viewer-token"
            },
        )

    assert response.status_code == 502
    assert (
        response.json()["error"]["message"]
        == "Downstream unavailable"
    )
