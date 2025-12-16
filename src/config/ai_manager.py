"""
Centralized AI Manager for multiple providers.
Supports Gemini, Nebius Token Factory, and other OpenAI-compatible providers.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers."""
    GEMINI = "gemini"
    NEBIUS = "nebius"
    OPENAI = "openai"


class AIManager:
    """
    Centralized manager for AI API calls across different providers.
    Provides a unified interface regardless of the underlying provider.
    """
    
    # Default configurations
    DEFAULT_PROVIDER = "gemini"
    DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
    DEFAULT_NEBIUS_MODEL = "zai-org/GLM-4.5"
    DEFAULT_OPENAI_MODEL = "gpt-4"
    
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
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize AI Manager.
        
        Args:
            provider: AI provider to use (gemini, nebius, openai). 
                     If None, reads from AI_PROVIDER env var or uses default.
            model: Model name to use. If None, reads from provider-specific env var.
        """
        # Determine provider
        self.provider_name = (
            provider or 
            os.getenv("AI_PROVIDER", self.DEFAULT_PROVIDER)
        ).lower()
        
        try:
            self.provider = AIProvider(self.provider_name)
        except ValueError:
            logger.warning(
                f"Unknown provider '{self.provider_name}', falling back to Gemini"
            )
            self.provider = AIProvider.GEMINI
            self.provider_name = "gemini"
        
        # Initialize provider-specific client
        if self.provider == AIProvider.GEMINI:
            self._init_gemini(model)
        elif self.provider == AIProvider.NEBIUS:
            self._init_nebius(model)
        elif self.provider == AIProvider.OPENAI:
            self._init_openai(model)
        
        logger.info(
            f"AIManager initialized with provider: {self.provider_name}, "
            f"model: {self.model_name}"
        )
    
    def _init_gemini(self, model: Optional[str] = None):
        """Initialize Gemini provider."""
        from google import genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found in environment variables. "
                "Please set it in your .env file."
            )
        
        self.model_name = (
            model or 
            os.getenv("GEMINI_MODEL", self.DEFAULT_GEMINI_MODEL)
        )
        
        self.client = genai.Client(api_key=api_key)
        self.provider_type = "gemini"
    
    def _init_nebius(self, model: Optional[str] = None):
        """Initialize Nebius Token Factory provider (OpenAI-compatible)."""
        from openai import OpenAI
        
        api_key = os.getenv("NEBIUS_API_KEY")
        if not api_key:
            raise ValueError(
                "NEBIUS_API_KEY not found in environment variables. "
                "Please set it in your .env file."
            )
        
        self.model_name = (
            model or 
            os.getenv("NEBIUS_MODEL", self.DEFAULT_NEBIUS_MODEL)
        )
        
        self.client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=api_key
        )
        self.provider_type = "openai_compatible"
    
    def _init_openai(self, model: Optional[str] = None):
        """Initialize OpenAI provider."""
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables. "
                "Please set it in your .env file."
            )
        
        self.model_name = (
            model or 
            os.getenv("OPENAI_MODEL", self.DEFAULT_OPENAI_MODEL)
        )
        
        self.client = OpenAI(api_key=api_key)
        self.provider_type = "openai_compatible"
    
    def generate_content(
        self,
        prompt: str,
        temperature: float = TEMPERATURE_LOW,
        max_tokens: int = MAX_OUTPUT_TOKENS_MEDIUM,
        response_format: Optional[str] = None,
        response_schema: Optional[Dict[str, Any]] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate content using the configured AI provider.
        
        Args:
            prompt: The prompt to send to the AI
            temperature: Temperature setting (0.0-1.0)
            max_tokens: Maximum output tokens
            response_format: Response format ("json" or None)
            response_schema: JSON schema for structured responses (Gemini format)
            system_prompt: Optional system prompt (for OpenAI-compatible providers)
        
        Returns:
            Generated text content
        """
        if self.provider_type == "gemini":
            return self._generate_gemini(
                prompt, temperature, max_tokens, 
                response_format, response_schema
            )
        else:  # openai_compatible
            return self._generate_openai_compatible(
                prompt, temperature, max_tokens,
                response_format, system_prompt
            )
    
    def _generate_gemini(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
        response_schema: Optional[Dict[str, Any]]
    ) -> str:
        """Generate content using Gemini API."""
        config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "top_p": 0.95,
        }
        
        # Add JSON schema if provided
        if response_schema:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = response_schema
        elif response_format == "json":
            config["response_mime_type"] = "application/json"
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )
        
        return response.text
    
    def _generate_openai_compatible(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[str],
        system_prompt: Optional[str]
    ) -> str:
        """Generate content using OpenAI-compatible API."""
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Add JSON mode if requested
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(**kwargs)
        
        return response.choices[0].message.content
    
    def get_base_config(
        self,
        temperature: float = TEMPERATURE_LOW,
        max_tokens: int = MAX_OUTPUT_TOKENS_MEDIUM
    ) -> Dict[str, Any]:
        """
        Get base configuration for AI calls.
        
        Args:
            temperature: Temperature setting (0.0-1.0)
            max_tokens: Maximum output tokens
        
        Returns:
            Configuration dictionary
        """
        return {
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    
    def get_json_config(
        self,
        schema: Optional[Dict[str, Any]] = None,
        temperature: float = TEMPERATURE_PRECISE,
        max_tokens: int = MAX_OUTPUT_TOKENS_MEDIUM
    ) -> Dict[str, Any]:
        """
        Get configuration for JSON schema-enforced responses.
        
        Args:
            schema: JSON schema dictionary (Gemini format)
            temperature: Temperature setting (default: 0.0 for precision)
            max_tokens: Maximum output tokens
        
        Returns:
            Configuration dictionary
        """
        config = self.get_base_config(temperature, max_tokens)
        config["response_format"] = "json"
        
        if schema and self.provider_type == "gemini":
            config["response_schema"] = schema
        
        return config
    
    @classmethod
    def validate_config(cls) -> bool:
        """
        Validate that required configuration is present.
        
        Returns:
            True if configuration is valid
        
        Raises:
            ValueError: If required configuration is missing
        """
        provider = os.getenv("AI_PROVIDER", cls.DEFAULT_PROVIDER).lower()
        
        if provider == "gemini":
            if not os.getenv("GEMINI_API_KEY"):
                raise ValueError(
                    "GEMINI_API_KEY not found in environment variables. "
                    "Please set it in your .env file."
                )
        elif provider == "nebius":
            if not os.getenv("NEBIUS_API_KEY"):
                raise ValueError(
                    "NEBIUS_API_KEY not found in environment variables. "
                    "Please set it in your .env file."
                )
        elif provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError(
                    "OPENAI_API_KEY not found in environment variables. "
                    "Please set it in your .env file."
                )
        
        return True
