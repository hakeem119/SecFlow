import datetime
import uuid
from pathlib import PurePosixPath

import pytest
import yaml
from app.schemas.domain import GitHubRepoUrl, WorkspaceId
from app.schemas.snapshot import (
    DependenciesInfo,
    FileInfo,
    LimitsApplied,
    MetricsInfo,
    PackageInfo,
    RepositoryInfo,
    RepositorySnapshot,
    SecretFindingsInfo,
    SecurityEvidenceInfo,
    StructureInfo,
    SyntaxEvidenceInfo,
    SyntaxEvidenceItem,
    WorkspaceInfo,
)
from app.schemas.tool import SecretFinding, SecurityFinding, ToolName, ToolStatus
from pydantic import ValidationError


def test_file_info_rejects_content() -> None:
    with pytest.raises(ValidationError):
        FileInfo(
            path=PurePosixPath("main.py"),
            type="file",
            language="python",
            size=100,
            content="print('hello')",  # type: ignore[call-arg]
        )


def test_secret_finding_rejects_value() -> None:
    with pytest.raises(ValidationError):
        SecretFinding(
            detector="regex",
            path=PurePosixPath("main.py"),
            line=10,
            value="super_secret",  # type: ignore[call-arg]
        )


def test_file_info_rejects_absolute_path() -> None:
    with pytest.raises(ValueError, match="Path must be relative"):
        FileInfo(
            path=PurePosixPath("/etc/passwd"),
            type="file",
            language="python",
            size=100,
        )


def test_file_info_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="traversal"):
        FileInfo(
            path=PurePosixPath("../outside.py"),
            type="file",
            language="python",
            size=100,
        )


def test_snapshot_valid() -> None:
    wid = WorkspaceId(uuid.uuid4())
    snapshot = RepositorySnapshot(
        generated_at=datetime.datetime.now(datetime.UTC),
        repository=RepositoryInfo(
            name="repo",
            url=GitHubRepoUrl("owner", "repo"),
            commit="a" * 40,
            default_branch="main",
        ),
        workspace=WorkspaceInfo(id=wid),
        structure=StructureInfo(
            directories=[PurePosixPath("src")],
            files=[FileInfo(path=PurePosixPath("src/a.py"), type="f", language="python", size=10)],
        ),
        metrics=MetricsInfo(loc=1, complexity=1, languages=[]),
        dependencies=DependenciesInfo(
            ecosystems=["pip"],
            packages=[
                PackageInfo(
                    name="req",
                    version="1",
                    ecosystem="pip",
                    source_file=PurePosixPath("requirements.txt"),
                )
            ],
        ),
        syntax_evidence=SyntaxEvidenceInfo(
            imports=[
                SyntaxEvidenceItem(
                    name="sys", path=PurePosixPath("src/a.py"), start_line=1, end_line=1
                )
            ]
        ),
        security_evidence=SecurityEvidenceInfo(
            semgrep=[
                SecurityFinding(
                    rule_id="r", severity="high", path=PurePosixPath("src/a.py"), line=1
                )
            ]
        ),
        secret_findings=SecretFindingsInfo(
            count=1, findings=[SecretFinding(detector="d", path=PurePosixPath("src/a.py"), line=1)]
        ),
        tool_status={ToolName.SCC: ToolStatus.SUCCESS},
        limits_applied=LimitsApplied(
            files_truncated=False, items_capped=False, excluded_paths=[PurePosixPath("dist")]
        ),
    )
    assert snapshot.schema_version == "1.0"

    # Prove the snapshot dumps to YAML via model_dump(mode="json") + yaml.safe_dump
    data = snapshot.model_dump(mode="json")
    yaml_str = yaml.safe_dump(data)
    assert yaml_str is not None
    assert "schema_version: '1.0'" in yaml_str
    assert str(wid.value) in yaml_str

    # Prove round-trip equality
    reloaded = yaml.safe_load(yaml_str)
    snapshot2 = RepositorySnapshot.model_validate(reloaded)
    assert snapshot.model_dump() == snapshot2.model_dump()


def test_snapshot_rejects_invalid_commit() -> None:
    with pytest.raises(ValidationError, match="String should match pattern"):
        RepositoryInfo(
            name="repo",
            url=GitHubRepoUrl("owner", "repo"),
            commit="abc",
            default_branch="main",
        )


def test_syntax_evidence_start_line_validation() -> None:
    with pytest.raises(ValueError, match="start_line cannot be greater than end_line"):
        SyntaxEvidenceItem(
            name="foo",
            path=PurePosixPath("src/main.py"),
            start_line=5,
            end_line=1,
        )


def test_structure_info_directories_validation() -> None:
    with pytest.raises(ValueError, match="relative"):
        StructureInfo(directories=[PurePosixPath("/foo")], files=[])


def test_package_info_path_validation() -> None:
    with pytest.raises(ValueError, match="relative"):
        PackageInfo(name="pkg", version="1", ecosystem="pip", source_file=PurePosixPath("/foo"))


def test_limits_applied_path_validation() -> None:
    with pytest.raises(ValueError, match="relative"):
        LimitsApplied(
            files_truncated=False, items_capped=False, excluded_paths=[PurePosixPath("/foo")]
        )


def test_snapshot_schema_version_literal() -> None:
    """schema_version must be Literal['1.0']."""
    with pytest.raises(ValidationError):
        RepositorySnapshot(
            schema_version="2.0",  # type: ignore[arg-type]
            generated_at=datetime.datetime.now(datetime.UTC),
            repository=RepositoryInfo(
                name="r",
                url=GitHubRepoUrl("o", "r"),
                commit="a" * 40,
                default_branch="main",
            ),
            workspace=WorkspaceInfo(id=WorkspaceId(uuid.uuid4())),
            structure=StructureInfo(directories=[], files=[]),
            metrics=MetricsInfo(loc=0, complexity=0, languages=[]),
            dependencies=DependenciesInfo(ecosystems=[], packages=[]),
            syntax_evidence=SyntaxEvidenceInfo(),
            security_evidence=SecurityEvidenceInfo(),
            secret_findings=SecretFindingsInfo(count=0, findings=[]),
            tool_status={ToolName.SCC: ToolStatus.SUCCESS},
            limits_applied=LimitsApplied(
                files_truncated=False, items_capped=False, excluded_paths=[]
            ),
        )


def test_secret_findings_count_gte_len() -> None:
    """count must be >= len(findings)."""
    with pytest.raises(ValueError, match="count cannot be less"):
        SecretFindingsInfo(
            count=0,
            findings=[SecretFinding(detector="regex", path=PurePosixPath("a.py"), line=1)],
        )


def test_security_evidence_rejects_extra_keys() -> None:
    """SecurityEvidenceInfo only has 'semgrep', no arbitrary keys."""
    with pytest.raises(ValidationError):
        SecurityEvidenceInfo(
            semgrep=[],
            other_tool=[],  # type: ignore[call-arg]
        )


def test_syntax_evidence_item_typed() -> None:
    """SyntaxEvidenceItem has name, path, start_line, end_line."""
    item = SyntaxEvidenceItem(
        name="foo", path=PurePosixPath("src/main.py"), start_line=1, end_line=5
    )
    assert item.name == "foo"
    assert item.start_line == 1


def test_syntax_evidence_item_rejects_source_key() -> None:
    """extra='forbid' blocks arbitrary keys like 'source' or 'content'."""
    with pytest.raises(ValidationError):
        SyntaxEvidenceItem(
            name="foo",
            path=PurePosixPath("main.py"),
            start_line=1,
            end_line=5,
            source="print()",  # type: ignore[call-arg]
        )


def test_tool_status_enum_values() -> None:
    """tool_status uses ToolStatus enum values."""
    snapshot = RepositorySnapshot(
        generated_at=datetime.datetime.now(datetime.UTC),
        repository=RepositoryInfo(
            name="r",
            url=GitHubRepoUrl("o", "r"),
            commit="a" * 40,
            default_branch="main",
        ),
        workspace=WorkspaceInfo(id=WorkspaceId(uuid.uuid4())),
        structure=StructureInfo(directories=[], files=[]),
        metrics=MetricsInfo(loc=0, complexity=0, languages=[]),
        dependencies=DependenciesInfo(ecosystems=[], packages=[]),
        syntax_evidence=SyntaxEvidenceInfo(),
        security_evidence=SecurityEvidenceInfo(),
        secret_findings=SecretFindingsInfo(count=0, findings=[]),
        tool_status={ToolName.SCC: ToolStatus.SUCCESS, ToolName.SYFT: ToolStatus.PARTIAL},
        limits_applied=LimitsApplied(files_truncated=False, items_capped=False, excluded_paths=[]),
    )
    assert snapshot.tool_status[ToolName.SCC] == ToolStatus.SUCCESS
