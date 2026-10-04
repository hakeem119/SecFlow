from pathlib import Path

import pytest
from app.schemas.tool import ToolContext


def test_tool_context_relative_paths_valid() -> None:
    ctx = ToolContext(
        repository_path=Path("/opt/workspaces/uuid"),
        include_paths=[Path("src"), Path("docs/readme.md")],
        exclude_paths=[Path("tests")],
        timeout_seconds=60,
        max_output_items=100,
    )
    assert ctx.timeout_seconds == 60


def test_tool_context_rejects_absolute_paths() -> None:
    with pytest.raises(ValueError, match="Path must be relative"):
        ToolContext(
            repository_path=Path("/opt/workspaces/uuid"),
            include_paths=[Path("/etc/passwd")],
            exclude_paths=[],
            timeout_seconds=60,
            max_output_items=100,
        )


def test_tool_context_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="Path traversal not allowed"):
        ToolContext(
            repository_path=Path("/opt/workspaces/uuid"),
            include_paths=[],
            exclude_paths=[Path("../../secret")],
            timeout_seconds=60,
            max_output_items=100,
        )
