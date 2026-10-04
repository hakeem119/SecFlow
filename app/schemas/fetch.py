"""
FetchResult: structured output produced by the Git adapter (Phase 4).

Validates:
- commit: exactly 40 lower-case hex chars (full SHA1).
- default_branch: non-empty, ≤ 255 chars, no leading '-', no ASCII whitespace
  or control characters.  (Git ref rules; enough for Phase 1.)
- tracked_files: list of relative POSIX paths, max length aligned with
  Settings.max_file_count (default 10 000, hard cap 100 000).
  No absolute paths, no '..' components, no backslash, no NUL byte,
  no empty path, no bare '.'.
"""

from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.limits import LIMIT_MAX_FILE_COUNT
from app.schemas.paths import validate_posix_path
from app.schemas.validators import validate_branch_name


class FetchResult(BaseModel):
    """Structured output of the Git fetch adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    commit: str = Field(
        ...,
        pattern=r"^[0-9a-f]{40}$",
        description="Full 40-character lower-case git commit SHA1.",
    )
    default_branch: str = Field(
        ...,
        description=(
            "Default branch name. Non-empty, ≤ 255 chars, no leading '-', "
            "no ASCII whitespace or control characters."
        ),
    )
    tracked_files: list[PurePosixPath] = Field(
        ...,
        max_length=LIMIT_MAX_FILE_COUNT,
        description="All files tracked by git, as relative POSIX paths.",
    )

    @field_validator("default_branch")
    @classmethod
    def _validate_branch(cls, v: str) -> str:
        """Reject branches that would be unsafe to use as ref names or log values."""
        return validate_branch_name(v)

    @model_validator(mode="after")
    def validate_paths(self) -> "FetchResult":
        """Ensure every tracked file path is safe and relative."""
        for p in self.tracked_files:
            validate_posix_path(p)
        return self
