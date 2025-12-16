"""
Code Transformer - Generates modernized code using AI with RAG.
Supports multiple AI providers (Gemini, Nebius, OpenAI).
"""

import os
import json
import logging
from typing import Dict, List, Optional

from src.config import AIManager

logger = logging.getLogger(__name__)


class CodeTransformer:
    """
    Transforms legacy code to modern equivalents using Gemini 2.5 Flash.
    Integrates with MCP servers for examples and context.
    """
    
    def __init__(self, mcp_manager=None, search_engine=None):
        """
        Initialize Code Transformer.
        
        Args:
            mcp_manager: Optional MCPManager instance
            search_engine: Optional CodeSearchEngine instance
        """
        self.mcp_manager = mcp_manager
        self.search_engine = search_engine
        
        # Use centralized AI manager
        self.ai_manager = AIManager()
        
        logger.info(
            f"CodeTransformer initialized with provider: {self.ai_manager.provider_name}, "
            f"model: {self.ai_manager.model_name}"
        )
    
    async def transform_code(self, file_path: str, original_code: str, 
                            transformation_plan: Dict) -> str:
        """
        Transform legacy code using Gemini 2.5 Flash.
        
        Args:
            file_path: Path to the file being transformed
            original_code: Original code content
            transformation_plan: Plan from analyzer with steps and recommendations
        
        Returns:
            Modernized code as string
        """
        logger.info(f"Transforming code: {file_path}")
        
        # Get transformation examples from Memory MCP if available
        examples_text = ""
        if self.mcp_manager:
            try:
                from src.mcp.memory_client import MemoryMCPClient
                memory_client = MemoryMCPClient(self.mcp_manager)
                
                pattern_type = transformation_plan.get('pattern', '')
                examples = await memory_client.get_transformation_examples(
                    pattern_type, 
                    limit=3
                )
                
                if examples:
                    examples_text = "\n\nSUCCESSFUL TRANSFORMATION EXAMPLES:\n"
                    for i, ex in enumerate(examples, 1):
                        examples_text += f"\nExample {i}:\n"
                        examples_text += f"Before: {ex.get('before', '')[:200]}...\n"
                        examples_text += f"After: {ex.get('after', '')[:200]}...\n"
            except Exception as e:
                logger.warning(f"Could not retrieve transformation examples: {e}")
        
        # Get similar code from search engine if available
        context_text = ""
        if self.search_engine:
            try:
                similar_files = self.search_engine.find_similar_patterns(
                    f"Modern code similar to {file_path}",
                    top_k=3
                )
                
                if similar_files:
                    context_text = "\n\nSIMILAR MODERN CODE EXAMPLES:\n"
                    for f in similar_files[:2]:
                        context_text += f"- {f['file_path']}: {f['text_snippet']}\n"
            except Exception as e:
                logger.warning(f"Could not get similar code context: {e}")
        
        # Build transformation prompt
        prompt = f"""You are an expert code modernization assistant. Transform this legacy code to modern best practices.

FILE: {file_path}

TRANSFORMATION PLAN:
{json.dumps(transformation_plan, indent=2)}

{examples_text}
{context_text}

ORIGINAL CODE:
```
{original_code}
```

SANDBOX EXECUTION CONTEXT (for reference when generating imports):
- This code will be tested in Modal Sandbox at /workspace/
- Python: Tests will be combined with source in test_<module>.py
- Java: Source in <Module>.java (package: com.modernizer), tests in <Module>Test.java
- JavaScript: Source in <module>.js (ES modules with Jest), tests in <module>.test.js
- TypeScript: Source in <module>.ts (CommonJS for Jest/ts-jest), tests in <module>.test.ts
- All files in same /workspace/ directory
- Use relative imports and ensure all external dependencies are available

CRITICAL MODULE SYSTEM RULES:
- TypeScript: Use CommonJS-compatible code (NO import.meta, NO top-level await)
- TypeScript: Jest uses ts-jest with module: "commonjs" - avoid ES module-only features
- JavaScript: Can use ES modules but avoid Node.js-specific ES module features
- Do NOT add CLI execution code (if __name__ == "__main__", import.meta.url checks, etc.)
- Focus on library/module code that can be imported and tested

REQUIREMENTS:
1. Apply the transformation plan exactly
2. Maintain behavioral equivalence (same inputs → same outputs)
3. Add type hints for all functions (Python) or appropriate types
4. Include docstrings for public functions
5. Follow language-specific style guides (PEP 8 for Python, Java conventions, etc.)
6. Add error handling where missing
7. Use environment variables for secrets/credentials
8. Add comments explaining complex logic
9. Ensure all imports are at the top
10. Remove unused imports and variables
11. Use correct relative paths for local imports (same directory imports)
12. Include necessary package declarations (Java) or module exports
13. CRITICAL: Export ALL types, interfaces, enums, and classes that might be used in tests
    - TypeScript: Use 'export' keyword for all public types, interfaces, enums, classes
    - JavaScript: Include all functions/classes in module.exports or export statements
    - Python: All public functions/classes should be importable
    - Java: Use public access modifiers for classes/methods that will be tested

IMPORTANT: 
- Return ONLY the transformed code, no explanations or markdown formatting
- Do NOT include markdown code fences in the response
- Ensure imports work in sandbox environment where all files are in /workspace/
"""
        
        try:
            # Call AI with configured model
            modernized_code = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_MEDIUM,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_LARGE
            ).strip()
            
            # Extract code from markdown if present
            modernized_code = self._extract_code(modernized_code)
            
            # Validate that code is complete (not truncated)
            if modernized_code:
                # Check for common truncation indicators
                last_lines = modernized_code.split('\n')[-5:]
                last_text = '\n'.join(last_lines)
                
                # Warn if code appears truncated
                if (not modernized_code.rstrip().endswith((')', '}', ']', '"', "'")) and 
                    len(modernized_code) > 1000 and
                    not any(keyword in last_text for keyword in ['if __name__', 'main()', 'return'])):
                    logger.warning(f"Code for {file_path} may be truncated (length: {len(modernized_code)} chars)")
                    logger.warning(f"Last few lines: {last_text[:200]}")
            
            # Store successful transformation as example
            if self.mcp_manager:
                try:
                    from src.mcp.memory_client import MemoryMCPClient
                    memory_client = MemoryMCPClient(self.mcp_manager)
                    
                    example = {
                        "pattern": transformation_plan.get('pattern', ''),
                        "before": original_code[:500],
                        "after": modernized_code[:500],
                        "file_path": file_path
                    }
                    
                    example_id = f"{transformation_plan.get('pattern', 'unknown')}_{hash(file_path)}"
                    await memory_client.store_transformation_example(example_id, example)
                except Exception as e:
                    logger.warning(f"Could not store transformation example: {e}")
            
            logger.info(f"Transformation complete for {file_path}")
            return modernized_code
            
        except Exception as e:
            logger.error(f"Error during transformation: {e}")
            return original_code  # Return original on error
    
    def _extract_code(self, text: str) -> str:
        """
        Extract code from markdown code blocks if present.
        Handles both complete blocks and trailing markdown fences.
        
        Args:
            text: Text that may contain markdown code blocks
        
        Returns:
            Extracted code
        """
        if not text:
            return ""
            
        # Check for markdown code blocks
        if "```" in text:
            # Try to extract code between ``` markers
            parts = text.split("```")
            if len(parts) >= 3:
                # Get the code block (skip language identifier)
                code_block = parts[1]
                # Remove language identifier if present
                lines = code_block.split('\n')
                if lines[0].strip() in ['python', 'java', 'javascript', 'typescript', 'cpp', 'c', 'go', 'js', 'ts', 'py']:
                    code_block = '\n'.join(lines[1:])
                return code_block.strip()
            elif len(parts) == 2:
                # Only one ``` found - might be trailing fence
                # Take everything before the fence
                return parts[0].strip()
        
        # Remove any trailing markdown fences
        text = text.strip()
        if text.endswith('```'):
            text = text[:-3].strip()
        
        return text
    
    async def bulk_transform(self, files: Dict[str, str], 
                            transformation_plan: Dict) -> Dict[str, str]:
        """
        Transform multiple files with the same pattern.
        
        Args:
            files: Dictionary mapping file paths to their contents
            transformation_plan: Transformation plan to apply
        
        Returns:
            Dictionary mapping file paths to transformed code
        """
        logger.info(f"Bulk transforming {len(files)} files")
        
        results = {}
        
        for file_path, original_code in files.items():
            try:
                transformed = await self.transform_code(
                    file_path, 
                    original_code, 
                    transformation_plan
                )
                results[file_path] = transformed
                logger.info(f"✓ Transformed {file_path}")
            except Exception as e:
                logger.error(f"✗ Failed to transform {file_path}: {e}")
                results[file_path] = original_code
        
        logger.info(f"Bulk transformation complete: {len(results)}/{len(files)} successful")
        return results
    
    async def add_type_hints(self, file_path: str, code: str) -> str:
        """
        Add type hints to Python code.
        
        Args:
            file_path: Path to the file
            code: Code content
        
        Returns:
            Code with type hints added
        """
        logger.info(f"Adding type hints to {file_path}")
        
        prompt = f"""Add comprehensive type hints to this Python code.

FILE: {file_path}

CODE:
```python
{code}
```

REQUIREMENTS:
1. Add type hints to all function parameters and return types
2. Use typing module for complex types (List, Dict, Optional, etc.)
3. Add type hints to class attributes
4. Maintain all existing functionality
5. Follow PEP 484 type hinting standards

Return ONLY the code with type hints added, no explanations.
"""
        
        try:
            typed_code = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_PRECISE,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_MEDIUM
            )
            
            return self._extract_code(typed_code)
            
        except Exception as e:
            logger.error(f"Error adding type hints: {e}")
            return code
    
    async def add_docstrings(self, file_path: str, code: str) -> str:
        """
        Add docstrings to code.
        
        Args:
            file_path: Path to the file
            code: Code content
        
        Returns:
            Code with docstrings added
        """
        logger.info(f"Adding docstrings to {file_path}")
        
        prompt = f"""Add comprehensive docstrings to this code.

FILE: {file_path}

CODE:
```
{code}
```

REQUIREMENTS:
1. Add docstrings to all functions and classes
2. Use Google-style or NumPy-style docstrings
3. Include parameter descriptions, return values, and exceptions
4. Add module-level docstring if missing
5. Maintain all existing functionality

Return ONLY the code with docstrings added, no explanations.
"""
        
        try:
            documented_code = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_PRECISE,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_MEDIUM
            )
            
            return self._extract_code(documented_code)
            
        except Exception as e:
            logger.error(f"Error adding docstrings: {e}")
            return code
