# pyrefly: ignore [missing-import]
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.config import get_settings
from app.analyzer.services.analyzer_service import run_analyzer_workflow

router = APIRouter(prefix="/analyzer", tags=["AI Analyzer"])


def _resolve_workspace(workspace_id: str) -> Path:
    """
    Safely resolves workspace path against the configured workspace root.
    Guards against path traversal characters.
    """
    if ".." in workspace_id or "/" in workspace_id or "\\" in workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID parameter.",
        )

    settings = get_settings()
    workspace_root = Path(settings.workspace_dir).resolve()
    target_path = (workspace_root / workspace_id).resolve()

    if not str(target_path).startswith(str(workspace_root)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Boundary Error: Workspace resolution outside root.",
        )

    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )

    return target_path


@router.post("/{workspace_id}/run")
def run_repository_analysis(workspace_id: str):
    """
    Triggers the LangGraph AI Analyzer agent loop for the target workspace.
    Parses repository snapshot, executes safe evidence inspection,
    and saves project_manifest.json and manifest.html.
    """
    workspace_path = _resolve_workspace(workspace_id)
    result = run_analyzer_workflow(str(workspace_path))
    return {
        "status": "success",
        "workspace_id": workspace_id,
        "iteration_count": result.get("iteration_count"),
        "artifacts": result.get("artifacts"),
        "manifest": result.get("manifest"),
    }


@router.get("/{workspace_id}/manifest")
def get_manifest_json(workspace_id: str):
    """
    Retrieves the generated project_manifest.json for the workspace.
    """
    workspace_path = _resolve_workspace(workspace_id)
    manifest_file = workspace_path / "project_manifest.json"

    if not manifest_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="project_manifest.json not found for this workspace. Run analysis first.",
        )

    with open(manifest_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return JSONResponse(content=data)


@router.get("/{workspace_id}/html", response_class=HTMLResponse)
def get_manifest_dashboard(workspace_id: str):
    """
    Renders and serves the interactive manifest.html dashboard.
    """
    workspace_path = _resolve_workspace(workspace_id)
    html_file = workspace_path / "manifest.html"

    if not html_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="manifest.html dashboard not found for this workspace. Run analysis first.",
        )

    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read()

    return HTMLResponse(content=content)