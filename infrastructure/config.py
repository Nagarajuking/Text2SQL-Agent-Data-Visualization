"""
Configuration management for Text-to-SQL system.

This module handles:
- Environment variable loading
- Model configuration
- Application settings
- Validation of required configurations

Production-grade features:
- Type-safe configuration using Pydantic
- Comprehensive validation
- Clear error messages for missing configuration
"""

import os
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class Config(BaseModel):
    """
    Application configuration with validation.
    
    All configuration values are loaded from environment variables
    with sensible defaults where appropriate.
    """
    
    # API Configuration
    google_api_key: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""),
        description="Google Gemini API key"
    )
    
    # Model Configuration
    router_model: str = Field(
        default_factory=lambda: os.getenv("ROUTER_MODEL", "gemini-2.0-flash-exp"),
        description="Model for intent routing and fast operations"
    )
    
    sql_generator_model: str = Field(
        default_factory=lambda: os.getenv("SQL_GENERATOR_MODEL", "gemini-1.5-pro"),
        description="Model for SQL generation (requires strong reasoning)"
    )
    
    reflector_model: str = Field(
        default_factory=lambda: os.getenv("REFLECTOR_MODEL", "gemini-2.0-flash-exp"),
        description="Model for error correction and reflection"
    )
    
    use_open_source: bool = Field(
        default_factory=lambda: os.getenv("USE_OPEN_SOURCE", "False").lower() == "true",
        description="Whether to use open-source models instead of Gemini"
    )
    
    # Database Configuration
    database_path: Path = Field(
        default_factory=lambda: Path(os.getenv("DATABASE_PATH", "chinook.db")),
        description="Path to SQLite database file"
    )
    
    # Application Settings
    max_retry_count: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RETRY_COUNT", "3")),
        description="Maximum number of retry attempts for SQL generation",
        ge=1,
        le=5
    )
    
    max_result_rows: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RESULT_ROWS", "50")),
        description="Maximum number of rows to return from queries",
        ge=1,
        le=1000
    )
    
    # LLM Settings
    temperature: float = Field(
        default=0.0,
        description="Temperature for LLM generation (0 for deterministic)",
        ge=0.0,
        le=1.0
    )
    
    @field_validator("google_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that API key is provided when not using open-source models."""
        if not v or v == "your_api_key_here":
            # Check if we're using open-source models
            use_open_source = os.getenv("USE_OPEN_SOURCE", "False").lower() == "true"
            if not use_open_source:
                raise ValueError(
                    "GOOGLE_API_KEY is required. Please set it in your .env file. "
                    "Get your API key from: https://makersuite.google.com/app/apikey"
                )
        return v
    
    @field_validator("database_path")
    @classmethod
    def validate_database_path(cls, v: Path) -> Path:
        """Validate that database file exists."""
        if not v.exists():
            raise ValueError(
                f"Database file not found: {v}. "
                f"Please ensure chinook.db is in the correct location."
            )
        return v
    
    class Config:
        """Pydantic configuration."""
        frozen = True  # Make configuration immutable
        validate_assignment = True


# Global configuration instance
# This is initialized once and reused throughout the application
try:
    config = Config()
except Exception as e:
    # Provide helpful error message if configuration fails
    print(f"[ERROR] Configuration Error: {e}")
    print("\n[INFO] Quick Fix:")
    print("1. Copy .env.example to .env")
    print("2. Add your GOOGLE_API_KEY to the .env file")
    print("3. Ensure chinook.db is in the project directory")
    raise


def get_config() -> Config:
    """
    Get the global configuration instance.
    
    Returns:
        Config: Validated configuration object
    """
    return config
