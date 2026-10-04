from dataclasses import dataclass, field
from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_URL = "invalid_url"
    INVALID_REQUEST = "invalid_request"
    CLONE_FAILED = "clone_failed"
    TIMEOUT = "timeout"
    TOOL_FAILED = "tool_failed"
    SNAPSHOT_INVALID = "snapshot_invalid"
    WORKSPACE_NOT_FOUND = "workspace_not_found"
    NOT_IMPLEMENTED = "not_implemented"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class ErrorContext:
    raw_input: str | None = field(default=None, repr=False)
    tool_name: str | None = None
    exit_code: int | None = None
    path: str | None = field(default=None, repr=False)


class SecFlowError(Exception):
    """Base domain exception mapped to stable error codes."""

    stable_code: ErrorCode
    message: str

    def __init__(self, internal_ctx: ErrorContext | None = None) -> None:
        if not hasattr(self.__class__, "stable_code") or not hasattr(self.__class__, "message"):
            raise TypeError("SecFlowError must be subclassed with stable_code and message")
        super().__init__(self.message)
        self._internal_ctx = internal_ctx or ErrorContext()


class InvalidUrlError(SecFlowError):
    stable_code = ErrorCode.INVALID_URL
    message = "The provided URL is not a valid GitHub repository URL."


class CloneFailedError(SecFlowError):
    stable_code = ErrorCode.CLONE_FAILED
    message = "Failed to clone the repository."


class AnalysisTimeoutError(SecFlowError):
    stable_code = ErrorCode.TIMEOUT
    message = "Analysis timed out."


class ToolFailedError(SecFlowError):
    stable_code = ErrorCode.TOOL_FAILED
    message = "An analysis tool failed unexpectedly."


class SnapshotInvalidError(SecFlowError):
    stable_code = ErrorCode.SNAPSHOT_INVALID
    message = "The generated snapshot is invalid."


class WorkspaceNotFoundError(SecFlowError):
    stable_code = ErrorCode.WORKSPACE_NOT_FOUND
    message = "The requested workspace does not exist or has expired."


class NotImplementedYetError(SecFlowError):
    stable_code = ErrorCode.NOT_IMPLEMENTED
    message = "Endpoint or feature is not implemented yet."
