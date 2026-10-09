# pyrefly: ignore [missing-import]
import os
import webbrowser
from pathlib import Path

# 1. Configure runtime environment for Colab ngrok endpoint
os.environ["MODEL_BASE_URL"] = "https://carrousel-attic-antarctic.ngrok-free.dev/v1"
os.environ["MODEL_NAME"] = "Qwen/Qwen2.5-Coder-3B-Instruct"
os.environ["OPENAI_API_KEY"] = "not-needed"

from app.analyzer.services.analyzer_service import run_analyzer_workflow

def main():
    # 2. Select the sample workspace provided by Team 1 fixtures
    workspace_path = Path("tests/fixtures/dummy_repo").resolve()
    print(f"[*] Target Workspace: {workspace_path}")
    print("[*] Contacting Qwen model on Colab via ngrok...")

    # 3. Trigger Team 2 AI Analyzer workflow
    result = run_analyzer_workflow(str(workspace_path))

    # 4. Display results and output artifacts
    print(f"\n[+] Workflow Finished!")
    print(f"[+] Total Iterations: {result.get('iteration_count')}")
    print(f"[+] Validation Errors: {result.get('validation_errors')}")
    
    artifacts = result.get("artifacts", {})
    json_path = artifacts.get("manifest_json")
    html_path = artifacts.get("manifest_html")

    print(f"\n[+] Manifest JSON: {json_path}")
    print(f"[+] Manifest HTML: {html_path}")

    # 5. Automatically open HTML dashboard in browser if generated
    if html_path and Path(html_path).exists():
        print("[*] Opening manifest.html in default browser...")
        webbrowser.open(f"file://{Path(html_path).resolve()}")

if __name__ == "__main__":
    main()