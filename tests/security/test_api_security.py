import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from _pytest.logging import LogCaptureFixture
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


def test_unhandled_exception_security(caplog: LogCaptureFixture) -> None:
    # Q1 Acceptance test
    caplog.set_level(logging.DEBUG, logger="")

    app = create_app(
        Settings(workspace_root=Path("/var/lib/secflow/workspaces"), enable_docs=False)
    )

    @app.get("/test_500")
    def test_500() -> None:
        raise RuntimeError("SECRET-MARKER-123")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test_500")

    assert response.status_code == 500
    data = response.json()
    assert data["error_code"] == "internal_error"

    marker = "SECRET-MARKER-123"
    # The marker appears in NO record's message, args, exc_text or formatted traceback
    # no record has exc_info; a record with the class name exists.
    class_name_found = False
    for record in caplog.records:
        assert marker not in record.message
        if getattr(record, "args", None):
            assert marker not in str(record.args)
        assert getattr(record, "exc_text", None) is None
        assert getattr(record, "exc_info", None) is None

        if "RuntimeError" in record.message:
            class_name_found = True

    assert class_name_found


def test_create_app_oversized_body_stream_disconnect(caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    app = create_app(
        Settings(workspace_root=Path("/var/lib/secflow/workspaces"), enable_docs=False)
    )

    flag = False

    from pydantic import BaseModel

    class Chunk1(BaseModel):
        a: int

    @app.post("/test_chunked")
    def test_chunked(body: Chunk1) -> dict[str, str]:
        nonlocal flag
        flag = True
        return {"status": "ok"}

    def chunk_generator() -> Iterator[bytes]:
        yield b'{"a": 1}'
        yield b"a" * LIMIT_MAX_REQUEST_BODY_BYTES

    client = TestClient(app)
    response = client.post(
        "/test_chunked", content=chunk_generator(), headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 413
    assert response.json()["error_code"] == "invalid_request"
    assert response.json()["message"] == "Request body too large"
    assert flag is False

    for record in caplog.records:
        assert "validation" not in record.name.lower()


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
async def test_asgi_middleware_receive_wrapper_short_circuits() -> None:
    # At ASGI level: after the limit trips, the wrapper must not call the underlying
    # receive() again (return http.disconnect directly); add a test where the
    # underlying receive would block forever and the app calls receive() twice.
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        message1 = await receive()
        assert message1["type"] == "http.disconnect"
        message2 = await receive()
        assert message2["type"] == "http.disconnect"
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

    receive_calls = 0

    async def fake_receive() -> Message:
        nonlocal receive_calls
        receive_calls += 1
        if receive_calls == 1:
            return {
                "type": "http.request",
                "body": b"a" * (LIMIT_MAX_REQUEST_BODY_BYTES + 1),
                "more_body": True,
            }

        # If it calls receive again, block forever.
        # (Simulated via a very long sleep, but we use asyncio.wait_for)
        import asyncio

        await asyncio.sleep(86400)
        return {"type": "http.disconnect"}

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    import asyncio

    # using wait_for to ensure it doesn't actually block forever
    await asyncio.wait_for(middleware(scope, fake_receive, fake_send), timeout=2.0)

    # 1. 413 response is sent
    starts = [m for m in responses if m["type"] == "http.response.start"]
    assert len(starts) == 1
    assert starts[0]["status"] == 413

    # 2. fake_receive was called exactly once
    assert receive_calls == 1


@pytest.mark.asyncio
async def test_receive_disconnect_before_limit() -> None:
    # Covers branch 87->94: message type is not http.request
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        message = await receive()
        assert message["type"] == "http.disconnect"

    middleware = SecurityMiddleware(dummy_app)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json")],
    }

    async def fake_receive() -> Message:
        return {"type": "http.disconnect"}

    async def fake_send(message: Message) -> None:
        pass

    await middleware(scope, fake_receive, fake_send)


@pytest.mark.asyncio
async def test_limit_trips_after_response_started() -> None:
    # Covers branch 91->93: response started, then body too large
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        message = await receive()
        assert message["type"] == "http.disconnect"

    middleware = SecurityMiddleware(dummy_app)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json")],
    }

    async def fake_receive() -> Message:
        return {
            "type": "http.request",
            "body": b"a" * (LIMIT_MAX_REQUEST_BODY_BYTES + 1),
            "more_body": True,
        }

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    await middleware(scope, fake_receive, fake_send)
    assert responses[0]["type"] == "http.response.start"
    assert responses[0]["status"] == 200
    # No 413 was sent because response already started!
    assert len([m for m in responses if m["type"] == "http.response.start"]) == 1


@pytest.mark.asyncio
async def test_exception_after_response_started() -> None:
    # Covers branch 108->110: unhandled exception after response started
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        raise RuntimeError("Crash")

    middleware = SecurityMiddleware(dummy_app)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json")],
    }

    async def fake_receive() -> Message:
        return {"type": "http.request", "body": b""}

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    await middleware(scope, fake_receive, fake_send)
    assert responses[0]["type"] == "http.response.start"
    assert responses[0]["status"] == 200
    assert len([m for m in responses if m["type"] == "http.response.start"]) == 1


@pytest.mark.asyncio
async def test_content_length_max_digits(caplog: LogCaptureFixture) -> None:
    # 5000-digit Content-Length -> 413, no exception, no log record with exc_info
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        pass

    middleware = SecurityMiddleware(dummy_app)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json"), (b"content-length", b"9" * 5000)],
    }

    async def fake_receive() -> Message:
        return {"type": "http.request", "body": b""}

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    await middleware(scope, fake_receive, fake_send)
    assert responses[0]["status"] == 413
    assert not any("exc_info" in record.getMessage() for record in caplog.records)


@pytest.mark.asyncio
async def test_content_length_max_digits_non_numeric(caplog: LogCaptureFixture) -> None:
    # 5000-character non-numeric Content-Length -> 422, no exception, no log record with exc_info
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        pass

    middleware = SecurityMiddleware(dummy_app)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json"), (b"content-length", b"a" * 5000)],
    }

    async def fake_receive() -> Message:
        return {"type": "http.request", "body": b""}

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    await middleware(scope, fake_receive, fake_send)
    assert responses[0]["status"] == 422
    assert not any("exc_info" in record.getMessage() for record in caplog.records)


@pytest.mark.asyncio
async def test_content_length_12_digits_within_limit() -> None:
    # exactly 12 digits within limit boundary, leading zeros accepted
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})

    middleware = SecurityMiddleware(dummy_app)
    # 12-digit number with leading zeros, value is exactly LIMIT_MAX_REQUEST_BODY_BYTES
    val_str = str(LIMIT_MAX_REQUEST_BODY_BYTES).zfill(12)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json"), (b"content-length", val_str.encode())],
    }

    async def fake_receive() -> Message:
        return {"type": "http.request", "body": b""}

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    await middleware(scope, fake_receive, fake_send)
    assert responses[0]["status"] == 200


@pytest.mark.asyncio
async def test_exception_after_limit_trips_mid_stream(caplog: LogCaptureFixture) -> None:
    # limit trips mid-stream (sends 413), then app raises RuntimeError -> exactly ONE response start
    # one log line with class name, nothing re-raised
    async def dummy_app(scope: Scope, receive: Receive, send: Send) -> None:
        message = await receive()
        assert message["type"] == "http.disconnect"
        # The limit tripped and receive_wrapper sent 413. Now crash.
        raise RuntimeError("Crash")

    middleware = SecurityMiddleware(dummy_app)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json")],
    }

    async def fake_receive() -> Message:
        return {
            "type": "http.request",
            "body": b"a" * (LIMIT_MAX_REQUEST_BODY_BYTES + 1),
            "more_body": True,
        }

    responses: list[Message] = []

    async def fake_send(message: Message) -> None:
        responses.append(message)

    await middleware(scope, fake_receive, fake_send)
    starts = [m for m in responses if m["type"] == "http.response.start"]
    assert len(starts) == 1
    assert starts[0]["status"] == 413

    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(errors) == 1
    assert "Unhandled exception: RuntimeError" in errors[0].getMessage()
