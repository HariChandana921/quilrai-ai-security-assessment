
import pytest
from fastapi.testclient import TestClient

from task3_streaming_guardrail.gateway import app

client = TestClient(app)


def test_gateway_exists():
    """Verify that the gateway application is available."""
    assert app is not None


def test_generate_endpoint_exists():
    """Verify that the streaming endpoint is registered."""
    routes = [route.path for route in app.routes]
    assert "/generate" in routes


def test_gateway_rejects_get_request():
    """Verify that the POST endpoint rejects GET requests."""
    response = client.get("/generate")
    assert response.status_code == 405



import json
import httpx

from task3_streaming_guardrail import gateway


def make_sse(chunks):
    events = []
    for chunk in chunks:
        event = {
            "choices": [
                {"delta": {"content": chunk}}
            ]
        }
        events.append(f"data: {json.dumps(event)}\n\n")

    events.append("data: [DONE]\n\n")
    return "".join(events)


def mock_upstream(monkeypatch, chunks, status_code=200):
    body = make_sse(chunks)

    def handler(request):
        return httpx.Response(
            status_code,
            text=body,
            headers={"content-type": "text/event-stream"},
        )

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(
        gateway.httpx, "AsyncClient", client_factory
    )


def get_stream_text(response):
    result = []
    done = False

    for line in response.text.splitlines():
        if not line.startswith("data: "):
            continue

        data = line[6:]

        if data == "[DONE]":
            done = True
            continue

        event = json.loads(data)
        result.append(
            event["choices"][0]["delta"]["content"]
        )

    return "".join(result), done


def test_email_redaction(monkeypatch):
    mock_upstream(
        monkeypatch,
        ["Contact me at alice@example.com please."],
    )

    response = TestClient(gateway.app).post("/generate")
    text, done = get_stream_text(response)

    assert response.status_code == 200
    assert "alice@example.com" not in text
    assert "[REDACTED]" in text
    assert done


def test_ssn_split_across_chunks(monkeypatch):
    mock_upstream(
        monkeypatch,
        ["My SSN is 123-", "45-", "6789."],
    )

    response = TestClient(gateway.app).post("/generate")
    text, done = get_stream_text(response)

    assert response.status_code == 200
    assert "123-45-6789" not in text
    assert "[REDACTED]" in text
    assert done


def test_credit_card_redaction(monkeypatch):
    mock_upstream(
        monkeypatch,
        ["Card: 4111 1111 ", "1111 1111."],
    )

    response = TestClient(gateway.app).post("/generate")
    text, done = get_stream_text(response)

    assert response.status_code == 200
    assert "4111 1111 1111 1111" not in text
    assert "[REDACTED]" in text
    assert done


def test_normal_text_preserved(monkeypatch):
    original = "Hello! This is a safe message."

    mock_upstream(
        monkeypatch,
        ["Hello! ", "This is a safe message."],
    )

    response = TestClient(gateway.app).post("/generate")
    text, done = get_stream_text(response)

    assert response.status_code == 200
    assert text == original
    assert done


def test_upstream_http_error(monkeypatch):
    mock_upstream(monkeypatch, [], status_code=503)

    response = TestClient(gateway.app).post("/generate")

    assert response.status_code == 502
    assert response.json()["error"] == "Upstream LLM error"


def test_downstream_unavailable(monkeypatch):
    def handler(request):
        raise httpx.ConnectError(
            "Connection failed",
            request=request,
        )

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(
        gateway.httpx, "AsyncClient", client_factory
    )

    response = TestClient(gateway.app).post("/generate")

    assert response.status_code == 502
    assert response.json()["error"] == "Downstream unavailable"
