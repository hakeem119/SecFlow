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
