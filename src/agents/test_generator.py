"""
Test Generator - Generates unit tests for code transformations using AI.
Supports multiple AI providers (Gemini, Nebius, OpenAI).
"""

import os
import logging
from typing import Dict, Optional
from pathlib import Path

from src.config import AIManager

logger = logging.getLogger(__name__)


class CodeTestGenerator:
    """
    Generates comprehensive unit tests for code transformations.
    Uses Gemini 2.5 Flash to create behavioral equivalence tests.
    
    Note: Renamed from TestGenerator to avoid pytest collection conflicts.
    """
    
    def __init__(self):
        """Initialize Code Test Generator."""
        # Use centralized AI manager
        self.ai_manager = AIManager()
        
        logger.info(
            f"CodeTestGenerator initialized with provider: {self.ai_manager.provider_name}, "
            f"model: {self.ai_manager.model_name}"
        )
    
    def generate_tests(self, original_code: str, modernized_code: str, 
                      file_path: str, language: str = None) -> str:
        """
        Generate comprehensive unit tests for code transformation.
        
        Args:
            original_code: Original legacy code
            modernized_code: Modernized code
            file_path: Path to the file
            language: Programming language (auto-detected if not provided)
        
        Returns:
            Generated test code as string
        """
        logger.info(f"Generating tests for {file_path}")
        
        # Auto-detect language from file extension if not provided
        if language is None:
            language = self._detect_language(file_path, modernized_code)
        
        logger.info(f"Detected language: {language}")
        
        # Language-specific test framework
        framework_map = {
            "python": "pytest",
            "java": "JUnit 5",
            "javascript": "Jest",
            "typescript": "Jest",
            "go": "testing package",
            "ruby": "RSpec",
            "csharp": "xUnit",
            "cpp": "Google Test",
            "kotlin": "JUnit 5",
            "scala": "ScalaTest"
        }
        
        framework = framework_map.get(language.lower(), "pytest")
        
        # Truncate code if too long to avoid token limits
        # Increased from 3000 to 8000 to give AI more context
        max_code_length = 8000  # chars per code block
        original_truncated = original_code[:max_code_length] + ("\n\n# ... (truncated)" if len(original_code) > max_code_length else "")
        modernized_truncated = modernized_code[:max_code_length] + ("\n\n# ... (truncated)" if len(modernized_code) > max_code_length else "")
        
        # Extract module name for proper imports
        module_name = Path(file_path).stem
        
        # Language-specific setup instructions
        setup_instructions = ""
        import_instructions = ""
        
        if language == "python":
            setup_instructions = """1. **CRITICAL SANDBOX ENVIRONMENT**: Modal Sandbox Execution:
   - Test file location: `/workspace/test_{module_name}.py`
   - IMPORTANT: The test file contains BOTH source code AND tests combined in one file
   - Implementation code is defined first, then test functions use it
   - Start the test file with:
   ```python
   import sys
   import os
   sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
   ```"""
            import_instructions = f'2. Import/Usage: Either "from {module_name} import ..." OR call functions directly (same file)'
        elif language == "java":
            setup_instructions = """1. **CRITICAL SANDBOX ENVIRONMENT**: Modal Sandbox Maven Execution:
   - Source file: `/workspace/{module_name}.java` with package `com.modernizer`
   - Test file: `/workspace/{module_name}Test.java` with package `com.modernizer`
   - Both files are compiled together by Maven in the `/workspace/` directory
   - Use proper JUnit 5 annotations:
   ```java
   package com.modernizer;
   import org.junit.jupiter.api.Test;
   import org.junit.jupiter.api.BeforeEach;
   import static org.junit.jupiter.api.Assertions.*;
   
   public class {module_name}Test {{
       @BeforeEach
       void setUp() {{
           // Setup code
       }}
       
       @Test
       void testMethodName() {{
           // Test code with assertions
       }}
   }}
   ```"""
            import_instructions = f'2. Package: Use "package com.modernizer;" in both files - no imports needed (same package)'
        elif language in ["javascript", "typescript"]:
            ext = '.ts' if language == 'typescript' else '.js'
            if language == 'typescript':
                import_example = f'import {{ ... }} from "./{module_name}";'
                import_note = "WITHOUT .ts extension (TypeScript resolves automatically)"
            else:
                import_example = f'import {{ ... }} from "./{module_name}.js";'
                import_note = "WITH .js extension (ES modules require explicit extensions)"
            
            setup_instructions = f"""1. **CRITICAL SANDBOX ENVIRONMENT**: Modal Sandbox Jest Execution:
   - Source file: `/workspace/{module_name}{ext}`
   - Test file: `/workspace/{module_name}.test{ext}`
   - Framework: Jest configured for {'TypeScript (ts-jest preset)' if language == 'typescript' else 'JavaScript (ES modules)'}
   - Use proper module import statements"""
            import_instructions = f'2. Import: Use relative path {import_note}: `{import_example}`'
        else:
            setup_instructions = "1. Ensure proper imports/includes for the sandbox environment."
            import_instructions = "2. Import the module/class to be tested from the same /workspace/ directory."

        prompt = f"""Generate comprehensive unit tests for this code transformation.

FILE: {file_path}
MODULE NAME: {module_name}
LANGUAGE: {language}
TEST FRAMEWORK: {framework}

ORIGINAL CODE (truncated for context):
```{language}
{original_truncated}
```

MODERNIZED CODE (truncated for context):
```{language}
{modernized_truncated}
```

REQUIREMENTS:
{setup_instructions}

{import_instructions}
3. Test behavioral equivalence (same inputs → same outputs)
4. Test edge cases (empty inputs, None/null, invalid types, boundary values)
5. Test error handling and exceptions
6. Use {framework} framework
7. Mock external dependencies (databases, APIs, file system)
8. Include fixtures for common test data
9. Test both success and failure scenarios
10. Add descriptive test names and docstrings
11. Ensure tests are independent and can run in any order
12. Include setup and teardown if needed

SANDBOX FILE STRUCTURE:
- Python: test_{module_name}.py contains BOTH source code and tests combined
- Java: {module_name}.java and {module_name}Test.java in package com.modernizer, compiled together by Maven
- JavaScript: {module_name}.js and {module_name}.test.js (ES modules with "type": "module" in package.json)
- TypeScript: {module_name}.ts and {module_name}.test.ts (ts-jest preset handles compilation)
- All files are in /workspace/ directory in the Modal Sandbox

CRITICAL IMPORT INSTRUCTIONS:
- JavaScript: MUST use .js extension in imports: `import {{ ... }} from "./{module_name}.js";`
- TypeScript: MUST NOT use .ts extension in imports: `import {{ ... }} from "./{module_name}";`
- This is critical - wrong extensions will cause compilation/runtime errors!

CRITICAL OUTPUT INSTRUCTIONS:
- Return ONLY the complete test code in a single code block
- For Python: Source and tests are in SAME file, define functions first then tests
- For Java: Source and tests are SEPARATE files, same package, no imports needed
- For JS/TS: Tests are SEPARATE files, use relative imports with correct extensions (see above)
- DO NOT include any explanatory text, descriptions, or commentary before or after the code
- The response must be executable code that can run directly in a sandbox environment
- Start your response with the code block marker (```{language}) and end with the closing marker (```)
"""
        try:
            response_text = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_MEDIUM,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_LARGE
            )
            
            # Check if response has text
            if not response_text:
                logger.warning(f"Empty response from AI for {file_path}")
                return self._generate_fallback_test(file_path, language, framework)
            
            test_code = self._extract_code(response_text)
            
            # Validate that we got actual test code, not just fallback
            if not test_code or len(test_code.strip()) < 100:
                logger.warning(f"Generated test code too short for {file_path}, using fallback")
                return self._generate_fallback_test(file_path, language, framework)
            
            # Check if it contains actual test functions
            if language == "python" and "def test_" not in test_code:
                logger.warning(f"No test functions found in generated code for {file_path}")
                return self._generate_fallback_test(file_path, language, framework)
            
            logger.info(f"Test generation complete for {file_path} ({len(test_code)} chars)")
            return test_code
            
        except Exception as e:
            logger.error(f"Error generating tests for {file_path}: {e}")
            return self._generate_fallback_test(file_path, language, framework)
    
    def generate_integration_tests(self, files: Dict[str, str], 
                                   language: str = "python") -> str:
        """
        Generate integration tests for multiple related files.
        
        Args:
            files: Dictionary mapping file paths to their contents
            language: Programming language
        
        Returns:
            Generated integration test code
        """
        logger.info(f"Generating integration tests for {len(files)} files")
        
        files_summary = "\n\n".join([
            f"FILE: {path}\n```{language}\n{content[:500]}...\n```"
            for path, content in list(files.items())[:5]
        ])
        
        prompt = f"""Generate integration tests for these related files.

{files_summary}

REQUIREMENTS:
1. Test interactions between modules
2. Test data flow across components
3. Test end-to-end scenarios
4. Mock external dependencies
5. Include setup and teardown for test environment
6. Test error propagation across modules
7. Ensure tests are comprehensive but maintainable

CRITICAL: Return ONLY the complete test code in a single code block.
DO NOT include any explanatory text, descriptions, or commentary.
The response must be executable code that can run directly in a sandbox.
"""
        
        try:
            response_text = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_MEDIUM,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_LARGE
            )
            
            if not response_text:
                logger.warning("Empty response for integration tests")
                return ""
            
            test_code = self._extract_code(response_text)
            logger.info(f"Integration test generation complete ({len(test_code)} chars)")
            return test_code
            
        except Exception as e:
            logger.error(f"Error generating integration tests: {e}")
            return ""
    
    def generate_security_tests(self, file_path: str, code: str, 
                               vulnerabilities: list) -> str:
        """
        Generate security-focused tests.
        
        Args:
            file_path: Path to the file
            code: Code content
            vulnerabilities: List of identified vulnerabilities
        
        Returns:
            Generated security test code
        """
        logger.info(f"Generating security tests for {file_path}")
        
        vulns_text = "\n".join([
            f"- {v.get('type', 'Unknown')}: {v.get('description', '')}"
            for v in vulnerabilities
        ])
        
        # Detect language
        language = self._detect_language(file_path, code)
        framework_map = {
            "python": "pytest",
            "java": "JUnit 5",
            "javascript": "Jest",
            "typescript": "Jest",
            "go": "testing package",
            "ruby": "RSpec",
            "csharp": "xUnit",
            "cpp": "Google Test",
            "kotlin": "JUnit 5",
            "scala": "ScalaTest"
        }
        framework = framework_map.get(language.lower(), "pytest")

        prompt = f"""Generate security-focused tests for this code.

FILE: {file_path}
LANGUAGE: {language}
TEST FRAMEWORK: {framework}

CODE:
```{language}
{code}
```

IDENTIFIED VULNERABILITIES:
{vulns_text}

REQUIREMENTS:
1. Test for SQL injection prevention
2. Test for XSS prevention
3. Test for authentication/authorization
4. Test for input validation
5. Test for secure credential handling
6. Test for proper error handling (no info leakage)
7. Use {framework} framework
8. Include security-specific assertions

CRITICAL: Return ONLY the complete test code in a single code block.
DO NOT include any explanatory text, descriptions, or commentary.
The response must be executable code that can run directly in a sandbox.
"""
        
        try:
            response_text = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_PRECISE,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_LARGE
            )
            
            if not response_text:
                logger.warning(f"Empty response for security tests: {file_path}")
                return ""
            
            test_code = self._extract_code(response_text)
            logger.info(f"Security test generation complete for {file_path} ({len(test_code)} chars)")
            return test_code
            
        except Exception as e:
            logger.error(f"Error generating security tests: {e}")
            return ""
    
    def generate_performance_tests(self, file_path: str, code: str) -> str:
        """
        Generate performance/benchmark tests.
        
        Args:
            file_path: Path to the file
            code: Code content
        
        Returns:
            Generated performance test code
        """
        logger.info(f"Generating performance tests for {file_path}")
        
        # Detect language
        language = self._detect_language(file_path, code)
        framework_map = {
            "python": "pytest-benchmark",
            "java": "JMH (Java Microbenchmark Harness)",
            "javascript": "Jest (with performance hooks)",
            "typescript": "Jest (with performance hooks)",
            "go": "testing package benchmarks",
            "ruby": "Benchmark module",
            "csharp": "BenchmarkDotNet",
            "cpp": "Google Benchmark",
        }
        framework = framework_map.get(language.lower(), "pytest-benchmark")

        prompt = f"""Generate performance tests for this code.

FILE: {file_path}
LANGUAGE: {language}
TEST FRAMEWORK: {framework}

CODE:
```{language}
{code}
```

REQUIREMENTS:
1. Use {framework} for performance testing
2. Test execution time for critical functions
3. Test memory usage
4. Test scalability with different input sizes
5. Include baseline performance metrics
6. Test for performance regressions
7. Add timeout tests for long-running operations

CRITICAL: Return ONLY the complete test code in a single code block.
DO NOT include any explanatory text, descriptions, or commentary.
The response must be executable code that can run directly in a sandbox.
"""
        
        try:
            response_text = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_PRECISE,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_LARGE
            )
            
            if not response_text:
                logger.warning(f"Empty response for performance tests: {file_path}")
                return ""
            
            test_code = self._extract_code(response_text)
            logger.info(f"Performance test generation complete for {file_path} ({len(test_code)} chars)")
            return test_code
            
        except Exception as e:
            logger.error(f"Error generating performance tests: {e}")
            return ""
    
    def _extract_code(self, text: str) -> str:
        """
        Extract code from markdown code blocks, removing any explanatory text.
        
        Args:
            text: Text that may contain markdown code blocks
        
        Returns:
            Extracted code only, without explanatory text
        """
        # Handle None or empty text
        if not text:
            return ""
        
        # Try to extract from markdown code blocks
        if "```" in text:
            parts = text.split("```")
            
            # Find all code blocks
            code_blocks = []
            for i in range(1, len(parts), 2):  # Code blocks are at odd indices
                if i < len(parts):
                    code_block = parts[i]
                    lines = code_block.split('\n')
                    
                    # Remove language identifier if present
                    first_line = lines[0].strip().lower()
                    if first_line in ['python', 'java', 'javascript', 'typescript', 'pytest', 'py', 'js', 'ts', 'go', 'ruby', 'rb']:
                        code_block = '\n'.join(lines[1:])
                    
                    extracted = code_block.strip()
                    
                    # Only add substantial code blocks
                    if len(extracted) > 50:
                        code_blocks.append(extracted)
            
            # Return the largest code block (usually the main test file)
            if code_blocks:
                return max(code_blocks, key=len)
        
        # If no code blocks found, check if the text itself looks like code
        # (starts with import, def, class, etc.)
        text_stripped = text.strip()
        code_indicators = ['import ', 'from ', 'def ', 'class ', 'async def ', '@pytest', '@test']
        
        # If text starts with code indicators, it might be plain code without markdown
        if any(text_stripped.startswith(indicator) for indicator in code_indicators):
            return text_stripped
        
        # Otherwise, return empty string to trigger fallback
        return ""
    
    def _detect_language(self, file_path: str, code: str) -> str:
        """
        Detect programming language from file extension or code content.
        
        Args:
            file_path: Path to the file
            code: Source code content
        
        Returns:
            Detected language name
        """
        if file_path:
            ext = Path(file_path).suffix.lower()
            extension_map = {
                # Python
                '.py': 'python', '.pyw': 'python', '.pyx': 'python',
                # Java
                '.java': 'java',
                # JavaScript/TypeScript
                '.js': 'javascript', '.jsx': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
                '.ts': 'typescript', '.tsx': 'typescript',
                # PHP
                '.php': 'php', '.php3': 'php', '.php4': 'php', '.php5': 'php', '.phtml': 'php',
                # Ruby
                '.rb': 'ruby', '.rbw': 'ruby',
                # Go
                '.go': 'go',
                # C/C++
                '.c': 'c', '.h': 'c',
                '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.c++': 'cpp',
                '.hpp': 'cpp', '.hh': 'cpp', '.hxx': 'cpp', '.h++': 'cpp',
                # C#
                '.cs': 'csharp',
                # Rust
                '.rs': 'rust',
                # Kotlin
                '.kt': 'kotlin', '.kts': 'kotlin',
                # Swift
                '.swift': 'swift',
                # Scala
                '.scala': 'scala', '.sc': 'scala',
                # R
                '.r': 'r', '.R': 'r',
                # Perl
                '.pl': 'perl', '.pm': 'perl', '.t': 'perl', '.pod': 'perl',
                # Shell
                '.sh': 'shell', '.bash': 'shell', '.zsh': 'shell', '.fish': 'shell'
            }
            if ext in extension_map:
                return extension_map[ext]
        
        # Fallback: detect from code content
        if code:
            if 'public class' in code or 'import java.' in code:
                return 'java'
            elif 'package main' in code or 'func main()' in code:
                return 'go'
            elif 'def ' in code and ('import ' in code or 'from ' in code):
                return 'python'
            elif 'function ' in code or 'const ' in code or 'let ' in code:
                return 'javascript'
            elif 'namespace ' in code and 'using ' in code:
                return 'csharp'
            elif 'fn main()' in code or 'use std::' in code:
                return 'rust'
            elif '<?php' in code:
                return 'php'
            elif 'class ' in code and 'def ' in code and 'end' in code:
                return 'ruby'
        
        return 'python'  # Default
    
    def _generate_fallback_test(self, file_path: str, language: str, 
                               framework: str) -> str:
        """
        Generate a basic fallback test when generation fails.
        
        Args:
            file_path: Path to the file
            language: Programming language
            framework: Test framework
        
        Returns:
            Basic test template
        """
        if language == "python":
            module_name = Path(file_path).stem
            return f"""import sys
import os
# Ensure module can be imported from any directory structure
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, patch

# Tests for {file_path}
# Note: These are placeholder tests. AI generation failed.
# Please add comprehensive tests based on your code's functionality.

class Test{module_name.title().replace('_', '')}:
    \"\"\"Test suite for {module_name}\"\"\"
    
    def test_module_imports(self):
        \"\"\"Test that the module can be imported without errors\"\"\"
        try:
            import {module_name}
            assert True
        except ImportError:
            pytest.skip("Module not in path")
    
    def test_placeholder_basic(self):
        \"\"\"Placeholder test - replace with actual tests\"\"\"
        assert True
    
    def test_placeholder_edge_cases(self):
        \"\"\"Test edge cases - implement based on your code\"\"\"
        # TODO: Add edge case tests
        assert True
    
    def test_placeholder_error_handling(self):
        \"\"\"Test error handling - implement based on your code\"\"\"
        # TODO: Add error handling tests
        assert True

# TODO: Add comprehensive tests for {file_path}
# Consider testing:
# - Normal operation with valid inputs
# - Edge cases (empty, None, boundary values)
# - Error conditions and exceptions
# - Integration with other modules
"""
        elif language == "java":
            class_name = Path(file_path).stem.replace('_', '').title()
            return f"""import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for {file_path}
 * Note: These are placeholder tests. AI generation failed.
 * Please add comprehensive tests based on your code's functionality.
 */
class {class_name}Test {{
    
    @BeforeEach
    void setUp() {{
        // Initialize test fixtures
    }}
    
    @Test
    @DisplayName("Placeholder test - replace with actual tests")
    void testPlaceholderBasic() {{
        assertTrue(true);
    }}
    
    @Test
    @DisplayName("Test edge cases - implement based on your code")
    void testEdgeCases() {{
        // TODO: Add edge case tests
        assertTrue(true);
    }}
    
    @Test
    @DisplayName("Test error handling - implement based on your code")
    void testErrorHandling() {{
        // TODO: Add error handling tests
        assertTrue(true);
    }}
}}

// TODO: Add comprehensive tests for {file_path}
// Consider testing:
// - Normal operation with valid inputs
// - Edge cases (null, empty, boundary values)
// - Exception handling
// - Integration with other classes
"""
        elif language in ("javascript", "typescript"):
            module_name = Path(file_path).stem
            return f"""// Tests for {file_path}
// Note: These are placeholder tests. AI generation failed.
// Please add comprehensive tests based on your code's functionality.

describe('{module_name}', () => {{
    beforeEach(() => {{
        // Initialize test fixtures
    }});
    
    test('placeholder test - replace with actual tests', () => {{
        expect(true).toBe(true);
    }});
    
    test('edge cases - implement based on your code', () => {{
        // TODO: Add edge case tests
        expect(true).toBe(true);
    }});
    
    test('error handling - implement based on your code', () => {{
        // TODO: Add error handling tests
        expect(true).toBe(true);
    }});
}});

// TODO: Add comprehensive tests for {file_path}
// Consider testing:
// - Normal operation with valid inputs
// - Edge cases (null, undefined, empty, boundary values)
// - Error conditions and exceptions
// - Async operations (if applicable)
"""
        else:
            return f"""// Tests for {file_path}
// Language: {language}
// Note: AI test generation failed. Please add tests manually.

// TODO: Add comprehensive tests for {file_path}
"""
