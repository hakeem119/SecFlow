# SecFlow_Full_Project
Official SecFlow repository — the controlled and production-ready source of the project, containing only reviewed, validated, and finalized contributions across its services, AI components, infrastructure, and documentation.

## Contribution & Repository Rules

This repository is the official and controlled **SecFlow main repository**.

It is **not a personal workspace, experimentation area, or temporary storage for unfinished work**.

### 1. Final Work Only

Only **final, reviewed, and project-ready work** should be merged into this repository.

Do not push or merge:

* Experimental code
* Temporary files
* Unfinished implementations
* Personal test files
* Debugging artifacts
* Unused dependencies
* Local configuration files
* Draft documentation
* Generated files that are not required by the project

Work in progress should remain on the developer's local environment or dedicated feature branch until it is ready for review.

### 2. No Direct Push to `main`

Direct pushes to `main` are not allowed.

All changes must follow:

```text
Local Development
      ↓
Feature Branch
      ↓
Testing
      ↓
Pull Request
      ↓
Code Review
      ↓
CI / Validation
      ↓
Approval
      ↓
Merge to main
```

### 3. Final Submission Standard

Before opening a Pull Request, the contributor must make sure that the submitted work is:

* Functional
* Tested
* Clean
* Properly structured
* Documented when necessary
* Free of secrets or sensitive information
* Consistent with the project's architecture and coding standards

A Pull Request should represent a **complete and reviewable change**, not an incomplete work log.

### 4. Branches

Each contributor must work on a dedicated branch.

Examples:

```text
feat/repository-analysis/scc
feat/ai-analyzer/manifest-schema
fix/repository-analysis/clone-timeout
docs/architecture/update
refactor/ai-analyzer/orchestration
```

### 5. Pull Requests

Every change must be submitted through a Pull Request.

The Pull Request must clearly describe:

* What was implemented
* Why it was implemented
* What was changed
* How it was tested
* Any important technical considerations

The reviewer should be able to understand the change without needing access to the contributor's personal development environment.

### 6. Repository Ownership

The `main` branch represents the **official and stable state of SecFlow**.

Anything merged into `main` is considered part of the official project and must therefore meet the project's quality and architecture requirements.

### 7. Team Collaboration

Team members are encouraged to experiment freely during development, but experimentation must remain outside the stable `main` branch.

The repository should always reflect the **clean, final, and agreed-upon state of the project**.

### 8. Rule of Thumb

> **Develop freely. Experiment freely. Push carefully. Merge only what is final.**

The goal is to keep the SecFlow repository clean, stable, traceable, and production-ready throughout the project's development.

---

# SecFlow Repository Analysis Service

Phase 1, Team 1 — an independent Python FastAPI microservice that clones a GitHub repository,
runs deterministic analysis tools (scc, Tree-sitter, Syft, Semgrep, detect-secrets), and produces
a structured `repository_snapshot.yaml` containing metadata and evidence only (no source code).

See [AGENTS.md](AGENTS.md) for the full specification, decisions D1-D10, and phase plan.

## Prerequisites

- Python 3.12
- [uv](https://github.com/astral-sh/uv) (for venv and package management)
- Linux (WSL2 Ubuntu or `ubuntu-latest` in CI). Windows is best-effort only.

## Setup

### Linux (primary)

```bash
# Create venv (one time)
uv venv --python 3.12 .venv
source .venv/bin/activate

# Install from lock file (reproducible)
uv pip install -r requirements-dev.lock

# Or install from pyproject.toml (editable, for development)
uv pip install -e ".[dev]"
```

### Lock files

Lock files are generated on Linux only and are the primary installation method for
reproducible environments:

- `requirements.lock` — production dependencies only
- `requirements-dev.lock` — production + development dependencies

### Windows (best-effort)

Lock files are Linux-generated. On Windows, install directly from `pyproject.toml`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Unit tests, ruff, and mypy must pass on Windows. Integration and security tests
may be skipped (`@pytest.mark.skipif(sys.platform == "win32", reason="...")`).

## Quality Gate

```bash
python scripts/quality_gate.py
```

Runs: ruff format check, ruff lint, mypy --strict, pytest, bandit, pip-audit (against lock files).

## Project Structure

```
app/
  api/        routes only, thin
  schemas/    request/response/snapshot/tool models
  services/   RepositoryAnalysisService, WorkspaceManager, SnapshotBuilder
  tools/      one adapter per external tool + ToolRunner
  core/       config, errors, logging, security helpers
tests/
  unit/  integration/  security/  fixtures/
scripts/
  quality_gate.py
docs/
  reference/  (PDFs and architecture image, never modified by agents)
```
