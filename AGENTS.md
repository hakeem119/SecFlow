# SecFlow Repository Analysis Service (Team 1)

## 1. Role

You are the implementation agent for **SecFlow Phase 1, Team 1: Repository Analysis / Backend**.
This repository is an **independent Python FastAPI microservice**.

- External API: JSON in / JSON out.
- Internal artifact: `repository_snapshot.yaml`.
- Final AI output (JSON Manifest) belongs to Team 2, NOT to this repository.
- Processing is deterministic first. No AI inside this service.

---

## 2. Source of Truth (priority order)

1. `docs/reference/Arch2.jpg` (architecture image)
2. `docs/reference/Phase1_Repository_Analysis_Service.pdf`
3. `docs/reference/Phase1_Tools_MCP_Reference.pdf`
4. `docs/reference/SecFlow_Project_Documentation.pdf` (not included in repo, context only)
5. Approved Decisions D1-D10 below (they OVERRIDE the documents where they conflict)

Never silently redesign an approved decision. If you find a contradiction, a security issue or a
technical blocker: **STOP, explain it, and wait**. Do not "fix" it by guessing.

---

## 3. Approved Decisions (D1-D10)

| ID | Decision |
|----|----------|
| D1 | `repository_snapshot.yaml` contains **metadata + evidence ONLY**. No source code content. |
| D2 | The temporary workspace contains the real cloned code, **unmodified**. It is NOT deleted after the API response, because later phases work on it. |
| D3 | The API response includes `workspace_id`. |
| D4 | Workspace cleanup = **TTL (default 24h, configurable)** + **manual DELETE endpoint**. |
| D5 | `git clone --depth=1`. |
| D6 | Tools: **Git, scc, Tree-sitter, Syft, Semgrep, detect-secrets** (all owned by Team 1). |
| D7 | Team 1 owns **workspace isolation and path validation**. |
| D8 | The AI-facing controlled tool layer (`read_file`, `search_code`, `list_files`, `get_file_metadata`) belongs to **Team 2**. Do NOT implement it. |
| D9 | `scc` hotspots/coupling are out of scope (they need git history, which D5 removes). |
| D10 | Semgrep uses a **pinned local ruleset**. `config=auto` is forbidden (needs network). |

---

## 4. Scope

**Team 1 owns:**
FastAPI API, GitHub URL validation, Git clone, workspace lifecycle (create / resolve / TTL / delete),
tool adapters (scc, Tree-sitter, Syft, Semgrep, detect-secrets), result normalization and filtering,
`repository_snapshot.yaml`, security boundaries, tests, Docker, documentation.

**Team 1 does NOT own:**
AI reasoning, prompts, architecture inference, JSON Manifest, RAG, the AI-facing controlled tool layer,
sending results to SaaS/Desk.

---

## 5. Architecture

```
GitHub URL
  -> FastAPI (JSON)
  -> validate URL
  -> create workspace (UUID4)
  -> git clone --depth=1
  -> tools: scc, Tree-sitter, Syft, Semgrep, detect-secrets
  -> normalize + filter
  -> repository_snapshot.yaml (no source code)
  -> JSON response (includes workspace_id)
```

Two separate things, never confuse them:

- **Workspace**: the real code, unmodified, lives on disk until TTL or manual delete.
- **Snapshot**: structured metadata and evidence only, with file paths as evidence.

Team 2 reads the snapshot, and reaches the workspace through its own read-only tools.
Team 1 only guarantees the workspace is isolated, valid and addressable by `workspace_id`.

---

## 6. API Contract (draft, frozen in Phase 1)

```
POST   /api/v1/repositories/analyze
DELETE /api/v1/workspaces/{workspace_id}
GET    /health
```

**Request (analyze)**
```json
{ "repo_url": "https://github.com/owner/repo", "analysis_depth": "standard" }
```
`analysis_depth` is an enum. `standard` is the only Phase 1 value.

**Response (analyze)**
```json
{
  "status": "success | partial | error",
  "workspace_id": "<uuid4>",
  "repository": { "name": "", "url": "", "commit": "" },
  "snapshot": { "format": "yaml", "location": "" },
  "warnings": []
}
```

**Errors:** JSON with stable codes:
`invalid_url`, `clone_failed`, `timeout`, `tool_failed`, `snapshot_invalid`, `workspace_not_found`.

**URL rules:** only `https://github.com/<owner>/<repo>`. Reject other hosts, other schemes,
credentials in the URL, IP addresses, ports, and path tricks.

---

## 7. Workspace Rules

- Workspace ID = UUID4. Never derived from the repo name. Unguessable.
- All workspaces live under one configured root directory.
- Every path is resolved and checked to stay inside the workspace root.
- Symlinks that escape the workspace are detected and never followed.
- Clone with hooks disabled and submodules not fetched. Never run repository code.
- TTL cleanup (default 24h, configurable) plus manual `DELETE`.
- Cleanup of a failed analysis must happen even if a tool crashes (no leaked workspaces).
- File-size, file-count and total-size limits are enforced.

---

## 8. Engineering Constitution

Priority order. **When two principles conflict, the one EARLIER in this list wins.**

1. **Make it work**: every phase runs end-to-end and is proven by a test.
2. **Secure**: repositories are untrusted. Security beats elegance.
3. **YAGNI**: no code for future phases, no speculative abstractions.
4. **Least Astonishment**: a function does what its name says, nothing more.
   (`clone_repository` must not secretly validate, log secrets, or delete things.)
5. **KISS**: the simplest solution that satisfies the contract.
6. **Consistency**: same naming, structure and error handling across all adapters.
7. **DRY**: extract only after the third repetition, never into a wrong abstraction.
8. **Separation of Concerns**: `api / schemas / services / tools / core`.
   Routes contain NO business logic. Adapters contain NO orchestration.
9. **Composition over inheritance**: Protocols and constructor injection. No deep hierarchies.
10. **SOLID**: as clean design after the above, not as a goal in itself.
11. **Design patterns**: ONLY Adapter, Port/Protocol, Service Layer, Dependency Injection.
    Registry/Factory only if real multiplicity exists. Every pattern must be justified in one
    sentence by the concrete problem it solves.
12. **Performance**: only after measurement.

Before finishing any file, ask:
- Will someone else understand this?
- Am I repeating myself?
- Am I making this more complex than needed?
- Is it secure against a hostile repository?

Boy Scout rule: leave code slightly better, but only if the fix is small. Never rewrite a working
design just to make it more elegant.

---

## 8.1 Pattern Map (apply ONLY in the listed phase)

Every pattern needs a one-sentence justification: the concrete problem it solves.
If you cannot write that sentence, do not add the pattern.

| Phase | Pattern | Problem it solves |
|-------|---------|-------------------|
| 1 | Value Objects (`GitHubRepoUrl`, `WorkspaceId`), Ports (Protocols), Domain Exceptions mapped to stable error codes | Parse, don't validate: an object that exists is valid by construction. Ports fix boundaries before any implementation. |
| 2 | Dependency Injection with ONE Composition Root (`app/core/dependencies.py`), central exception handlers, thin routes | Routes stay free of logic and tests can swap any dependency for a fake. |
| 3 | `SafePath` value object, context manager (RAII) for cleanup, TTL reaper | Path traversal/symlink escape handled in one place; failed workspaces are never leaked. |
| 4 | Adapter implementing the `RepositoryFetcher` Port | Git CLI can be replaced without touching the service. |
| 5 | `ToolRunner` (the ONLY place that spawns subprocesses: fixed args, timeout, output cap); one Adapter per tool normalizing into `ToolResult`; `AnalysisTool` Protocol | Subprocess security lives in one place; upstream output changes never leak into the rest of the code. |
| 6-8 | Same Adapter shape, NO Registry/Factory; inject `list[AnalysisTool]` | A plain list is enough for six fixed tools. |
| 9 | Builder + Pipeline: filter -> normalize -> redact -> validate | Fixed, testable order; redaction is mandatory and happens before anything is written. |
| 10 | Service Layer (`RepositoryAnalysisService`) + per-tool fault isolation | One failing tool yields `partial` + warning, not a failed analysis. |

**Forbidden:** Singleton, global mutable state, Abstract Factory, deep inheritance, DB-style Repository,
Observer/Event Bus, CQRS, plugin systems. Any pattern not in this map needs explicit approval.
A phase must not introduce a pattern that belongs to a later phase.

---

## 9. Code Standards

- Python 3.12+, full type hints, `mypy --strict`.
- Pydantic models for every external contract and every cross-layer data structure.
- `pathlib` for paths. No string path concatenation.
- No untyped `dict` crossing layers.
- No global mutable state. No hidden side effects.
- No bare `except Exception` unless re-raised with context.
- Small functions, meaningful names, docstrings on public interfaces.
- Async only where it gives a real benefit (subprocess/IO). Never block the event loop.
- Prefer composition and constructor injection. FastAPI `Depends` for wiring.
- Configuration through `pydantic-settings` (env vars). No hardcoded paths or limits.

Layout:
```
app/
  api/        routes only, thin
  schemas/    request/response/snapshot/tool models
  services/   RepositoryAnalysisService, WorkspaceManager, SnapshotBuilder
  tools/      one adapter per external tool + ToolRunner
  core/       config, errors, logging, security helpers
tests/
  unit/  integration/  security/  fixtures/
docs/
```

---

## 10. Security Rules

Repositories are **hostile input**.

**Never:**
- use `shell=True`
- execute repository code or repository-provided scripts
- build or run Dockerfiles from analyzed repositories
- install repository dependencies
- log secret values
- let a path escape the workspace
- accept arbitrary CLI arguments, config paths or commands from a user or a model
- trust repository-provided tool config (`.semgrep.yml`, `.sccignore`, etc.) as system config

**Always:**
- fixed executable names + argument arrays
- explicit timeouts and output-size caps on every subprocess
- environment sanitized for subprocesses
- path validation + symlink checks
- file-size limits, skip binary/vendored/generated content
- UUID4 workspace IDs
- structured errors that never leak internal paths or secrets
- secret redaction before anything is written to the snapshot or logs

**Checklist for every change touching repos/files/URLs/subprocesses:**
SSRF, URL validation, command injection, path traversal, symlink escape, git hooks/submodules,
subprocess timeout, resource exhaustion (zip bombs, huge files, deep trees), malicious filenames,
secret leakage in logs, cleanup after failure.

---

## 11. Tool Adapter Contract

Every adapter defines:
`name`, `purpose`, `input model`, `output model`, `timeout`, `failure behavior`,
`evidence semantics`, `security constraints`.

Every adapter returns a normalized `ToolResult`:
```json
{ "tool": "", "status": "success | partial | error", "evidence": [], "data": {}, "warnings": [] }
```

Rules:
- Tools return **facts and evidence paths**, never architecture conclusions.
- Upstream CLI output is parsed into stable internal models. Malformed output = `error`, not a crash.
- A tool failure does not kill the whole analysis: status becomes `partial` with a warning.
- Each adapter is testable with fixtures of real CLI output (no live tool needed in unit tests).

| Tool | Purpose | Notes |
|------|---------|-------|
| git | clone + commit + tracked file list | internal only |
| scc | languages, LOC, complexity | `scc_analyze` only (D9) |
| Tree-sitter | functions, classes, imports, decorators with source ranges | Python first, bounded by file size / node count |
| Syft | dependency / package inventory (SBOM) | cap output before normalization |
| Semgrep | pattern/security findings | pinned local ruleset, no network (D10) |
| detect-secrets | secret-like findings | values ALWAYS redacted, "no findings" is not proof |

---

## 12. repository_snapshot.yaml Contract (draft, frozen in Phase 1)

```yaml
schema_version: "1.0"
generated_at: <iso8601>
repository: { name, url, commit, default_branch }
workspace: { id }
structure:
  directories: []
  files: [ { path, type, language, size } ]      # NO content (D1)
metrics:
  loc: 0
  complexity: 0
  languages: [ { name, files, loc } ]
dependencies:
  ecosystems: []
  packages: [ { name, version, ecosystem, source_file } ]
syntax_evidence:
  imports: []      # each item has path + source range
  functions: []
  classes: []
  decorators: []
security_evidence:
  semgrep: [ { rule_id, severity, path, line } ]
secret_findings:
  count: 0
  findings: [ { detector, path, line } ]         # redacted, never the value
tool_status: { scc: success, syft: success, ... }
limits_applied: { files_truncated: false, items_capped: false, excluded_paths: [] }
warnings: []
```

Filtering excludes: `.git`, `node_modules`, binaries, vendored, generated and oversized files.
Every claim carries a path.

---

## 13. Quality Gate

A task is NOT complete until all of these were actually run:

1. Unit tests
2. Integration tests (where relevant)
3. Security tests (path traversal, symlink, injection, timeout, cleanup)
4. `ruff check` + `ruff format --check`
5. `mypy --strict`
6. `bandit`
7. `pip-audit`
8. Error-handling review
9. Resource-limit review
10. No secrets in logs
11. Docs updated when behavior changes

Never claim completion if a check was not run. If a check cannot run, say so explicitly.

---

## 14. Working Style

- Flow: **Analyze -> Plan -> Implement -> Test -> Review**.
- One phase at a time. **Never move to the next phase without explicit approval.**
- In PLAN mode: do not edit any file. Present the plan and STOP.
- Before editing multiple files, state the file boundaries (create / change / untouched).
- Do not touch unrelated files. Never modify `docs/reference/`.
- Prefer small, reviewable commits.
- Explain every design pattern you add in one sentence: what concrete problem it solves.
- If the instruction says STOP, you STOP. If you violate it, revert and present the plan only.
- Development environment is **WSL2 Ubuntu**. Use bash and `python -m ...`. The repo lives in the
  WSL filesystem, NEVER under `/mnt/*`. CI runs on `ubuntu-latest`. Linux is the PRIMARY target;
  Windows is best-effort only (unit tests, ruff, mypy).
- Python is 3.12 (matches the Dockerfile and CI). The venv is created with `uv`
  (`uv venv --python 3.12 .venv`), so use `uv pip install ...` and `uv pip freeze --exclude-editable`
  (uv venvs have no pip). Lock files are generated on Linux only.
- Tests that need Linux-only behavior (symlinks, permissions, external tool binaries) use
  `skipif(sys.platform == "win32", reason=...)`. CI on Linux is the final judge.
- Never hardcode path separators; always `pathlib`. The workspace root comes from configuration.

---

## 15. Phases (Team 1)

| Phase | Name | Owner |
|-------|------|-------|
| 0 | Bootstrap (structure, tooling, CI skeleton, Docker skeleton) | All |
| 1 | Contracts (request/response, config, ToolResult, snapshot schema, errors) | M1 + M3 |
| 2 | FastAPI foundation (app, health, analyze with validation only) | M1 |
| 3 | Workspace security (WorkspaceManager, path validation, TTL, delete) | M1 + M3 |
| 4 | Git adapter (clone, commit, tracked files) | M1 |
| 5 | Tool framework + scc | M2 |
| 6 | Tree-sitter | M2 |
| 7 | Syft | M2 |
| 8 | Semgrep + detect-secrets | M2 |
| 9 | Snapshot builder (normalize, filter, redact, write, validate YAML) | M3 |
| 10 | End-to-end integration | Team 1 |
| 11 | Testing, hardening, security review | Team 1 |

Member ownership:
- **M1**: FastAPI, GitHub URL validation, clone, workspace lifecycle, Docker.
- **M2**: tool wrappers/adapters and tool contracts.
- **M3**: aggregation, filtering, snapshot YAML, security boundaries, integration tests, API docs.

---

## 16. Definition of Done (per phase)

- Implementation matches the approved contract and D1-D10.
- All Quality Gate checks pass.
- Errors are structured, logs are safe, limits are enforced.
- No unrelated files modified.
- Documentation updated.
- Report: what changed, what remains, any open question.
- Then STOP and wait for approval.

---

## 17. Out of Scope for Phase 1

RAG, AI reasoning and prompts, JSON Manifest, the AI-facing controlled tool layer (D8),
sending to SaaS/Desk agents, scc hotspots/coupling (D9), private repos and auth tokens,
generic shell execution, executing repository code, multi-repo/monorepo specialization,
large-scale performance tuning, persistent storage of snapshots beyond the workspace lifetime.
