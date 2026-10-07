# SecFlow Final Demo Commands

This file contains the exact commands you need to run, step-by-step, to record your demo for the team. 
We are using **OWASP Juice Shop** (`https://github.com/juice-shop/juice-shop`) for this demo, as it is a very popular repository for security tools and will yield great metrics.

---

### Step 1: Ensure you are in the correct directory
Run this to make sure you are in the project folder before starting the demo recording:
```bash
cd ~/SecFlow_Project/Repo_Analysis
```

### Step 2: Build and start the SecFlow container
Run this to ensure the environment is clean and running:
```bash
docker rm -f secflow && \
docker build -t secflow-backend . && \
docker run -d -p 8000:8000 --name secflow \
  -v $(pwd)/app:/app/app \
  secflow-backend
```

### Step 3: Trigger the Analysis
Run this to analyze the OWASP Juice Shop repository. It will output a JSON response. 
*(Wait a few seconds for the `curl` command to return the JSON response)*
```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/juice-shop/juice-shop", "analysis_depth": "standard"}' \
  http://localhost:8000/api/v1/repositories/analyze | jq
```

### Step 4: Extract the HTML Report
Look at the JSON output from Step 3 and copy the `"workspace_id"` value. 
Run this command, replacing `<paste-workspace-id-here>` with the actual ID:
```bash
WORKSPACE_ID="<paste-workspace-id-here>"

docker cp secflow:/var/lib/secflow/workspaces/${WORKSPACE_ID}/repository_snapshot.html ./demo_report.html
```

### Step 5: Open the Report
Finally, open the `demo_report.html` file in your browser to show the team the generated dashboard!
You can open it from your file explorer, or if you are using WSL, you might be able to run:
```bash
explorer.exe demo_report.html
```
