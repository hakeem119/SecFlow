import os
import re
from pathlib import Path
from typing import List
from langchain_core.tools import tool

from app.core.safe_path import SafePath, PathSecurityError, open_nofollow

def _resolve_safe_path(workspace_path: str, target: str) -> Path:
    """Helper to validate paths securely."""
    ws = Path(workspace_path).resolve()
    clean_target = target.strip() if target else ""
    # Treat current directory aliases as root workspace directly
    if not clean_target or clean_target in [".", "./", ".\\"]:
        return ws
    try:
        return SafePath.within(ws, clean_target).path
    except PathSecurityError as e:
        raise ValueError(f"Boundary Error: Cannot access {target} outside workspace.") from e
    
def build_file_tools(workspace_path: str) -> list:
    @tool
    def read_file(path: str, start_line: int = 1, end_line: int = 200) -> str:
        """Reads a slice of a file within the workspace. Returns line numbers alongside content."""
        try:
            target = _resolve_safe_path(workspace_path, path)
            try:
                fd = open_nofollow(target)
                f = os.fdopen(fd, 'r', encoding='utf-8', errors='ignore')
            except AttributeError:
                f = open(target, 'r', encoding='utf-8', errors='ignore')
            with f:
                lines = f.readlines()
            
            start = max(0, start_line - 1)
            end = min(len(lines), end_line)
            return "\n".join(f"{i+1}: {lines[i].rstrip()}" for i in range(start, end))
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"Error reading file: {e}"

    @tool
    def search_code(query: str, path_regex: str = "") -> str:
        """Performs literal/regex search across workspace source files. Returns matched file paths and lines."""
        try:
            root = Path(workspace_path)
            pattern = re.compile(path_regex) if path_regex else None
            results = []
            
            for filepath in root.rglob("*"):
                if not filepath.is_file():
                    continue
                try:
                    rel_path = str(filepath.relative_to(root)).replace("\\", "/")
                    if pattern and not pattern.search(rel_path):
                        continue
                    
                    try:
                        fd = open_nofollow(filepath)
                        f = os.fdopen(fd, 'r', encoding='utf-8', errors='ignore')
                    except AttributeError:
                        f = open(filepath, 'r', encoding='utf-8', errors='ignore')
                    with f:
                        for i, line in enumerate(f):
                            if query in line:
                                results.append(f"{rel_path}:{i+1}:{line.strip()}")
                                if len(results) >= 15:
                                    return "\n".join(results)
                except Exception:
                    pass
            return "\n".join(results) if results else "No matches found."
        except Exception as e:
            return f"Error searching code: {e}"

    @tool
    def list_files(directory: str = ".") -> str:
        """Lists directory contents safely within the workspace."""
        try:
            target = _resolve_safe_path(workspace_path, directory)
            if not target.is_dir():
                return f"Error: {directory} is not a directory."
            items = []
            for item in target.iterdir():
                suffix = "/" if item.is_dir() else ""
                items.append(f"{item.name}{suffix}")
            return "\n".join(items) if items else "Empty directory."
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"Error listing files: {e}"

    @tool
    def get_file_metadata(path: str) -> str:
        """Returns file size, total line count, and last modification timestamp."""
        try:
            target = _resolve_safe_path(workspace_path, path)
            stat = target.stat()
            try:
                fd = open_nofollow(target)
                f = os.fdopen(fd, 'r', encoding='utf-8', errors='ignore')
            except AttributeError:
                f = open(target, 'r', encoding='utf-8', errors='ignore')
            with f:
                lines = sum(1 for _ in f)
            return f"Size: {stat.st_size} bytes\nLines: {lines}\nModified: {stat.st_mtime}"
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"Error getting metadata: {e}"

    return [read_file, search_code, list_files, get_file_metadata]
