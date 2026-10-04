from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.errors import ErrorCode
from app.schemas.domain import GitHubRepoUrl, WorkspaceId
from app.schemas.paths import validate_posix_path
from app.schemas.validators import validate_repo_name


class AnalysisDepth(StrEnum):
    STANDARD = "standard"


class HealthResponse(BaseModel):
    status: Literal["ok"]


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    repo_url: GitHubRepoUrl
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    url: GitHubRepoUrl
    commit: str = Field(..., pattern=r"^[0-9a-f]{40}$")

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        return validate_repo_name(v)


class SnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    format: Literal["yaml"] = "yaml"
    location: str

    @model_validator(mode="after")
    def validate_location(self) -> "SnapshotResponse":
        p = PurePosixPath(self.location)
        validate_posix_path(p)
        return self


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

    @model_validator(mode="after")
    def validate_snapshot_location(self) -> "AnalyzeResponse":
        expected = f"{self.workspace_id}/repository_snapshot.yaml"
        if self.snapshot.location != expected:
            raise ValueError(f"Snapshot location must be exactly {expected}")
        return self


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    error_code: ErrorCode
    status: AnalyzeResponseStatus = AnalyzeResponseStatus.ERROR
    message: str
