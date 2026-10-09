# pyrefly: ignore [missing-import]
from typing import Literal
from langgraph.graph import END, START, StateGraph

from app.analyzer.graph.nodes import agent_node, tools_node
from app.analyzer.graph.state import AgentState
from app.analyzer.graph.validation import validation_node

# Guardrail limit to prevent infinite reasoning or reflection loops
MAX_ITERATIONS = 15


def route_after_agent(state: AgentState) -> Literal["tools", "validate", "__end__"]:
    """
    Evaluates agent output: routes to tools execution if requested,
    routes to validation if manifest draft is synthesized,
    or enforces hard termination if MAX_ITERATIONS is reached.
    """
    if state.get("iteration_count", 0) >= MAX_ITERATIONS:
        return END

    last_message = state["messages"][-1]

    # If tool calls are requested, execute tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # Agent produced output without tool calls -> validate schema
    return "validate"


def route_after_validation(state: AgentState) -> Literal["agent", "__end__"]:
    """
    Evaluates schema validation outcome.
    Triggers self-correction reflection back to agent if validation failed,
    or terminates successfully if schema is verified.
    """
    if state.get("iteration_count", 0) >= MAX_ITERATIONS:
        return END

    errors = state.get("validation_errors", [])
    if errors:
        # Self-correction: feedback errors to agent for regeneration
        return "agent"

    # Manifest is valid and ready
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