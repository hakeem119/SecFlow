# pyrefly: ignore [missing-import]
import json
import re
from typing import Any
from pydantic import ValidationError

from app.analyzer.graph.state import AgentState
from app.analyzer.schemas.manifest import ProjectManifest


def extract_json_payload(raw_content: str) -> str:
    """
    Extracts raw JSON from string, handling markdown code fences if present.
    """
    content = raw_content.strip()
    # Remove markdown code fences if LLM accidentally enclosed output
    fence_pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.match(fence_pattern, content)
    if match:
        return match.group(1).strip()
    return content


def validation_node(state: AgentState) -> dict[str, Any]:
    """
    Validates candidate manifest draft against the strict ProjectManifest schema.
    If valid, clears error ledger. If invalid, stores formatted schema violations.
    """
    manifest_draft = state.get("manifest_draft")

    if not manifest_draft:
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
        ProjectManifest(**parsed_data)

        # Success: Clear any previous validation errors
        return {
            "validation_errors": [],
            "manifest_draft": clean_json,
        }

    except json.JSONDecodeError as jde:
        return {
            "validation_errors": [
                f"JSON Syntax Error: {str(jde)}. Ensure valid JSON output without trailing commas or syntax errors."
            ]
        }
    except ValidationError as ve:
        # Capture precise Pydantic validation error paths and messages
        errors = [
            f"Field '{'.'.join(str(loc) for loc in err['loc'])}': {err['msg']}"
            for err in ve.errors()
        ]
        return {
            "validation_errors": errors
        }
    except Exception as exc:
        return {
            "validation_errors": [f"Unexpected validation failure: {str(exc)}"]
        }