"""
Agent state definition for LangGraph Text-to-SQL system.

This module defines the state structure that flows through the graph.
Uses Pydantic BaseModel for runtime validation and type safety.

Production-grade features:
- Runtime type validation with clear error messages
- Automatic default values for optional fields
- Field-level validation constraints
- Rich field metadata and documentation
- Self-documenting code structure
"""

from typing import List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field, field_validator, ConfigDict


class AgentState(BaseModel):
    """
    State that flows through the LangGraph agent.
    
    This state is passed between nodes and updated as the agent progresses
    through the workflow. Using Pydantic BaseModel provides:
    - Runtime validation of field types and constraints
    - Automatic default values for optional fields
    - Clear error messages for invalid data
    - Rich field documentation
    
    Only the 'question' field is required at initialization.
    All other fields have sensible defaults and are populated during workflow execution.
    """
    
    # Configuration for Pydantic model behavior
    model_config = ConfigDict(
        # Allow extra fields for future extensibility
        extra='allow',
        # Validate on assignment to catch errors early
        validate_assignment=True,
        # Use enum values instead of enum objects
        use_enum_values=True,
        # Populate by field name (not alias)
        populate_by_name=True,
    )
    
    # ==================== Input ====================
    question: Annotated[
        str,
        Field(
            description="Original user question in natural language",
            min_length=1,
            examples=["Show me the top 5 artists", "What are the total sales by country?"]
        )
    ]
    
    # ==================== Routing ====================
    is_relevant: Annotated[
        bool,
        Field(
            default=False,
            description="Whether the question is relevant to the music store database. "
                       "Set by the intent router node."
        )
    ] = False
    
    # ==================== SQL Generation ====================
    sql_query: Annotated[
        str,
        Field(
            default="",
            description="Generated SQL query from the LLM. "
                       "Set by the SQL generator node."
        )
    ] = ""
    
    reasoning: Annotated[
        str,
        Field(
            default="",
            description="Chain-of-thought reasoning from the LLM explaining how it generated the SQL query. "
                       "Helps with debugging and transparency."
        )
    ] = ""
    
    # ==================== Validation ====================
    validation_passed: Annotated[
        bool,
        Field(
            default=False,
            description="Whether the SQL query passed all validation checks (safety, syntax, relevancy). "
                       "Set by the SQL validator node."
        )
    ] = False
    
    validation_error: Annotated[
        str,
        Field(
            default="",
            description="Error message from validation if it failed. "
                       "Empty string if validation passed."
        )
    ] = ""
    
    # ==================== Execution ====================
    query_result: Annotated[
        List[Dict[str, Any]],
        Field(
            default_factory=list,
            description="Results from executing the SQL query. "
                       "Each item is a dictionary representing a row with column names as keys."
        )
    ] = []
    
    error: Annotated[
        str,
        Field(
            default="",
            description="Error message if query execution failed. "
                       "Empty string if execution succeeded."
        )
    ] = ""
    
    # ==================== Reflection/Retry ====================
    retry_count: Annotated[
        int,
        Field(
            default=0,
            ge=0,  # Greater than or equal to 0
            description="Number of retry attempts for SQL generation. "
                       "Incremented by the reflector node on each retry."
        )
    ] = 0
    
    # ==================== Visualization ====================
    visualization_spec: Annotated[
        Optional[Dict[str, Any]],
        Field(
            default=None,
            description="Specification for data visualization (chart type, columns, etc.). "
                       "Set by the visualizer node. None if no visualization is recommended."
        )
    ] = None
    
    # ==================== Final Output ====================
    final_response: Annotated[
        str,
        Field(
            default="",
            description="Final formatted response to the user. "
                       "Set by the format response node or error handling nodes."
        )
    ] = ""
    
    # ==================== Validators ====================
    @field_validator('retry_count')
    @classmethod
    def validate_retry_count(cls, v: int) -> int:
        """Ensure retry count is non-negative."""
        if v < 0:
            raise ValueError("retry_count must be non-negative")
        return v
    
    @field_validator('query_result')
    @classmethod
    def validate_query_result(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure query_result is a list."""
        if not isinstance(v, list):
            raise ValueError("query_result must be a list")
        return v
    
    # ==================== Helper Methods ====================
    def has_error(self) -> bool:
        """Check if the state contains any error."""
        return bool(self.error or self.validation_error)
    
    def is_complete(self) -> bool:
        """Check if the workflow is complete (has final response)."""
        return bool(self.final_response)
    
    def get_error_message(self) -> str:
        """Get the current error message (validation or execution)."""
        return self.validation_error or self.error
    
    def reset_errors(self) -> None:
        """Clear all error fields (used before retry)."""
        self.error = ""
        self.validation_error = ""
