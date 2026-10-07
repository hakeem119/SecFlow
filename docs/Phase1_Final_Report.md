# SecFlow Repository Analysis Service - Final Documentation

## 1. Project Overview (شرح البروجيكت كامل)
The SecFlow Repository Analysis Service is a deterministic, high-performance Python FastAPI microservice (Team 1). Its primary role is to accept a GitHub repository URL, clone it safely into an isolated ephemeral workspace, run a suite of static analysis tools (Git, scc, Tree-sitter, Syft, Semgrep, detect-secrets), and aggregate the findings into a standard `repository_snapshot.yaml` artifact. The service handles strict security validation (path traversal prevention, symlink escape detection), resource limits, and automated TTL (Time-to-Live) cleanup for workspaces. It operates with zero AI involvement internally, serving strictly as a safe, structured ingestion pipeline for Team 2.

## 2. System Design (تصميم النظام)
The architecture follows a strictly layered Port/Protocol Adapter pattern:
- **API Layer (`app/api/`)**: Thin routes that validate incoming JSON requests and return standard HTTP JSON responses.
- **Service Layer (`app/services/`)**: Orchestrates the business logic. Uses Dependency Injection (`app/core/dependencies.py`) to wire up the Git fetcher, analysis tools, and snapshot builder.
- **Tool Adapters (`app/tools/`)**: Isolated adapters for external subprocesses. They conform to the `AnalysisTool` protocol, launching strictly bounded command-line utilities using the centralized `ToolRunner`, absorbing failures, and normalizing CLI output into Pydantic models (`ToolResult`).
- **Data/Schemas (`app/schemas/`)**: Pydantic models ensuring data integrity at every boundary (Request, Domain, Tool, Snapshot).
- **Workspace Lifecycle**: Workspaces are assigned unpredictable UUIDs. Background Asyncio Reapers (`app/services/reaper.py`) automatically sweep the filesystem for expired sidecar `.meta` files, deleting old workspaces.

## 3. Directory and File Breakdown (شرح كل فايل)
- **`app/api/routes.py`**: Exposes `/api/v1/repositories/analyze` and `/api/v1/workspaces/{workspace_id}` endpoints.
- **`app/api/middleware.py` & `error_handlers.py`**: Traps unhandled exceptions, enforcing a strict internal error mapping so no tracebacks leak via the API.
- **`app/core/dependencies.py`**: The single Composition Root that initializes and injects the Git fetcher, tools, and snapshot builder.
- **`app/core/safe_path.py`**: Implements the `SafePath` Value Object to prevent directory traversal and symlink escapes.
- **`app/schemas/`**:
  - `api.py`: External JSON request/response models.
  - `domain.py`: Core domain Value Objects (`GitHubRepoUrl`, `WorkspaceId`).
  - `snapshot.py`: Pydantic models rigidly defining the output `repository_snapshot.yaml` (evidence without source values).
  - `tool.py`: Normalized structures representing extracted findings (e.g., `SecretFinding`, `SecurityFinding`).
- **`app/services/`**:
  - `repository_service.py`: Orchestrates the clone, tool execution, and snapshot aggregation.
  - `workspace.py`: Creates, validates, and explicitly deletes `UUID4`-named workspace directories on disk.
  - `workspace_scan.py`: Performs size/file bounds checks post-clone.
  - `reaper.py`: A lifespan async background task that deletes expired workspaces based on a TTL `.meta` sidecar.
  - `snapshot_builder.py`: A 5-stage pipeline (Filter -> Normalize -> Redact -> Validate -> Write) that guarantees the final artifact is safe, schema-compliant, and free of aliases.
- **`app/tools/`**:
  - `runner.py`: The single centralized `CommandRunner`. Wraps all `subprocess` execution with fixed timeouts and stdout/stderr byte limits.
  - `git.py`, `scc.py`, `tree_sitter.py`, `syft.py`, `semgrep.py`, `secrets.py`: Tool-specific adapters. Normalizes upstream outputs into Pydantic models.
- **`scripts/quality_gate.py` & `check_ownership.py`**: Local CI/CD scripts validating typing, linting, tests, and branch file-ownership limits.
- **`.github/workflows/ci.yml`**: GitHub Actions CI workflow ensuring gates pass on `main`.

## 4. Workflow and Operations (طريقة العمل والتشغيل)
**To Run Locally**:
1. Ensure `uv`, `Python 3.12`, `Docker`, and external tools (scc, syft, semgrep) are locally available.
2. Initialize virtualenv: `uv venv --python 3.12 .venv && source .venv/bin/activate`
3. Install dependencies: `uv pip install -r requirements.lock`
4. Run the Dev Server: `fastapi dev app/main.py`
**To Run the CI/Quality Gate**:
- `python scripts/quality_gate.py` (Append `--dev` to bypass test coverage requirements).

**Operational Flow**:
- A user makes a `POST /api/v1/repositories/analyze`.
- The API clones the repo depth=1, scans it, runs parallel subprocesses for `syft`, `semgrep`, etc., with timeouts.
- The Builder filters out `.git/`, truncates large responses, and dumps the `repository_snapshot.yaml`.
- The background `reaper` sweeps the ephemeral workspace directory continuously.

## 5. Implementation Phases (المراحل التي مشينا عليها)
- **Phase 0 & 1**: Bootstrap, API Contracts, and Tool schemas/models.
- **Phase 2**: FastAPI foundation and Health checks.
- **Phase 3**: Workspace Security (SafePath, UUIDs, TTL Reaper).
- **Phase 4**: Git Adapter execution bounded tightly by Subprocess runner.
- **Phase 5-8**: Orchestrating individual Tool Adapters (SCC, Tree-sitter, Syft, Semgrep, Detect-secrets).
- **Phase 9**: Snapshot Builder (Filter -> Normalize -> Redact -> Validate -> Write).
- **Phase 10 & 11**: End-to-End Dependency Wiring, Integration, and PR Reviews (M1/M2/M3).

## 6. Hand-off to Team 2 (التيم اللي بعدينا هياخد مننا إيه وهيشتغل إزاي)
**What Team 2 Receives**:
- Team 2 receives a `workspace_id` corresponding to the securely vetted clone residing on the filesystem.
- They receive the generated `repository_snapshot.yaml` artifact containing rich metadata, metrics, and security evidence pointers. **Crucially, the snapshot has no actual code snippets or leaked secret values (Per D1).**

**How Team 2 Will Work**:
- **MCP Server & Dynamic Retrieval**: Team 2 takes ownership of dynamically executing LLM tool calls against the workspace. They will deploy a Model Context Protocol (MCP) server.
- **Targeted Lookups**: The LLM will read the findings (e.g., "Semgrep found a critical bug on line 15 of src/main.py"). The AI Agent will use its AI-facing tools (e.g., `read_file`, `search_code`) provided by Team 2 to reach directly into the isolated workspace and fetch ONLY the code context it needs to reason about the bug.
- **Final Manifest**: The AI generates a `JSON Manifest` interpreting the vulnerabilities and architectural hotspots, acting entirely independent of Team 1's backend orchestration.
