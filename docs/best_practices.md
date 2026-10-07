# SecFlow Best Practices

## 1. Subprocess Execution Security

- **Strict Allowlist:** All executable commands must be from a predefined allowlist within `CommandRunner`.
- **Environment Sanitization:** Environment variables passed to sub-processes must be explicitly declared or filtered through an allowlist to prevent credentials or dangerous configs from leaking into external tools. For example, `GIT_TERMINAL_PROMPT=0` and `GIT_CONFIG_GLOBAL=/dev/null` must be set.
- **Resource Limits:** Sub-processes must be run with explicit `timeout` constraints and `max_stdout_bytes` / `max_stderr_bytes` bounds to mitigate denial of service attacks via infinite output loops.
- **Disk exhaustion (rlimit):** Long-running processes like `git clone` or heavy code scanners that write directly to the filesystem should ideally be bounded using `resource.RLIMIT_FSIZE` or container `cgroups` to prevent disk exhaustion.

## 2. Workspace Hygiene

- **Isolated Creation:** Workspaces are generated using UUID4 identifiers and strict `0700` permissions.
- **Immediate Path Validation:** Any path extracted from an external tool or repo must be strictly validated as a `PurePosixPath` that is relative and explicitly bounded within the workspace root to prevent path traversal attacks.
- **Context Managers for Cleanup:** Implement workspace usage via `WorkspaceManager.lifecycle(workspace_id)` which ensures that on *any* exception, the workspace is atomically renamed to a `.trash` directory and recursively destroyed.
- **Early `.git` Eviction:** Hostile `.git` folders must be deleted immediately after cloning and before passing the codebase to any subsequent analysis tools. This ensures that repository-provided Git hooks or local configs are never executed or processed.
