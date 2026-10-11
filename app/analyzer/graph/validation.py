# pyrefly: ignore [missing-import]
import json
import re
from typing import Any
from pydantic import ValidationError

from app.analyzer.graph.state import AgentState
from app.analyzer.schemas.manifest import ProjectManifest


def extract_json_payload(raw_content) -> str:
    """
    Cleans raw LLM response, extracts pure JSON, handles lists, and strips Markdown fences.
    """
    if isinstance(raw_content, dict):
        return json.dumps(raw_content)

    if isinstance(raw_content, list):
        parts = []
        for item in raw_content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif hasattr(item, "text"):
                parts.append(item.text)
            else:
                parts.append(str(item))
        raw_content = "\n".join(parts)
    elif not isinstance(raw_content, str):
        raw_content = str(raw_content)

    content = raw_content.strip()

    if "```" in content:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if match:
            content = match.group(1).strip()

    start_idx = content.find("{")
    end_idx = content.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        content = content[start_idx : end_idx + 1]

    return content


def validation_node(state: AgentState) -> dict[str, Any]:
    """
    Validates candidate manifest draft against the strict ProjectManifest schema.
    If valid, clears error ledger. If invalid, stores formatted schema violations.
    """
    manifest_draft = state.get("manifest_draft")

    if not manifest_draft:
        print("\n---> [Validation Node] Failed: No manifest draft found.")
        return {
            "validation_errors": [
                "No manifest draft found. Agent must produce valid JSON matching ProjectManifest schema."
            ]
        }

    clean_json = extract_json_payload(manifest_draft)

    try:
        # First ensure string is well-formed JSON
        parsed_data = json.loads(clean_json)

        # Validate against authoritative Pydantic contract (extra='forbid')
        manifest_obj = ProjectManifest(**parsed_data)

        print("\n---> [Validation Node] ProjectManifest successfully validated! ✅")
        # Success: Clear any previous validation errors
        return {
            "validation_errors": [],
            "manifest_draft": clean_json,
        }

    except json.JSONDecodeError as jde:
        print(f"\n---> [Validation Node] JSON Syntax Error: {jde}")
        return {
            "validation_errors": [
                f"JSON Syntax Error: {str(jde)}. Ensure valid JSON output without trailing commas or syntax errors."
            ]
        }
    except ValidationError as ve:
        errors = [
            f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}"
            for err in ve.errors()
        ]
        print(f"\n---> [Validation Node] Schema Validation Errors: {errors}")
        return {
            "validation_errors": errors
        }
    except Exception as exc:
        print(f"\n---> [Validation Node] Unexpected error: {exc}")
        return {
            "validation_errors": [f"Unexpected validation failure: {str(exc)}"]
        }