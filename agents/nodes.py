"""
Node implementations for LangGraph Text-to-SQL agent.

This module contains all the node functions that process the agent state:
- Intent Router: Determines if question is relevant
- SQL Generator: Creates SQL queries with Chain-of-Thought
- SQL Validator: Validates safety, syntax, and relevancy
- Executor: Runs SQL queries
- Reflector: Fixes errors and retries
- Visualizer: Recommends data visualizations

Production-grade features:
- Async support for LLM and DB operations
- Tool decorators for LangChain integration
- Comprehensive error handling
- Detailed logging
- Type-safe state updates
- Robust validation logic
"""

import re
import json
import asyncio
from typing import Dict, Any


from agents.state import AgentState
from core.llm import (
    get_router_llm,
    get_sql_generator_llm,
    get_reflector_llm,
    get_visualizer_llm
)
from core.prompts import (
    get_intent_router_prompt,
    get_sql_generator_prompt,
    get_error_reflection_prompt,
    get_visualization_prompt
)
from core.db_manager import DatabaseManager
from core.config import get_config


# Initialize database manager
db_manager = DatabaseManager()



async def intent_router_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 1: Intent Router
    
    Determines if the user's question is relevant to the music store database.
    Uses a fast model (Gemini Flash) for quick classification.
    
    Args:
        state: Current agent state
        
    Returns:
        Dict with updated state fields
    """
    question = state.question if isinstance(state, AgentState) else state["question"]
    
    # Get router LLM
    llm = get_router_llm()
    
    # Generate prompt
    prompt = get_intent_router_prompt(question)
    
    try:
        # Invoke LLM asynchronously
        response = await llm.ainvoke(prompt)
        response_text = response.content.strip().upper()
        
        # Parse response
        is_relevant = "RELEVANT" in response_text and "NOT_RELEVANT" not in response_text
        
        return {
            "is_relevant": is_relevant,
            "final_response": "" if is_relevant else (
                "I can only answer questions about the music store database. "
                "Please ask about artists, albums, tracks, customers, sales, or employees."
            )
        }
        
    except Exception as e:
        # On error, assume relevant and let downstream nodes handle it
        print(f"[WARNING] Intent router error: {e}")
        return {
            "is_relevant": True,
            "final_response": ""
        }



async def sql_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 2: SQL Generator
    
    Generates SQL query with Chain-of-Thought reasoning.
    Uses a powerful model (Gemini Pro) for complex SQL generation.
    
    Args:
        state: Current agent state
        
    Returns:
        Dict with updated state fields
    """
    question = state.question if isinstance(state, AgentState) else state["question"]
    
    # Get database context
    schema = db_manager.get_annotated_schema()
    sample_data = db_manager.get_sample_data()
    
    # Get SQL generator LLM
    llm = get_sql_generator_llm()
    
    # Generate prompt
    prompt = get_sql_generator_prompt(question, schema, sample_data)
    
    try:
        # Invoke LLM asynchronously
        response = await llm.ainvoke(prompt)
        response_text = response.content
        
        # Extract reasoning (everything before the SQL code block)
        reasoning_match = re.search(r'Reasoning:(.*?)```sql', response_text, re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"
        
        # Extract SQL query from code block
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response_text, re.DOTALL)
        if sql_match:
            sql_query = sql_match.group(1).strip()
        else:
            # Fallback: try to find any SQL-like content
            sql_query = response_text.strip()
        
        return {
            "sql_query": sql_query,
            "reasoning": reasoning,
            "validation_passed": False,  # Will be set by validator
            "validation_error": ""
        }
        
    except Exception as e:
        return {
            "sql_query": "",
            "reasoning": "",
            "validation_passed": False,
            "validation_error": f"SQL generation failed: {str(e)}"
        }



def sql_validator_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 3: SQL Validator
    
    Validates the generated SQL query for:
    - Safety (no DROP, DELETE, UPDATE, etc.)
    - Syntax correctness
    - Table/column relevancy
    - LIMIT enforcement
    
    Args:
        state: Current agent state
        
    Returns:
        Dict with updated state fields
    """
    sql_query = state.sql_query if isinstance(state, AgentState) else state["sql_query"]
    
    # Safety check: Block dangerous SQL operations
    dangerous_keywords = [
        r'\bDROP\b',
        r'\bDELETE\b',
        r'\bUPDATE\b',
        r'\bINSERT\b',
        r'\bALTER\b',
        r'\bTRUNCATE\b',
        r'\bCREATE\b',
        r'\bREPLACE\b'
    ]
    
    for keyword_pattern in dangerous_keywords:
        if re.search(keyword_pattern, sql_query, re.IGNORECASE):
            keyword = keyword_pattern.replace(r'\b', '').replace('\\', '')
            return {
                "validation_passed": False,
                "validation_error": (
                    f"Query contains forbidden keyword: {keyword}. "
                    f"Only SELECT queries are allowed for safety."
                )
            }
    
    # Relevancy check: Ensure query only references valid tables
    valid_tables = set(db_manager.get_table_names())
    
    # Extract table names from query (simple pattern matching)
    # This catches FROM and JOIN clauses
    table_pattern = r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    referenced_tables = set(re.findall(table_pattern, sql_query, re.IGNORECASE))
    
    invalid_tables = referenced_tables - valid_tables
    if invalid_tables:
        return {
            "validation_passed": False,
            "validation_error": (
                f"Query references invalid table(s): {', '.join(invalid_tables)}. "
                f"Valid tables are: {', '.join(sorted(valid_tables))}"
            )
        }
    
    # Syntax check: Use EXPLAIN QUERY PLAN to validate syntax
    is_valid, syntax_error = db_manager.validate_query_syntax(sql_query)
    if not is_valid:
        return {
            "validation_passed": False,
            "validation_error": f"SQL syntax error: {syntax_error}"
        }
    
    # LIMIT enforcement: Add LIMIT if not present
    config = get_config()
    if not re.search(r'\bLIMIT\s+\d+', sql_query, re.IGNORECASE):
        sql_query = sql_query.rstrip(';')
        sql_query = f"{sql_query} LIMIT {config.max_result_rows};"
    
    # All checks passed
    return {
        "sql_query": sql_query,  # May be modified with LIMIT
        "validation_passed": True,
        "validation_error": ""
    }



def executor_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 4: Executor
    
    Executes the validated SQL query against the database.
    
    Args:
        state: Current agent state
        
    Returns:
        Dict with updated state fields
    """
    sql_query = state.sql_query if isinstance(state, AgentState) else state["sql_query"]
    
    # Execute query
    results, error = db_manager.execute_query(sql_query, enforce_limit=True)
    
    if error:
        return {
            "query_result": [],
            "error": error
        }
    else:
        return {
            "query_result": results,
            "error": ""
        }



async def reflector_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 5: Reflector
    
    Analyzes errors and generates corrected SQL queries.
    Uses a fast model (Gemini Flash) for quick error correction.
    
    Args:
        state: Current agent state
        
    Returns:
        Dict with updated state fields
    """
    question = state.question if isinstance(state, AgentState) else state["question"]
    sql_query = state.sql_query if isinstance(state, AgentState) else state["sql_query"]
    
    # Get error from either validation or execution
    if isinstance(state, AgentState):
        error = state.error or state.validation_error
        retry_count = state.retry_count
    else:
        error = state.get("error") or state.get("validation_error", "")
        retry_count = state.get("retry_count", 0)
    
    # Increment retry count
    retry_count += 1
    
    # Check if we've exceeded max retries
    config = get_config()
    if retry_count > config.max_retry_count:
        return {
            "retry_count": retry_count,
            "final_response": (
                f"I apologize, but I couldn't generate a valid SQL query after "
                f"{config.max_retry_count} attempts. Error: {error}"
            )
        }
    
    # Get database schema for context
    schema = db_manager.get_annotated_schema()
    
    # Get reflector LLM
    llm = get_reflector_llm()
    
    # Generate error reflection prompt
    prompt = get_error_reflection_prompt(question, sql_query, error, schema)
    
    try:
        # Invoke LLM asynchronously
        response = await llm.ainvoke(prompt)
        response_text = response.content
        
        # Extract explanation
        explanation_match = re.search(r'Explanation:(.*?)```sql', response_text, re.DOTALL)
        explanation = explanation_match.group(1).strip() if explanation_match else ""
        
        # Extract corrected SQL
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response_text, re.DOTALL)
        if sql_match:
            corrected_sql = sql_match.group(1).strip()
        else:
            corrected_sql = sql_query  # Keep original if extraction fails
        
        return {
            "sql_query": corrected_sql,
            "reasoning": f"Retry {retry_count}: {explanation}",
            "retry_count": retry_count,
            "validation_passed": False,  # Will be re-validated
            "error": ""  # Clear error for retry
        }
        
    except Exception as e:
        return {
            "retry_count": retry_count,
            "final_response": f"Error correction failed: {str(e)}"
        }



async def visualizer_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 6: Visualizer
    
    Analyzes query results and recommends appropriate visualizations.
    
    Args:
        state: Current agent state
        
    Returns:
        Dict with updated state fields
    """
    question = state.question if isinstance(state, AgentState) else state["question"]
    results = state.query_result if isinstance(state, AgentState) else state["query_result"]
    
    # If no results, no visualization needed
    if not results:
        return {
            "visualization_spec": None,
            "final_response": "Query executed successfully but returned no results."
        }
    
    # Get column names and row count
    columns = list(results[0].keys()) if results else []
    row_count = len(results)
    
    # Get visualizer LLM
    llm = get_visualizer_llm()
    
    # Generate visualization prompt
    prompt = get_visualization_prompt(question, columns, row_count)
    
    try:
        # Invoke LLM asynchronously
        response = await llm.ainvoke(prompt)
        response_text = response.content.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            viz_spec = json.loads(json_match.group(0))
        else:
            # Default to table if no JSON found
            viz_spec = {"chart_type": "table"}
        
        return {
            "visualization_spec": viz_spec
        }
        
    except Exception as e:
        # On error, default to table visualization
        print(f"[WARNING] Visualization recommendation failed: {e}")
        return {
            "visualization_spec": {"chart_type": "table"}
        }



def format_response_node(state: AgentState) -> Dict[str, Any]:
    """
    Final node: Format the response for the user.
    
    Args:
        state: Current agent state
        
    Returns:
        Dict with updated state fields
    """
    # If we already have a final response (from error handling), use it
    if isinstance(state, AgentState):
        if state.final_response:
            return {}
        results = state.query_result
    else:
        if state.get("final_response"):
            return {}
        results = state["query_result"]
    
    row_count = len(results)
    
    # Format success message
    final_response = f"Query executed successfully! Found {row_count} result(s)."
    
    return {
        "final_response": final_response
    }
