import json
import pytest
from langgraph.graph import END

from app.analyzer.graph.state import AgentState
from app.analyzer.graph.validation import extract_json_payload, validation_node
from app.analyzer.graph.workflow import MAX_ITERATIONS, route_after_validation


def get_valid_payload() -> dict:
    """Helper generating a schema-compliant manifest payload."""
    return {
        "project": {
            "name": "sample-app",
            "type": "web_application",
            "description": "A sample web application",
            "primary_purpose": "Demonstrate functionality",
        },
        "actors": [{"name": "Admin", "role": "Full access"}],
        "technologies": [
            {
                "name": "Python",
                "category": "language",
                "evidence": [
                    {"file_path": "main.py", "description": "Main app entry"}
                ],
            }
        ],
        "architecture": {
            "pattern": "monolith",
            "entry_points": ["main.py"],
            "core_components": ["api", "db"],
            "data_flow_summary": "Client to server",
        },
        "deployment": {
            "containerized": True,
            "configs": ["Dockerfile"],
            "target_platforms": ["Docker"],
        },
        "key_dependencies": ["fastapi", "pydantic"],
        "confidence_score": 0.95,
        "evidence_ledger": [],
    }


def test_extract_json_payload_markdown_stripping():
    """Ensure json extraction strips markdown code fences."""
    raw = '```json\n{"key": "value"}\n```'
    extracted = extract_json_payload(raw)
    assert extracted == '{"key": "value"}'


def test_validation_node_valid_manifest():
    """Ensure validation passes cleanly for valid ProjectManifest schema."""
    valid_data = get_valid_payload()
    state: AgentState = {
        "messages": [],
        "snapshot_data": {},
        "workspace_path": "/mock/workspace",
        "manifest_draft": json.dumps(valid_data),
        "validation_errors": [],
        "iteration_count": 1,
    }
    res = validation_node(state)
    assert res["validation_errors"] == []


def test_validation_node_catches_schema_violations():
    """Ensure validation node catches forbidden extra fields and invalid bounds."""
    invalid_data = get_valid_payload()
    invalid_data["unknown_extra_field"] = "malicious"
    invalid_data["confidence_score"] = 2.5  # Exceeds max 1.0

    state: AgentState = {
        "messages": [],
        "snapshot_data": {},
        "workspace_path": "/mock/workspace",
        "manifest_draft": json.dumps(invalid_data),
        "validation_errors": [],
        "iteration_count": 1,
    }
    res = validation_node(state)
    assert len(res["validation_errors"]) >= 1
    error_blob = " ".join(res["validation_errors"])
    assert "unknown_extra_field" in error_blob or "confidence_score" in error_blob


def test_route_after_validation_feedback_loop():
    """Ensure route_after_validation redirects to 'agent' when errors exist."""
    state_with_errors: AgentState = {
        "messages": [],
        "snapshot_data": {},
        "workspace_path": "/mock/workspace",
        "manifest_draft": "{}",
        "validation_errors": ["Field 'project': Field required"],
        "iteration_count": 1,
    }
    assert route_after_validation(state_with_errors) == "agent"


def test_route_after_validation_success():
    """Ensure route_after_validation reaches END when validation errors are empty."""
    state_clean: AgentState = {
        "messages": [],
        "snapshot_data": {},
        "workspace_path": "/mock/workspace",
        "manifest_draft": "{}",
        "validation_errors": [],
        "iteration_count": 1,
    }
    assert route_after_validation(state_clean) == END


def test_route_after_validation_respects_iteration_limit():
    """Ensure router terminates at MAX_ITERATIONS even with validation errors."""
    state_capped: AgentState = {
        "messages": [],
        "snapshot_data": {},
        "workspace_path": "/mock/workspace",
        "manifest_draft": "{}",
        "validation_errors": ["Error here"],
        "iteration_count": MAX_ITERATIONS,
    }
    assert route_after_validation(state_capped) == END