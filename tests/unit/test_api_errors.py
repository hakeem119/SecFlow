from pathlib import Path

import pytest
from app.api.error_table import DOMAIN_STATUS_TABLE, TRANSPORT_ERROR_TABLE, TransportError
from app.core.config import Settings
from app.core.errors import ErrorCode
from app.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    app = create_app(Settings(workspace_root=Path("/var/lib/secflow/workspaces")))
    return TestClient(app)


def test_unknown_route(client: TestClient) -> None:
    response = client.get("/unknown_route")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "invalid_request"
    assert data["message"] == "Not found"
    assert "detail" not in data


def test_wrong_method(client: TestClient) -> None:
    response = client.delete("/health")
    assert response.status_code == 405
    assert "allow" in response.headers
    data = response.json()
    assert data["error_code"] == "invalid_request"
    assert data["message"] == "Method not allowed"


def test_post_health_no_json(client: TestClient) -> None:
    response = client.post("/health")
    assert response.status_code == 415
    data = response.json()
    assert data["error_code"] == "invalid_request"
    assert data["message"] == "Unsupported Media Type: Must be application/json"


def test_error_table_completeness() -> None:
    for code in ErrorCode:
        assert code in DOMAIN_STATUS_TABLE
        status_code = DOMAIN_STATUS_TABLE[code]
        assert isinstance(status_code, int)

    for t_code in TransportError:
        assert t_code in TRANSPORT_ERROR_TABLE
        status_code, err_code, msg = TRANSPORT_ERROR_TABLE[t_code]
        assert isinstance(status_code, int)
        assert isinstance(err_code, ErrorCode)
        assert isinstance(msg, str)


def test_generic_http_exception() -> None:
    # Test route raising a generic HTTPException
    from fastapi import FastAPI, HTTPException

    app = FastAPI()

    from app.api.error_handlers import http_exception_handler
    from starlette.exceptions import HTTPException as StarletteHTTPException

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]

    @app.get("/test_418")
    def test_418() -> None:
        raise HTTPException(status_code=418, detail="I'm a teapot")

    client = TestClient(app)
    response = client.get("/test_418")
    assert response.status_code == 418
    data = response.json()
    assert data["error_code"] == "invalid_request"
    assert data["message"] == "HTTP Exception"
    assert "detail" not in data


def test_analyze_repository_invalid_json(client: TestClient) -> None:
    response = client.post(
        "/api/v1/repositories/analyze",
        content=b"invalid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "invalid_request"
    assert data["message"] == "Invalid request payload"
    assert "detail" not in data
    assert "input" not in data


def test_analyze_repository_empty_body(client: TestClient) -> None:
    response = client.post(
        "/api/v1/repositories/analyze", content=b"", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "invalid_request"


def test_analyze_repository_null_body(client: TestClient) -> None:
    response = client.post(
        "/api/v1/repositories/analyze",
        content=b"null",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "invalid_request"


def test_analyze_repository_invalid_url(client: TestClient) -> None:
    response = client.post(
        "/api/v1/repositories/analyze",
        json={"repo_url": "https://not-github.com/owner/repo", "analysis_depth": "standard"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "invalid_url"
    assert "detail" not in data


def test_analyze_repository_extra_field(client: TestClient) -> None:
    response = client.post(
        "/api/v1/repositories/analyze",
        json={
            "repo_url": "https://github.com/owner/repo",
            "analysis_depth": "standard",
            "extra": "field",
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "invalid_request"


def test_delete_workspace_invalid_uuid(client: TestClient) -> None:
    response = client.delete("/api/v1/workspaces/invalid-uuid")
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "invalid_request"
