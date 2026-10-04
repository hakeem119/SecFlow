from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.domain import GitHubRepoUrl, WorkspaceId
from app.schemas.tool import ToolContext, ToolResult, ToolSpec


class FetchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    commit: str = Field(..., description="The fetched commit hash")
    default_branch: str = Field(..., description="The default branch name")
    tracked_files: list[Path] = Field(..., description="List of tracked file paths")


class RepositoryFetcher(Protocol):
    """
    Port for fetching a repository into a workspace.
    """

    async def fetch(self, url: GitHubRepoUrl, workspace_id: WorkspaceId) -> FetchResult: ...


class AnalysisTool(Protocol):
    """
    Port for wrapping a static analysis tool execution.
    Async is explicitly used here (and in Fetcher) because these adapters wrap
    subprocess I/O and network operations, preventing the FastAPI event loop from blocking.
    """

    @property
    def name(self) -> str: ...

    @property
    def spec(self) -> ToolSpec: ...

    async def analyze(self, context: ToolContext) -> ToolResult[Any]: ...
