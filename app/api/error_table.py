from enum import StrEnum

from app.core.errors import ErrorCode


class TransportError(StrEnum):
    REQUEST_BODY_TOO_LARGE = "request_body_too_large"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    DUPLICATE_CONTENT_LENGTH = "duplicate_content_length"
    NEGATIVE_CONTENT_LENGTH = "negative_content_length"
    INVALID_CONTENT_LENGTH = "invalid_content_length"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    HTTP_EXCEPTION = "http_exception"
    INTERNAL_ERROR = "internal_error"
    INVALID_URL = "invalid_url"
    INVALID_REQUEST = "invalid_request"


# Status code for domain errors
DOMAIN_STATUS_TABLE: dict[ErrorCode, int] = {
    ErrorCode.INVALID_URL: 422,
    ErrorCode.INVALID_REQUEST: 422,
    ErrorCode.WORKSPACE_NOT_FOUND: 404,
    ErrorCode.CLONE_FAILED: 502,
    ErrorCode.TIMEOUT: 504,
    ErrorCode.TOOL_FAILED: 500,
    ErrorCode.SNAPSHOT_INVALID: 500,
    ErrorCode.NOT_IMPLEMENTED: 501,
    ErrorCode.INTERNAL_ERROR: 500,
}

# (status_code, error_code, message) for transport and generic errors
TRANSPORT_ERROR_TABLE: dict[TransportError, tuple[int, ErrorCode, str]] = {
    TransportError.REQUEST_BODY_TOO_LARGE: (
        413,
        ErrorCode.INVALID_REQUEST,
        "Request body too large",
    ),
    TransportError.UNSUPPORTED_MEDIA_TYPE: (
        415,
        ErrorCode.INVALID_REQUEST,
        "Unsupported Media Type: Must be application/json",
    ),
    TransportError.DUPLICATE_CONTENT_LENGTH: (
        422,
        ErrorCode.INVALID_REQUEST,
        "Duplicate Content-Length header",
    ),
    TransportError.NEGATIVE_CONTENT_LENGTH: (
        422,
        ErrorCode.INVALID_REQUEST,
        "Negative Content-Length header",
    ),
    TransportError.INVALID_CONTENT_LENGTH: (
        422,
        ErrorCode.INVALID_REQUEST,
        "Invalid Content-Length header",
    ),
    TransportError.NOT_FOUND: (404, ErrorCode.INVALID_REQUEST, "Not found"),
    TransportError.METHOD_NOT_ALLOWED: (405, ErrorCode.INVALID_REQUEST, "Method not allowed"),
    TransportError.HTTP_EXCEPTION: (400, ErrorCode.INVALID_REQUEST, "HTTP Exception"),
    TransportError.INTERNAL_ERROR: (500, ErrorCode.INTERNAL_ERROR, "Internal server error"),
    TransportError.INVALID_URL: (422, ErrorCode.INVALID_URL, "Invalid GitHub repository URL"),
    TransportError.INVALID_REQUEST: (422, ErrorCode.INVALID_REQUEST, "Invalid request payload"),
}
