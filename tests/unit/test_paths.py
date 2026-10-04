from pathlib import PurePosixPath

import pytest
from app.schemas.paths import validate_posix_path


def test_valid_paths() -> None:
    # F5: valid cases include Arabic/Unicode printable names
    valid_paths_clean = ["file.py", "dir/file.py", "a..b.py", "dir.name/file", "مستند.txt"]
    for p in valid_paths_clean:
        validate_posix_path(PurePosixPath(p))


@pytest.mark.parametrize(
    "invalid_path, expected_match",
    [
        ("", "Invalid path"),
        (".", "Invalid path"),
        ("..", "Path traversal not allowed"),
        ("a/../b", "Path traversal not allowed"),
        ("/absolute/path", "Path must be relative"),
        ("has\\backslash", "Invalid path"),
        ("has\0nul", "Invalid path"),
        ("a" * 1025, "exceeds maximum length"),
        ("has\x01control", "non-printable character"),
        ("has\x7fcontrol", "non-printable character"),
        ("has\u2028control", "non-printable character"),
        ("has\u0085control", "non-printable character"),
    ],
)
def test_invalid_paths_raise(invalid_path: str, expected_match: str) -> None:
    with pytest.raises(ValueError, match=expected_match):
        validate_posix_path(PurePosixPath(invalid_path))
