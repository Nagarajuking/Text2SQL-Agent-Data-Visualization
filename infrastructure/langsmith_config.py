# infrastructure/langsmith_config.py
"""
LangSmith configuration for observability and tracing.

This module configures LangSmith for:
- Request tracing
- LLM call monitoring
- Performance metrics
- Error tracking
- Cost analysis

Production-grade features:
- Automatic trace capture
- Metadata enrichment
- Error logging
- Performance monitoring
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def setup_langsmith(
    project_name: str = "text2sql-agent",
    enabled: bool = True
) -> bool:
    """
    Configure LangSmith tracing.
    
    Args:
        project_name: Name of the LangSmith project
        enabled: Whether to enable LangSmith tracing
    
    Returns:
        bool: True if LangSmith is configured, False otherwise
    """
    # Check if LangSmith API key is available
    langsmith_api_key = os.getenv("LANGSMITH_API_KEY", "")
    
    if not langsmith_api_key or not enabled:
        print("[INFO] LangSmith tracing disabled (no API key or disabled in config)")
        return False
    
    # Configure LangSmith environment variables
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = project_name
    os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    
    print(f"[INFO] LangSmith tracing enabled for project: {project_name}")
    print(f"[INFO] View traces at: https://smith.langchain.com/o/default/projects/p/{project_name}")
    
    return True


def get_langsmith_config() -> dict:
    """
    Get current LangSmith configuration.
    
    Returns:
        dict: Configuration status
    """
    return {
        "enabled": os.getenv("LANGCHAIN_TRACING_V2") == "true",
        "project": os.getenv("LANGCHAIN_PROJECT", ""),
        "endpoint": os.getenv("LANGCHAIN_ENDPOINT", ""),
        "has_api_key": bool(os.getenv("LANGSMITH_API_KEY"))
    }
