import json

from app.core.safe_path import SafePath
from app.schemas.tool import SccData, SccLanguage, ToolContext, ToolName, ToolResult, ToolStatus
from app.tools.runner import CommandRequest, CommandRunner


class SccAdapter:
    """
    Adapter for executing the `scc` tool and normalizing its JSON output.
    """

    def __init__(self, runner: CommandRunner) -> None:
        self.runner = runner
        self.max_json_size = 10 * 1024 * 1024  # 10MB cap

    async def analyze(self, context: ToolContext) -> ToolResult[SccData]:
        args = ("-f", "json")
        cwd = SafePath(context.repository_path, _internal=True)

        request = CommandRequest(
            executable="scc",
            args=args,
            cwd=cwd,
            timeout=context.timeout_seconds,
            max_stdout_bytes=self.max_json_size,
            max_stderr_bytes=1024 * 1024,
        )

        result = await self.runner.run(request)
        warnings: list[str] = []

        if result.timed_out:
            return ToolResult[SccData](
                tool=ToolName.SCC,
                status=ToolStatus.ERROR,
                evidence=[],
                data=SccData(),
                warnings=["scc timed out"],
            )

        if result.exit_code != 0:
            status = ToolStatus.PARTIAL if result.stdout else ToolStatus.ERROR
            warnings.append(f"scc exited with code {result.exit_code}")
            if not result.stdout:
                return ToolResult[SccData](
                    tool=ToolName.SCC,
                    status=ToolStatus.ERROR,
                    evidence=[],
                    data=SccData(),
                    warnings=warnings,
                )

        if result.truncated:
            warnings.append("scc output was truncated due to size limits")

        try:
            parsed = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            warnings.append(f"malformed scc JSON: {e}")
            return ToolResult[SccData](
                tool=ToolName.SCC,
                status=ToolStatus.ERROR,
                evidence=[],
                data=SccData(),
                warnings=warnings,
            )

        if not isinstance(parsed, list):
            warnings.append("malformed scc JSON: Expected a list of language objects")
            return ToolResult[SccData](
                tool=ToolName.SCC,
                status=ToolStatus.ERROR,
                evidence=[],
                data=SccData(),
                warnings=warnings,
            )

        languages: list[SccLanguage] = []
        total_files = 0
        total_loc = 0
        total_complexity = 0

        for item in parsed:
            if not isinstance(item, dict):
                continue
            name = item.get("Name", "Unknown")
            files = item.get("Count", 0)
            loc = item.get("Code", 0)
            complexity = item.get("Complexity", 0)

            lang = SccLanguage(
                name=str(name),
                files=int(files),
                loc=int(loc),
                complexity=int(complexity),
            )
            languages.append(lang)
            total_files += lang.files
            total_loc += lang.loc
            total_complexity += lang.complexity

        status = ToolStatus.SUCCESS if not warnings else ToolStatus.PARTIAL

        return ToolResult[SccData](
            tool=ToolName.SCC,
            status=status,
            evidence=[],
            data=SccData(
                languages=languages,
                files=total_files,
                loc=total_loc,
                complexity=total_complexity,
            ),
            warnings=warnings,
        )
