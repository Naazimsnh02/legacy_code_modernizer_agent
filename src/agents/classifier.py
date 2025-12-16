"""Code classification using AI."""

import json
from typing import Dict, List
import os
from dotenv import load_dotenv

from src.config import AIManager, GeminiSchemas

load_dotenv()


class CodeClassifier:
    """Classifies code files into modernization categories using Gemini."""
    
    def __init__(self):
        """Initialize the classifier with AI client."""
        # Use centralized AI manager
        self.ai_manager = AIManager()
        
    def classify_files(self, file_list: List[str], batch_size: int = 25) -> Dict[str, str]:
        """
        Classify files using Gemini with few-shot prompting.
        
        Args:
            file_list: List of file paths to classify
            batch_size: Number of files to process per API call
            
        Returns:
            Dictionary mapping filenames to categories
        """
        all_results = {}
        
        # Process in batches to avoid token limits
        for i in range(0, len(file_list), batch_size):
            batch = file_list[i:i + batch_size]
            batch_results = self._classify_batch(batch)
            all_results.update(batch_results)
        
        return all_results
    
    def _classify_batch(self, file_list: List[str]) -> Dict[str, str]:
        """Classify a batch of files."""
        
        prompt = f"""You are a code modernization expert. Classify these files into categories.

CATEGORIES:
- modernize_high: Legacy patterns that need immediate update (Python 2, deprecated libs, security issues)
- modernize_low: Minor improvements needed (add type hints, optimize imports)
- skip: Already modern or non-code files

FEW-SHOT EXAMPLES:
1. utils/db.py (uses MySQLdb, string interpolation) → modernize_high
2. config.py (hardcoded credentials) → modernize_high
3. models/user.py (missing type hints) → modernize_low
4. src/api/UserController.java (uses deprecated Vector, no generics) → modernize_high
5. frontend/app.js (uses jQuery 1.x, inline event handlers) → modernize_high
6. legacy_php/login.php (mysql_connect, no prepared statements) → modernize_high
7. README.md → skip
8. tests/test_api.py (uses unittest, modern Python 3) → skip
9. package.json → skip
10. .gitignore → skip

FILES TO CLASSIFY:
{json.dumps(file_list, indent=2)}

Return JSON object with filename as key and category as value.
Example: {{"file1.py": "modernize_high", "file2.js": "skip"}}
"""
        
        try:
            # Use JSON schema for guaranteed structure
            schema = GeminiSchemas.file_classification()
            
            response_text = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_PRECISE,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_MEDIUM,
                response_format="json",
                response_schema=schema
            )
            
            result = json.loads(response_text)
            
            # Validate results
            valid_categories = {"modernize_high", "modernize_low", "skip"}
            for filename, category in result.items():
                if category not in valid_categories:
                    result[filename] = "skip"  # Default to skip if invalid
            
            return result
            
        except Exception as e:
            print(f"Error classifying batch: {e}")
            # Return default classifications on error
            return {f: "skip" for f in file_list}
    
    def get_statistics(self, classifications: Dict[str, str]) -> Dict[str, int]:
        """
        Get statistics about classifications.
        
        Args:
            classifications: Dictionary of file classifications
            
        Returns:
            Dictionary with counts per category
        """
        stats = {
            "modernize_high": 0,
            "modernize_low": 0,
            "skip": 0,
            "total": len(classifications)
        }
        
        for category in classifications.values():
            if category in stats:
                stats[category] += 1
        
        return stats
