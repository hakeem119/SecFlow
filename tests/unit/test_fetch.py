"""Unit tests for FetchResult schema (app/schemas/fetch.py)."""

from pathlib import PurePosixPath

import pytest
from app.schemas.fetch import FetchResult
from pydantic import ValidationError

_GOOD_COMMIT = "a" * 40
_GOOD_BRANCH = "main"
_GOOD_FILES: list[PurePosixPath] = [PurePosixPath("src/main.py")]


def _make(**kwargs: object) -> FetchResult:
    base: dict[str, object] = {
        "commit": _GOOD_COMMIT,
        "default_branch": _GOOD_BRANCH,
        "tracked_files": _GOOD_FILES,
    }
    base.update(kwargs)
    return FetchResult.model_validate(base)


# ---------------------------------------------------------------------------
# Valid construction
# ---------------------------------------------------------------------------


def test_fetchresult_valid() -> None:
    r = _make()
    assert r.commit == _GOOD_COMMIT
    assert r.default_branch == _GOOD_BRANCH


def test_fetchresult_empty_tracked_files() -> None:
    r = _make(tracked_files=[])
    assert r.tracked_files == []


def test_fetchresult_multiple_files() -> None:
    files = [PurePosixPath("a/b.py"), PurePosixPath("c/d.txt")]
    r = _make(tracked_files=files)
    assert len(r.tracked_files) == 2


# ---------------------------------------------------------------------------
# commit validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_commit",
    [
        "abc123",  # too short
        "A" * 40,  # upper-case hex not allowed
        "g" * 40,  # 'g' is not hex
        "",  # empty
        "a" * 39,  # 39 chars
        "a" * 41,  # 41 chars
    ],
)
def test_fetchresult_rejects_bad_commit(bad_commit: str) -> None:
    with pytest.raises(ValidationError):
        _make(commit=bad_commit)


# ---------------------------------------------------------------------------
# default_branch validation
# ---------------------------------------------------------------------------


def test_fetchresult_rejects_empty_branch() -> None:
    with pytest.raises(ValidationError, match="empty"):
        _make(default_branch="")


def test_fetchresult_rejects_branch_too_long() -> None:
    with pytest.raises(ValidationError, match="255"):
        _make(default_branch="a" * 256)


def test_fetchresult_rejects_branch_leading_dash() -> None:
    with pytest.raises(ValidationError, match="start with"):
        _make(default_branch="-main")


def test_fetchresult_rejects_branch_with_space() -> None:
    with pytest.raises(ValidationError, match="whitespace"):
        _make(default_branch="feature branch")


def test_fetchresult_rejects_branch_with_tab() -> None:
    with pytest.raises(ValidationError, match="non-printable"):
        _make(default_branch="feature\tbranch")


def test_fetchresult_rejects_branch_with_newline() -> None:
    with pytest.raises(ValidationError, match="non-printable"):
        _make(default_branch="feature\nbranch")


def test_fetchresult_rejects_branch_with_null() -> None:
    with pytest.raises(ValidationError, match="non-printable"):
        _make(default_branch="main\x00")


# ---------------------------------------------------------------------------
# tracked_files path validation
# ---------------------------------------------------------------------------


def test_fetchresult_rejects_absolute_path() -> None:
    with pytest.raises(ValidationError, match="relative"):
        _make(tracked_files=[PurePosixPath("/etc/passwd")])


def test_fetchresult_rejects_dotdot_component() -> None:
    with pytest.raises(ValidationError, match="traversal not allowed"):
        _make(tracked_files=[PurePosixPath("../secret")])


def test_fetchresult_rejects_dotdot_in_middle() -> None:
    with pytest.raises(ValidationError, match="traversal not allowed"):
        _make(tracked_files=[PurePosixPath("a/../b")])


def test_fetchresult_rejects_backslash_in_path() -> None:
    with pytest.raises(ValidationError, match="Invalid path"):
        _make(tracked_files=[PurePosixPath("a\\b")])


def test_fetchresult_rejects_nul_in_path() -> None:
    with pytest.raises(ValidationError, match="Invalid path"):
        _make(tracked_files=[PurePosixPath("a\x00b")])


def test_fetchresult_rejects_bare_dot_path() -> None:
    """PurePosixPath('.') is a non-empty string but a meaningless path."""
    with pytest.raises(ValidationError, match="Invalid path"):
        _make(tracked_files=[PurePosixPath(".")])
