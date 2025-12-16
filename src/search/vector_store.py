"""
Vector Store implementation using LlamaIndex and Chroma for semantic code search.
"""

import os
import logging
from typing import List, Dict, Optional
from pathlib import Path

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, Document
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb
import warnings

from .embeddings import get_embedding_model
from src.config import AIManager

# Suppress deprecation warnings
warnings.filterwarnings('ignore', category=DeprecationWarning, module='llama_index.llms.gemini')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='llama_index.embeddings.gemini')

logger = logging.getLogger(__name__)


class CodeSearchEngine:
    """
    Semantic code search engine using LlamaIndex + Chroma vector store.
    Enables finding similar legacy patterns across large codebases.
    """
    
    def __init__(self, persist_dir: Optional[str] = None, use_modal: bool = True):
        """
        Initialize the code search engine.
        
        Args:
            persist_dir: Optional directory to persist Chroma database
            use_modal: If True, use Modal embedding as primary (default: True)
        """
        self.persist_dir = persist_dir
        self.index: Optional[VectorStoreIndex] = None
        self.chroma_client = None
        self.chroma_collection = None
        self.use_modal = use_modal
        
        # Configure embeddings (Modal primary, Gemini fallback)
        try:
            Settings.embed_model = get_embedding_model(prefer_modal=use_modal)
        except Exception as e:
            logger.warning(f"Failed to initialize preferred embedding, using Gemini: {e}")
            Settings.embed_model = get_embedding_model(force_gemini=True)
            self.use_modal = False
        
        # Configure LLM using centralized AIManager
        self.ai_manager = AIManager()
        
        # Set up LlamaIndex LLM based on provider
        if self.ai_manager.provider_name == "gemini":
            from llama_index.llms.gemini import Gemini
            Settings.llm = Gemini(
                model=self.ai_manager.model_name,
                api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.1
            )
        elif self.ai_manager.provider_name in ["nebius", "openai"]:
            from llama_index.llms.openai import OpenAI
            if self.ai_manager.provider_name == "nebius":
                # Use gpt-3.5-turbo as placeholder to pass LlamaIndex validation
                # The actual model is passed via additional_kwargs
                Settings.llm = OpenAI(
                    model="gpt-3.5-turbo",
                    api_key=os.getenv("NEBIUS_API_KEY"),
                    api_base="https://api.tokenfactory.nebius.com/v1/",
                    temperature=0.1,
                    additional_kwargs={"model": self.ai_manager.model_name}
                )
            else:
                Settings.llm = OpenAI(
                    model=self.ai_manager.model_name,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    temperature=0.1
                )
        
        embedding_type = "Modal (primary)" if self.use_modal else "Gemini (fallback)"
        logger.info(f"CodeSearchEngine initialized with {embedding_type} embeddings and {self.ai_manager.provider_name} LLM")
    
    def build_index(self, repo_path: str, file_extensions: Optional[List[str]] = None) -> VectorStoreIndex:
        """
        Build searchable index of codebase.
        
        Args:
            repo_path: Path to repository to index
            file_extensions: Optional list of file extensions to include (e.g., ['.py', '.java'])
        
        Returns:
            VectorStoreIndex for querying
        """
        logger.info(f"Building code index for: {repo_path}")
        
        # Initialize Chroma client
        if self.persist_dir:
            self.chroma_client = chromadb.PersistentClient(path=self.persist_dir)
        else:
            self.chroma_client = chromadb.EphemeralClient()
        
        # Create or get collection
        collection_name = "code_embeddings"
        try:
            self.chroma_collection = self.chroma_client.get_or_create_collection(collection_name)
        except Exception as e:
            logger.warning(f"Error with collection, creating new: {e}")
            self.chroma_collection = self.chroma_client.create_collection(collection_name)
        
        vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        
        # Load documents from repository
        documents = self._load_code_files(repo_path, file_extensions)
        
        if not documents:
            logger.warning(f"No code files found in {repo_path}")
            return None
        
        logger.info(f"Loaded {len(documents)} code files")
        
        # Build index (using default text splitter instead of CodeSplitter to avoid tree-sitter dependency)
        try:
            self.index = VectorStoreIndex.from_documents(
                documents,
                vector_store=vector_store,
                show_progress=True
            )
            logger.info("Code index built successfully")
        except Exception as e:
            if self.use_modal:
                logger.warning(f"Modal embedding failed during indexing: {e}")
                logger.info("Retrying with Gemini embeddings...")
                
                # Switch to Gemini
                Settings.embed_model = get_embedding_model(force_gemini=True)
                self.use_modal = False
                
                # Retry building index
                self.index = VectorStoreIndex.from_documents(
                    documents,
                    vector_store=vector_store,
                    show_progress=True
                )
                logger.info("Code index built successfully with Gemini embeddings")
            else:
                raise
        
        return self.index
    
    def _load_code_files(self, repo_path: str, file_extensions: Optional[List[str]] = None) -> List[Document]:
        """
        Load code files from repository.
        
        Args:
            repo_path: Path to repository
            file_extensions: Optional list of extensions to include
        
        Returns:
            List of Document objects
        """
        documents = []
        repo_path = Path(repo_path)
        
        # Default extensions if not specified
        if file_extensions is None:
            file_extensions = [
                # Python
                '.py', '.pyw', '.pyx',
                # Java
                '.java',
                # JavaScript/TypeScript
                '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
                # PHP
                '.php', '.php3', '.php4', '.php5', '.phtml',
                # Ruby
                '.rb', '.rbw',
                # Go
                '.go',
                # C/C++
                '.c', '.cpp', '.cc', '.cxx', '.c++', '.h', '.hpp', '.hh', '.hxx', '.h++',
                # C#
                '.cs',
                # Rust
                '.rs',
                # Kotlin
                '.kt', '.kts',
                # Swift
                '.swift',
                # Scala
                '.scala', '.sc',
                # R
                '.r', '.R',
                # Perl
                '.pl', '.pm', '.t', '.pod',
                # Shell
                '.sh', '.bash', '.zsh', '.fish'
            ]
        
        # Walk through directory
        for file_path in repo_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in file_extensions:
                try:
                    # Skip hidden files and common non-code directories
                    if any(part.startswith('.') for part in file_path.parts):
                        continue
                    if any(part in ['node_modules', 'venv', '__pycache__', 'build', 'dist'] 
                           for part in file_path.parts):
                        continue
                    
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Create document with metadata
                    doc = Document(
                        text=content,
                        metadata={
                            'file_path': str(file_path.relative_to(repo_path)),
                            'file_name': file_path.name,
                            'extension': file_path.suffix,
                            'size': len(content)
                        }
                    )
                    documents.append(doc)
                    
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {e}")
        
        return documents
    
    def find_similar_patterns(self, pattern_query: str, top_k: int = 20) -> List[Dict]:
        """
        Find files with similar legacy patterns.
        
        Args:
            pattern_query: Natural language query describing the pattern
            top_k: Number of results to return
        
        Returns:
            List of dictionaries with file paths and relevance scores
        """
        if not self.index:
            raise ValueError("Index not built. Call build_index() first.")
        
        logger.info(f"Searching for pattern: {pattern_query}")
        
        # Create query engine
        query_engine = self.index.as_query_engine(
            similarity_top_k=top_k,
            response_mode="tree_summarize"
        )
        
        # Execute query
        response = query_engine.query(pattern_query)
        
        # Extract source files and scores
        results = []
        for node in response.source_nodes:
            results.append({
                'file_path': node.metadata.get('file_path', 'unknown'),
                'file_name': node.metadata.get('file_name', 'unknown'),
                'score': node.score,
                'text_snippet': node.text[:200] + '...' if len(node.text) > 200 else node.text
            })
        
        logger.info(f"Found {len(results)} matching files")
        return results
    
    def analyze_pattern_with_context(self, pattern_query: str, files: List[str]) -> str:
        """
        Deep analysis of legacy pattern with full context retrieval.
        
        Args:
            pattern_query: Description of the pattern to analyze
            files: List of file paths to analyze
        
        Returns:
            Analysis result from Gemini
        """
        if not self.index:
            raise ValueError("Index not built. Call build_index() first.")
        
        logger.info(f"Analyzing pattern with context: {pattern_query}")
        
        # Build enhanced query with file context
        enhanced_query = f"""
        Analyze the following legacy code pattern and provide:
        1. What the code currently does
        2. Why it's problematic (security, performance, maintainability)
        3. Modern equivalent (recommended library/pattern)
        4. Migration steps with risk assessment
        
        Pattern to analyze: {pattern_query}
        Files to focus on: {', '.join(files)}
        
        Provide detailed analysis in JSON format with keys:
        - analysis: Overall analysis
        - issues: List of specific issues
        - recommendation: Recommended modern approach
        - steps: Migration steps
        - risks: Risk assessment
        """
        
        # Create query engine with custom prompt
        query_engine = self.index.as_query_engine(
            similarity_top_k=10,
            response_mode="compact"
        )
        
        # Execute analysis
        response = query_engine.query(enhanced_query)
        
        return response.response
    
    def get_transformation_examples(self, pattern_type: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve examples of successful transformations for a pattern type.
        
        Args:
            pattern_type: Type of pattern (e.g., "MySQLdb to SQLAlchemy")
            top_k: Number of examples to retrieve
        
        Returns:
            List of example transformations
        """
        if not self.index:
            raise ValueError("Index not built. Call build_index() first.")
        
        query = f"Find examples of code that was successfully transformed from {pattern_type}"
        
        query_engine = self.index.as_query_engine(
            similarity_top_k=top_k,
            response_mode="compact"
        )
        
        response = query_engine.query(query)
        
        # Extract examples from source nodes
        examples = []
        for node in response.source_nodes:
            examples.append({
                'file_path': node.metadata.get('file_path', 'unknown'),
                'code_snippet': node.text,
                'score': node.score
            })
        
        return examples
