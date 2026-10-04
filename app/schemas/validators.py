import re

GITHUB_REPO_NAME_RE = re.compile(r"[A-Za-z0-9._-]{1,100}")


def validate_branch_name(v: str) -> str:
    """
    Reject branches that would be unsafe to use as ref names or log values.
    Rules: Non-empty, ≤ 255 chars, no leading '-', no ASCII whitespace or control characters.
    """
    if not v:
        raise ValueError("branch name must not be empty")
    if len(v) > 255:
        raise ValueError("branch name exceeds 255 characters")
    if v.startswith("-"):
        raise ValueError("branch name must not start with '-'")
    for ch in v:
        if not ch.isprintable():
            raise ValueError("branch name contains non-printable character")
        if ch == " ":
            raise ValueError("branch name must not contain whitespace")
    return v


def validate_repo_name(v: str) -> str:
    """
    Validate a repository name.
    Rules: 1-100 characters.
    """
    if not v or len(v) > 100:
        raise ValueError("Repository name must be 1-100 characters")
    if v in (".", ".."):
        raise ValueError("Repo name cannot be '.' or '..'")

    if not GITHUB_REPO_NAME_RE.fullmatch(v):
        raise ValueError("Repository name contains invalid characters")
    return v
