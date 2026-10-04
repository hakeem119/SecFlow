from collections.abc import Iterator
from pathlib import Path

import pytest
from app.api.middleware import SecurityMiddleware
from app.core.config import Settings
from app.core.limits import LIMIT_MAX_REQUEST_BODY_BYTES
from app.main import create_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send


@pytest.fixture
def app_instance() -> FastAPI:
    return create_app(
        Settings(workspace_root=Path("/var/lib/secflow/workspaces"), enable_docs=False)
    )


@pytest.fixture
def client(app_instance: FastAPI) -> TestClient:
    return TestClient(app_instance, raise_server_exceptions=False)


def test_docs_disabled_by_default(client: TestClient) -> None:
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_docs_enabled() -> None:
    app = create_app(Settings(workspace_root=Path("/var/lib/secflow/workspaces"), enable_docs=True))
    with TestClient(app) as test_client:
        assert test_client.get("/openapi.json").status_code == 200


def test_hostile_echo(client: TestClient) -> None:
    marker = "HOSTILE_MARKER_123"

    # 1. Body
    response = client.post(
        "/api/v1/repositories/analyze",
        json={"repo_url": f"https://github.com/owner/{marker}", "analysis_depth": "standard"},
    )
    assert marker not in response.text
    for v in response.headers.values():
        assert marker not in v

    # 2. Path
    response = client.delete(f"/api/v1/workspaces/{marker}")
    assert marker not in response.text
    for v in response.headers.values():
        assert marker not in v

    # 3. Unknown route
    response = client.get(f"/{marker}")
    assert marker not in response.text
    for v in response.headers.values():
        assert marker not in v

    # 4. Query string
    response = client.get(f"/health?q={marker}")
    assert marker not in response.text
    for v in response.headers.values():
        assert marker not in v


def test_missing_content_type(client: TestClient) -> None:
    response = client.post(
        "/api/v1/repositories/analyze",
        content=b'{"repo_url": "https://github.com/a/b"}',
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 415


def test_oversized_body_with_content_length(client: TestClient) -> None:
    oversized = b"a" * (LIMIT_MAX_REQUEST_BODY_BYTES + 1)
    response = client.post(
        "/api/v1/repositories/analyze",
        content=oversized,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413


def test_oversized_body_chunked(app_instance: FastAPI) -> None:
    def chunk_generator() -> Iterator[bytes]:
        yield b"a" * (LIMIT_MAX_REQUEST_BODY_BYTES // 2)
        yield b"a" * (LIMIT_MAX_REQUEST_BODY_BYTES // 2 + 10)

    with TestClient(app_instance) as tc:
        response = tc.post(
            "/api/v1/repositories/analyze",
            content=chunk_generator(),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413


@pytest.mark.asyncio
async def test_duplicate_content_length() -> None:
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = SecurityMiddleware(dummy_app)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", b"10"),
            (b"content-length", b"10"),
        ],
    }

    async def fake_receive() -> Message:
        return {"type": "http.request", "body": b""}

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    await middleware(scope, fake_receive, fake_send)
    assert responses[0]["status"] == 422
    assert b"Duplicate" in responses[1]["body"]


@pytest.mark.asyncio
async def test_negative_content_length() -> None:
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        pass

    middleware = SecurityMiddleware(dummy_app)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", b"-5"),
        ],
    }

    async def fake_receive() -> Message:
        return {"type": "http.request", "body": b""}

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    await middleware(scope, fake_receive, fake_send)
    assert responses[0]["status"] == 422
    assert b"Negative" in responses[1]["body"]


@pytest.mark.asyncio
async def test_exact_limit_body() -> None:
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = SecurityMiddleware(dummy_app)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(LIMIT_MAX_REQUEST_BODY_BYTES).encode()),
        ],
    }

    async def fake_receive() -> Message:
        return {"type": "http.request", "body": b"a" * LIMIT_MAX_REQUEST_BODY_BYTES}

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    await middleware(scope, fake_receive, fake_send)
    assert responses[0]["status"] == 200


@pytest.mark.asyncio
async def test_non_numeric_content_length() -> None:
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        pass

    middleware = SecurityMiddleware(dummy_app)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", b"abc"),
        ],
    }

    async def fake_receive() -> Message:
        return {"type": "http.request", "body": b""}

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    await middleware(scope, fake_receive, fake_send)
    assert responses[0]["status"] == 422
    assert b"Invalid Content-Length header" in responses[1]["body"]


@pytest.mark.asyncio
async def test_oversized_body_stream_disconnect() -> None:
    # ACCEPTANCE TEST for P2: A test route that sets a mutable flag
    flag = False

    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal flag
        # Consume the entire body
        while True:
            message = await receive()
            if message["type"] == "http.request":
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                # call receive one more time to hit branch coverage for body_too_large = True
                await receive()
                # try to send something to hit body_too_large check in send_wrapper
                await send({"type": "http.response.start", "status": 200, "headers": []})
                return
        flag = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = SecurityMiddleware(dummy_app)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [
            (b"content-type", b"application/json"),
        ],
    }

    # Stream chunk 1 = complete valid small JSON, chunk 2 pushes past the limit, no Content-Length
    chunks = [
        {"type": "http.request", "body": b'{"a": 1}', "more_body": True},
        {"type": "http.request", "body": b"a" * LIMIT_MAX_REQUEST_BODY_BYTES, "more_body": False},
    ]

    async def fake_receive() -> Message:
        if chunks:
            return chunks.pop(0)
        return {"type": "http.disconnect"}

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    await middleware(scope, fake_receive, fake_send)

    # flag is NOT set
    assert flag is False

    # exactly ONE http.response.start was sent
    starts = [m for m in responses if m["type"] == "http.response.start"]
    assert len(starts) == 1

    # Response is 413
    assert starts[0]["status"] == 413
