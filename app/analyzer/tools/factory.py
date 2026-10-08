from langchain_core.tools import BaseTool
from app.analyzer.tools.file_tools import build_file_tools
from app.analyzer.tools.adapter_tools import build_adapter_tools

def get_analyzer_tools(workspace_path: str) -> list[BaseTool]:
    """Instantiates and returns all 10 safe tools bound to the active workspace path."""
    return build_file_tools(workspace_path) + build_adapter_tools(workspace_path)
