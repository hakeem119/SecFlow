from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    ttl_hours: int = Field(default=24, gt=0, description="Time-to-live for workspaces in hours.")

    max_file_size_bytes: int = Field(
        default=10_000_000, gt=0, description="Max size per file in bytes."
    )
    max_file_count: int = Field(default=10000, gt=0, description="Max total files to analyze.")
    max_total_size_bytes: int = Field(
        default=1_000_000_000, gt=0, description="Max total size of repository in bytes."
    )

    tool_timeout_seconds_default: int = Field(
        default=120, gt=0, description="Default subprocess timeout."
    )
    tool_timeout_git: int = Field(default=120, gt=0, description="Git clone timeout.")
    tool_timeout_scc: int = Field(default=60, gt=0, description="scc timeout.")
    tool_timeout_syft: int = Field(default=120, gt=0, description="Syft timeout.")
    tool_timeout_semgrep: int = Field(default=120, gt=0, description="Semgrep timeout.")
    tool_timeout_tree_sitter: int = Field(default=120, gt=0, description="Tree-sitter timeout.")
    tool_timeout_detect_secrets: int = Field(
        default=120, gt=0, description="detect-secrets timeout."
    )

    max_output_items: int = Field(default=500, gt=0, description="Default max output items.")
    max_output_syft: int = Field(default=1000, gt=0, description="Max dependencies from Syft.")
    max_output_semgrep: int = Field(default=200, gt=0, description="Max findings from Semgrep.")
    max_output_tree_sitter: int = Field(
        default=500, gt=0, description="Max nodes from Tree-sitter."
    )
