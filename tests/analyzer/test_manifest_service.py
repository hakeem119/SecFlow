# pyrefly: ignore [missing-import]
import json
from pathlib import Path
import pytest

from app.analyzer.services.manifest_reporter import (
    render_manifest_html,
    save_manifest_artifacts,
)


@pytest.fixture
def mock_manifest_data() -> dict:
    """Fixture providing a mock verified ProjectManifest dictionary."""
    return {
        "project": {
            "name": "SecFlow Benchmark App",
            "type": "web_application",
            "description": "Enterprise security demonstration repository",
            "primary_purpose": "Security automation",
        },
        "actors": [
            {"name": "Security Engineer", "role": "Full system inspection"},
            {"name": "Auditor", "role": "Read-only compliance reporting"},
        ],
        "technologies": [
            {
                "name": "FastAPI",
                "category": "framework",
                "evidence": [
                    {"file_path": "app/main.py", "description": "Application root"}
                ],
            },
            {
                "name": "Python",
                "category": "language",
                "evidence": [
                    {"file_path": "pyproject.toml", "description": "Runtime definition"}
                ],
            },
        ],
        "architecture": {
            "pattern": "modular_monolith",
            "entry_points": ["app/main.py"],
            "core_components": ["API Gateway", "Inspection Engine"],
            "data_flow_summary": "Inbound webhook -> Queue -> Analyzer",
        },
        "deployment": {
            "containerized": True,
            "configs": ["Dockerfile", "docker-compose.yml"],
            "target_platforms": ["Docker Engine"],
        },
        "key_dependencies": ["fastapi", "uvicorn", "pydantic"],
        "confidence_score": 0.98,
        "evidence_ledger": [],
    }


def test_render_manifest_html_structure(mock_manifest_data):
    """Ensure HTML report renders core project data and sanitized structures."""
    rendered_html = render_manifest_html(mock_manifest_data)

    assert "<!DOCTYPE html>" in rendered_html
    assert "SecFlow Benchmark App" in rendered_html
    assert "Security Engineer" in rendered_html
    assert "FastAPI" in rendered_html
    assert "modular_monolith" in rendered_html
    assert "Confidence: 98%" in rendered_html


def test_save_manifest_artifacts_disk_persistence(tmp_path: Path, mock_manifest_data):
    """Ensure JSON and HTML artifacts are correctly persisted inside target workspace."""
    artifacts = save_manifest_artifacts(str(tmp_path), mock_manifest_data)

    json_path = tmp_path / "project_manifest.json"
    html_path = tmp_path / "manifest.html"

    # Verify return mapping
    assert artifacts["manifest_json"] == str(json_path)
    assert artifacts["manifest_html"] == str(html_path)

    # Verify physical file existence
    assert json_path.exists()
    assert html_path.exists()

    # Verify persisted JSON integrity
    with open(json_path, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
    assert loaded_data["project"]["name"] == "SecFlow Benchmark App"
    assert loaded_data["confidence_score"] == 0.98

    # Verify persisted HTML integrity
    with open(html_path, "r", encoding="utf-8") as f:
        loaded_html = f.read()
    assert "<title>SecFlow Manifest Dashboard - SecFlow Benchmark App</title>" in loaded_html