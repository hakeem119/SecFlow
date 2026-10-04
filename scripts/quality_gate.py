import subprocess
import sys


def run_command(cmd: list[str], name: str) -> bool:
    print(f"--- Running {name} ---")
    print(f"Command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"--- {name} FAILED with exit code {e.returncode} ---")
        return False
    except FileNotFoundError:
        print(f"--- {name} FAILED: command not found ---")
        return False
    else:
        print(f"--- {name} PASS ---")
        return True


def main() -> None:
    checks = [
        ("Format Check", [sys.executable, "-m", "ruff", "format", "--check", "."]),
        ("Lint", [sys.executable, "-m", "ruff", "check", "."]),
        ("Type Check", [sys.executable, "-m", "mypy"]),
        ("Test", [sys.executable, "-m", "pytest", "tests"]),
        ("Security (Code)", [sys.executable, "-m", "bandit", "-r", "app", "-c", "pyproject.toml"]),
        (
            "Security (Deps - prod)",
            [sys.executable, "-m", "pip_audit", "-r", "requirements.lock"],
        ),
        (
            "Security (Deps - dev)",
            [sys.executable, "-m", "pip_audit", "-r", "requirements-dev.lock"],
        ),
    ]

    for name, cmd in checks:
        if not run_command(cmd, name):
            sys.exit(1)

    print("All quality gates passed successfully.")


if __name__ == "__main__":
    main()
