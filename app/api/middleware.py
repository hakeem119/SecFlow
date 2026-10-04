import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import ErrorCode
from app.core.limits import LIMIT_MAX_REQUEST_BODY_BYTES


def _build_error_response(
    status_code: int, error_code: str, message: str
) -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    """Helper to build standard error response for ASGI layer."""
    body = json.dumps(
        {
            "error_code": error_code,
            "status": "error",
            "message": message,
        }
    ).encode("utf-8")

    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    return status_code, headers, body


async def send_error(send: Send, status_code: int, error_code: str, message: str) -> None:
    code, headers, body = _build_error_response(status_code, error_code, message)
    await send({"type": "http.response.start", "status": code, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class SecurityMiddleware:
    """
    ASGI Middleware to enforce request body size limits and Content-Type.
    Intercepts at ASGI level to short-circuit before FastAPI parses the request,
    preventing memory exhaustion and ensuring error responses match ErrorResponse.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        method = scope.get("method", "").upper()
        headers = dict(scope.get("headers", []))

        if method in ("POST", "PUT", "PATCH"):
            content_type_full = headers.get(b"content-type", b"").decode("latin-1")
            content_type = content_type_full.split(";")[0].strip().lower()
            if content_type != "application/json":
                await send_error(
                    send,
                    415,
                    ErrorCode.INVALID_REQUEST,
                    "Unsupported Media Type: Must be application/json",
                )
                return

        # Check Content-Length if present (applies to all methods)
        content_length_header = headers.get(b"content-length", b"")
        if content_length_header:
            cl_count = sum(1 for k, _ in scope.get("headers", []) if k == b"content-length")
            if cl_count > 1:
                await send_error(
                    send, 422, ErrorCode.INVALID_REQUEST, "Duplicate Content-Length header"
                )
                return
            try:
                length = int(content_length_header)
                if length < 0:
                    await send_error(
                        send, 422, ErrorCode.INVALID_REQUEST, "Negative Content-Length header"
                    )
                    return
                if length > LIMIT_MAX_REQUEST_BODY_BYTES:
                    await send_error(send, 413, ErrorCode.INVALID_REQUEST, "Request body too large")
                    return
            except ValueError:
                await send_error(
                    send, 422, ErrorCode.INVALID_REQUEST, "Invalid Content-Length header"
                )
                return

        # Wrap receive to enforce streaming size limit
        body_size = 0
        body_too_large = False
        response_started = False

        async def receive_wrapper() -> Message:
            nonlocal body_size, body_too_large
            message = await receive()
            if message["type"] == "http.request" and not body_too_large:
                body_size += len(message.get("body", b""))
                if body_size > LIMIT_MAX_REQUEST_BODY_BYTES:
                    body_too_large = True
                    if not response_started:
                        await send_error(
                            send, 413, ErrorCode.INVALID_REQUEST, "Request body too large"
                        )
                    return {"type": "http.disconnect"}
            return message

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if body_too_large:
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        await self.app(scope, receive_wrapper, send_wrapper)
