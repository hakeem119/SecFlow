# pyrefly: ignore [missing-import]
import os
import asyncio
from pathlib import Path
from langchain_core.tools import tool, BaseTool

from app.core.safe_path import SafePath

class FakeCommandRunner:
    """Fallback runner for Windows / testing environments."""
    async def run(self, req):
        class MockResult:
            stdout = b"mocked output"
            stderr = b""
        return MockResult()

try:
    from app.tools.runner import CommandRequest, ToolRunner
except ModuleNotFoundError:
    class CommandRequest:
        def __init__(self, **kwargs): pass
    ToolRunner = FakeCommandRunner

def build_adapter_tools(workspace_path: str, runner=None) -> list[BaseTool]:
    if runner is None:
        if os.name == 'nt':
            runner = FakeCommandRunner()
        else:
            runner = ToolRunner()

    @tool
    async def query_semgrep_pattern(pattern: str, target_path: str = ".") -> str:
        """Executes a controlled pattern match on-demand to verify framework usage or specific logic."""
        try:
            cwd = SafePath.within(Path(workspace_path), ".")
            req = CommandRequest(
                executable="semgrep",
                args=("-e", pattern, "--json", target_path),
                cwd=cwd,
                timeout=30,
                max_stdout_bytes=5*1024*1024,
                max_stderr_bytes=1024*1024,
            )
            res = await runner.run(req)
            return res.stdout.decode('utf-8', errors='ignore') or res.stderr.decode('utf-8', errors='ignore') or "No matches."
        except Exception as e:
            return f"Semgrep error: {e}"

    @tool
    async def query_syntax_symbols(file_path: str) -> str:
        """Invokes Tree-sitter inspection on an entry-point file to extract structural AST symbols (classes, functions, routes)."""
        try:
            cwd = SafePath.within(Path(workspace_path), ".")
            req = CommandRequest(
                executable="tree-sitter",
                args=("parse", file_path),
                cwd=cwd,
                timeout=30,
                max_stdout_bytes=5*1024*1024,
                max_stderr_bytes=1024*1024,
            )
            res = await runner.run(req)
            return res.stdout.decode('utf-8', errors='ignore') or "Parsed."
        except Exception as e:
            return f"Tree-sitter error: {e}"

    @tool
    async def query_code_metrics(subpath: str = "") -> str:
        """Invokes SCC on a subpath or directory to extract localized line-of-code and language metrics."""
        try:
            cwd = SafePath.within(Path(workspace_path), ".")
            target = subpath if subpath else "."
            req = CommandRequest(
                executable="scc",
                args=("-f", "json", target),
                cwd=cwd,
                timeout=30,
                max_stdout_bytes=5*1024*1024,
                max_stderr_bytes=1024*1024,
            )
            res = await runner.run(req)
            return res.stdout.decode('utf-8', errors='ignore')
        except Exception as e:
            return f"SCC error: {e}"

    @tool
    async def query_dependencies(ecosystem: str = "") -> str:
        """Invokes Syft or parses SBOM dependencies filtered by package ecosystem."""
        try:
            cwd = SafePath.within(Path(workspace_path), ".")
            req = CommandRequest(
                executable="syft",
                args=("dir:.", "-o", "json"),
                cwd=cwd,
                timeout=60,
                max_stdout_bytes=10*1024*1024,
                max_stderr_bytes=1024*1024,
            )
            res = await runner.run(req)
            return res.stdout.decode('utf-8', errors='ignore')[:5000]
        except Exception as e:
            return f"Syft error: {e}"

    @tool
    async def scan_secrets(target_path: str = ".") -> str:
        """Invokes detect-secrets on a specific candidate file or subfolder to verify credential exposure."""
        try:
            cwd = SafePath.within(Path(workspace_path), ".")
            req = CommandRequest(
                executable="detect-secrets",
                args=("scan", target_path),
                cwd=cwd,
                timeout=60,
                max_stdout_bytes=5*1024*1024,
                max_stderr_bytes=1024*1024,
            )
            res = await runner.run(req)
            return res.stdout.decode('utf-8', errors='ignore')
        except Exception as e:
            return f"detect-secrets error: {e}"

    @tool
    async def query_git_log(file_path: str = "", max_commits: int = 5) -> str:
        """Safely queries commit history and author information to determine project ownership and evolution."""
        try:
            cwd = SafePath.within(Path(workspace_path), ".")
            args = ["log", f"-n{max_commits}", "--oneline"]
            if file_path:
                args.extend(["--", file_path])
            req = CommandRequest(
                executable="git",
                args=tuple(args),
                cwd=cwd,
                timeout=30,
                max_stdout_bytes=5*1024*1024,
                max_stderr_bytes=1024*1024,
            )
            res = await runner.run(req)
            return res.stdout.decode('utf-8', errors='ignore') or "No history."
        except Exception as e:
            return f"Git error: {e}"

    return [query_semgrep_pattern, query_syntax_symbols, query_code_metrics, query_dependencies, scan_secrets, query_git_log]
