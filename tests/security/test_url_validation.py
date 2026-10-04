import pytest
from app.schemas.domain import GitHubRepoUrl


def test_github_url_valid() -> None:
    url = GitHubRepoUrl("owner-name", "repo_name.1")
    assert str(url) == "https://github.com/owner-name/repo_name.1"


def test_github_url_valid_trailing_slash() -> None:
    url = GitHubRepoUrl._validate("https://github.com/owner/repo/")
    assert str(url) == "https://github.com/owner/repo"


def test_github_url_valid_git_suffix() -> None:
    url = GitHubRepoUrl._validate("https://github.com/owner/repo.git")
    assert str(url) == "https://github.com/owner/repo"


def test_github_url_valid_git_suffix_and_slash() -> None:
    url = GitHubRepoUrl._validate("https://github.com/owner/repo.git/")
    assert str(url) == "https://github.com/owner/repo"


@pytest.mark.parametrize(
    "invalid_url",
    [
        # Hostile SSRF
        "https://localhost/owner/repo",
        "https://127.0.0.1/owner/repo",
        "https://169.254.169.254/owner/repo",
        "https://internal-server/owner/repo",
        "https://www.github.com/owner/repo",
        # Userinfo
        "https://user:pass@github.com/owner/repo",
        # Ports
        "https://github.com:443/owner/repo",
        "https://github.com:80/owner/repo",
        # IPv4 / IPv6 literals
        "https://[::1]/owner/repo",
        # Unicode / lookalikes
        "https://gith\u0441b.com/owner/repo",
        "https://github.com/öwner/repo",
        # Path traversal / extra segments
        "https://github.com/owner/repo/tree/main",
        "https://github.com/owner/repo/..",
        "https://github.com/../owner/repo",
        # Dot repo
        "https://github.com/owner/.",
        "https://github.com/owner/..",
        # Encoded characters
        "https://github.com/owner%20/repo",
        "https://github.com/owner/repo%0A",
        # Queries / Fragments
        "https://github.com/owner/repo?token=123",
        "https://github.com/owner/repo#readme",
        # Whitespace
        "https://github.com/owner /repo",
        "https://github.com/owner/repo\n",
        " https://github.com/owner/repo",
        # Empty
        "",
        "   ",
    ],
)
def test_github_url_invalid(invalid_url: str) -> None:
    with pytest.raises(ValueError):
        GitHubRepoUrl._validate(invalid_url)


def test_github_url_host_case_handling() -> None:
    url = GitHubRepoUrl._validate("https://GitHub.com/owner/repo")
    # Urllib parses netloc case-insensitively, so parsed.netloc is github.com
    assert str(url) == "https://github.com/owner/repo"
