from app.core.errors import ErrorCode

# Single source of truth for status codes and messages
ERROR_TABLE: dict[ErrorCode | str, tuple[int, str]] = {
    # Domain Errors
    ErrorCode.INVALID_URL: (422, "Invalid GitHub repository URL"),
    ErrorCode.INVALID_REQUEST: (422, "Invalid request payload"),
    ErrorCode.WORKSPACE_NOT_FOUND: (404, "Workspace not found"),
    ErrorCode.CLONE_FAILED: (502, "Failed to clone repository"),
    ErrorCode.TIMEOUT: (504, "Analysis timeout"),
    ErrorCode.TOOL_FAILED: (500, "Tool execution failed"),
    ErrorCode.SNAPSHOT_INVALID: (500, "Invalid snapshot format"),
    ErrorCode.NOT_IMPLEMENTED: (501, "Not implemented"),
    ErrorCode.INTERNAL_ERROR: (500, "Internal server error"),
    # Transport Errors (strings as keys since they are not domain ErrorCode)
    "request_body_too_large": (413, "Request body too large"),
    "unsupported_media_type": (415, "Unsupported Media Type: Must be application/json"),
    "duplicate_content_length": (422, "Duplicate Content-Length header"),
    "negative_content_length": (422, "Negative Content-Length header"),
    "invalid_content_length": (422, "Invalid Content-Length header"),
    "not_found": (404, "Not found"),
    "method_not_allowed": (405, "Method not allowed"),
    "http_exception": (400, "HTTP Exception"),  # Default for other HTTPExceptions
}
