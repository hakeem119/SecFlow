"""Fail if a branch touches files outside its owner's list.
Usage: python scripts/check_ownership.py m1 origin/main
In DEV MODE also fails on new/changed files under tests/
(except fixtures and integration for m3)."""

import fnmatch
import subprocess
import sys

OWN = {
    "m1": [
        "app/services/workspace*",
        "app/services/reaper.py",
        "app/core/safe_path.py",
        "app/tools/git.py",
        "app/tools/tree_sitter.py",
        "app/tools/secrets.py",
        "app/main.py",
        "app/api/routes.py",
        "app/services/repository_service.py",
        "docs/plans/m1-*",
        "Dockerfile",
    ],
    "m2": [
        "app/tools/runner.py",
        "app/tools/scc.py",
        "app/tools/syft.py",
        "app/tools/semgrep.py",
        "app/schemas/tool.py",
        "docs/plans/m2-*",
        "Dockerfile",
    ],
    "m3": [
        "app/schemas/snapshot.py",
        "app/services/snapshot*",
        "tests/fixtures/*",
        "sample_snapshot.yaml",
        ".github/*",
        "AGENTS.md",
        "pyproject.toml",
        "*.lock",
        "scripts/*",
        "docs/plans/m3-*",
    ],
}


def main() -> int:
    member, base = sys.argv[1], sys.argv[2]
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", f"{base}...HEAD"],  # noqa: S607
        text=True,
    ).split()
    bad = [f for f in changed if not any(fnmatch.fnmatch(f, p) for p in OWN[member])]
    if bad:
        print(f"FAIL: {len(bad)} file(s) outside ownership")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
