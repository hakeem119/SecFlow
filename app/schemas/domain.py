import re
import urllib.parse
from typing import Any
from uuid import UUID

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


# Value object wrapper for WorkspaceId
class WorkspaceId:
    def __init__(self, value: UUID):
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.uuid_schema(version=4),
        )


class GitHubRepoUrl:
    """
    Hostile-input safe GitHub URL parser.
    Parses and completely rebuilds the canonical URL.
    """

    def __init__(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo
        self.value = f"https://github.com/{owner}/{repo}"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.any_schema(),
        )

    @classmethod
    def _validate(cls, value: Any) -> "GitHubRepoUrl":
        if isinstance(value, cls):
            return value

        if not isinstance(value, str):
            raise TypeError("URL must be a string")

        if not value.isascii() or not value.isprintable():
            raise ValueError("URL must contain only printable ASCII characters")

        for char in ("%", "\\", " ", "\n", "\r", "\t"):
            if char in value:
                raise ValueError(f"URL contains invalid character: {char!r}")

        parsed = urllib.parse.urlparse(value)

        if parsed.scheme != "https":
            raise ValueError("Scheme must be https")

        if parsed.netloc.lower() != "github.com":
            raise ValueError("Host must be exactly github.com")

        if parsed.username or parsed.password or parsed.port:
            raise ValueError("URL cannot contain credentials or ports")

        if parsed.query or parsed.fragment:
            raise ValueError("URL cannot contain query strings or fragments")

        path = parsed.path
        if path.endswith("/"):
            path = path[:-1]
        if path.endswith(".git"):
            path = path[:-4]

        if not path.startswith("/"):
            raise ValueError("Path must start with /")

        parts = path.split("/")[1:]  # Skip empty string from leading slash

        if len(parts) != 2:
            raise ValueError("Path must be exactly /<owner>/<repo>")

        owner, repo = parts

        if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner):
            raise ValueError("Invalid GitHub owner format")

        if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", repo):
            raise ValueError("Invalid GitHub repo format")

        if repo in (".", ".."):
            raise ValueError("Repo name cannot be '.' or '..'")

        return cls(owner=owner, repo=repo)
