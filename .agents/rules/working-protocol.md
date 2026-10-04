---
trigger: always
description: "Working protocol for flow, approvals, platform policy. AGENTS.md section 14 is authoritative."
---

# Working Protocol (summary of AGENTS.md section 14)

- Flow: **Analyze > Plan > wait for approval > Implement > Test > Review**.
  One phase at a time. Never move to the next phase without explicit approval.
- In PLAN mode: do not edit any file. Present the plan and STOP.
- Before editing multiple files, state the file boundaries (create / change / untouched).
- Do not touch unrelated files. Never modify `docs/reference/`.
- Prefer small, reviewable commits.
- Explain every design pattern you add in one sentence: what concrete problem it solves.
- If the instruction says STOP, you STOP.
- After every phase: run the quality gate, report what changed / what remains / open questions,
  then STOP.
- Never claim a check passed unless you actually ran it. If a check cannot run, say so.

Platform policy:
- Development environment is **WSL2 Ubuntu**. Use bash and `python -m ...`.
- The repo lives in the WSL filesystem, NEVER under `/mnt/*`.
- CI runs on `ubuntu-latest`. Linux is the PRIMARY target.
- Windows is best-effort only (unit tests, ruff, mypy must pass there;
  integration and security tests may be skipped).
- Python is 3.12. The venv is created with `uv`. Lock files are generated on Linux only.
- Never hardcode path separators; always `pathlib`. The workspace root comes from configuration.

AGENTS.md section 14 is the canonical, complete source. This file is a summary only.
