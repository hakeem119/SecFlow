from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from ..core.errors import ErrorCode
from .domain import GitHubRepoUrl, WorkspaceId


class AnalysisDepth(StrEnum):
    STANDARD = "standard"


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    repo_url: GitHubRepoUrl
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    url: str
    commit: str


class SnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    format: str = "yaml"
    location: str


class AnalyzeResponseStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    status: AnalyzeResponseStatus
    workspace_id: WorkspaceId
    repository: RepositoryResponse
    snapshot: SnapshotResponse
    warnings: list[str]


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    error_code: ErrorCode
    status: AnalyzeResponseStatus = AnalyzeResponseStatus.ERROR
    message: str
