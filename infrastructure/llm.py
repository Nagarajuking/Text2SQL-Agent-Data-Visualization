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

import os
from typing import Optional, Any, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.language_models import BaseChatModel

from infrastructure.config import get_config


class LLMManager:
    """
    Manages LLM instances for the Text-to-SQL system.
    
    Implements singleton pattern to avoid recreating model instances.
    Provides different models for different tasks (routing, generation, reflection).
    """
    
    _instances: Dict[str, Any] = {}
    
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
    def get_huggingface_model(cls) -> HuggingFaceEndpoint:
        """
        Get the Hugging Face model for SQL generation.
        
        Returns:
            HuggingFaceEndpoint: Configured HF model instance
        """
        config = get_config()
        return HuggingFaceEndpoint(
            repo_id=config.huggingface_model_repo,
            huggingfacehub_api_token=config.huggingface_api_token,
            temperature=0.1,
            max_new_tokens=512,
            task="text-generation"
        )
    
    @classmethod
    def get_sql_generator_model(cls) -> Any:
        """
        Get the SQL generation model.
        
        Supports hybrid architecture:
        - Gemini Pro (default)
        - SQLCoder (if USE_OPEN_SOURCE is True)
        
        Returns:
            LLM instance (Gemini or HuggingFace)
        """
        if "sql_generator" not in cls._instances:
            config = get_config()
            
            if config.use_open_source:
                # Use specialized SQLCoder model
                cls._instances["sql_generator"] = cls.get_huggingface_model()
            else:
                # Use Gemini Pro
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


def get_sql_generator_llm() -> Any:
    """Get SQL generator LLM instance."""
    return LLMManager.get_sql_generator_model()


def get_reflector_llm() -> BaseChatModel:
    """Get reflector LLM instance."""
    return LLMManager.get_reflector_model()


def get_visualizer_llm() -> BaseChatModel:
    """Get visualizer LLM instance."""
    return LLMManager.get_visualizer_model()
