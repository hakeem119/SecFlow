"""
Unit tests for WorkspaceId and GitHubRepoUrl value objects (domain.py).

Coverage targets:
- WorkspaceId.__init__: rejects non-v4 UUID directly
- WorkspaceId.__eq__: False for non-WorkspaceId
- WorkspaceId._validate: rejects non-str/non-UUID input
- WorkspaceId._validate: rejects trailing \\n in string (fullmatch)
- WorkspaceId.__delattr__: blocked
- GitHubRepoUrl.__init__: validates owner/repo directly
- GitHubRepoUrl.__eq__: False for non-GitHubRepoUrl
- GitHubRepoUrl._validate: trailing \\n in owner/repo rejected (fullmatch)
- GitHubRepoUrl.__delattr__: blocked
- Credentials/port rejection: the netloc check fires (no separate guard)
- GITHUB.COM upper-case host: accepted (netloc is case-folded)
"""

import json
import uuid

import pytest
from app.schemas.domain import GitHubRepoUrl, WorkspaceId
from pydantic import BaseModel, ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class WsDummy(BaseModel):
    ws_id: WorkspaceId


class UrlDummy(BaseModel):
    url: GitHubRepoUrl


# ===========================================================================
# WorkspaceId — valid paths
# ===========================================================================


def test_workspace_id_init_typeerror() -> None:
    with pytest.raises(TypeError, match="initialized with a UUID object"):
        WorkspaceId("not-a-uuid")  # type: ignore[arg-type]


def test_workspace_id_valid() -> None:
    u = uuid.uuid4()
    d = WsDummy(ws_id=u)  # type: ignore[arg-type]
    assert str(d.ws_id) == str(u)


def test_workspace_id_string_valid() -> None:
    u = str(uuid.uuid4())
    d = WsDummy(ws_id=u)  # type: ignore[arg-type]
    assert str(d.ws_id) == u


def test_workspace_id_eq_same() -> None:
    u = uuid.uuid4()
    a = WorkspaceId(u)
    b = WorkspaceId(u)
    assert a == b
    assert hash(a) == hash(b)


def test_workspace_id_eq_different() -> None:
    a = WorkspaceId(uuid.uuid4())
    b = WorkspaceId(uuid.uuid4())
    assert a != b


def test_workspace_id_json_roundtrip() -> None:
    u = uuid.uuid4()
    d = WsDummy(ws_id=u)  # type: ignore[arg-type]
    j = json.loads(d.model_dump_json())
    assert j["ws_id"] == str(u)


def test_workspace_id_json_schema() -> None:
    schema = WsDummy.model_json_schema()
    assert schema["properties"]["ws_id"]["type"] == "string"


def test_workspace_id_passthrough() -> None:
    """_validate returns the same instance when passed a WorkspaceId."""
    ws = WorkspaceId(uuid.uuid4())
    assert WorkspaceId._validate(ws) is ws


# ===========================================================================
# WorkspaceId — invalid / immutability
# ===========================================================================


def test_workspace_id_rejects_uuid1() -> None:
    """__init__ rejects a non-v4 UUID directly (no Pydantic involved)."""
    with pytest.raises(ValueError, match="UUID v4"):
        WorkspaceId(uuid.uuid1())


def test_workspace_id_eq_non_workspace_id() -> None:
    """__eq__ returns False (not an error) for a non-WorkspaceId."""
    ws = WorkspaceId(uuid.uuid4())
    assert ws != "not-a-workspace-id"
    assert ws != 42
    assert ws != None  # noqa: E711


def test_workspace_id_rejects_non_str_non_uuid() -> None:
    """_validate raises for input that is neither str nor UUID."""
    with pytest.raises(ValidationError):
        WsDummy(ws_id=12345)  # type: ignore[arg-type]


def test_workspace_id_rejects_uuid1_via_pydantic() -> None:
    u = uuid.uuid1()
    with pytest.raises(ValidationError, match="UUID v4"):
        WsDummy(ws_id=u)  # type: ignore[arg-type]


def test_workspace_id_rejects_malformed() -> None:
    with pytest.raises(ValidationError):
        WsDummy(ws_id="not-a-uuid")  # type: ignore[arg-type]


def test_workspace_id_rejects_braces() -> None:
    u = "{" + str(uuid.uuid4()) + "}"
    with pytest.raises(ValidationError):
        WsDummy(ws_id=u)  # type: ignore[arg-type]


def test_workspace_id_rejects_urn_form() -> None:
    u = "urn:uuid:" + str(uuid.uuid4())
    with pytest.raises(ValidationError):
        WsDummy(ws_id=u)  # type: ignore[arg-type]


def test_workspace_id_rejects_unhyphenated() -> None:
    """32 hex chars without hyphens must be rejected (fullmatch)."""
    u = uuid.uuid4().hex  # no hyphens
    with pytest.raises(ValidationError):
        WsDummy(ws_id=u)  # type: ignore[arg-type]


def test_workspace_id_uppercase_string_valid() -> None:
    """Uppercase UUIDs are converted to lowercase and accepted."""
    u = uuid.uuid4()
    d = WsDummy(ws_id=str(u).upper())  # type: ignore[arg-type]
    assert str(d.ws_id) == str(u)


def test_workspace_id_rejects_trailing_newline() -> None:
    """fullmatch rejects a canonical UUID4 string with a trailing newline."""
    u = str(uuid.uuid4()) + "\n"
    with pytest.raises(ValidationError):
        WsDummy(ws_id=u)  # type: ignore[arg-type]


def test_workspace_id_immutable_setattr() -> None:
    """Attribute assignment on a WorkspaceId instance must raise AttributeError."""
    ws = WorkspaceId(uuid.uuid4())
    with pytest.raises(AttributeError):
        ws.value = uuid.uuid4()


def test_workspace_id_immutable_delattr() -> None:
    """Attribute deletion on a WorkspaceId instance must raise AttributeError."""
    ws = WorkspaceId(uuid.uuid4())
    with pytest.raises(AttributeError):
        del ws.value


def test_workspace_id_setattr_non_existent() -> None:
    """Assigning to non-existent attr hits object.__setattr__ and raises AttributeError."""
    ws = WorkspaceId(uuid.uuid4())
    with pytest.raises(AttributeError):
        ws.does_not_exist = 1


def test_workspace_id_repr() -> None:
    u = uuid.uuid4()
    ws = WorkspaceId(u)
    assert repr(ws) == f"WorkspaceId({u!r})"


# ===========================================================================
# GitHubRepoUrl — valid paths
# ===========================================================================


def test_github_url_valid() -> None:
    d = UrlDummy(url="https://github.com/owner/repo")  # type: ignore[arg-type]
    assert str(d.url) == "https://github.com/owner/repo"


def test_github_url_strips_trailing_slash() -> None:
    url = GitHubRepoUrl._validate("https://github.com/owner/repo/")
    assert str(url) == "https://github.com/owner/repo"


def test_github_url_strips_git_suffix() -> None:
    url = GitHubRepoUrl._validate("https://github.com/owner/repo.git")
    assert str(url) == "https://github.com/owner/repo"


def test_github_url_strips_git_suffix_and_slash() -> None:
    url = GitHubRepoUrl._validate("https://github.com/owner/repo.git/")
    assert str(url) == "https://github.com/owner/repo"


def test_github_url_case_insensitive_host() -> None:
    """urllib folds the netloc to lower-case; GITHUB.COM is accepted."""
    url = GitHubRepoUrl._validate("https://GITHUB.COM/owner/repo")
    assert str(url) == "https://github.com/owner/repo"


def test_github_url_eq_same() -> None:
    a = GitHubRepoUrl._validate("https://github.com/owner/repo")
    b = GitHubRepoUrl._validate("https://github.com/owner/repo")
    assert a == b
    assert hash(a) == hash(b)


def test_github_url_eq_different() -> None:
    a = GitHubRepoUrl._validate("https://github.com/owner/repo")
    b = GitHubRepoUrl._validate("https://github.com/other/repo")
    assert a != b


def test_github_url_eq_non_githubrepourl() -> None:
    """__eq__ returns False for a non-GitHubRepoUrl."""
    url = GitHubRepoUrl._validate("https://github.com/owner/repo")
    assert url != "https://github.com/owner/repo"
    assert url != 42
    assert url != None  # noqa: E711


def test_github_url_json_roundtrip() -> None:
    d = UrlDummy(url="https://github.com/owner/repo")  # type: ignore[arg-type]
    j = json.loads(d.model_dump_json())
    assert j["url"] == "https://github.com/owner/repo"


def test_github_url_json_schema() -> None:
    schema = UrlDummy.model_json_schema()
    assert schema["properties"]["url"]["type"] == "string"


def test_github_url_passthrough() -> None:
    url = GitHubRepoUrl._validate("https://github.com/owner/repo")
    assert GitHubRepoUrl._validate(url) is url


def test_github_url_parse_classmethod() -> None:
    url = GitHubRepoUrl.parse("https://github.com/owner/repo")
    assert str(url) == "https://github.com/owner/repo"


# ===========================================================================
# GitHubRepoUrl — __init__ validates owner/repo directly
# ===========================================================================


def test_github_url_direct_bad_owner_dotdot_raises() -> None:
    """__init__ must reject '..' as owner even when called directly."""
    with pytest.raises(ValueError, match="Invalid GitHub owner format"):
        GitHubRepoUrl("..", "repo")


def test_github_url_direct_bad_owner_slash_raises() -> None:
    """__init__ must reject 'a/b' as owner (slash is not alphanumeric/hyphen)."""
    with pytest.raises(ValueError, match="Invalid GitHub owner format"):
        GitHubRepoUrl("a/b", "repo")


def test_github_url_direct_bad_owner_leading_dash_raises() -> None:
    """__init__ must reject owners that start with '-'."""
    with pytest.raises(ValueError, match="Owner cannot start with -"):
        GitHubRepoUrl("-owner", "repo")


def test_github_url_direct_bad_owner_trailing_newline_raises() -> None:
    """fullmatch in _validate_owner rejects 'owner\\n'."""
    with pytest.raises(ValueError, match="Invalid GitHub owner format"):
        GitHubRepoUrl("owner\n", "repo")


def test_github_url_direct_bad_repo_dot_raises() -> None:
    """__init__ must reject '.' as repo."""
    with pytest.raises(ValueError, match="Repo name cannot be"):
        GitHubRepoUrl("owner", ".")


def test_github_url_direct_bad_repo_dotdot_raises() -> None:
    """__init__ must reject '..' as repo."""
    with pytest.raises(ValueError, match="Repo name cannot be"):
        GitHubRepoUrl("owner", "..")


def test_github_url_direct_bad_repo_trailing_newline_raises() -> None:
    """fullmatch in _validate_repo rejects 'repo\\n'."""
    with pytest.raises(ValueError, match="Invalid GitHub repo format"):
        GitHubRepoUrl("owner", "repo\n")


def test_github_url_direct_bad_repo_at_raises() -> None:
    """__init__ must reject '@' in repo name."""
    with pytest.raises(ValueError, match="Invalid GitHub repo format"):
        GitHubRepoUrl("owner", "repo@bad")


# ===========================================================================
# GitHubRepoUrl — URL-level rejections
# ===========================================================================


def test_github_url_rejects_non_string() -> None:
    with pytest.raises(ValidationError):
        UrlDummy(url=12345)  # type: ignore[arg-type]


def test_github_url_rejects_too_long() -> None:
    long_url = "https://github.com/owner/" + "a" * 300
    with pytest.raises(ValidationError, match="URL too long"):
        UrlDummy(url=long_url)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad_owner",
    [
        "owner_name",  # underscore not in _OWNER_RE
        "owner@name",  # @ not allowed
        "owner$name",  # $ not allowed
        "owner!name",  # ! not allowed
        "o" * 40,  # exceeds 39 chars
        "",  # empty owner → len(parts) != 2 or regex rejection
    ],
)
def test_github_url_rejects_invalid_owner(bad_owner: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        GitHubRepoUrl._validate(f"https://github.com/{bad_owner}/repo")


@pytest.mark.parametrize(
    "bad_repo",
    [
        "repo name",  # space caught by char-scan before regex
        "repo@name",  # @ not in _REPO_RE
        "repo!",  # ! not allowed
        "repo#hash",  # # not allowed
        "r" * 101,  # exceeds 100 chars
    ],
)
def test_github_url_rejects_invalid_repo(bad_repo: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        GitHubRepoUrl._validate(f"https://github.com/owner/{bad_repo}")


def test_github_url_rejects_repeated_git_suffix() -> None:
    with pytest.raises(ValueError, match=r"Repeated \.git suffix"):
        GitHubRepoUrl._validate("https://github.com/owner/repo.git.git")


def test_github_url_rejects_empty_path() -> None:
    with pytest.raises(ValueError):
        GitHubRepoUrl._validate("https://github.com")


def test_github_url_rejects_owner_starting_with_dash() -> None:
    with pytest.raises((ValidationError, ValueError), match="Owner cannot start with -"):
        GitHubRepoUrl._validate("https://github.com/-owner/repo")


def test_github_url_rejects_params_semicolon() -> None:
    with pytest.raises(ValidationError):
        UrlDummy(url="https://github.com/owner/repo;x")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Credentials / port: netloc check fires, no separate guard
# ---------------------------------------------------------------------------


def test_github_url_credentials_rejected_by_netloc() -> None:
    """
    'user:pass@github.com' → netloc = 'user:pass@github.com'.
    The netloc != 'github.com' check rejects it with "Host must be exactly".
    There is no separate credential guard; this IS the guard.
    """
    with pytest.raises(ValueError, match=r"Host must be exactly github\.com"):
        GitHubRepoUrl._validate("https://user:pass@github.com/owner/repo")


def test_github_url_explicit_port_rejected_by_netloc() -> None:
    """
    'github.com:443' → netloc = 'github.com:443'.
    The netloc != 'github.com' check rejects it.
    """
    with pytest.raises(ValueError, match=r"Host must be exactly github\.com"):
        GitHubRepoUrl._validate("https://github.com:443/owner/repo")


def test_github_url_uppercase_host_accepted() -> None:
    """
    'GITHUB.COM' → urllib.parse gives netloc = 'GITHUB.COM', but we
    lower-case it for comparison, so this is accepted.
    """
    url = GitHubRepoUrl._validate("https://GITHUB.COM/owner/repo")
    assert str(url) == "https://github.com/owner/repo"


# ===========================================================================
# GitHubRepoUrl — immutability
# ===========================================================================


def test_github_url_immutable_setattr() -> None:
    """Attribute assignment must raise AttributeError."""
    url = GitHubRepoUrl._validate("https://github.com/owner/repo")
    with pytest.raises(AttributeError):
        url.owner = "other"


def test_github_url_immutable_delattr() -> None:
    """Attribute deletion must raise AttributeError."""
    url = GitHubRepoUrl._validate("https://github.com/owner/repo")
    with pytest.raises(AttributeError):
        del url.owner


def test_github_url_setattr_non_existent() -> None:
    """Assigning to non-existent attr hits object.__setattr__ and raises AttributeError."""
    url = GitHubRepoUrl._validate("https://github.com/owner/repo")
    with pytest.raises(AttributeError):
        url.does_not_exist = 1


def test_github_url_repr() -> None:
    url = GitHubRepoUrl._validate("https://github.com/owner/repo")
    assert repr(url) == "GitHubRepoUrl('https://github.com/owner/repo')"


# ===========================================================================
# Trailing-\\n rejection via fullmatch (UUID / owner / repo regex)
# ===========================================================================


def test_uuid4_re_rejects_trailing_newline() -> None:
    """The _UUID4_RE fullmatch rejects a string with a trailing newline."""
    s = str(uuid.uuid4()) + "\n"
    with pytest.raises(ValidationError):
        WsDummy(ws_id=s)  # type: ignore[arg-type]


def test_owner_re_rejects_trailing_newline_via_init() -> None:
    """_validate_owner (fullmatch) rejects 'owner\\n' even from __init__."""
    with pytest.raises(ValueError, match="Invalid GitHub owner format"):
        GitHubRepoUrl("owner\n", "repo")


def test_repo_re_rejects_trailing_newline_via_init() -> None:
    """_validate_repo (fullmatch) rejects 'repo\\n' even from __init__."""
    with pytest.raises(ValueError, match="Invalid GitHub repo format"):
        GitHubRepoUrl("owner", "repo\n")
