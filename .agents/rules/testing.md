---
trigger: glob
description: "Testing and verification rules for Team 1."
globs: "tests/**/*.py"
---

# Testing Rules

Required categories per component:
happy path, invalid input, timeout, tool failure, malformed tool output,
filesystem failure, security boundary violation, cleanup and TTL behavior.

- Adapters are tested with fixtures of real CLI output.
- Integration tests use small LOCAL sample repositories (never live third-party repos).
- Mark tests: `unit`, `integration`, `security` (markers are strict).
- Linux-only behavior (symlinks, permissions, tool binaries) uses
  `skipif(sys.platform == "win32", reason="...")`.
- A security test must prove the attack is rejected, not only that the happy path works.
