from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    INVALID_URL = "invalid_url"
    CLONE_FAILED = "clone_failed"
    TIMEOUT = "timeout"
    TOOL_FAILED = "tool_failed"
    SNAPSHOT_INVALID = "snapshot_invalid"
    WORKSPACE_NOT_FOUND = "workspace_not_found"


class SecFlowError(Exception):
    """Base domain exception mapped to stable error codes."""

    stable_code: ErrorCode
    message: str

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(self.message)
        self.details = details or {}


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
