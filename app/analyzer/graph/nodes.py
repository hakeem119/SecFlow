# pyrefly: ignore [missing-import]

import json
import os
from typing import Any
from dotenv import load_dotenv
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from app.analyzer.graph.state import AgentState
from app.analyzer.schemas.manifest import ProjectManifest
from app.analyzer.tools.factory import get_analyzer_tools
load_dotenv()

# ============================================================
# System Prompt
# ============================================================

SYSTEM_PROMPT = """You are a Principal Security & Software Systems Architect responsible for repository-level project understanding within SecFlow.

Your mission is to transform repository_snapshot.yaml plus selectively retrieved evidence into a highly detailed, security-focused ProjectManifest JSON.

CORE ANALYSIS GUIDELINES:
1. DEPENDENCIES & EXACT VERSIONS:
   - Extract primary third-party dependencies along with their exact versions from manifest files (package.json, requirements.txt, pom.xml, go.mod, etc.).
   - Distinguish runtime vs dev dependencies.

2. ROUTES & ENDPOINTS SURFACE MAPPING:
   - Enumerate key exposed API endpoints and WebSocket routes.
   - For each endpoint specify:
     * HTTP Method (GET, POST, PUT, DELETE, WS, etc.).
     * Authentication Requirement & Scheme: Specify whether auth is needed and which mechanism is used (jwt, session_cookie, api_key, oauth2, basic, none, custom).
     * Middlewares: List exact middleware functions guarding or preprocessing the route (e.g. authMiddleware, multer/upload, rateLimiter, validator).
     * Input Types: Identify how user input is accepted (query, path_param, json_body, form_data, file_upload, header). Highlight any file upload routes.
     * Response Type: Identify format (application/json, text/html, file_stream).

3. ARCHITECTURE & GLOBAL MIDDLEWARES:
   - Identify concrete application entry points and architectural patterns.
   - Map global middlewares (CORS policies, Helmet/security headers, global error handlers, session loaders) with their roles.
   - Trace data flow from client entry points through routers, middlewares, and services down to databases.

4. SECRETS & CREDENTIAL MANAGEMENT:
   - Detect secret handling patterns: environment variables, configuration templates (.env.example), and hardcoded token fallbacks.
   - SECURITY RULE: NEVER output the actual plaintext secret values. Only identify the secret key name (e.g. JWT_SECRET, DB_PASSWORD) and its usage.

5. ACTORS, ROLES & PRIVILEGES:
   - Enumerate threat actors and roles (Anonymous, Authenticated Users, Admins, Service Accounts) and their authorization boundaries.

6. STRICT EVIDENCE GROUNDING & FORMAT:
   - Ground every single claim in repository facts. Never guess, assume, or hallucinate.
   - Provide exact file paths and line ranges in evidence ledgers.
   - Output ONLY the raw JSON string matching the target schema. No markdown fences (```json), no conversational chatter.
"""
# ============================================================
# Target Manifest Structure
# ============================================================

TARGET_MANIFEST_STRUCTURE = """
{
  "project": {
    "name": "string",
    "type": "web_application | api_service | cli_tool | library | microservice | monolith",
    "description": "string",
    "primary_purpose": "string"
  },
  "actors": [
    {
      "name": "string",
      "role": "string"
    }
  ],
  "technologies": [
    {
      "name": "string",
      "category": "language | framework | database | orm | library | tool | ci_cd | runtime",
      "version": "string or null",
      "evidence": [
        {
          "file_path": "string",
          "line_start": 1,
          "line_end": 10,
          "description": "string"
        }
      ]
    }
  ],
  "architecture": {
    "pattern": "monolith | microservices | modular_monolith | event_driven | serverless | unknown",
    "entry_points": ["string"],
    "core_components": ["string"],
    "global_middlewares": [
      {
        "name": "string",
        "type": "auth | cors | rate_limit | logging | validation | security_headers | file_handling | error_handling | other",
        "description": "string",
        "file_path": "string or null"
      }
    ],
    "data_flow_summary": "string"
  },
  "deployment": {
    "containerized": false,
    "configs": ["string"],
    "target_platforms": ["string"]
  },
  "key_dependencies": [
    {
      "name": "string",
      "version": "string or null",
      "is_dev": false,
      "description": "string or null"
    }
  ],
  "secrets": [
    {
      "name": "string",
      "type": "env_var | hardcoded_fallback | config_file | secret_manager | other",
      "file_path": "string",
      "line_start": 1,
      "line_end": 10,
      "description": "string"
    }
  ],
  "endpoints": [
    {
      "path": "string",
      "method": "GET | POST | PUT | PATCH | DELETE | WS",
      "auth_required": false,
      "auth_method": "jwt | session_cookie | api_key | oauth2 | basic | none | custom or null",
      "middlewares": ["string"],
      "input_types": ["query | path_param | json_body | form_data | file_upload | header | none"],
      "response_type": "string",
      "description": "string"
    }
  ],
  "confidence_score": 0.95,
  "evidence_ledger": [
    {
      "file_path": "string",
      "line_start": 1,
      "line_end": 10,
      "description": "string"
    }
  ]
}
"""

# ============================================================
# Model Configuration
# ============================================================
def get_model(tools: list[BaseTool] | None = None) -> Any:
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("MODEL_NAME", "gemini-3.8-flash")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.0,
    )

    if tools:
        return llm.bind_tools(tools)
    return llm

print("GEMINI KEY LOADED:", bool(os.getenv("GEMINI_API_KEY")))
print("MODEL:", os.getenv("MODEL_NAME"))
# ============================================================
# Agent Node
# ============================================================

def agent_node(state: AgentState) -> dict[str, Any]:
    """
    Reasoning node:
    - evaluates current evidence
    - decides whether tools are required
    - produces the final ProjectManifest draft
    """

    workspace_path = state.get("workspace_path", "")

    current_iteration = (
        state.get("iteration_count", 0) + 1
    )

    # Allow exploratory tool calls only during early iterations
    allow_tools = current_iteration <= 6

    tools = (
        get_analyzer_tools(workspace_path)
        if allow_tools
        else []
    )

    model = get_model(
        tools if allow_tools else None
    )

    existing_messages = list(
        state.get("messages", [])
    )

    messages_to_add: list[Any] = []

    messages_for_llm: list[Any] = list(
        existing_messages
    )

    # ========================================================
    # First Agent Turn
    # ========================================================

    if not existing_messages:

        snapshot_clean = json.dumps(
            state.get("snapshot_data", {}),
            separators=(",", ":"),
        )

        sys_msg = SystemMessage(
            content=SYSTEM_PROMPT
        )

        task_prompt = (
            "### PRIMARY INPUT: repository_snapshot.yaml\n"
            f"```json\n{snapshot_clean}\n```\n\n"

            "### REQUIRED OUTPUT SCHEMA:\n"
            f"```json\n"
            f"{TARGET_MANIFEST_STRUCTURE.strip()}"
            f"\n```\n\n"

            "### REASONING STEPS:\n"
            "1. Review the snapshot facts.\n"
            "2. If entry-point code or architecture details "
            "are unclear, call targeted tools (e.g. read_file).\n"
            "3. If evidence is complete, synthesize and output "
            "ONLY the validated ProjectManifest JSON."
        )

        usr_msg = HumanMessage(
            content=task_prompt
        )

        messages_to_add.extend(
            [
                sys_msg,
                usr_msg,
            ]
        )

        messages_for_llm.extend(
            [
                sys_msg,
                usr_msg,
            ]
        )

    # ========================================================
    # Subsequent Turns
    # ========================================================

    else:

        validation_errors = state.get(
            "validation_errors",
            [],
        )

        if validation_errors:

            err_msg = HumanMessage(
                content=(
                    "CRITICAL: Schema validation failed "
                    "with errors:\n"
                    + "\n".join(
                        f"- {e}"
                        for e in validation_errors
                    )
                    + "\nCorrect the JSON structure and "
                    "regenerate ONLY valid JSON."
                )
            )

            messages_to_add.append(
                err_msg
            )

            messages_for_llm.append(
                err_msg
            )

        elif not allow_tools:

            cut_msg = HumanMessage(
                content=(
                    "Evidence collection complete. "
                    "Synthesize and output the final "
                    "validated ProjectManifest JSON now."
                )
            )

            messages_to_add.append(
                cut_msg
            )

            messages_for_llm.append(
                cut_msg
            )

    # ========================================================
    # Invoke Qwen through Groq
    # ========================================================

    print(
        f"\n---> [Agent Turn {current_iteration}] "
        "Invoking Qwen3.8-27B via Groq..."
    )

    response = model.invoke(
        messages_for_llm
    )

    # ========================================================
    # Tool Calls
    # ========================================================

    has_tools = (
        hasattr(response, "tool_calls")
        and bool(response.tool_calls)
        and allow_tools
    )

    if has_tools:

        calls = [
            f"{t['name']}({t.get('args', {})})"
            for t in response.tool_calls
        ]

        print(
            f"---> [Agent Turn {current_iteration}] "
            f"Native Tool Call Requested: {calls}"
        )

    else:

        print(
            f"---> [Agent Turn {current_iteration}] "
            "Manifest Draft Synthesized!"
        )

    messages_to_add.append(
        response
    )

    # ========================================================
    # State Updates
    # ========================================================

    updates: dict[str, Any] = {
        "messages": messages_to_add,
        "iteration_count": current_iteration,
        "validation_errors": [],
    }

    if not has_tools:

        updates["manifest_draft"] = (
            response.content
        )

    return updates


# ============================================================
# Tools Node
# ============================================================

def tools_node(
    state: AgentState,
) -> dict[str, Any]:
    """
    Execution node:
    runs requested safe tools inside the workspace
    and appends observations back to state messages.
    """

    workspace_path = state.get(
        "workspace_path",
        "",
    )

    tools = get_analyzer_tools(
        workspace_path
    )

    tool_map = {
        tool.name: tool
        for tool in tools
    }

    last_message = state["messages"][-1]

    tool_messages: list[ToolMessage] = []

    if (
        hasattr(last_message, "tool_calls")
        and last_message.tool_calls
    ):

        for tool_call in last_message.tool_calls:

            name = tool_call["name"]

            args = tool_call.get(
                "args",
                {},
            )

            tool_id = tool_call.get(
                "id",
                name,
            )

            if name in tool_map:

                try:

                    result = tool_map[
                        name
                    ].invoke(args)

                except Exception as exc:

                    result = (
                        f"Error executing tool "
                        f"{name}: {str(exc)}"
                    )

            else:

                result = (
                    f"Error: Tool '{name}' "
                    "is not recognized."
                )

            print(
                f"---> [Safe Tools Node] "
                f"Executed '{name}' successfully."
            )

            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id,
                )
            )

    return {
        "messages": tool_messages,
    }