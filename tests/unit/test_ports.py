from app.core.ports import AnalysisTool, RepositoryFetcher
from app.schemas.domain import GitHubRepoUrl, WorkspaceId
from app.schemas.fetch import FetchResult
from app.schemas.tool import ToolContext, ToolResult, ToolSpec


class FakeAdapter:
    @property
    def spec(self) -> ToolSpec:
        raise NotImplementedError

    async def fetch(self, url: GitHubRepoUrl, workspace_id: WorkspaceId) -> FetchResult:
        raise NotImplementedError

    async def analyze(self, context: ToolContext) -> ToolResult[str]:
        raise NotImplementedError


def _assert_fetcher(f: RepositoryFetcher) -> None:
    pass


def _assert_tool(t: AnalysisTool) -> None:
    pass


def test_protocol_conformance() -> None:
    fake = FakeAdapter()
    _assert_fetcher(fake)
    _assert_tool(fake)
