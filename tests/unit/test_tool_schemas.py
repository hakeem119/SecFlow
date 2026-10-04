from pathlib import Path

import pytest
from app.schemas.tool import SccData, ToolContext, ToolSpec
from pydantic import ValidationError


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


def test_tool_spec_valid() -> None:
    spec = ToolSpec(
        name="scc",
        purpose="Count lines of code.",
        when_to_use="Always",
        when_not_to_use="Never",
        input_schema=ToolContext.model_json_schema(),
        output_schema=SccData.model_json_schema(),
        evidence_semantics="Returns dict of language metrics.",
        limits="Max 500 items",
    )
    assert spec.name == "scc"
    assert spec.input_schema == ToolContext.model_json_schema()
    assert spec.output_schema == SccData.model_json_schema()


def test_tool_spec_rejects_empty_fields() -> None:
    # They are standard strings, but let's test that Pydantic enforces required fields.
    with pytest.raises(ValidationError):
        ToolSpec(  # type: ignore
            name="",
            purpose="",
            # Missing when_to_use and other fields entirely
        )


def test_tool_spec_descriptions_have_no_absolute_paths() -> None:
    # A spec shouldn't have absolute paths in its static metadata.
    # We test our generic test case:
    spec = ToolSpec(
        name="scc",
        purpose="Count lines of code.",
        when_to_use="Always",
        when_not_to_use="Never",
        input_schema=ToolContext.model_json_schema(),
        output_schema=SccData.model_json_schema(),
        evidence_semantics="Returns dict of language metrics.",
        limits="Max 500 items",
    )
    fields = [
        spec.name,
        spec.purpose,
        spec.when_to_use,
        spec.when_not_to_use,
        spec.evidence_semantics,
        spec.limits,
    ]
    for field_value in fields:
        assert not field_value.startswith("/")


def test_tool_spec_rejects_empty_strings() -> None:
    with pytest.raises(ValidationError):
        ToolSpec(
            name="",
            purpose="",
            when_to_use="",
            when_not_to_use="",
            input_schema={},
            output_schema={},
            evidence_semantics="",
            limits="",
        )
