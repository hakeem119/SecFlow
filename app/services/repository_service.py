import logging
from typing import Any, Protocol

from app.core.safe_path import SafePath
from app.schemas.api import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyzeResponseStatus,
    RepositoryResponse,
    SnapshotResponse,
)
from app.schemas.domain import GitHubRepoUrl, WorkspaceId
from app.schemas.fetch import FetchResult
from app.schemas.tool import ToolContext, ToolResult
from app.services.workspace import WorkspaceManager

logger = logging.getLogger(__name__)


class GitPort(Protocol):
    """Protocol for fetching a repository into a workspace."""

    async def fetch(self, repo_url: GitHubRepoUrl, workspace_path: SafePath) -> FetchResult:
        """Clone the repository and return fetch metrics."""
        ...


class AnalysisTool(Protocol):
    """Protocol for external analysis tools per AGENTS.md."""

    async def analyze(self, context: ToolContext) -> ToolResult[Any]:
        """Run the tool and return normalized evidence and data."""
        ...


class SnapshotPort(Protocol):
    """Protocol for building and writing the final RepositorySnapshot."""

    async def write(
        self,
        repo_url: GitHubRepoUrl,
        fetch_result: FetchResult,
        tool_results: list[ToolResult[Any]],
        workspace_id: WorkspaceId,
    ) -> str:
        """Build, write the snapshot to disk, and return its relative location string."""
        ...


class RepositoryAnalysisService:
    """
    Orchestrates the repository analysis pipeline:
    create workspace -> git -> tools -> snapshot -> response.
    """

    def __init__(
        self,
        workspace_manager: WorkspaceManager,
        git_port: GitPort,
        tools: list[AnalysisTool],
        snapshot_port: SnapshotPort,
        timeout_seconds: int = 120,
        max_output_items: int = 500,
    ) -> None:
        self.workspace_manager = workspace_manager
        self.git_port = git_port
        self.tools = tools
        self.snapshot_port = snapshot_port
        self.timeout_seconds = timeout_seconds
        self.max_output_items = max_output_items

    async def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        workspace_id_str = await self.workspace_manager.create()
        workspace_id = WorkspaceId._validate(workspace_id_str)

        async with self.workspace_manager.lifecycle(workspace_id_str) as workspace_path:
            safe_workspace_path = SafePath(workspace_path, _internal=True)
            fetch_result = await self.git_port.fetch(request.repo_url, safe_workspace_path)

            tool_context = ToolContext(
                repository_path=workspace_path,
                include_paths=[],
                exclude_paths=[],
                timeout_seconds=self.timeout_seconds,
                max_output_items=self.max_output_items,
            )

            warnings: list[str] = []
            tool_results = []
            has_error = False
            has_success = False

            for tool in self.tools:
                try:
                    result = await tool.analyze(tool_context)
                    tool_results.append(result)
                    warnings.extend(result.warnings)
                    if result.status == "error":
                        has_error = True
                    else:
                        has_success = True
                except Exception:
                    logger.exception("Tool failed during analysis for workspace %s", workspace_id)
                    has_error = True
                    warnings.append("A tool failed unexpectedly.")

            if not has_success and self.tools:
                status = AnalyzeResponseStatus.ERROR
            elif has_error:
                status = AnalyzeResponseStatus.PARTIAL
            else:
                status = AnalyzeResponseStatus.SUCCESS

            location = await self.snapshot_port.write(
                repo_url=request.repo_url,
                fetch_result=fetch_result,
                tool_results=tool_results,
                workspace_id=workspace_id,
            )

            return AnalyzeResponse(
                status=status,
                workspace_id=workspace_id,
                repository=RepositoryResponse(
                    name=request.repo_url.repo,
                    url=request.repo_url,
                    commit=fetch_result.commit,
                ),
                snapshot=SnapshotResponse(location=location),
                warnings=warnings,
            )
