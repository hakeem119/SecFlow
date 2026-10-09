# pyrefly: ignore [missing-import]
import pytest
from langchain_core.messages import AIMessage, ToolCall
from langgraph.graph import END

from app.analyzer.graph.state import AgentState
from app.analyzer.graph.workflow import MAX_ITERATIONS, create_analyzer_graph, route_after_agent


def test_route_to_tools():
    """Ensure route_after_agent routes to 'tools' when tool calls are requested."""
    tool_call: ToolCall = {
        "name": "read_file",
        "args": {"path": "README.md"},
        "id": "call_123",
    }
    msg = AIMessage(content="", tool_calls=[tool_call])
    state: AgentState = {
        "messages": [msg],
        "snapshot_data": {},
        "workspace_path": "/mock/workspace",
        "manifest_draft": None,
        "validation_errors": [],
        "iteration_count": 1,
    }
    decision = route_after_agent(state)
    assert decision == "tools"


def test_route_to_end_on_manifest_draft():
    """Ensure route_after_agent routes to END when agent outputs manifest draft."""
    msg = AIMessage(content='{"project": {"name": "sample"}}')
    state: AgentState = {
        "messages": [msg],
        "snapshot_data": {},
        "workspace_path": "/mock/workspace",
        "manifest_draft": '{"project": {"name": "sample"}}',
        "validation_errors": [],
        "iteration_count": 2,
    }
    decision = route_after_agent(state)
    assert decision == END


def test_max_iteration_guardrail():
    """Ensure loop breaks at MAX_ITERATIONS even if tool calls are pending."""
    tool_call: ToolCall = {
        "name": "read_file",
        "args": {"path": "README.md"},
        "id": "call_999",
    }
    # LLM requests a tool, but iteration threshold is reached
    msg = AIMessage(content="", tool_calls=[tool_call])
    state: AgentState = {
        "messages": [msg],
        "snapshot_data": {},
        "workspace_path": "/mock/workspace",
        "manifest_draft": None,
        "validation_errors": [],
        "iteration_count": MAX_ITERATIONS,
    }
    decision = route_after_agent(state)
    assert decision == END


def test_graph_compilation():
    """Verify that the compiled LangGraph workflow exposes required nodes."""
    graph = create_analyzer_graph()
    assert graph is not None
    assert "agent" in graph.nodes
    assert "tools" in graph.nodes