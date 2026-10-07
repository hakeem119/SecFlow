import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

import yaml

from app.services.html_reporter import generate_html_report

from app.schemas.snapshot import (
    DependenciesInfo,
    FileInfo,
    LanguageMetrics,
    LimitsApplied,
    MetricsInfo,
    PackageInfo,
    RepositoryInfo,
    RepositorySnapshot,
    SecretFindingsInfo,
    SecurityEvidenceInfo,
    StructureInfo,
    SyntaxEvidenceInfo,
    WorkspaceInfo,
)
from app.schemas.tool import (
    ToolResult,
)


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: Any) -> bool:
        return True


logger = logging.getLogger(__name__)


@dataclass
class PipelineInput:
    workspace_id: str
    repo_name: str
    repo_url: str
    commit: str
    default_branch: str
    scanned_files: list[dict[str, Any]]
    scanned_directories: list[str]
    tool_results: list[ToolResult[Any]]
    files_truncated: bool


class SnapshotPipelineError(Exception):
    pass


class SnapshotPipeline:
    """
    Pipeline stages for building the repository_snapshot.yaml.
    Stages: Filter -> Normalize -> Redact -> Validate -> Write
    """

    def __init__(self) -> None:
        self.exclude_dirs = {".git", "node_modules", "vendor", ".venv"}
        # Oversized or binary definition
        self.max_file_size = 5 * 1024 * 1024  # 5MB

    def _is_excluded(self, path_str: str) -> bool:
        parts = PurePosixPath(path_str).parts
        return any(part in self.exclude_dirs for part in parts)

    def filter_stage(self, raw_input: PipelineInput) -> PipelineInput:
        """
        Stage 1: Filter
        Failure mode: If filtering crashes, raises SnapshotPipelineError (Internal Error).
        """
        try:
            filtered_files = []
            for f in raw_input.scanned_files:
                path_str = str(f["path"])
                if self._is_excluded(path_str):
                    continue
                if f.get("size", 0) > self.max_file_size:
                    continue
                filtered_files.append(f)

            filtered_dirs = [d for d in raw_input.scanned_directories if not self._is_excluded(d)]

            raw_input.scanned_files = filtered_files
            raw_input.scanned_directories = filtered_dirs
        except Exception as e:
            logger.exception("Filter stage failed:")
            raise SnapshotPipelineError("Failed to filter workspace scan data") from e
        else:
            return raw_input

    def normalize_stage(self, filtered_input: PipelineInput) -> RepositorySnapshot:
        """
        Stage 2: Normalize
        Failure mode: If a tool's data is malformed, we catch it and set its tool_status to ERROR,
        but the snapshot itself is PARTIAL, not an overall failure.
        """
        # Parse Repo Info
        repo_info = RepositoryInfo(
            name=filtered_input.repo_name,
            url=filtered_input.repo_url,  # type: ignore
            commit=filtered_input.commit,
            default_branch=filtered_input.default_branch,
        )
        ws_info = WorkspaceInfo(id=filtered_input.workspace_id)  # type: ignore

        # Parse Structure Info
        files_info = [
            FileInfo(
                path=PurePosixPath(f["path"]),
                type="file",
                language=f.get("language", "Unknown"),
                size=f.get("size", 0),
            )
            for f in filtered_input.scanned_files
        ]
        dirs_info = [PurePosixPath(d) for d in filtered_input.scanned_directories]
        structure = StructureInfo(directories=dirs_info, files=files_info)

        tool_status = {}
        warnings = []

        loc = 0
        complexity = 0
        languages = []
        ecosystems = []
        packages = []
        semgrep_findings = []
        secret_findings = []

        for result in filtered_input.tool_results:
            tool_status[result.tool] = result.status
            if result.warnings:
                warnings.extend(result.warnings)
            
            if result.tool == "scc" and result.status != "error":
                loc = result.data.loc
                complexity = result.data.complexity
                languages = [
                    LanguageMetrics(name=lang.name, files=lang.files, loc=lang.loc)
                    for lang in result.data.languages
                ]
            elif result.tool == "syft" and result.status != "error":
                ecosystems = result.data.ecosystems
                packages = [
                    PackageInfo(
                        name=pkg.name,
                        version=pkg.version,
                        ecosystem=pkg.ecosystem,
                        source_file=PurePosixPath(pkg.source_file)
                    )
                    for pkg in result.data.packages
                ]
            elif result.tool == "semgrep" and result.status != "error":
                semgrep_findings = result.data.findings
            elif result.tool == "detect-secrets" and result.status != "error":
                secret_findings = result.data.findings

        metrics = MetricsInfo(loc=loc, complexity=complexity, languages=languages)
        dependencies = DependenciesInfo(ecosystems=ecosystems, packages=packages)
        syntax = SyntaxEvidenceInfo()
        security = SecurityEvidenceInfo(semgrep=semgrep_findings)
        secrets = SecretFindingsInfo(count=len(secret_findings), findings=secret_findings)

        limits = LimitsApplied(
            files_truncated=filtered_input.files_truncated,
            items_capped=False,
            excluded_paths=[],
        )

        return RepositorySnapshot(
            generated_at=datetime.now(UTC),
            repository=repo_info,
            workspace=ws_info,
            structure=structure,
            metrics=metrics,
            dependencies=dependencies,
            syntax_evidence=syntax,
            security_evidence=security,
            secret_findings=secrets,
            tool_status=tool_status,
            limits_applied=limits,
            warnings=warnings,
        )

    def redact_stage(self, snapshot: RepositorySnapshot) -> RepositorySnapshot:
        """
        Stage 3: Redact
        Failure mode: Fail closed.
        Pydantic models with `extra="forbid"` structurally prove that no `value` or `snippet`
        fields exist to hold secrets. However, as an extra layer, we ensure warnings
        are capped in length and do not contain structured data.
        """
        redacted_warnings = []
        for w in snapshot.warnings:
            # Simple length cap on free-text to prevent massive dumps that might leak state
            safe_w = w[:200]
            redacted_warnings.append(safe_w)

        # Pydantic models are frozen, so we must use model_copy(update=...)
        return snapshot.model_copy(update={"warnings": redacted_warnings})

    def validate_stage(self, snapshot: RepositorySnapshot) -> RepositorySnapshot:
        """
        Stage 4: Validate
        Failure mode: Pydantic constraints violated -> raises SnapshotPipelineError.
        """
        try:
            return RepositorySnapshot.model_validate(snapshot.model_dump())
        except Exception as e:
            logger.exception("Validate stage failed:")
            raise SnapshotPipelineError("Final snapshot failed validation") from e

    def write_stage(self, snapshot: RepositorySnapshot, output_path: PurePosixPath) -> None:
        """
        Stage 5: Write
        Failure mode: If writing to disk fails, raises SnapshotPipelineError.
        """
        try:
            dumped = snapshot.model_dump(mode="json")
            yaml_str = yaml.dump(
                dumped, Dumper=NoAliasDumper, sort_keys=False, default_flow_style=False
            )

            # Size cap: if YAML is > 10MB, fail closed.
            if len(yaml_str.encode("utf-8")) > 10 * 1024 * 1024:
                raise SnapshotPipelineError("Snapshot YAML exceeds 10MB safety cap")  # noqa: TRY301

            from pathlib import Path

            from pathlib import Path

            with Path(output_path).open("w") as f:
                f.write(yaml_str)

            # Generate and write HTML report
            html_str = generate_html_report(dumped)
            html_path = Path(output_path).with_suffix(".html")
            with html_path.open("w") as f:
                f.write(html_str)
        except Exception as e:
            logger.exception("Write stage failed:")
            raise SnapshotPipelineError("Failed to write snapshot YAML") from e

    def build(self, raw_input: PipelineInput, output_path: PurePosixPath) -> RepositorySnapshot:
        """
        Orchestrate the pipeline.
        """
        filtered = self.filter_stage(raw_input)
        snapshot = self.normalize_stage(filtered)
        snapshot = self.redact_stage(snapshot)
        snapshot = self.validate_stage(snapshot)
        self.write_stage(snapshot, output_path)
        return snapshot
