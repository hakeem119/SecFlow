# pyrefly: ignore [missing-import]
from typing import Literal
from langgraph.graph import END, START, StateGraph

from app.analyzer.graph.nodes import agent_node, tools_node
from app.analyzer.graph.state import AgentState
from app.analyzer.graph.validation import validation_node

# Guardrail limit to prevent infinite reasoning or reflection loops

MAX_ITERATIONS = 8

def route_after_agent(state: AgentState) -> Literal["tools", "validate", "__end__"]:
    iteration = state.get("iteration_count", 0)
    last_message = state["messages"][-1]
    has_tool_calls = hasattr(last_message, "tool_calls") and bool(last_message.tool_calls)

    if iteration <= 6 and has_tool_calls:
        return "tools"

    return "validate"


def route_after_validation(state: AgentState) -> Literal["agent", "__end__"]:
    iteration = state.get("iteration_count", 0)
    errors = state.get("validation_errors", [])

    if not errors or iteration >= MAX_ITERATIONS:
        return END

    if iteration <= 4:
        return "agent"

    return END

def create_analyzer_graph():
    """
    Compiles the complete cognitive workflow with self-correction feedback loop.
    """
    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    workflow.add_node("validate", validation_node)

    # Base entry
    workflow.add_edge(START, "agent")

    # Conditional routing after agent node
    workflow.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tools": "tools",
            "validate": "validate",
            END: END,
        },
    )

    # ReAct tool execution edge
    workflow.add_edge("tools", "agent")

    # Conditional routing after validation (Reflection Loop)
    workflow.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "agent": "agent",
            END: END,
        },
    )

    return workflow.compile()