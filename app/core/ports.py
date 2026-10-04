from typing import Any, Protocol

from app.schemas.domain import GitHubRepoUrl, WorkspaceId
from app.schemas.fetch import FetchResult
from app.schemas.tool import ToolContext, ToolResult, ToolSpec


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
    def spec(self) -> ToolSpec: ...

    async def analyze(self, context: ToolContext) -> ToolResult[Any]: ...
