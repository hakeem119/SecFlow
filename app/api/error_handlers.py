import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.error_table import DOMAIN_STATUS_TABLE, TRANSPORT_ERROR_TABLE, TransportError
from app.core.errors import SecFlowError
from app.schemas.api import ErrorResponse

logger = logging.getLogger(__name__)


async def secflow_error_handler(request: Request, exc: SecFlowError) -> Response:
    # A missing code must raise KeyError
    status_code = DOMAIN_STATUS_TABLE[exc.stable_code]
    body = ErrorResponse(error_code=exc.stable_code, message=exc.message).model_dump_json()
    return Response(status_code=status_code, content=body, media_type="application/json")


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    # Check if any error is about repo_url
    is_url_error = False
    for err in exc.errors():
        if "repo_url" in err.get("loc", []):
            is_url_error = True
            break

    transport_err = TransportError.INVALID_URL if is_url_error else TransportError.INVALID_REQUEST
    status_code, error_code, message = TRANSPORT_ERROR_TABLE[transport_err]

    body = ErrorResponse(error_code=error_code, message=message).model_dump_json()
    return Response(status_code=status_code, content=body, media_type="application/json")


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
    if exc.status_code == 404:
        status_code, error_code, message = TRANSPORT_ERROR_TABLE[TransportError.NOT_FOUND]
    elif exc.status_code == 405:
        status_code, error_code, message = TRANSPORT_ERROR_TABLE[TransportError.METHOD_NOT_ALLOWED]
    else:
        # Default for other HTTPExceptions
        _, error_code, message = TRANSPORT_ERROR_TABLE[TransportError.HTTP_EXCEPTION]
        status_code = exc.status_code

    body = ErrorResponse(error_code=error_code, message=message).model_dump_json()
    headers = getattr(exc, "headers", None)
    return Response(
        status_code=status_code, content=body, media_type="application/json", headers=headers
    )
