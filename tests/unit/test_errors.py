import pytest
from app.core.errors import ErrorCode, ErrorContext, InvalidUrlError, SecFlowError


def test_invalid_url_error() -> None:
    err = InvalidUrlError(internal_ctx=ErrorContext(raw_input="http://foo"))
    assert err.stable_code == ErrorCode.INVALID_URL
    assert "GitHub" in err.message
    assert err._internal_ctx.raw_input == "http://foo"


def test_secflow_error_base_instantiation_fails() -> None:
    with pytest.raises(TypeError, match="SecFlowError must be subclassed"):
        SecFlowError()


def test_error_context_repr_redaction() -> None:
    ctx = ErrorContext(raw_input="secret123", tool_name="git", exit_code=1, path="/secret/path")
    r = repr(ctx)
    assert "secret123" not in r
    assert "/secret/path" not in r
    assert "tool_name='git'" in r

    err = InvalidUrlError(internal_ctx=ctx)
    err_r = repr(err)
    assert "secret123" not in err_r
    assert "/secret/path" not in err_r
