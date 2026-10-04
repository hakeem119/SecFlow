import json
import uuid

import pytest
from app.core.errors import ErrorCode
from app.schemas.api import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyzeResponseStatus,
    ErrorResponse,
    RepositoryResponse,
    SnapshotResponse,
)
from app.schemas.domain import GitHubRepoUrl, WorkspaceId
from pydantic import ValidationError


def test_analyze_request_valid() -> None:
    req = AnalyzeRequest(repo_url=GitHubRepoUrl.parse("https://github.com/owner/repo"))
    assert str(req.repo_url) == "https://github.com/owner/repo"
    assert req.analysis_depth.value == "standard"


def test_error_response_valid() -> None:
    err = ErrorResponse(error_code=ErrorCode.INVALID_URL, message="Invalid URL.")
    assert err.error_code == ErrorCode.INVALID_URL
    assert err.status.value == "error"


def test_analyze_response_json_roundtrip_and_schema() -> None:
    wid = WorkspaceId(uuid.uuid4())
    resp = AnalyzeResponse(
        status=AnalyzeResponseStatus.SUCCESS,
        workspace_id=wid,
        repository=RepositoryResponse(
            name="repo",
            url=GitHubRepoUrl.parse("https://github.com/owner/repo"),
            commit="a" * 40,
        ),
        snapshot=SnapshotResponse(location=f"{wid}/repository_snapshot.yaml"),
        warnings=["warning1"],
    )

    j_str = resp.model_dump_json()
    j_dict = json.loads(j_str)

    # Check that WorkspaceId is serialized as string
    assert j_dict["workspace_id"] == str(wid)

    # Generate OpenAPI schema and verify
    schema = AnalyzeResponse.model_json_schema()
    assert "workspace_id" in schema["properties"]
    assert schema["properties"]["workspace_id"]["type"] == "string"


def test_analyze_request_schema() -> None:
    schema = AnalyzeRequest.model_json_schema()
    assert "repo_url" in schema["properties"]
    assert schema["properties"]["repo_url"]["type"] == "string"


def test_analyze_response_invalid_location() -> None:
    wid = WorkspaceId(uuid.uuid4())
    with pytest.raises(ValidationError, match="must be exactly"):
        AnalyzeResponse(
            status=AnalyzeResponseStatus.SUCCESS,
            workspace_id=wid,
            repository=RepositoryResponse(
                name="repo",
                url=GitHubRepoUrl("owner", "repo"),
                commit="a" * 40,
            ),
            snapshot=SnapshotResponse(location=f"{wid}/wrong_file.yaml"),
            warnings=[],
        )
