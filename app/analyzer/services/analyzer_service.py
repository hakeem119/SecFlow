# pyrefly: ignore [missing-import]
import json
from pathlib import Path
from typing import Any
import yaml

from app.analyzer.graph.state import AgentState
from app.analyzer.graph.workflow import create_analyzer_graph
from app.analyzer.services.manifest_reporter import save_manifest_artifacts


def run_analyzer_workflow(workspace_path: str) -> dict[str, Any]:
    """
    Executes the SecFlow AI Analyzer pipeline for a target workspace.
    Loads repository_snapshot.yaml, runs the LangGraph ReAct agent loop,
    validates the manifest schema, and persists output artifacts.
    """
    ws_path = Path(workspace_path)
    snapshot_file = ws_path / "repository_snapshot.yaml"

    snapshot_data: dict[str, Any] = {}
    if snapshot_file.exists():
        try:
            with open(snapshot_file, "r", encoding="utf-8") as f:
                snapshot_data = yaml.safe_load(f) or {}
        except Exception as e:
            snapshot_data = {"error": f"Failed to load snapshot: {str(e)}"}

    # Initialize execution state
    initial_state: AgentState = {
        "messages": [],
        "snapshot_data": snapshot_data,
        "workspace_path": str(ws_path.resolve()),
        "manifest_draft": None,
        "validation_errors": [],
        "iteration_count": 0,
    }

    # Execute compiled cognitive graph
    graph = create_analyzer_graph()
    final_state = graph.invoke(initial_state)

    manifest_draft = final_state.get("manifest_draft")
    manifest_json_data: dict[str, Any] = {}

    if manifest_draft:
        try:
            manifest_json_data = json.loads(manifest_draft)
        except Exception:
            manifest_json_data = {"raw_output": manifest_draft}

    # Persist artifacts inside target workspace sandbox
    artifacts: dict[str, str] = {}
    if manifest_json_data:
        artifacts = save_manifest_artifacts(str(ws_path), manifest_json_data)

    return {
        "manifest": manifest_json_data,
        "artifacts": artifacts,
        "iteration_count": final_state.get("iteration_count", 0),
        "validation_errors": final_state.get("validation_errors", []),
    }