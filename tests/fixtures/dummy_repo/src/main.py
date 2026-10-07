import sys


def main() -> None:
    # This is a canary secret for redaction testing
    # It must NEVER appear in the generated repository_snapshot.yaml
    aws_access_key = "AKIAIOSFODNN7EXAMPLE"  # noqa: F841
    aws_secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  # noqa: F841

    print("Hello from dummy_repo!")  # noqa: T201

    # Intentionally trigger a semgrep finding via exec
    user_input = sys.argv[1] if len(sys.argv) > 1 else "print('no input')"
    exec(user_input)  # noqa: S102


if __name__ == "__main__":
    main()
