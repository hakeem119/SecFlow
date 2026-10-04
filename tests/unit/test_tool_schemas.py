from pathlib import Path, PurePosixPath

import pytest
from app.schemas.tool import (
    DetectSecretsData,
    SccData,
    SecretFinding,
    SecurityFinding,
    SemgrepData,
    SyftData,
    ToolContext,
    ToolName,
    ToolResult,
    ToolSpec,
    ToolStatus,
    TreeSitterData,
)
from pydantic import ValidationError

# --- ToolContext ---


def test_tool_context_relative_paths_valid() -> None:
    ctx = ToolContext(
        repository_path=Path("/opt/workspaces/uuid"),
        include_paths=[PurePosixPath("src"), PurePosixPath("docs/readme.md")],
        exclude_paths=[PurePosixPath("tests")],
        timeout_seconds=60,
        max_output_items=100,
    )
    assert ctx.timeout_seconds == 60


def test_tool_context_rejects_absolute_paths() -> None:
    with pytest.raises(ValueError, match="Path must be relative"):
        ToolContext(
            repository_path=Path("/opt/workspaces/uuid"),
            include_paths=[PurePosixPath("/etc/passwd")],
            exclude_paths=[],
            timeout_seconds=60,
            max_output_items=100,
        )


def test_tool_context_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="Path traversal not allowed"):
        ToolContext(
            repository_path=Path("/opt/workspaces/uuid"),
            include_paths=[],
            exclude_paths=[PurePosixPath("../../secret")],
            timeout_seconds=60,
            max_output_items=100,
        )


def test_tool_context_rejects_relative_repository_path() -> None:
    with pytest.raises(ValueError, match="repository_path must be absolute"):
        ToolContext(
            repository_path=Path("relative/path"),
            include_paths=[],
            exclude_paths=[],
            timeout_seconds=60,
            max_output_items=100,
        )


def test_tool_context_rejects_timeout_above_upper_bound() -> None:
    with pytest.raises(ValidationError, match="less than or equal to"):
        ToolContext(
            repository_path=Path("/opt/workspaces/uuid"),
            include_paths=[],
            exclude_paths=[],
            timeout_seconds=99999,
            max_output_items=100,
        )


def test_tool_context_rejects_max_output_above_upper_bound() -> None:
    with pytest.raises(ValidationError, match="less than or equal to"):
        ToolContext(
            repository_path=Path("/opt/workspaces/uuid"),
            include_paths=[],
            exclude_paths=[],
            timeout_seconds=60,
            max_output_items=999999,
        )


# --- ToolSpec ---


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
    with pytest.raises(ValidationError):
        ToolSpec(  # type: ignore[call-arg]
            name="",
            purpose="",
        )


def test_tool_spec_descriptions_have_no_absolute_paths() -> None:
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


# --- D1: typed data models reject "content", "source", "value" keys ---


def test_scc_data_rejects_extra_keys() -> None:
    with pytest.raises(ValidationError):
        SccData(metrics=[], content="some code")  # type: ignore[call-arg]


def test_tree_sitter_data_rejects_extra_keys() -> None:
    with pytest.raises(ValidationError):
        TreeSitterData(nodes=[], source="code")  # type: ignore[call-arg]


def test_syft_data_rejects_extra_keys() -> None:
    with pytest.raises(ValidationError):
        SyftData(packages=[], value="leak")  # type: ignore[call-arg]


def test_semgrep_data_rejects_extra_keys() -> None:
    with pytest.raises(ValidationError):
        SemgrepData(findings=[], content="code")  # type: ignore[call-arg]


def test_detect_secrets_data_rejects_value_key() -> None:
    """D1: DetectSecretsData must not allow a 'value' field."""
    with pytest.raises(ValidationError):
        DetectSecretsData(
            findings=[],
            value="secret",  # type: ignore[call-arg]
        )


def test_secret_finding_rejects_value_key() -> None:
    """D1: SecretFinding has no value field — extra='forbid' blocks it."""
    with pytest.raises(ValidationError):
        SecretFinding(
            detector="regex",
            path=PurePosixPath("main.py"),
            line=1,
            value="secret123",  # type: ignore[call-arg]
        )


def test_security_finding_rejects_message_and_snippet() -> None:
    """SecurityFinding has no message or code snippet fields."""
    with pytest.raises(ValidationError):
        SecurityFinding(
            rule_id="xss",
            severity="high",
            path=PurePosixPath("app.py"),
            line=10,
            message="XSS found",  # type: ignore[call-arg]
        )


def test_security_finding_rejects_source() -> None:
    with pytest.raises(ValidationError):
        SecurityFinding(
            rule_id="xss",
            severity="high",
            path=PurePosixPath("app.py"),
            line=10,
            source="print(x)",  # type: ignore[call-arg]
        )


# --- ToolResult ---


def test_tool_result_evidence_rejects_absolute_path() -> None:
    with pytest.raises(ValueError, match="Path must be relative"):
        ToolResult[SccData](
            tool=ToolName.SCC,
            status=ToolStatus.SUCCESS,
            evidence=[PurePosixPath("/etc/passwd")],
            data=SccData(),
        )


def test_tool_result_evidence_rejects_traversal() -> None:
    with pytest.raises(ValueError, match="Path traversal not allowed"):
        ToolResult[SccData](
            tool=ToolName.SCC,
            status=ToolStatus.SUCCESS,
            evidence=[PurePosixPath("../../etc/passwd")],
            data=SccData(),
        )


def test_tool_result_evidence_rejects_backslash() -> None:
    with pytest.raises(ValueError, match="Invalid path"):
        ToolResult[SccData](
            tool=ToolName.SCC,
            status=ToolStatus.SUCCESS,
            evidence=[PurePosixPath("some\\path")],
            data=SccData(),
        )


def test_tool_result_valid() -> None:
    result = ToolResult[SccData](
        tool=ToolName.SCC,
        status=ToolStatus.SUCCESS,
        evidence=[PurePosixPath("src/main.py")],
        data=SccData(metrics=["Python: 100 LOC"]),
    )
    assert result.tool == "scc"
    assert result.evidence == [PurePosixPath("src/main.py")]
