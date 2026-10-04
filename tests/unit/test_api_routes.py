import importlib
from pathlib import Path

import pytest
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    app = create_app(Settings(workspace_root=Path("/var/lib/secflow/workspaces")))
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_repository_valid(client: TestClient) -> None:
    response = client.post(
        "/api/v1/repositories/analyze",
        json={"repo_url": "https://github.com/owner/repo", "analysis_depth": "standard"},
    )
    assert response.status_code == 501
    assert response.json() == {
        "error_code": "not_implemented",
        "status": "error",
        "message": "Endpoint or feature is not implemented yet.",
    }


def test_delete_workspace_valid(client: TestClient) -> None:
    import uuid

    workspace_id = str(uuid.uuid4())
    response = client.delete(f"/api/v1/workspaces/{workspace_id}")
    assert response.status_code == 501
    assert response.json() == {
        "error_code": "not_implemented",
        "status": "error",
        "message": "Endpoint or feature is not implemented yet.",
    }


def test_create_app_no_args(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECFLOW_WORKSPACE_ROOT", "/var/lib/secflow/workspaces")
    app = create_app()
    assert app.state.settings is not None
    assert app.state.settings.workspace_root == Path("/var/lib/secflow/workspaces")


def test_import_main_unset_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECFLOW_WORKSPACE_ROOT", raising=False)
    # Import should succeed even if env var is missing, since it's evaluated at runtime
    import app.main

    importlib.reload(app.main)
    from pydantic import ValidationError

    # The app should only fail if create_app is called without settings
    with pytest.raises(ValidationError):
        app.main.create_app()
