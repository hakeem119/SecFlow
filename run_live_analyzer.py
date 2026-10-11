import os
import webbrowser
from pathlib import Path
from dotenv import load_dotenv

# 1. Load secrets from .env before importing the analyzer
load_dotenv()

# 2. Configure Gemini API
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")

os.environ["GEMINI_API_KEY"] = api_key
os.environ["MODEL_NAME"] = "gemini-3.8-flash"

print(f"GEMINI KEY LOADED: {bool(api_key)}")
print(f"MODEL: {os.environ['MODEL_NAME']}")

from app.analyzer.services.analyzer_service import run_analyzer_workflow

# Keep this only if your analyzer uses the OpenAI-compatible client
os.environ["OPENAI_API_KEY"] = api_key

from app.analyzer.services.analyzer_service import run_analyzer_workflow


def main():
    # 3. Select the test repository
    project_root = Path(__file__).resolve().parent
    workspace_path = (
        project_root / "tests" / "fixtures" / "dummy_repo"
    ).resolve()

    if not workspace_path.is_dir():
        raise FileNotFoundError(
            f"Workspace not found: {workspace_path}"
        )

    print(f"[*] Target Workspace: {workspace_path}")
    print("[*] Contacting Qwen via Groq API...")

    # 4. Run Team 2 AI Analyzer
    result = run_analyzer_workflow(str(workspace_path))

    if not isinstance(result, dict):
        raise RuntimeError(
            f"Unexpected workflow result: {type(result).__name__}"
        )

    # 5. Display workflow results
    print("\n[+] Workflow Finished!")
    print(f"[+] Total Iterations: {result.get('iteration_count')}")
    print(f"[+] Validation Errors: {result.get('validation_errors')}")

    artifacts = result.get("artifacts") or {}
    json_path = artifacts.get("manifest_json")
    html_path = artifacts.get("manifest_html")

    print(f"\n[+] Manifest JSON: {json_path}")
    print(f"[+] Manifest HTML: {html_path}")

    # 6. Open the generated HTML report
    if html_path:
        report_path = Path(html_path)

        if not report_path.is_absolute():
            report_path = project_root / report_path

        report_path = report_path.resolve()

        if report_path.is_file():
            print("[*] Opening HTML report...")
            webbrowser.open(report_path.as_uri())
        else:
            print(f"[!] HTML report not found: {report_path}")


if __name__ == "__main__":
    main()