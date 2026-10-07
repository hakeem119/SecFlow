import subprocess
import sys


def run_command(cmd: list[str], name: str, timeout: int = 120) -> bool:
    print(f"--- Running {name} ---")
    print(f"Command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        print(f"--- {name} FAILED: timed out after {e.timeout} seconds ---")
        return False
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
    is_dev = "--dev" in sys.argv
    from pathlib import Path

    try:
        with Path("gate_mode.txt").open() as f:
            if f.read().strip() == "dev":
                is_dev = True
    except FileNotFoundError:
        pass

    pytest_cmd = [sys.executable, "-m", "pytest", "tests"]
    if is_dev:
        pytest_cmd.append("--no-cov")

    checks = [
        ("Format Check", [sys.executable, "-m", "ruff", "format", "--check", "."]),
        ("Lint", [sys.executable, "-m", "ruff", "check", "."]),
        ("Type Check", [sys.executable, "-m", "mypy"]),
        ("Test", pytest_cmd),
        ("Security (Code)", [sys.executable, "-m", "bandit", "-r", "app", "-c", "pyproject.toml"]),
        (
            "Security (Deps - prod)",
            [
                sys.executable,
                "-m",
                "pip_audit",
                "-r",
                "requirements.lock",
                "--disable-pip",
                "--no-deps",
            ],
        ),
        (
            "Security (Deps - dev)",
            [
                sys.executable,
                "-m",
                "pip_audit",
                "-r",
                "requirements-dev.lock",
                "--disable-pip",
                "--no-deps",
            ],
        ),
    ]

    # Use a 120-second timeout specifically for the pip-audit checks,
    # but the run_command defaults to 120 seconds.
    for name, cmd in checks:
        cmd_timeout = 120
        if not run_command(cmd, name, timeout=cmd_timeout):
            sys.exit(1)

    print("All quality gates passed successfully.")


if __name__ == "__main__":
    main()
