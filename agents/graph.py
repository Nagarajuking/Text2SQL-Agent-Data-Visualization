"""
LangGraph workflow construction for Text-to-SQL system.

This module builds the state graph that orchestrates the agent workflow:
1. Intent Router → SQL Generator → Validator → Executor → Visualizer
2. Error handling with Reflector node (retry loop)
3. Conditional edges based on validation and execution results

Production-grade features:
- Async workflow execution for better performance
- Cyclic error handling with retry limits
- Conditional routing based on state
- Clear workflow visualization
- Type-safe state management
"""

import asyncio
from typing import Literal
from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.nodes import (
    intent_router_node,
    sql_generator_node,
    sql_validator_node,
    executor_node,
    reflector_node,
    visualizer_node,
    format_response_node
)
from core.config import get_config


def should_continue_after_routing(state: AgentState) -> Literal["generate_sql", "end"]:
    """
    Conditional edge after intent routing.
    
    Args:
        state: Current agent state
        
    Returns:
        Next node name or END
    """
    is_relevant = state.get("is_relevant") if isinstance(state, dict) else state.is_relevant
    if is_relevant:
        return "generate_sql"
    else:
        return "end"


def should_continue_after_validation(
    state: AgentState
) -> Literal["execute_query", "reflect"]:
    """
    Conditional edge after SQL validation.
    
    Args:
        state: Current agent state
        
    Returns:
        Next node name
    """
    validation_passed = state.get("validation_passed") if isinstance(state, dict) else state.validation_passed
    if validation_passed:
        return "execute_query"
    else:
        return "reflect"


def should_continue_after_execution(
    state: AgentState
) -> Literal["visualize", "reflect"]:
    """
    Conditional edge after query execution.
    
    Args:
        state: Current agent state
        
    Returns:
        Next node name
    """
    error = state.get("error") if isinstance(state, dict) else state.error
    if error:
        return "reflect"
    else:
        return "visualize"


def should_continue_after_reflection(
    state: AgentState
) -> Literal["validate_sql", "end"]:
    """
    Conditional edge after error reflection.
    
    Args:
        state: Current agent state
        
    Returns:
        Next node name or END
    """
    # Check if we have a final response (max retries exceeded)
    final_response = state.get("final_response") if isinstance(state, dict) else state.final_response
    if final_response:
        return "end"
    else:
        # Retry: go back to validation
        return "validate_sql"


def build_graph() -> StateGraph:
    """
    Build the LangGraph workflow for Text-to-SQL.
    
    Graph structure:
    
    START
      ↓
    [Intent Router] → (not relevant) → END
      ↓ (relevant)
    [SQL Generator]
      ↓
    [SQL Validator] → (invalid) → [Reflector] ←┐
      ↓ (valid)                      ↓          │
    [Executor] → (error) ─────────────┘          │
      ↓ (success)                                │
    [Visualizer]                                 │
      ↓                                          │
    [Format Response]                            │
      ↓                                          │
    END ←────────────────────────────────────────┘
    
    Returns:
        Compiled StateGraph
    """
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("route_intent", intent_router_node)
    workflow.add_node("generate_sql", sql_generator_node)
    workflow.add_node("validate_sql", sql_validator_node)
    workflow.add_node("execute_query", executor_node)
    workflow.add_node("reflect", reflector_node)
    workflow.add_node("visualize", visualizer_node)
    workflow.add_node("format_response", format_response_node)
    
    # Set entry point
    workflow.set_entry_point("route_intent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "route_intent",
        should_continue_after_routing,
        {
            "generate_sql": "generate_sql",
            "end": "format_response"
        }
    )
    
    # Linear edge from generator to validator
    workflow.add_edge("generate_sql", "validate_sql")
    
    # Conditional edge after validation
    workflow.add_conditional_edges(
        "validate_sql",
        should_continue_after_validation,
        {
            "execute_query": "execute_query",
            "reflect": "reflect"
        }
    )
    
    # Conditional edge after execution
    workflow.add_conditional_edges(
        "execute_query",
        should_continue_after_execution,
        {
            "visualize": "visualize",
            "reflect": "reflect"
        }
    )
    
    # Conditional edge after reflection (retry loop)
    workflow.add_conditional_edges(
        "reflect",
        should_continue_after_reflection,
        {
            "validate_sql": "validate_sql",
            "end": "format_response"
        }
    )
    
    # Linear edge from visualizer to formatter
    workflow.add_edge("visualize", "format_response")
    
    # Format response goes to END
    workflow.add_edge("format_response", END)
    
    # Compile graph
    return workflow.compile()


def run_agent(question: str) -> AgentState:
    """
    Run the Text-to-SQL agent on a question (synchronous wrapper).
    
    Args:
        question: User's natural language question
        
    Returns:
        Final agent state with results
    """
    # Run async version in sync context
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(arun_agent(question))


async def arun_agent(question: str) -> AgentState:
    """
    Run the Text-to-SQL agent on a question (async version).
    
    Args:
        question: User's natural language question
        
    Returns:
        Final agent state with results
    """
    # Build graph
    graph = build_graph()
    
    # Initialize state - Pydantic handles all defaults automatically
    initial_state = AgentState(question=question)
    
    # Run graph asynchronously - convert to dict for LangGraph compatibility
    final_state = await graph.ainvoke(initial_state.model_dump())
    
    # Convert back to AgentState for type safety
    return AgentState(**final_state)


# Export graph for visualization/debugging
def get_graph_visualization() -> str:
    """
    Get a text representation of the graph structure.
    
    Returns:
        Graph visualization as string
    """
    graph = build_graph()
    try:
        # Try to get Mermaid diagram if available
        return graph.get_graph().draw_mermaid()
    except:
        return "Graph visualization not available. Install mermaid support."
