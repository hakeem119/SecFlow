import json
from pathlib import Path, PurePosixPath

from app.core.safe_path import SafePath
from app.schemas.tool import SyftData, SyftPackage, ToolContext, ToolName, ToolResult, ToolStatus
from app.tools.runner import CommandRequest, CommandRunner


class SyftAdapter:
    """
    Adapter for executing the `syft` tool to generate an SBOM offline.
    """

    def __init__(self, runner: CommandRunner) -> None:
        self.runner = runner
        self.max_json_size = 20 * 1024 * 1024  # 20MB cap

    async def analyze(self, context: ToolContext) -> ToolResult[SyftData]:
        # Pinned CLI flags for syft: absolute dir target, fixed config, offline
        args = ("dir:" + str(context.repository_path), "-c", "/etc/syft.yaml", "-o", "json")
        # Run outside the workspace
        cwd = SafePath(Path("/tmp"), _internal=True)  # noqa: S108

        request = CommandRequest(
            executable="syft",
            args=args,
            cwd=cwd,
            timeout=context.timeout_seconds,
            max_stdout_bytes=self.max_json_size,
            max_stderr_bytes=2 * 1024 * 1024,
        )

        result = await self.runner.run(request)
        warnings: list[str] = []

        if result.timed_out:
            return ToolResult[SyftData](
                tool=ToolName.SYFT,
                status=ToolStatus.ERROR,
                evidence=[],
                data=SyftData(),
                warnings=["syft timed out"],
            )

        if result.exit_code != 0:
            status = ToolStatus.PARTIAL if result.stdout else ToolStatus.ERROR
            warnings.append(f"syft exited with code {result.exit_code}")
            if not result.stdout:
                return ToolResult[SyftData](
                    tool=ToolName.SYFT,
                    status=ToolStatus.ERROR,
                    evidence=[],
                    data=SyftData(),
                    warnings=warnings,
                )

        if result.truncated:
            warnings.append("syft output was truncated due to size limits")

        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            warnings.append(f"malformed syft JSON: {e}")
            return ToolResult[SyftData](
                tool=ToolName.SYFT,
                status=ToolStatus.ERROR,
                evidence=[],
                data=SyftData(),
                warnings=warnings,
            )

        if not isinstance(parsed, dict) or "artifacts" not in parsed:
            warnings.append("malformed syft JSON: Missing artifacts list")
            return ToolResult[SyftData](
                tool=ToolName.SYFT,
                status=ToolStatus.ERROR,
                evidence=[],
                data=SyftData(),
                warnings=warnings,
            )

        artifacts = parsed.get("artifacts", [])
        if not isinstance(artifacts, list):
            artifacts = []

        packages: list[SyftPackage] = []
        ecosystems_set: set[str] = set()

        for item in artifacts:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "Unknown")
            version = item.get("version", "Unknown")
            ecosystem = item.get("type", "Unknown")

            locations = item.get("locations", [])
            source_file = "Unknown"
            if isinstance(locations, list) and locations and isinstance(locations[0], dict):
                path_str = locations[0].get("path", "Unknown")
                if path_str != "Unknown":
                    try:
                        p = PurePosixPath(path_str)
                        if p.is_absolute():
                            p = p.relative_to(p.anchor)
                        source_file = str(p)
                    except ValueError:
                        source_file = str(path_str)

            packages.append(
                SyftPackage(
                    name=str(name),
                    version=str(version),
                    ecosystem=str(ecosystem),
                    source_file=source_file,
                )
            )
            ecosystems_set.add(str(ecosystem))

        status = ToolStatus.SUCCESS if not warnings else ToolStatus.PARTIAL

        return ToolResult[SyftData](
            tool=ToolName.SYFT,
            status=status,
            evidence=[],
            data=SyftData(
                ecosystems=sorted(ecosystems_set),
                packages=packages,
            ),
            warnings=warnings,
        )
