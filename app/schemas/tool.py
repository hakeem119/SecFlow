from enum import StrEnum
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ToolContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_path: Path = Field(
        ..., description="Absolute path to the cloned repository workspace."
    )
    include_paths: list[Path] = Field(
        default_factory=list,
        description="List of relative POSIX paths to explicitly include in the analysis.",
    )
    exclude_paths: list[Path] = Field(
        default_factory=list,
        description="List of relative POSIX paths to explicitly exclude from the analysis.",
    )
    timeout_seconds: int = Field(
        ..., gt=0, description="Maximum execution time for the tool in seconds."
    )
    max_output_items: int = Field(
        ..., gt=0, description="Maximum number of findings or items the tool should return."
    )

    @model_validator(mode="after")
    def validate_relative_paths(self) -> "ToolContext":
        for p in self.include_paths + self.exclude_paths:
            if p.is_absolute():
                raise ValueError(f"Path must be relative: {p}")
            if ".." in p.parts:
                raise ValueError(f"Path traversal not allowed: {p}")
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


class ToolStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR = "error"


# Typed data models per tool


class SccData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    languages: dict[str, Any] = Field(default_factory=dict, description="SCC language metrics")


class TreeSitterData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    nodes: list[dict[str, Any]] = Field(default_factory=list, description="Extracted AST nodes")


class SyftData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sbom: dict[str, Any] = Field(default_factory=dict, description="Syft SBOM data")


class SemgrepData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    findings: list[dict[str, Any]] = Field(default_factory=list, description="Semgrep findings")


class DetectSecretsData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    findings: list[dict[str, Any]] = Field(
        default_factory=list, description="Secret findings without values"
    )


TData = TypeVar(
    "TData", SccData, TreeSitterData, SyftData, SemgrepData, DetectSecretsData, type[None]
)


class ToolResult[TData](BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: str = Field(..., description="Name of the tool that ran.")
    status: ToolStatus = Field(..., description="Execution status.")
    evidence: list[str] = Field(default_factory=list, description="List of evidence paths.")
    data: TData = Field(..., description="Tool-specific structured data.")
    warnings: list[str] = Field(default_factory=list, description="Warnings emitted during run.")
