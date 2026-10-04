from pathlib import Path

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class RepositoryInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(...)
    url: str = Field(...)
    commit: str = Field(...)
    default_branch: str = Field(...)


class WorkspaceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(...)


class FileInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: Path = Field(...)
    type: str = Field(...)
    language: str = Field(...)
    size: int = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_relative_path(self) -> "FileInfo":
        if self.path.is_absolute() or ".." in self.path.parts:
            raise ValueError(f"Path must be relative and cannot traverse: {self.path}")
        return self


class StructureInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    directories: list[Path] = Field(...)
    files: list[FileInfo] = Field(...)


class LanguageMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(...)
    files: int = Field(..., ge=0)
    loc: int = Field(..., ge=0)


class MetricsInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    loc: int = Field(..., ge=0)
    complexity: int = Field(..., ge=0)
    languages: list[LanguageMetrics] = Field(...)


class PackageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(...)
    version: str = Field(...)
    ecosystem: str = Field(...)
    source_file: Path = Field(...)


class DependenciesInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ecosystems: list[str] = Field(...)
    packages: list[PackageInfo] = Field(...)


class SyntaxEvidenceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    imports: list[dict[str, str | int]] = Field(default_factory=list)
    functions: list[dict[str, str | int]] = Field(default_factory=list)
    classes: list[dict[str, str | int]] = Field(default_factory=list)
    decorators: list[dict[str, str | int]] = Field(default_factory=list)


class SecurityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    rule_id: str = Field(...)
    severity: str = Field(...)
    path: Path = Field(...)
    line: int = Field(..., gt=0)


class SecretFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    detector: str = Field(...)
    path: Path = Field(...)
    line: int = Field(..., gt=0)


class SecretFindingsInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    count: int = Field(..., ge=0)
    findings: list[SecretFinding] = Field(...)


class LimitsApplied(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    files_truncated: bool = Field(...)
    items_capped: bool = Field(...)
    excluded_paths: list[Path] = Field(...)


class RepositorySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(default="1.0")
    generated_at: AwareDatetime = Field(...)
    repository: RepositoryInfo = Field(...)
    workspace: WorkspaceInfo = Field(...)
    structure: StructureInfo = Field(...)
    metrics: MetricsInfo = Field(...)
    dependencies: DependenciesInfo = Field(...)
    syntax_evidence: SyntaxEvidenceInfo = Field(...)
    security_evidence: dict[str, list[SecurityFinding]] = Field(default_factory=dict)
    secret_findings: SecretFindingsInfo = Field(...)
    tool_status: dict[str, str] = Field(...)
    limits_applied: LimitsApplied = Field(...)
    warnings: list[str] = Field(default_factory=list)
