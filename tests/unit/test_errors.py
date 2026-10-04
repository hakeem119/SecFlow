from app.core.errors import ErrorCode, InvalidUrlError


def test_invalid_url_error() -> None:
    err = InvalidUrlError(details={"raw": "http://foo"})
    assert err.stable_code == ErrorCode.INVALID_URL
    assert "GitHub" in err.message
    assert err.details == {"raw": "http://foo"}
