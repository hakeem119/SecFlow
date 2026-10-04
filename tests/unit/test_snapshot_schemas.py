import datetime
from pathlib import Path

import pytest
from app.schemas.snapshot import (
    DependenciesInfo,
    FileInfo,
    LimitsApplied,
    MetricsInfo,
    RepositoryInfo,
    RepositorySnapshot,
    SecretFinding,
    SecretFindingsInfo,
    StructureInfo,
    SyntaxEvidenceInfo,
    WorkspaceInfo,
)
from pydantic import ValidationError


def test_file_info_rejects_content() -> None:
    with pytest.raises(ValidationError):
        FileInfo(
            path=Path("main.py"),
            type="file",
            language="python",
            size=100,
            content="print('hello')",  # type: ignore
        )


def test_secret_finding_rejects_value() -> None:
    with pytest.raises(ValidationError):
        SecretFinding(
            detector="regex",
            path=Path("main.py"),
            line=10,
            value="super_secret",  # type: ignore
        )


def test_file_info_rejects_absolute_path() -> None:
    with pytest.raises(ValueError, match="Path must be relative"):
        FileInfo(
            path=Path("/etc/passwd"),
            type="file",
            language="python",
            size=100,
        )


def test_file_info_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="Path must be relative and cannot traverse"):
        FileInfo(
            path=Path("../outside.py"),
            type="file",
            language="python",
            size=100,
        )


def test_snapshot_valid() -> None:
    snapshot = RepositorySnapshot(
        generated_at=datetime.datetime.now(datetime.UTC),
        repository=RepositoryInfo(
            name="repo", url="https://github.com/owner/repo", commit="abc", default_branch="main"
        ),
        workspace=WorkspaceInfo(id="uuid-123"),
        structure=StructureInfo(directories=[], files=[]),
        metrics=MetricsInfo(loc=0, complexity=0, languages=[]),
        dependencies=DependenciesInfo(ecosystems=[], packages=[]),
        syntax_evidence=SyntaxEvidenceInfo(),
        security_evidence={},
        secret_findings=SecretFindingsInfo(count=0, findings=[]),
        tool_status={},
        limits_applied=LimitsApplied(files_truncated=False, items_capped=False, excluded_paths=[]),
    )
    assert snapshot.schema_version == "1.0"
