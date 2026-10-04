import pytest
from app.schemas.validators import validate_branch_name, validate_repo_name


def test_validate_repo_name_valid() -> None:
    assert validate_repo_name("my-repo") == "my-repo"


def test_validate_repo_name_empty() -> None:
    with pytest.raises(ValueError, match="1-100"):
        validate_repo_name("")


def test_validate_repo_name_too_long() -> None:
    with pytest.raises(ValueError, match="1-100"):
        validate_repo_name("a" * 101)


@pytest.mark.parametrize(
    "invalid_name, expected_match",
    [
        ("repo\nname", "invalid characters"),
        ("repo name", "invalid characters"),
        ("repo\x00name", "invalid characters"),
        ("repo\x7fname", "invalid characters"),
        ("مستودع", "invalid characters"),
        ("my#repo", "invalid characters"),
        (".", "cannot be '.' or '..'"),
        ("..", "cannot be '.' or '..'"),
    ],
)
def test_validate_repo_name_invalid_chars(invalid_name: str, expected_match: str) -> None:
    with pytest.raises(ValueError, match=expected_match):
        validate_repo_name(invalid_name)


def test_validate_branch_name_valid() -> None:
    assert validate_branch_name("main") == "main"


def test_validate_branch_name_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        validate_branch_name("")


def test_validate_branch_name_too_long() -> None:
    with pytest.raises(ValueError, match="exceeds 255"):
        validate_branch_name("a" * 256)


def test_validate_branch_name_leading_dash() -> None:
    with pytest.raises(ValueError, match="start with '-'"):
        validate_branch_name("-main")


def test_validate_branch_name_control_char() -> None:
    with pytest.raises(ValueError, match="non-printable character"):
        validate_branch_name("main\x00")
    with pytest.raises(ValueError, match="non-printable character"):
        validate_branch_name("main\x7f")


def test_validate_branch_name_arabic_valid() -> None:
    # F3: Arabic or non-ASCII printable should be valid
    assert validate_branch_name("فرع-رئيسي") == "فرع-رئيسي"


def test_validate_branch_name_whitespace() -> None:
    with pytest.raises(ValueError, match="whitespace"):
        validate_branch_name("main branch")
