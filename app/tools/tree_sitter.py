import logging

from app.schemas.tool import ToolContext, ToolName, ToolResult, ToolStatus, TreeSitterData
from app.tools.runner import CommandRunner

logger = logging.getLogger(__name__)


class TreeSitterAdapter:
    """
    Adapter for extracting AST nodes using tree-sitter.
    Pending M3 queries and extraction logic.
    """

    def __init__(self, runner: CommandRunner) -> None:
        self.runner = runner

    async def analyze(self, context: ToolContext) -> ToolResult[TreeSitterData]:
        """
        Stubbed pending M3 queries.
        """
        logger.info("TreeSitterAdapter is awaiting M3 query definitions.")

        return ToolResult[TreeSitterData](
            tool=ToolName.TREE_SITTER,
            status=ToolStatus.SUCCESS,
            evidence=[],
            data=TreeSitterData(nodes=[]),
            warnings=[],
        )
