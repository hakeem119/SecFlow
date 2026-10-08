import pytest
from pathlib import Path
from app.analyzer.tools.factory import get_analyzer_tools

def test_tool_registry(tmp_path: Path):
    tools = get_analyzer_tools(str(tmp_path))
    assert len(tools) == 10
    names = [t.name for t in tools]
    assert "read_file" in names
    assert "search_code" in names
    assert "list_files" in names
    assert "get_file_metadata" in names
    assert "query_semgrep_pattern" in names
    assert "query_syntax_symbols" in names
    assert "query_code_metrics" in names
    assert "query_dependencies" in names
    assert "scan_secrets" in names
    assert "query_git_log" in names

def test_workspace_sandboxing(tmp_path: Path):
    tools = get_analyzer_tools(str(tmp_path))
    read_file = next(t for t in tools if t.name == "read_file")
    
    # Try directory traversal
    result = read_file.invoke({"path": "../../../../etc/passwd"})
    assert "Boundary Error" in result

def test_safe_reading(tmp_path: Path):
    tools = get_analyzer_tools(str(tmp_path))
    read_file = next(t for t in tools if t.name == "read_file")
    
    test_file = tmp_path / "test.txt"
    test_file.write_text("line 1\nline 2\nline 3\n")
    
    result = read_file.invoke({"path": "test.txt", "start_line": 1, "end_line": 2})
    assert "1: line 1" in result
    assert "2: line 2" in result
    assert "3: line 3" not in result
