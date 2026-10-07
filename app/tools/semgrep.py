import json
from pathlib import Path, PurePosixPath

from app.core.safe_path import SafePath
from app.schemas.tool import (
    SecurityFinding,
    SemgrepData,
    ToolContext,
    ToolName,
    ToolResult,
    ToolStatus,
)
from app.tools.runner import CommandRequest, CommandRunner


class SemgrepAdapter:
    """
    Adapter for executing the `semgrep` tool to scan for security patterns.
    """

    def __init__(self, runner: CommandRunner, rules_dir: Path | None = None) -> None:
        self.runner = runner
        self.max_json_size = 20 * 1024 * 1024  # 20MB cap
        # Use a pinned local ruleset directory, D10 compliance
        self.rules_dir = rules_dir or Path("/opt/secflow/rules/semgrep")

    async def analyze(self, context: ToolContext) -> ToolResult[SemgrepData]:
        # Pinned CLI flags for semgrep: local rules, strict JSON
        # No config=auto is allowed
        args = (
            "scan",
            "--config",
            str(self.rules_dir),
            "--json",
            "--quiet",
            "--disable-version-check",
            "--no-rewrite-rule-ids",
            str(context.repository_path),
        )

        # Run outside the workspace to avoid implicit config discovery
        cwd = SafePath(Path("/tmp"), _internal=True)  # noqa: S108

        # Disable Semgrep metrics and network usage completely
        env = {
            "SEMGREP_SEND_METRICS": "off",
            "SEMGREP_ENABLE_METRICS": "0",
        }

        request = CommandRequest(
            executable="semgrep",
            args=args,
            cwd=cwd,
            timeout=context.timeout_seconds,
            max_stdout_bytes=self.max_json_size,
            max_stderr_bytes=2 * 1024 * 1024,
            env=env,
        )

        result = await self.runner.run(request)
        warnings: list[str] = []

        if result.timed_out:
            return ToolResult[SemgrepData](
                tool=ToolName.SEMGREP,
                status=ToolStatus.ERROR,
                evidence=[],
                data=SemgrepData(),
                warnings=["semgrep timed out"],
            )

        # Semgrep exits with 1 if there are findings, 0 if no findings, 2+ for errors
        if result.exit_code not in (0, 1):
            status = ToolStatus.PARTIAL if result.stdout else ToolStatus.ERROR
            warnings.append(f"semgrep exited with code {result.exit_code}")
            if not result.stdout:
                return ToolResult[SemgrepData](
                    tool=ToolName.SEMGREP,
                    status=ToolStatus.ERROR,
                    evidence=[],
                    data=SemgrepData(),
                    warnings=warnings,
                )

        if result.truncated:
            warnings.append("semgrep output was truncated due to size limits")

        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            warnings.append(f"malformed semgrep JSON: {e}")
            return ToolResult[SemgrepData](
                tool=ToolName.SEMGREP,
                status=ToolStatus.ERROR,
                evidence=[],
                data=SemgrepData(),
                warnings=warnings,
            )

        if not isinstance(parsed, dict) or "results" not in parsed:
            warnings.append("malformed semgrep JSON: Missing results list")
            return ToolResult[SemgrepData](
                tool=ToolName.SEMGREP,
                status=ToolStatus.ERROR,
                evidence=[],
                data=SemgrepData(),
                warnings=warnings,
            )

        results = parsed.get("results", [])
        if not isinstance(results, list):
            results = []

        findings: list[SecurityFinding] = []

        for item in results:
            if not isinstance(item, dict):
                continue

            rule_id = item.get("check_id", "Unknown")

            extra = item.get("extra", {})
            severity = extra.get("severity", "UNKNOWN") if isinstance(extra, dict) else "UNKNOWN"

            path_str = item.get("path", "Unknown")
            # Parse line number
            start = item.get("start", {})
            line = start.get("line", 0) if isinstance(start, dict) else 0

            if path_str != "Unknown":
                try:
                    p = PurePosixPath(path_str)
                    if p.is_absolute():
                        repo_path_str = str(context.repository_path)
                        # Remove the prefix
                        if str(p).startswith(repo_path_str):
                            p = PurePosixPath(str(p)[len(repo_path_str) :].lstrip("/"))
                        else:
                            p = p.relative_to(p.anchor)
                    finding_path = p
                except ValueError:
                    finding_path = PurePosixPath("Unknown")
            else:
                finding_path = PurePosixPath("Unknown")

            if finding_path != PurePosixPath("Unknown"):
                findings.append(
                    SecurityFinding(
                        rule_id=str(rule_id),
                        severity=str(severity),
                        path=finding_path,
                        line=int(line),
                    )
                )

        status = ToolStatus.SUCCESS if not warnings else ToolStatus.PARTIAL

        return ToolResult[SemgrepData](
            tool=ToolName.SEMGREP,
            status=status,
            evidence=[],
            data=SemgrepData(findings=findings),
            warnings=warnings,
        )
