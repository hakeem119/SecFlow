from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.limits import (
    LIMIT_MAX_FILE_COUNT,
    LIMIT_MAX_FILE_SIZE_BYTES,
    LIMIT_MAX_OUTPUT_ITEMS,
    LIMIT_MAX_TOTAL_SIZE_BYTES,
    LIMIT_TOOL_TIMEOUT_SECONDS_MAX,
    LIMIT_TTL_HOURS_MAX,
)


class Settings(BaseSettings):
    """
    Configuration mapped from environment variables.
    Validates limits and settings without module-level global state.
    """

    model_config = SettingsConfigDict(env_prefix="SECFLOW_")

    workspace_root: Path = Field(
        ...,
        description="Absolute path to the workspace root directory.",
    )
    ttl_hours: int = Field(
        default=24,
        gt=0,
        le=LIMIT_TTL_HOURS_MAX,
        description="Time-to-live for workspaces in hours.",
    )

    max_file_size_bytes: int = Field(
        default=10_000_000,
        gt=0,
        le=LIMIT_MAX_FILE_SIZE_BYTES,
        description="Max size per file in bytes.",
    )
    max_file_count: int = Field(
        default=10000, gt=0, le=LIMIT_MAX_FILE_COUNT, description="Max total files to analyze."
    )
    max_total_size_bytes: int = Field(
        default=1_000_000_000,
        gt=0,
        le=LIMIT_MAX_TOTAL_SIZE_BYTES,
        description="Max total size of repository in bytes.",
    )

    tool_timeout_git: int = Field(
        default=120, gt=0, le=LIMIT_TOOL_TIMEOUT_SECONDS_MAX, description="Git clone timeout."
    )
    tool_timeout_scc: int = Field(
        default=60, gt=0, le=LIMIT_TOOL_TIMEOUT_SECONDS_MAX, description="scc timeout."
    )
    tool_timeout_syft: int = Field(
        default=120, gt=0, le=LIMIT_TOOL_TIMEOUT_SECONDS_MAX, description="Syft timeout."
    )
    tool_timeout_semgrep: int = Field(
        default=120, gt=0, le=LIMIT_TOOL_TIMEOUT_SECONDS_MAX, description="Semgrep timeout."
    )
    tool_timeout_tree_sitter: int = Field(
        default=120, gt=0, le=LIMIT_TOOL_TIMEOUT_SECONDS_MAX, description="Tree-sitter timeout."
    )
    tool_timeout_detect_secrets: int = Field(
        default=120, gt=0, le=LIMIT_TOOL_TIMEOUT_SECONDS_MAX, description="detect-secrets timeout."
    )

    max_output_items: int = Field(
        default=500, gt=0, le=LIMIT_MAX_OUTPUT_ITEMS, description="Default max output items."
    )
    max_output_syft: int = Field(
        default=1000, gt=0, le=LIMIT_MAX_OUTPUT_ITEMS, description="Max dependencies from Syft."
    )
    max_output_semgrep: int = Field(
        default=200, gt=0, le=LIMIT_MAX_OUTPUT_ITEMS, description="Max findings from Semgrep."
    )
    max_output_tree_sitter: int = Field(
        default=500, gt=0, le=LIMIT_MAX_OUTPUT_ITEMS, description="Max nodes from Tree-sitter."
    )

    enable_docs: bool = Field(default=False, description="Enable FastAPI OpenAPI docs.")

    @model_validator(mode="after")
    def validate_absolute_paths(self) -> "Settings":
        if not self.workspace_root.is_absolute():
            raise ValueError("workspace_root must be an absolute path")
        return self
