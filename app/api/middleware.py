import logging

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.error_table import TRANSPORT_ERROR_TABLE, TransportError
from app.core.limits import LIMIT_MAX_REQUEST_BODY_BYTES
from app.schemas.api import ErrorResponse

logger = logging.getLogger(__name__)


async def send_error(send: Send, transport_error: TransportError) -> None:
    status_code, error_code, message = TRANSPORT_ERROR_TABLE[transport_error]
    body = (
        ErrorResponse(
            error_code=error_code,
            message=message,
        )
        .model_dump_json()
        .encode("utf-8")
    )

    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    await send({"type": "http.response.start", "status": status_code, "headers": headers})
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

        response_sent = False

        async def secure_send(message: Message) -> None:
            nonlocal response_sent
            if message["type"] == "http.response.start":
                response_sent = True
            await send(message)

        method = scope.get("method", "").upper()
        headers = dict(scope.get("headers", []))

        if method in ("POST", "PUT", "PATCH"):
            content_type_full = headers.get(b"content-type", b"").decode("latin-1")
            content_type = content_type_full.split(";")[0].strip().lower()
            if content_type != "application/json":
                await send_error(secure_send, TransportError.UNSUPPORTED_MEDIA_TYPE)
                return

        # Check Content-Length if present (applies to all methods)
        content_length_header = headers.get(b"content-length")
        if content_length_header is not None:
            cl_count = sum(1 for k, _ in scope.get("headers", []) if k == b"content-length")
            if cl_count > 1:
                await send_error(secure_send, TransportError.DUPLICATE_CONTENT_LENGTH)
                return

            if len(content_length_header) > 12:
                await send_error(secure_send, TransportError.REQUEST_BODY_TOO_LARGE)
                return

            if not content_length_header.isdigit():
                # negative lengths will have a '-', making isdigit() False
                if content_length_header.startswith(b"-") and content_length_header[1:].isdigit():
                    await send_error(secure_send, TransportError.NEGATIVE_CONTENT_LENGTH)
                else:
                    await send_error(secure_send, TransportError.INVALID_CONTENT_LENGTH)
                return

            length = int(content_length_header)
            if length > LIMIT_MAX_REQUEST_BODY_BYTES:
                await send_error(secure_send, TransportError.REQUEST_BODY_TOO_LARGE)
                return

        # Wrap receive to enforce streaming size limit
        body_size = 0
        body_too_large = False

        async def receive_wrapper() -> Message:
            nonlocal body_size, body_too_large
            if body_too_large:
                return {"type": "http.disconnect"}

            message = await receive()
            if message["type"] == "http.request":
                body_size += len(message.get("body", b""))
                if body_size > LIMIT_MAX_REQUEST_BODY_BYTES:
                    body_too_large = True
                    if not response_sent:
                        await send_error(secure_send, TransportError.REQUEST_BODY_TOO_LARGE)
                    return {"type": "http.disconnect"}
            return message

        async def send_wrapper(message: Message) -> None:
            if body_too_large:
                return
            await secure_send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except Exception as exc:  # noqa: BLE001
            # BLE001: deliberate catch-all so exception text never reaches logs
            # TRY400: exc_info forbidden, class name only
            logger.error("Unhandled exception: %s", exc.__class__.__name__)  # noqa: TRY400
            if not response_sent:
                await send_error(secure_send, TransportError.INTERNAL_ERROR)
            return
