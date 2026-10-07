# Running SecFlow Repository Analysis Service

This guide explains how to build, run, and test the SecFlow backend.

## 1. Prerequisites

- **Docker** running on your system.
- Ensure your user is in the `docker` group to run commands without `sudo`.

## 2. Build the Docker Image

Run this in the repository root (`/home/zodiac/SecFlow_Project/Repo_Analysis/`):

```bash
docker build -t secflow-backend .
```

## 3. Run the Service

You can run the service by mounting the `app` directory so you can edit code live, and mounting the `workspaces` directory if you want to inspect cloned repos on the host:

```bash
docker rm -f secflow
docker run -d -p 8000:8000 --name secflow \
  -v $(pwd)/app:/app/app \
  -e SECFLOW_WORKSPACE_ROOT=/app/tmp_workspace \
  secflow-backend
```

> **Note**: Setting `SECFLOW_WORKSPACE_ROOT=/app/tmp_workspace` inside the container makes it easier to mount and inspect from the host if you add `-v $(pwd)/tmp_workspace:/app/tmp_workspace`.

## 4. Test with a Real Repository

Use `curl` to analyze a real project. Here we use **OWASP/NodeGoat**:

```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/OWASP/NodeGoat", "analysis_depth": "standard"}' \
  http://localhost:8000/api/v1/repositories/analyze | jq
```

## 5. View the HTML Report

The service generates both a `repository_snapshot.yaml` and a premium **HTML report** (with Tailwind CSS and Vue) for each analysis.

To extract it from the running container (if `SECFLOW_WORKSPACE_ROOT` was kept as default `/var/lib/secflow/workspaces`):

```bash
# Get the workspace_id from the curl response, e.g. 265b868f-2082-4665-9b15-84b462de29e2
WORKSPACE_ID="<your_workspace_id>"

docker cp secflow:/var/lib/secflow/workspaces/${WORKSPACE_ID}/repository_snapshot.html ./report.html
```

Then open `report.html` in your web browser!

## Why were some fields empty for NodeGoat previously?

- **Dependencies**: `syft` requires specific package manager manifests. If the repo uses an unsupported format or relies on unstructured vendoring, `syft` might find 0 packages.
- **Security Findings**: The current `semgrep` setup uses a dummy rule (`TODO`). If there are no "TODO"s, or they are ignored by the generic scanner, it returns 0 findings.
- **Secrets**: `detect-secrets` might genuinely find 0 high-entropy secrets in the selected repository.

To see more findings, you can replace the dummy semgrep rule with the real ruleset in `Dockerfile`.
