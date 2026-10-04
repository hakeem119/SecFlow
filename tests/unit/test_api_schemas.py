from app.core.errors import ErrorCode
from app.schemas.api import AnalyzeRequest, ErrorResponse
from app.schemas.domain import GitHubRepoUrl


def test_analyze_request_valid() -> None:
    req = AnalyzeRequest(repo_url=GitHubRepoUrl("owner", "repo"))
    assert str(req.repo_url) == "https://github.com/owner/repo"
    assert req.analysis_depth.value == "standard"


def test_error_response_valid() -> None:
    err = ErrorResponse(error_code=ErrorCode.INVALID_URL, message="Invalid URL.")
    assert err.error_code == ErrorCode.INVALID_URL
    assert err.status.value == "error"
