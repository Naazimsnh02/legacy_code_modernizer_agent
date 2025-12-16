"""
Custom embedding implementations for Modal and Gemini.
"""

import os
import logging
from typing import List, Optional
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.bridge.pydantic import PrivateAttr

logger = logging.getLogger(__name__)

# Global tokenizer instance (lazy loaded)
_tokenizer = None

def get_tokenizer():
    """Get or create the tokenizer for BAAI/bge-base-en-v1.5."""
    global _tokenizer
    if _tokenizer is None:
        try:
            from transformers import AutoTokenizer
            _tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-base-en-v1.5")
            logger.info("Tokenizer loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load tokenizer: {e}. Falling back to word-based truncation.")
            _tokenizer = False  # Mark as failed
    return _tokenizer if _tokenizer else None


class ModalEmbedding(BaseEmbedding):
    """
    Custom embedding class that uses Modal's deployed TEI service.
    Primary embedding model for the application.
    """
    
    _modal_instance: Optional[object] = PrivateAttr(default=None)
    _model_name: str = PrivateAttr(default="BAAI/bge-base-en-v1.5")
    _max_text_length: int = PrivateAttr(default=4000)  # Reduced max chars per text
    _batch_size: int = PrivateAttr(default=2)  # Very small batches to avoid 413
    
    def __init__(self, **kwargs):
        """Initialize Modal embedding client."""
        super().__init__(**kwargs)
        try:
            import modal
            # Use modal.Cls.from_name and get an instance
            TextEmbeddingsInference = modal.Cls.from_name(
                "text-embeddings-inference-api", 
                "TextEmbeddingsInference"
            )
            # Create an instance and store it
            self._modal_instance = TextEmbeddingsInference()
            logger.info("ModalEmbedding initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Modal embedding: {e}")
            raise
    
    def _truncate_text(self, text: str) -> str:
        """Truncate text to max token limit using proper tokenization."""
        # Modal TEI has a hard limit of 512 tokens
        # Use 500 tokens to be safe (leave some buffer)
        max_tokens = 500
        
        tokenizer = get_tokenizer()
        
        if tokenizer:
            # Use proper tokenization
            try:
                tokens = tokenizer.encode(text, add_special_tokens=False)
                if len(tokens) > max_tokens:
                    # Truncate to max_tokens
                    truncated_tokens = tokens[:max_tokens]
                    # Decode back to text
                    return tokenizer.decode(truncated_tokens, skip_special_tokens=True)
                return text
            except Exception as e:
                logger.warning(f"Tokenization failed: {e}. Using word-based fallback.")
        
        # Fallback: word-based truncation (conservative estimate)
        # Assume 1.3 tokens per word: 500 tokens ≈ 385 words
        # Use 250 words to be very conservative
        words = text.split()
        if len(words) > 250:
            truncated_words = words[:250]
            return ' '.join(truncated_words)
        return text
    
    @classmethod
    def class_name(cls) -> str:
        return "ModalEmbedding"
    
    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Get query embedding asynchronously."""
        return await self._aget_text_embedding(query)
    
    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Get text embedding asynchronously."""
        try:
            text = self._truncate_text(text)
            embeddings = await self._modal_instance.embed.remote.aio([text])
            return embeddings[0]
        except Exception as e:
            logger.error(f"Error getting embedding from Modal: {e}")
            raise
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Get query embedding synchronously."""
        return self._get_text_embedding(query)
    
    def _get_text_embedding(self, text: str) -> List[float]:
        """Get text embedding synchronously."""
        try:
            text = self._truncate_text(text)
            embeddings = self._modal_instance.embed.remote([text])
            return embeddings[0]
        except Exception as e:
            logger.error(f"Error getting embedding from Modal: {e}")
            # If Modal fails due to size limits, try to fall back to Gemini for this request
            if "413" in str(e) or "Payload Too Large" in str(e) or "Input validation error" in str(e):
                logger.warning("Modal embedding failed due to size limits, attempting Gemini fallback for this request")
                try:
                    gemini_wrapper = GeminiEmbeddingWrapper()
                    return gemini_wrapper._get_text_embedding(text)
                except Exception as gemini_e:
                    logger.error(f"Gemini fallback also failed: {gemini_e}")
                    raise e
            raise
    
    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts with batching."""
        # Truncate all texts
        texts = [self._truncate_text(t) for t in texts]
        
        # Process in smaller batches to avoid payload size issues
        all_embeddings = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i:i + self._batch_size]
            try:
                batch_embeddings = self._modal_instance.embed.remote(batch)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Error getting embeddings from Modal for batch {i//self._batch_size + 1}: {e}")
                raise
        
        return all_embeddings
    
    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts asynchronously with batching."""
        # Truncate all texts
        texts = [self._truncate_text(t) for t in texts]
        
        # Process in smaller batches to avoid payload size issues
        all_embeddings = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i:i + self._batch_size]
            try:
                batch_embeddings = await self._modal_instance.embed.remote.aio(batch)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Error getting embeddings from Modal for batch {i//self._batch_size + 1}: {e}")
                raise


class NebiusEmbeddingWrapper(BaseEmbedding):
    """
    Wrapper for Nebius embeddings using OpenAI-compatible API.
    Uses Qwen/Qwen3-Embedding-8B model (4096 dimensions).
    """
    
    _client: Optional[object] = PrivateAttr(default=None)
    _model_name: str = PrivateAttr(default="Qwen/Qwen3-Embedding-8B")
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "Qwen/Qwen3-Embedding-8B", **kwargs):
        """Initialize Nebius embedding client."""
        super().__init__(**kwargs)
        
        # Get API key from environment if not provided
        if not api_key:
            api_key = os.getenv("NEBIUS_API_KEY")
        
        if not api_key:
            raise ValueError("NEBIUS_API_KEY not found")
        
        try:
            from openai import OpenAI
            self._client = OpenAI(
                base_url="https://api.tokenfactory.nebius.com/v1/",
                api_key=api_key
            )
            self._model_name = model_name
            logger.info(f"NebiusEmbeddingWrapper initialized with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Nebius embedding: {e}")
            raise
    
    @classmethod
    def class_name(cls) -> str:
        return "NebiusEmbeddingWrapper"
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Get query embedding."""
        return self._get_text_embedding(query)
    
    def _get_text_embedding(self, text: str) -> List[float]:
        """Get text embedding."""
        try:
            response = self._client.embeddings.create(
                model=self._model_name,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embedding from Nebius: {e}")
            raise
    
    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        try:
            response = self._client.embeddings.create(
                model=self._model_name,
                input=texts
            )
            # Sort by index to ensure correct order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            logger.error(f"Error getting batch embeddings from Nebius: {e}")
            raise
    
    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Get query embedding asynchronously."""
        return self._get_query_embedding(query)
    
    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Get text embedding asynchronously."""
        return self._get_text_embedding(text)


class GeminiEmbeddingWrapper(BaseEmbedding):
    """
    Wrapper for Gemini embeddings using the new google-genai SDK.
    Fallback embedding model.
    """
    
    _client: Optional[object] = PrivateAttr(default=None)
    _model_name: str = PrivateAttr(default="models/gemini-embedding-001")
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "models/gemini-embedding-001", **kwargs):
        """Initialize Gemini embedding client."""
        super().__init__(**kwargs)
        
        # Use centralized config if no API key provided
        if not api_key:
            try:
                from src.config import GeminiConfig
                api_key = GeminiConfig.get_api_key()
            except Exception:
                # Fallback to environment variable
                api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            self._model_name = model_name
            logger.info(f"GeminiEmbeddingWrapper initialized with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini embedding: {e}")
            raise
    
    @classmethod
    def class_name(cls) -> str:
        return "GeminiEmbeddingWrapper"
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Get query embedding."""
        return self._get_text_embedding(query)
    
    def _get_text_embedding(self, text: str) -> List[float]:
        """Get text embedding."""
        try:
            result = self._client.models.embed_content(
                model=self._model_name,
                contents=text
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error(f"Error getting embedding from Gemini: {e}")
            raise
    
    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embeddings.append(self._get_text_embedding(text))
        return embeddings
    
    async def _aget_query_embedding(self, query: str) -> List[float]:
        """Get query embedding asynchronously."""
        return self._get_query_embedding(query)
    
    async def _aget_text_embedding(self, text: str) -> List[float]:
        """Get text embedding asynchronously."""
        return self._get_text_embedding(text)


def get_embedding_model(prefer_modal: bool = True, force_gemini: bool = False) -> BaseEmbedding:
    """
    Get the best available embedding model.
    
    Priority order:
    1. Modal (if prefer_modal=True and available)
    2. Provider-specific embedding (Nebius if AI_PROVIDER=nebius, Gemini otherwise)
    
    Args:
        prefer_modal: If True, try Modal first, then fallback to provider-specific
        force_gemini: If True, skip Modal and use Gemini directly
    
    Returns:
        BaseEmbedding instance
    """
    if force_gemini:
        logger.info("Using Gemini embedding (forced)")
        return GeminiEmbeddingWrapper()
    
    if prefer_modal:
        try:
            logger.info("Attempting to use Modal embedding (primary)")
            return ModalEmbedding()
        except Exception as e:
            logger.warning(f"Modal embedding unavailable, falling back to provider-specific: {e}")
    
    # Determine which provider-specific embedding to use
    ai_provider = os.getenv("AI_PROVIDER", "gemini").lower()
    
    if ai_provider == "nebius":
        try:
            logger.info("Using Nebius embedding (Qwen/Qwen3-Embedding-8B)")
            return NebiusEmbeddingWrapper()
        except Exception as e:
            logger.warning(f"Nebius embedding unavailable, falling back to Gemini: {e}")
    
    try:
        logger.info("Using Gemini embedding (fallback)")
        return GeminiEmbeddingWrapper()
    except Exception as e:
        logger.error(f"Failed to initialize any embedding model: {e}")
        raise
