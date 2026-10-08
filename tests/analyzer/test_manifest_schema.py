import pytest
from pydantic import ValidationError

from app.analyzer.schemas.manifest import ProjectManifest

def get_valid_manifest_data() -> dict:
    return {
        "project": {
            "name": "sample-app",
            "type": "web_application",
            "description": "A sample web application",
            "primary_purpose": "Demonstrate functionality"
        },
        "actors": [
            {"name": "Admin", "role": "Full access"}
        ],
        "technologies": [
            {
                "name": "Python",
                "category": "language",
                "evidence": [
                    {
                        "file_path": "main.py",
                        "description": "Main app entry"
                    }
                ]
            }
        ],
        "architecture": {
            "pattern": "monolith",
            "entry_points": ["main.py"],
            "core_components": ["api", "db"],
            "data_flow_summary": "Client to server"
        },
        "deployment": {
            "containerized": True,
            "configs": ["Dockerfile"],
            "target_platforms": ["Docker"]
        },
        "key_dependencies": ["fastapi", "pydantic"],
        "confidence_score": 0.95,
        "evidence_ledger": []
    }

def test_valid_manifest_serialization():
    data = get_valid_manifest_data()
    manifest = ProjectManifest(**data)
    assert manifest.project.name == "sample-app"
    
    # Test serialization to JSON
    json_data = manifest.model_dump_json()
    assert "sample-app" in json_data

def test_extra_forbid():
    data = get_valid_manifest_data()
    data["unknown_key"] = "This should fail"
    
    with pytest.raises(ValidationError) as exc_info:
        ProjectManifest(**data)
    
    # Verify that an extra input error is raised
    assert "Extra inputs are not permitted" in str(exc_info.value) or "unknown_key" in str(exc_info.value)

def test_invalid_confidence_score():
    data = get_valid_manifest_data()
    
    # Over 1.0 should fail
    data["confidence_score"] = 1.5
    with pytest.raises(ValidationError) as exc_info:
        ProjectManifest(**data)
    assert "less than or equal to 1" in str(exc_info.value) or "Input should be <= 1" in str(exc_info.value)

    # Under 0.0 should fail
    data["confidence_score"] = -0.1
    with pytest.raises(ValidationError) as exc_info:
        ProjectManifest(**data)
    assert "greater than or equal to 0" in str(exc_info.value) or "Input should be >= 0" in str(exc_info.value)
