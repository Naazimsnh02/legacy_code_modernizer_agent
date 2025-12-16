"""File handling utilities for repository processing."""

import zipfile
import os
from pathlib import Path
from typing import List, Set
import shutil


class FileHandler:
    """Handles file extraction and code file discovery."""
    
    # Supported code file extensions
    CODE_EXTENSIONS: Set[str] = {
        '.py', '.java', '.js', '.ts', '.jsx', '.tsx',
        '.php', '.rb', '.go', '.rs', '.cpp', '.c', '.h',
        '.cs', '.swift', '.kt', '.scala', '.pl', '.r'
    }
    
    # Files/directories to exclude
    EXCLUDE_PATTERNS: Set[str] = {
        '__pycache__', '.git', '.svn', 'node_modules',
        'venv', 'env', '.venv', 'dist', 'build',
        '.idea', '.vscode', '.pytest_cache', '.mypy_cache'
    }
    
    def __init__(self, upload_dir: str = "./uploads"):
        """
        Initialize file handler.
        
        Args:
            upload_dir: Directory to store uploaded and extracted files
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True, parents=True)
        
    def extract_repo(self, zip_path: str) -> str:
        """
        Extract uploaded repository ZIP file.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            Path to extracted directory
            
        Raises:
            ValueError: If file is not a valid ZIP
        """
        if not zipfile.is_zipfile(zip_path):
            raise ValueError(f"File {zip_path} is not a valid ZIP file")
        
        # Create unique extraction directory
        extract_path = self.upload_dir / "extracted"
        
        # Clean up previous extraction
        if extract_path.exists():
            shutil.rmtree(extract_path)
        
        extract_path.mkdir(exist_ok=True, parents=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            return str(extract_path)
            
        except Exception as e:
            raise ValueError(f"Error extracting ZIP file: {e}")
    
    def list_code_files(self, repo_path: str) -> List[str]:
        """
        List all code files in repository.
        
        Args:
            repo_path: Path to repository directory
            
        Returns:
            List of relative file paths
        """
        code_files = []
        repo_path = Path(repo_path)
        
        for root, dirs, files in os.walk(repo_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_PATTERNS]
            
            for filename in files:
                file_path = Path(root) / filename
                
                # Check if it's a code file
                if file_path.suffix in self.CODE_EXTENSIONS:
                    # Get relative path
                    rel_path = file_path.relative_to(repo_path)
                    code_files.append(str(rel_path))
        
        return sorted(code_files)
    
    def read_file(self, file_path: str, max_size: int = 1024 * 1024) -> str:
        """
        Read file contents safely.
        
        Args:
            file_path: Path to file
            max_size: Maximum file size in bytes (default 1MB)
            
        Returns:
            File contents as string
            
        Raises:
            ValueError: If file is too large or cannot be read
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ValueError(f"File {file_path} does not exist")
        
        file_size = file_path.stat().st_size
        if file_size > max_size:
            raise ValueError(
                f"File {file_path} is too large ({file_size} bytes). "
                f"Maximum size is {max_size} bytes."
            )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                raise ValueError(f"Cannot read file {file_path}: {e}")
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Get information about a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file information
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"exists": False}
        
        stat = file_path.stat()
        
        return {
            "exists": True,
            "name": file_path.name,
            "extension": file_path.suffix,
            "size_bytes": stat.st_size,
            "size_kb": round(stat.st_size / 1024, 2),
            "is_code": file_path.suffix in self.CODE_EXTENSIONS
        }
    
    def cleanup(self):
        """Clean up temporary files and directories."""
        if self.upload_dir.exists():
            shutil.rmtree(self.upload_dir)
            self.upload_dir.mkdir(exist_ok=True, parents=True)
