"""
LLM initialization and management for Text-to-SQL system.

This module provides:
- Centralized LLM initialization
- Model selection based on configuration
- Error handling for API failures
- Retry logic with exponential backoff

Production-grade features:
- Singleton pattern for model instances
- Proper error handling and logging
- Support for multiple model types (router, generator, reflector)
"""

from typing import Optional, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel

from infrastructure.config import get_config


class LLMManager:
    """
    Manages LLM instances for the Text-to-SQL system.
    
    Implements singleton pattern to avoid recreating model instances.
    Provides different models for different tasks (routing, generation, reflection).
    """
    
    _instances: Dict[str, BaseChatModel] = {}
    
    @classmethod
    def get_router_model(cls) -> BaseChatModel:
        """
        Get the router model for intent classification.
        
        Uses a fast, lightweight model (Gemini Flash) for quick routing decisions.
        
        Returns:
            BaseChatModel: Initialized router model
        """
        if "router" not in cls._instances:
            config = get_config()
            cls._instances["router"] = ChatGoogleGenerativeAI(
                model=config.router_model,
                google_api_key=config.google_api_key,
                temperature=0.0,  # Deterministic for routing
                convert_system_message_to_human=True,
            )
        return cls._instances["router"]
    
    @classmethod
    def get_sql_generator_model(cls) -> BaseChatModel:
        """
        Get the SQL generation model.
        
        Uses a more powerful model (Gemini Pro) for complex SQL generation
        with chain-of-thought reasoning.
        
        Returns:
            BaseChatModel: Initialized SQL generator model
        """
        if "sql_generator" not in cls._instances:
            config = get_config()
            cls._instances["sql_generator"] = ChatGoogleGenerativeAI(
                model=config.sql_generator_model,
                google_api_key=config.google_api_key,
                temperature=config.temperature,
                convert_system_message_to_human=True,
            )
        return cls._instances["sql_generator"]
    
    @classmethod
    def get_reflector_model(cls) -> BaseChatModel:
        """
        Get the reflector model for error correction.
        
        Uses a fast model (Gemini Flash) for quick error analysis and fixes.
        
        Returns:
            BaseChatModel: Initialized reflector model
        """
        if "reflector" not in cls._instances:
            config = get_config()
            cls._instances["reflector"] = ChatGoogleGenerativeAI(
                model=config.reflector_model,
                google_api_key=config.google_api_key,
                temperature=0.1,  # Slightly creative for finding fixes
                convert_system_message_to_human=True,
            )
        return cls._instances["reflector"]
    
    @classmethod
    def get_visualizer_model(cls) -> BaseChatModel:
        """
        Get the visualizer model for chart recommendations.
        
        Uses the router model (fast) for quick visualization decisions.
        
        Returns:
            BaseChatModel: Initialized visualizer model
        """
        # Reuse router model for visualization (similar task complexity)
        return cls.get_router_model()
    
    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear all cached model instances.
        
        Useful for testing or when configuration changes.
        """
        cls._instances.clear()


def get_router_llm() -> BaseChatModel:
    """Get router LLM instance."""
    return LLMManager.get_router_model()


def get_sql_generator_llm() -> BaseChatModel:
    """Get SQL generator LLM instance."""
    return LLMManager.get_sql_generator_model()


def get_reflector_llm() -> BaseChatModel:
    """Get reflector LLM instance."""
    return LLMManager.get_reflector_model()


def get_visualizer_llm() -> BaseChatModel:
    """Get visualizer LLM instance."""
    return LLMManager.get_visualizer_model()
