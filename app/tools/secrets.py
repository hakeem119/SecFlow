import json
import logging
from pathlib import PurePosixPath

from app.core.safe_path import SafePath
from app.schemas.tool import (
    DetectSecretsData,
    SecretFinding,
    ToolContext,
    ToolName,
    ToolResult,
    ToolStatus,
)
from app.tools.runner import CommandRequest, CommandRunner

logger = logging.getLogger(__name__)


class DetectSecretsAdapter:
    """
    Adapter for executing detect-secrets and parsing the output.
    Ensures secret values are never retained or logged.
    """

    def __init__(self, runner: CommandRunner) -> None:
        self.runner = runner
        self.max_json_size = 5 * 1024 * 1024  # 5MB cap

    async def analyze(self, context: ToolContext) -> ToolResult[DetectSecretsData]:
        cwd = SafePath(context.repository_path, _internal=True)

        args = ("scan", ".")

        request = CommandRequest(
            executable="detect-secrets",
            args=args,
            cwd=cwd,
            timeout=context.timeout_seconds,
            max_stdout_bytes=self.max_json_size,
            max_stderr_bytes=1024 * 1024,
        )

        result = await self.runner.run(request)
        warnings: list[str] = []

        if result.timed_out:
            return ToolResult[DetectSecretsData](
                tool=ToolName.DETECT_SECRETS,
                status=ToolStatus.ERROR,
                evidence=[],
                data=DetectSecretsData(findings=[]),
                warnings=["detect-secrets timed out"],
            )

        if result.exit_code not in (0, 1):
            status = ToolStatus.PARTIAL if result.stdout else ToolStatus.ERROR
            warnings.append(f"detect-secrets exited with code {result.exit_code}")
            if not result.stdout:
                return ToolResult[DetectSecretsData](
                    tool=ToolName.DETECT_SECRETS,
                    status=ToolStatus.ERROR,
                    evidence=[],
                    data=DetectSecretsData(findings=[]),
                    warnings=warnings,
                )

        if result.truncated:
            warnings.append("detect-secrets output was truncated due to size limits")

        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError:
            warnings.append("malformed detect-secrets JSON")
            return ToolResult[DetectSecretsData](
                tool=ToolName.DETECT_SECRETS,
                status=ToolStatus.ERROR,
                evidence=[],
                data=DetectSecretsData(findings=[]),
                warnings=warnings,
            )

        findings: list[SecretFinding] = []
        evidence_paths: set[PurePosixPath] = set()

        results_dict = parsed.get("results", {})
        if not isinstance(results_dict, dict):
            warnings.append("malformed detect-secrets JSON: 'results' is not a dictionary")
            return ToolResult[DetectSecretsData](
                tool=ToolName.DETECT_SECRETS,
                status=ToolStatus.ERROR,
                evidence=[],
                data=DetectSecretsData(findings=[]),
                warnings=warnings,
            )

        for filename, file_secrets in results_dict.items():
            if not isinstance(file_secrets, list):
                continue

            try:
                posix_path = PurePosixPath(filename)
            except ValueError:
                continue

            for secret in file_secrets:
                if not isinstance(secret, dict):
                    continue

                detector = secret.get("type", "Unknown")
                line_number = secret.get("line_number", 1)

                finding = SecretFinding(
                    detector=str(detector),
                    path=posix_path,
                    line=int(line_number),
                )
                findings.append(finding)
                evidence_paths.add(posix_path)

                if len(findings) >= context.max_output_items:
                    warnings.append(f"findings capped at {context.max_output_items}")
                    break

            if len(findings) >= context.max_output_items:
                break

        status = ToolStatus.SUCCESS if not warnings else ToolStatus.PARTIAL

        return ToolResult[DetectSecretsData](
            tool=ToolName.DETECT_SECRETS,
            status=status,
            evidence=list(evidence_paths),
            data=DetectSecretsData(findings=findings),
            warnings=warnings,
        )
