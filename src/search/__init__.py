"""
Search module for semantic code search using LlamaIndex and Chroma.
"""

from .vector_store import CodeSearchEngine
from .embeddings import ModalEmbedding, GeminiEmbeddingWrapper, get_embedding_model

__all__ = ['CodeSearchEngine', 'ModalEmbedding', 'GeminiEmbeddingWrapper', 'get_embedding_model']
