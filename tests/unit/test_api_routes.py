import importlib
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    app = create_app(Settings(workspace_root=tmp_path / "workspaces"))
    with TestClient(app) as c:
        yield c


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

    workspace_id = str(uuid.uuid4())
    response = client.delete(f"/api/v1/workspaces/{workspace_id}")
    assert response.status_code == 404
    assert response.json() == {
        "error_code": "workspace_not_found",
        "status": "error",
        "message": "The requested workspace does not exist or has expired.",
    }


def test_delete_workspace_no_lifespan(tmp_path: Path) -> None:
    app = create_app(Settings(workspace_root=tmp_path / "workspaces"))
    # TestClient without `with` context does NOT run lifespan
    c = TestClient(app)

    workspace_id = str(uuid.uuid4())
    response = c.delete(f"/api/v1/workspaces/{workspace_id}")
    assert response.status_code == 404
    assert response.json()["error_code"] == "workspace_not_found"


def test_create_app_no_args(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SECFLOW_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    app = create_app()
    assert app.state.settings is not None
    assert app.state.settings.workspace_root == tmp_path / "workspaces"


def test_import_main_unset_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECFLOW_WORKSPACE_ROOT", raising=False)
    # Import should succeed even if env var is missing, since it's evaluated at runtime
    import app.main

    importlib.reload(app.main)
    from pydantic import ValidationError

    # The app should only fail if create_app is called without settings
    with pytest.raises(ValidationError):
        app.main.create_app()


@pytest.mark.asyncio
async def test_concurrent_delete_api(client: TestClient, tmp_path: Path) -> None:
    # We must run two async tasks to test concurrency properly, but TestClient is sync.
    # To test API level concurrent delete, we can use AsyncClient.
    # Let's just create a workspace via manager and use httpx.AsyncClient
    import asyncio
    from pathlib import Path

    from app.core.config import Settings
    from app.main import create_app
    from httpx import ASGITransport, AsyncClient

    app = create_app(Settings(workspace_root=Path(tmp_path / "workspaces_test_api")))
    # Use lifespan context to initialize manager and run reaper, otherwise state isn't populated
    async with ASGITransport(app=app):  # Lifespan init
        pass

    # Lifespan must be entered explicitly if testing app state
    # Wait, in the other tests, client calls hit the app directly.
    # Let's just mock the manager state for the test
    from app.services.workspace import WorkspaceManager

    manager = WorkspaceManager(Path(tmp_path / "workspaces_test_api"), 3600, lambda: 1000.0)
    app.state.workspace_manager = manager
    (tmp_path / "workspaces_test_api").mkdir()
    (tmp_path / "workspaces_test_api" / ".meta").mkdir()
    (tmp_path / "workspaces_test_api" / ".trash").mkdir()

    ws_id = await manager.create()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        results = await asyncio.gather(
            ac.delete(f"/api/v1/workspaces/{ws_id}"), ac.delete(f"/api/v1/workspaces/{ws_id}")
        )

        status_codes = [r.status_code for r in results]
        assert 204 in status_codes
        assert 404 in status_codes
        assert 500 not in status_codes
