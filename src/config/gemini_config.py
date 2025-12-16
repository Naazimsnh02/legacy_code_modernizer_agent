"""
Centralized Gemini API configuration.
Allows users to configure model settings from .env file.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class GeminiConfig:
    """Centralized configuration for Gemini API."""
    
    # Default model - can be overridden in .env
    DEFAULT_MODEL = "gemini-2.5-flash"
    
    # Model configuration from environment
    MODEL_NAME: str = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Temperature settings for different use cases
    TEMPERATURE_PRECISE = 0.0  # For JSON schema responses
    TEMPERATURE_LOW = 0.1      # For code generation
    TEMPERATURE_MEDIUM = 0.2   # For transformations
    TEMPERATURE_HIGH = 0.7     # For creative tasks
    
    # Token limits
    MAX_OUTPUT_TOKENS_SMALL = 8192
    MAX_OUTPUT_TOKENS_MEDIUM = 16384
    MAX_OUTPUT_TOKENS_LARGE = 32768
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        if not cls.API_KEY:
            raise ValueError(
                "GEMINI_API_KEY not found in environment variables. "
                "Please set it in your .env file."
            )
        return True
    
    @classmethod
    def get_model_name(cls) -> str:
        """Get the configured model name."""
        return cls.MODEL_NAME
    
    @classmethod
    def get_api_key(cls) -> str:
        """Get the API key."""
        cls.validate()
        return cls.API_KEY
    
    @classmethod
    def get_base_config(cls, temperature: float = TEMPERATURE_LOW, 
                       max_tokens: int = MAX_OUTPUT_TOKENS_MEDIUM) -> dict:
        """
        Get base configuration for Gemini API calls.
        
        Args:
            temperature: Temperature setting (0.0-1.0)
            max_tokens: Maximum output tokens
            
        Returns:
            Configuration dictionary
        """
        return {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "top_p": 0.95,
        }
    
    @classmethod
    def get_json_config(cls, schema: dict, 
                       temperature: float = TEMPERATURE_PRECISE,
                       max_tokens: int = MAX_OUTPUT_TOKENS_MEDIUM) -> dict:
        """
        Get configuration for JSON schema-enforced responses.
        
        Args:
            schema: JSON schema dictionary
            temperature: Temperature setting (default: 0.0 for precision)
            max_tokens: Maximum output tokens
            
        Returns:
            Configuration dictionary with schema enforcement
        """
        config = cls.get_base_config(temperature, max_tokens)
        config.update({
            "response_mime_type": "application/json",
            "response_schema": schema
        })
        return config
