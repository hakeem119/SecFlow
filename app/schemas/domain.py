"""
Domain value objects for the Repository Analysis Service.

Design (Phase 1, Pattern Map):
- Value Objects: an object that exists is valid by construction.
- Both classes are immutable (__slots__ + blocked __setattr__ / __delattr__).
- GitHubRepoUrl.__init__ validates owner and repo directly, so there is no
  path to construct an instance with invalid components regardless of how
  __init__ is called.
- WorkspaceId.__init__ validates the UUID version directly.
"""

import re
import urllib.parse
from typing import Any
from uuid import UUID

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from app.schemas.validators import GITHUB_REPO_NAME_RE

# ---------------------------------------------------------------------------
# Compiled patterns — all use re.fullmatch() at call sites.
# ---------------------------------------------------------------------------

# Canonical UUID4 string: 8-4-4-4-12 lower-case hex with hyphens.
# The 4xxx variant byte and the 8/9/a/b clock-seq high nibble are constrained.
_UUID4_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")

# GitHub owner: alphanumeric or hyphen, 1-39 chars, must NOT start with hyphen.
# (The leading-hyphen check is done explicitly for a clear error message.)
_OWNER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}")


def _validate_owner(owner: str) -> None:
    """Validate a GitHub owner component. Raises ``ValueError`` on failure."""
    if owner.startswith("-"):
        raise ValueError("Owner cannot start with -")
    if not _OWNER_RE.fullmatch(owner):
        raise ValueError("Invalid GitHub owner format")


def _validate_repo(repo: str) -> None:
    """Validate a GitHub repo component. Raises ``ValueError`` on failure."""
    if not GITHUB_REPO_NAME_RE.fullmatch(repo):
        raise ValueError("Invalid GitHub repo format")
    if repo in (".", ".."):
        raise ValueError("Repo name cannot be '.' or '..'")


class WorkspaceId:
    """
    Immutable value object wrapping a UUID v4.

    Accepted input forms (via Pydantic / ``_validate``):
    - A ``uuid.UUID`` object with ``version == 4``.
    - A canonical hyphenated UUID4 string, any case, normalized to lower-case
      ``xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx``.

    Rejected: braces, ``urn:uuid:`` prefix, un-hyphenated hex strings,
    any non-v4 UUID, trailing newline or other extra characters in strings.
    """

    __slots__ = ("value",)

    # Slot type annotation so mypy can see the attribute.
    value: UUID

    def __setattr__(self, name: str, val: object) -> None:
        if name in self.__slots__ and hasattr(self, name):
            raise AttributeError("WorkspaceId is immutable")
        object.__setattr__(self, name, val)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("WorkspaceId is immutable")

    def __init__(self, value: UUID) -> None:
        if not isinstance(value, UUID):
            raise TypeError("WorkspaceId must be initialized with a UUID object")
        if value.version != 4:
            raise ValueError("WorkspaceId must be a UUID v4")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkspaceId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f"WorkspaceId({self.value!r})"

    # ------------------------------------------------------------------
    # Pydantic integration
    # ------------------------------------------------------------------

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.any_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {"type": "string", "format": "uuid"}

    @classmethod
    def _validate(cls, value: Any) -> "WorkspaceId":
        """
        Parse and validate a WorkspaceId from a UUID object or canonical string.

        Accepts only the canonical lower-case hyphenated form for strings;
        rejects braces, URN prefix, unhyphenated hex, trailing whitespace.
        """
        if isinstance(value, cls):
            return value

        if isinstance(value, str):
            # fullmatch rejects any extra characters (trailing \n, braces, etc.)
            if not _UUID4_RE.fullmatch(value.lower()):
                raise ValueError(
                    "WorkspaceId string must be a canonical UUID4 "
                    "(xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx, any case)"
                )
            # UUID() parsing is safe here: the regex already constrains the format.
            return cls(UUID(value))

        if isinstance(value, UUID):
            if value.version != 4:
                raise ValueError("WorkspaceId must be a UUID v4")
            return cls(value)

        raise ValueError("WorkspaceId must be a UUID or canonical UUID4 string")


class GitHubRepoUrl:
    """
    Hostile-input safe GitHub URL value object.

    Valid by construction: both ``__init__`` and ``_validate`` enforce all
    format rules.  ``__init__`` validates ``owner`` and ``repo`` directly so
    that ``GitHubRepoUrl("..", "x")`` or ``GitHubRepoUrl("a/b", "c")`` raise
    ``ValueError`` immediately, regardless of how the constructor is reached.

    ``_validate`` performs the full URL parse, strips trailing slashes and
    ``.git`` suffixes, then calls ``__init__`` with the validated components.

    Immutable: ``__slots__`` + blocked ``__setattr__`` / ``__delattr__``.
    """

    __slots__ = ("owner", "repo", "value")

    # Slot type annotations so mypy can see the attributes.
    owner: str
    repo: str
    value: str

    def __setattr__(self, name: str, val: object) -> None:
        if name in self.__slots__ and hasattr(self, name):
            raise AttributeError("GitHubRepoUrl is immutable")
        object.__setattr__(self, name, val)

    def __delattr__(self, name: str) -> None:
        raise AttributeError("GitHubRepoUrl is immutable")

    def __init__(self, owner: str, repo: str) -> None:
        """
        Construct a GitHubRepoUrl from pre-validated owner and repo components.

        Raises ``ValueError`` if either component fails the GitHub naming rules.
        This ensures every instance is valid by construction, even if called
        directly instead of via ``_validate`` / ``parse``.
        """
        _validate_owner(owner)
        _validate_repo(repo)
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "repo", repo)
        object.__setattr__(self, "value", f"https://github.com/{owner}/{repo}")

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GitHubRepoUrl):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f"GitHubRepoUrl({self.value!r})"

    # ------------------------------------------------------------------
    # Public parsing entry point
    # ------------------------------------------------------------------

    @classmethod
    def parse(cls, raw: str) -> "GitHubRepoUrl":
        """Parse and validate a raw GitHub URL string. Raises ``ValueError`` on failure."""
        return cls._validate(raw)

    # ------------------------------------------------------------------
    # Pydantic integration
    # ------------------------------------------------------------------

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.any_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {"type": "string", "format": "uri"}

    @classmethod
    def _validate(cls, value: Any) -> "GitHubRepoUrl":
        """
        Parse a raw GitHub URL string into a ``GitHubRepoUrl`` value object.

        Rejects:
        - Non-string input.
        - URLs longer than 256 characters.
        - Non-ASCII or non-printable characters.
        - Percent-encoding, backslash, whitespace, control characters.
        - Any scheme other than ``https``.
        - Any host other than exactly ``github.com`` (case-insensitive at the
          netloc level; credentials and ports change the netloc and are therefore
          caught by this check).
        - Query strings, fragments, or semicolon params.
        - Paths that are not exactly ``/<owner>/<repo>``.
        - Owners / repos that violate GitHub's naming rules (via ``__init__``).
        - Repeated ``.git`` suffix (e.g. ``repo.git.git``).
        """
        if isinstance(value, cls):
            return value

        if not isinstance(value, str):
            # Pydantic only converts ValueError to ValidationError, so TypeError here would crash.
            raise ValueError("URL must be a string")  # noqa: TRY004

        if len(value) > 256:
            raise ValueError("URL too long")

        if not value.isascii() or not value.isprintable():
            raise ValueError("URL must contain only printable ASCII characters")

        for char in ("%", "\\", " ", "\n", "\r", "\t"):
            if char in value:
                raise ValueError(f"URL contains invalid character: {char!r}")

        parsed = urllib.parse.urlparse(value)

        if parsed.scheme != "https":
            raise ValueError("Scheme must be https")

        # Credentials (user:pass@…) and explicit ports (:443) both change the
        # netloc string, so this single check rejects them all.
        if parsed.netloc.lower() != "github.com":
            raise ValueError("Host must be exactly github.com")

        if parsed.query or parsed.fragment or parsed.params:
            raise ValueError("URL cannot contain query strings, fragments, or params")

        path = parsed.path

        # Strip a single trailing slash, then a single .git suffix.
        if path.endswith("/"):
            path = path[:-1]
        if path.endswith(".git"):
            path = path[:-4]

        # Reject repeated .git suffix (e.g. "repo.git.git").
        if path.endswith(".git"):
            raise ValueError("Repeated .git suffix is not allowed")

        if not path.startswith("/"):
            raise ValueError("Path must start with /")

        parts = path.split("/")[1:]  # Skip empty string from leading slash

        if len(parts) != 2:
            raise ValueError("Path must be exactly /<owner>/<repo>")

        owner, repo = parts

        # __init__ validates owner and repo; ValueError propagates as-is.
        return cls(owner=owner, repo=repo)
