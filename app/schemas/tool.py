from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.limits import LIMIT_MAX_OUTPUT_ITEMS, LIMIT_TOOL_TIMEOUT_SECONDS_MAX
from app.schemas.paths import validate_posix_path


class ToolContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_path: Path = Field(
        ..., description="Absolute path to the cloned repository workspace."
    )
    include_paths: list[PurePosixPath] = Field(
        default_factory=list,
        description="List of relative POSIX paths to explicitly include in the analysis.",
    )
    exclude_paths: list[PurePosixPath] = Field(
        default_factory=list,
        description="List of relative POSIX paths to explicitly exclude from the analysis.",
    )
    timeout_seconds: int = Field(
        ...,
        gt=0,
        le=LIMIT_TOOL_TIMEOUT_SECONDS_MAX,
        description="Maximum execution time for the tool in seconds.",
    )
    max_output_items: int = Field(
        ...,
        gt=0,
        le=LIMIT_MAX_OUTPUT_ITEMS,
        description="Maximum number of findings or items the tool should return.",
    )

    @model_validator(mode="after")
    def validate_paths(self) -> "ToolContext":
        if not self.repository_path.is_absolute():
            raise ValueError(f"repository_path must be absolute: {self.repository_path}")
        for p in self.include_paths + self.exclude_paths:
            validate_posix_path(p)
        return self


class ToolSpec(BaseModel):
    """
    Static metadata defining the tool's contract and usage context for Team 2 (AI agents).
    This must contain only static constants, never dynamic data derived from hostile repositories.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., min_length=1, description="The exact string identifying the tool.")
    purpose: str = Field(
        ..., min_length=1, description="A one-sentence description of what the tool does."
    )
    when_to_use: str = Field(
        ..., min_length=1, description="Conditions under which this tool is appropriate."
    )
    when_not_to_use: str = Field(
        ..., min_length=1, description="Conditions under which this tool should be avoided."
    )
    input_schema: dict[str, Any] = Field(
        ..., description="JSON schema defining the valid input structure."
    )
    output_schema: dict[str, Any] = Field(
        ..., description="JSON schema defining the exact output structure."
    )
    evidence_semantics: str = Field(
        ..., min_length=1, description="Description of the evidence returned by this tool."
    )
    limits: str = Field(
        ..., min_length=1, description="Description of the bounds and limitations of the tool."
    )


class ToolName(StrEnum):
    GIT = "git"
    SCC = "scc"
    TREE_SITTER = "tree-sitter"
    SYFT = "syft"
    SEMGREP = "semgrep"
    DETECT_SECRETS = "detect-secrets"


class ToolStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


# Typed data models per tool


class SecretFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    detector: str = Field(..., description="The name of the detector that found the secret.")
    path: PurePosixPath = Field(..., description="The file path where the secret was found.")
    line: int = Field(..., gt=0, description="The line number.")
    # NO value field to prevent leakage

    @model_validator(mode="after")
    def validate_path(self) -> "SecretFinding":
        validate_posix_path(self.path)
        return self


class SecurityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    rule_id: str = Field(..., description="The ID of the violated rule.")
    severity: str = Field(..., description="The severity of the finding.")
    path: PurePosixPath = Field(..., description="The file path.")
    line: int = Field(..., gt=0, description="The line number.")

    @model_validator(mode="after")
    def validate_path(self) -> "SecurityFinding":
        validate_posix_path(self.path)
        return self


class SccData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    # Minimal fields for Phase 1.1
    metrics: list[str] = Field(default_factory=list, description="SCC metrics summary")


class TreeSitterData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    # Minimal fields for Phase 1.1
    nodes: list[str] = Field(default_factory=list, description="Extracted AST nodes summary")


class SyftData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    # Minimal fields for Phase 1.1
    packages: list[str] = Field(default_factory=list, description="Syft packages summary")


class SemgrepData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    findings: list[SecurityFinding] = Field(default_factory=list, description="Semgrep findings")


class DetectSecretsData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    findings: list[SecretFinding] = Field(
        default_factory=list, description="Secret findings without values"
    )


class ToolResult[TData](BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: ToolName = Field(..., description="Name of the tool that ran.")
    status: ToolStatus = Field(..., description="Execution status.")
    evidence: list[PurePosixPath] = Field(
        default_factory=list, description="List of evidence paths."
    )
    data: TData = Field(..., description="Tool-specific structured data.")
    warnings: list[str] = Field(default_factory=list, description="Warnings emitted during run.")

    @model_validator(mode="after")
    def validate_evidence(self) -> "ToolResult[TData]":
        for e in self.evidence:
            validate_posix_path(e)
        return self
