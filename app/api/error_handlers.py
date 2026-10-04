import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.error_table import ERROR_TABLE
from app.core.errors import ErrorCode, SecFlowError
from app.schemas.api import ErrorResponse

logger = logging.getLogger(__name__)


async def secflow_error_handler(request: Request, exc: SecFlowError) -> JSONResponse:
    # A missing code must raise KeyError
    status_code, message_override = ERROR_TABLE[exc.stable_code]
    # We use the exception's own message if available, otherwise fallback
    message = exc.message if exc.message else message_override
    response = ErrorResponse(error_code=exc.stable_code, message=message)
    return JSONResponse(status_code=status_code, content=response.model_dump())


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Check if any error is about repo_url
    is_url_error = False
    for err in exc.errors():
        if "repo_url" in err.get("loc", []):
            is_url_error = True
            break

    error_code = ErrorCode.INVALID_URL if is_url_error else ErrorCode.INVALID_REQUEST

    status_code, message = ERROR_TABLE[error_code]
    response = ErrorResponse(error_code=error_code, message=message)
    return JSONResponse(status_code=status_code, content=response.model_dump())


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code == 404:
        status_code, message = ERROR_TABLE["not_found"]
    elif exc.status_code == 405:
        status_code, message = ERROR_TABLE["method_not_allowed"]
    else:
        # Default for other HTTPExceptions
        status_code, message = ERROR_TABLE["http_exception"]
        # Use actual exception status_code, but keep error_table message/status as defaults
        status_code = exc.status_code

    error_code = ErrorCode.INVALID_REQUEST
    response = ErrorResponse(error_code=error_code, message=message)

    headers = getattr(exc, "headers", None)
    return JSONResponse(status_code=status_code, content=response.model_dump(), headers=headers)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Log only the class name server-side to prevent leakage
    logger.error("Unhandled exception: %s", exc.__class__.__name__)

    status_code, message = ERROR_TABLE[ErrorCode.INTERNAL_ERROR]
    response = ErrorResponse(error_code=ErrorCode.INTERNAL_ERROR, message=message)
    return JSONResponse(status_code=status_code, content=response.model_dump())
