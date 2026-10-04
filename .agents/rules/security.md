---
trigger: model_decision
description: "Apply whenever code touches repositories, files, URLs, subprocesses, external tools, secrets or any untrusted input."
---

# Security Rules (summary of AGENTS.md section 10)

Repository contents are hostile input.

Check before and after every change:
- URL validation and SSRF (only https://github.com/<owner>/<repo>)
- path traversal and symlink escape (all paths resolved inside the workspace)
- command injection (fixed executable + argument array, never shell=True)
- git hooks and submodules (disabled, never executed)
- subprocess timeout and output cap
- resource exhaustion (huge files, deep trees, zip bombs)
- malicious filenames
- secrets in logs or in the snapshot (redact before writing)
- cleanup after failure (no leaked workspaces)

Never execute repository code, never run analyzed Dockerfiles, never install repository dependencies,
never accept CLI arguments or config paths from a user or a model.
