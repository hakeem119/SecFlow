from pathlib import PurePosixPath


def validate_posix_path(p: PurePosixPath) -> None:
    """
    Validate a PurePosixPath to ensure it is relative and safe from traversal.

    Note: Phase 4/9 must filter files that fail this check, with a warning,
    BEFORE validation, so one hostile filename cannot fail the whole snapshot.
    """
    p_str = str(p)
    if not p_str or p_str == ".":
        raise ValueError(f"Invalid path: {p}")
    if len(p_str) > 1024:
        raise ValueError(f"Path exceeds maximum length of 1024 characters: {p}")
    if "\\" in p_str or "\0" in p_str:
        raise ValueError(f"Invalid path: {p}")
    for ch in p_str:
        if not ch.isprintable():
            raise ValueError(f"Path contains non-printable character: {p}")
    if p.is_absolute():
        raise ValueError(f"Path must be relative: {p}")
    # Check parts exactly to reject ".." but allow valid substrings like "a..b.py"
    if ".." in p.parts:
        raise ValueError(f"Path traversal not allowed: {p}")
