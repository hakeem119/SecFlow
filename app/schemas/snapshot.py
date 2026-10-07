from pathlib import PurePosixPath
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.limits import (
    LIMIT_MAX_FILE_COUNT,
    LIMIT_MAX_OUTPUT_ITEMS,
)
from app.schemas.domain import GitHubRepoUrl, WorkspaceId
from app.schemas.paths import validate_posix_path
from app.schemas.tool import SecretFinding, SecurityFinding, ToolName, ToolStatus
from app.schemas.validators import validate_branch_name, validate_repo_name


class RepositoryInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(...)
    url: GitHubRepoUrl = Field(...)
    commit: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    default_branch: str = Field(...)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        return validate_repo_name(v)

    @field_validator("default_branch")
    @classmethod
    def _validate_branch(cls, v: str) -> str:
        return validate_branch_name(v)


class WorkspaceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: WorkspaceId = Field(...)


class FileInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: PurePosixPath = Field(...)
    type: str = Field(...)
    language: str = Field(...)
    size: int = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_path(self) -> "FileInfo":
        validate_posix_path(self.path)
        return self


class StructureInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    directories: list[PurePosixPath] = Field(..., max_length=LIMIT_MAX_FILE_COUNT)
    files: list[FileInfo] = Field(..., max_length=LIMIT_MAX_FILE_COUNT)

    @model_validator(mode="after")
    def validate_paths(self) -> "StructureInfo":
        for d in self.directories:
            validate_posix_path(d)
        return self


class LanguageMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(...)
    files: int = Field(..., ge=0)
    loc: int = Field(..., ge=0)


class MetricsInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    loc: int = Field(..., ge=0)
    complexity: int = Field(..., ge=0)
    languages: list[LanguageMetrics] = Field(..., max_length=LIMIT_MAX_OUTPUT_ITEMS)


class PackageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(...)
    version: str = Field(...)
    ecosystem: str = Field(...)
    source_file: PurePosixPath = Field(...)

    @model_validator(mode="after")
    def validate_path(self) -> "PackageInfo":
        validate_posix_path(self.source_file)
        return self


class DependenciesInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ecosystems: list[str] = Field(..., max_length=LIMIT_MAX_OUTPUT_ITEMS)
    packages: list[PackageInfo] = Field(..., max_length=LIMIT_MAX_OUTPUT_ITEMS)


class SyntaxEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str | None = Field(default=None)
    path: PurePosixPath = Field(...)
    start_line: int = Field(..., gt=0)
    end_line: int = Field(..., gt=0)

    @model_validator(mode="after")
    def validate_item(self) -> "SyntaxEvidenceItem":
        validate_posix_path(self.path)
        if self.start_line > self.end_line:
            raise ValueError("start_line cannot be greater than end_line")
        return self


class SyntaxEvidenceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    imports: list[SyntaxEvidenceItem] = Field(
        default_factory=list, max_length=LIMIT_MAX_OUTPUT_ITEMS
    )
    functions: list[SyntaxEvidenceItem] = Field(
        default_factory=list, max_length=LIMIT_MAX_OUTPUT_ITEMS
    )
    classes: list[SyntaxEvidenceItem] = Field(
        default_factory=list, max_length=LIMIT_MAX_OUTPUT_ITEMS
    )
    decorators: list[SyntaxEvidenceItem] = Field(
        default_factory=list, max_length=LIMIT_MAX_OUTPUT_ITEMS
    )


class SecurityEvidenceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    semgrep: list[SecurityFinding] = Field(default_factory=list, max_length=LIMIT_MAX_OUTPUT_ITEMS)


class SecretFindingsInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    count: int = Field(..., ge=0)
    findings: list[SecretFinding] = Field(..., max_length=LIMIT_MAX_OUTPUT_ITEMS)

    @model_validator(mode="after")
    def validate_count(self) -> "SecretFindingsInfo":
        if self.count < len(self.findings):
            raise ValueError("count cannot be less than the number of findings")
        return self


class LimitsApplied(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    files_truncated: bool = Field(...)
    items_capped: bool = Field(...)
    excluded_paths: list[PurePosixPath] = Field(..., max_length=LIMIT_MAX_FILE_COUNT)

    @model_validator(mode="after")
    def validate_paths(self) -> "LimitsApplied":
        for p in self.excluded_paths:
            validate_posix_path(p)
        return self


class RepositorySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = Field(default="1.0")
    generated_at: AwareDatetime = Field(...)
    repository: RepositoryInfo = Field(...)
    workspace: WorkspaceInfo = Field(...)
    structure: StructureInfo = Field(...)
    metrics: MetricsInfo = Field(...)
    dependencies: DependenciesInfo = Field(...)
    syntax_evidence: SyntaxEvidenceInfo = Field(...)
    security_evidence: SecurityEvidenceInfo = Field(...)
    secret_findings: SecretFindingsInfo = Field(...)
    tool_status: dict[ToolName, ToolStatus] = Field(...)
    limits_applied: LimitsApplied = Field(...)
    warnings: list[str] = Field(default_factory=list, max_length=LIMIT_MAX_OUTPUT_ITEMS)
