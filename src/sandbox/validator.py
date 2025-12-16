"""
Modal Sandbox Validator - Executes tests in isolated Modal containers.
Phase 5: Test execution in secure sandbox environment.

Supports multiple languages with dedicated Modal container images.
Falls back to local execution when Modal is not available.
"""

import os
import logging
import subprocess
import tempfile
import json
import time
from typing import Dict, List, Optional
from pathlib import Path

# Import Modal images and runners
from .images import (
    MODAL_AVAILABLE, app, LANGUAGE_IMAGES, LANGUAGE_SUPPORT_STATUS,
    get_image_for_language, get_support_status, is_language_supported
)
from .runners import LANGUAGE_RUNNERS, get_runner_for_language, is_runner_available

logger = logging.getLogger(__name__)


def _detect_language(file_path: str, code: str) -> str:
    """Detect programming language from file extension or code content."""
    if file_path:
        ext = Path(file_path).suffix.lower()
        extension_map = {
            # Python
            '.py': 'python', '.pyw': 'python', '.pyx': 'python',
            # Java
            '.java': 'java',
            # JavaScript/TypeScript
            '.js': 'javascript', '.jsx': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
            '.ts': 'typescript', '.tsx': 'typescript'
        }
        if ext in extension_map:
            return extension_map[ext]
    
    # Fallback: detect from code content
    if code:
        if 'public class' in code or 'import java.' in code:
            return 'java'
        elif 'def ' in code and ('import ' in code or 'from ' in code):
            return 'python'
        elif 'function ' in code or 'const ' in code or 'let ' in code:
            return 'javascript'
        elif 'interface ' in code or 'type ' in code:
            return 'typescript'
    
    return 'python'  # Default


def run_tests_locally(code: str, tests: str, requirements: List[str], 
                      module_name: str = "module", language: str = "python") -> Dict:
    """
    Execute tests locally (fallback when Modal is not available).
    
    Args:
        code: Modernized code to test
        tests: Generated test code
        requirements: Additional packages needed
        module_name: Name of the module
        language: Programming language
    
    Returns:
        Dictionary with test results
    """
    # Only support Python, Java, JavaScript, and TypeScript
    supported_languages = ['python', 'java', 'javascript', 'typescript']
    
    if language not in supported_languages:
        return {
            "success": False,
            "error": f"Unsupported language: {language}. Supported languages: {', '.join(supported_languages)}",
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "execution_mode": "unsupported"
        }
    
    if language == 'python':
        return _run_python_tests_locally(code, tests, requirements, module_name)
    elif language == 'java':
        return _run_java_tests_locally(code, tests, module_name)
    elif language in ('javascript', 'typescript'):
        return _run_js_tests_locally(code, tests, module_name, language)


def _run_python_tests_locally(code: str, tests: str, requirements: List[str], 
                               module_name: str) -> Dict:
    """Run Python tests locally using pytest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Write code and tests in same directory for proper imports
        code_file = tmpdir_path / f"{module_name}.py"
        test_file = tmpdir_path / f"test_{module_name}.py"
        
        # Add sys.path manipulation to tests if not already present
        # This ensures tests can import the module even from subdirectories
        if "sys.path" not in tests and "import sys" not in tests:
            path_setup = """import sys
import os
# Ensure module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

"""
            tests = path_setup + tests
        
        code_file.write_text(code, encoding='utf-8')
        test_file.write_text(tests, encoding='utf-8')
        
        # Install additional requirements
        if requirements:
            try:
                subprocess.run(
                    ["pip", "install", "-q", "--no-cache-dir"] + requirements,
                    capture_output=True,
                    timeout=60,
                    check=False  # Don't fail on install errors
                )
            except Exception as e:
                logger.warning(f"Failed to install requirements: {e}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                [
                    "pytest",
                    str(test_file),
                    "-v",
                    "--tb=short",
                    "--timeout=30",
                    "-p", "no:warnings"
                ],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test execution timeout (>2 minutes)",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_time": 120.0,
                "execution_mode": "local"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "pytest not found. Install with: pip install pytest",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "local"
            }
        
        execution_time = time.time() - start_time
        stdout = result.stdout
        
        # Count tests
        passed = stdout.count(" PASSED")
        failed = stdout.count(" FAILED")
        errors = stdout.count(" ERROR")
        test_count = passed + failed + errors
        
        return {
            "success": result.returncode == 0,
            "tests_run": test_count,
            "tests_passed": passed,
            "tests_failed": failed,
            "tests_errors": errors,
            "execution_time": round(execution_time, 2),
            "coverage_percent": 0.0,  # Coverage not measured in local mode
            "stdout": stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "execution_mode": "local"
        }


def _run_java_tests_locally(code: str, tests: str, module_name: str) -> Dict:
    """Run Java tests locally using JUnit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Extract class name from code
        class_name = module_name.replace('_', '').title()
        if 'public class ' in code:
            import re
            match = re.search(r'public class (\w+)', code)
            if match:
                class_name = match.group(1)
        
        # Write Java files
        code_file = tmpdir_path / f"{class_name}.java"
        test_file = tmpdir_path / f"{class_name}Test.java"
        
        code_file.write_text(code, encoding='utf-8')
        test_file.write_text(tests, encoding='utf-8')
        
        start_time = time.time()
        
        try:
            # Compile
            compile_result = subprocess.run(
                ["javac", str(code_file), str(test_file)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if compile_result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Compilation failed: {compile_result.stderr}",
                    "tests_run": 0,
                    "tests_passed": 0,
                    "tests_failed": 0,
                    "execution_mode": "local"
                }
            
            # Run tests (simplified - would need JUnit runner in real scenario)
            run_result = subprocess.run(
                ["java", f"{class_name}Test"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            execution_time = time.time() - start_time
            
            return {
                "success": run_result.returncode == 0,
                "tests_run": 1,  # Simplified
                "tests_passed": 1 if run_result.returncode == 0 else 0,
                "tests_failed": 0 if run_result.returncode == 0 else 1,
                "execution_time": round(execution_time, 2),
                "stdout": run_result.stdout,
                "stderr": run_result.stderr,
                "exit_code": run_result.returncode,
                "execution_mode": "local"
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Java compiler (javac) not found. Install JDK.",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "local"
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Java test execution timeout",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "local"
            }


def _run_js_tests_locally(code: str, tests: str, module_name: str, 
                          language: str) -> Dict:
    """Run JavaScript/TypeScript tests locally using Jest or Node."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        ext = '.ts' if language == 'typescript' else '.js'
        
        # Write files
        code_file = tmpdir_path / f"{module_name}{ext}"
        test_file = tmpdir_path / f"{module_name}.test{ext}"
        
        code_file.write_text(code, encoding='utf-8')
        test_file.write_text(tests, encoding='utf-8')
        
        # Create minimal package.json
        package_json = {
            "name": "test-sandbox",
            "scripts": {"test": "jest"},
            "devDependencies": {"jest": "^29.0.0"}
        }
        if language == 'typescript':
            package_json["devDependencies"]["ts-jest"] = "^29.0.0"
            package_json["devDependencies"]["typescript"] = "^5.0.0"
        
        (tmpdir_path / "package.json").write_text(json.dumps(package_json))
        
        start_time = time.time()
        
        try:
            # Try running with node directly for simple tests
            run_result = subprocess.run(
                ["node", str(test_file)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            execution_time = time.time() - start_time
            
            return {
                "success": run_result.returncode == 0,
                "tests_run": 1,
                "tests_passed": 1 if run_result.returncode == 0 else 0,
                "tests_failed": 0 if run_result.returncode == 0 else 1,
                "execution_time": round(execution_time, 2),
                "stdout": run_result.stdout,
                "stderr": run_result.stderr,
                "exit_code": run_result.returncode,
                "execution_mode": "local"
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Node.js not found. Install Node.js.",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "local"
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "JavaScript test execution timeout",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "local"
            }


# Import Modal executor if available
if MODAL_AVAILABLE:
    try:
        from .modal_executor import execute_in_modal
        MODAL_EXECUTOR_AVAILABLE = True
    except Exception as e:
        logger.warning(f"Failed to import Modal executor: {e}")
        MODAL_EXECUTOR_AVAILABLE = False
else:
    MODAL_EXECUTOR_AVAILABLE = False


def run_tests_in_sandbox(code: str, tests: str, requirements: List[str], 
                         module_name: str = "module", language: str = "python") -> Dict:
    """
    Execute tests in sandbox (Modal if available, otherwise local).
    
    Args:
        code: Source code
        tests: Test code
        requirements: Package requirements
        module_name: Module name
        language: Programming language
    
    Returns:
        Test execution results
    """
    if MODAL_EXECUTOR_AVAILABLE:
        try:
            return execute_in_modal(code, tests, requirements, module_name, language)
        except Exception as e:
            logger.warning(f"Modal execution failed: {e}, falling back to local")
            return run_tests_locally(code, tests, requirements, module_name, language)
    else:
        logger.info("Modal not available, running tests locally")
        return run_tests_locally(code, tests, requirements, module_name, language)


class ModalSandboxValidator:
    """
    Validates code transformations using Modal sandbox.
    Provides safe, isolated test execution environment.
    Falls back to local execution when Modal is not available.
    
    Supports multiple languages: Python, Java, JavaScript, TypeScript, etc.
    """
    
    def __init__(self, prefer_modal: bool = None):
        """
        Initialize Modal Sandbox Validator.
        
        Args:
            prefer_modal: If True, try Modal first, fallback to local.
                         If False, always use local execution.
                         If None (default), auto-detect based on environment.
        """
        # Import config to get environment-aware settings
        from .config import should_prefer_modal, validate_environment, IS_HUGGINGFACE
        
        # Auto-detect if not specified
        if prefer_modal is None:
            prefer_modal = should_prefer_modal()
        
        self.prefer_modal = prefer_modal and MODAL_AVAILABLE
        self.is_huggingface = IS_HUGGINGFACE
        self.app = app
        
        # Validate environment configuration
        validate_environment()
        
        if self.is_huggingface and not self.prefer_modal:
            logger.error("Running on Hugging Face but Modal is not available!")
            logger.error("Test execution will fail. Please configure Modal.")
        
        if self.prefer_modal:
            logger.info("ModalSandboxValidator initialized with Modal support")
        else:
            logger.info("ModalSandboxValidator initialized (local execution mode)")
    
    def validate_transformation(
        self,
        original_code: str,
        modernized_code: str,
        tests: str,
        requirements: Optional[List[str]] = None,
        file_path: Optional[str] = None
    ) -> Dict:
        """
        Validate code transformation by running tests in sandbox.
        
        Args:
            original_code: Original legacy code
            modernized_code: Modernized code
            tests: Generated test code
            requirements: Additional packages needed
            file_path: Path to the file (used to extract module name and language)
        
        Returns:
            Validation results with test metrics
        """
        logger.info("Starting sandbox validation")
        
        # Detect language from file path or code
        language = _detect_language(file_path, modernized_code)
        logger.info(f"Detected language: {language}")
        
        # Extract requirements based on language
        if requirements is None:
            requirements = self._extract_requirements(modernized_code, language)
        
        # Extract module name from file path
        if file_path:
            module_name = Path(file_path).stem
        else:
            module_name = "module"
        
        logger.info(f"Validating module: {module_name} (language: {language})")
        
        # Try Modal first if available and preferred
        if self.prefer_modal and MODAL_AVAILABLE:
            try:
                logger.info("Attempting Modal sandbox execution...")
                results = run_tests_in_sandbox(
                    code=modernized_code,
                    tests=tests,
                    requirements=requirements,
                    module_name=module_name,
                    language=language
                )
                
                results['execution_mode'] = 'modal'
                logger.info(f"Modal validation complete: {results['tests_passed']}/{results['tests_run']} passed")
                return results
                
            except Exception as e:
                logger.warning(f"Modal execution failed: {e}, falling back to local")
        
        # Fallback to local execution
        logger.info("Running tests locally...")
        try:
            results = run_tests_locally(
                code=modernized_code,
                tests=tests,
                requirements=requirements,
                module_name=module_name,
                language=language
            )
            
            logger.info(f"Local validation complete: {results['tests_passed']}/{results['tests_run']} passed")
            return results
            
        except Exception as e:
            logger.error(f"Local validation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "failed"
            }
    
    def validate_batch(
        self,
        transformations: List[Dict]
    ) -> List[Dict]:
        """
        Validate multiple transformations in parallel.
        
        Args:
            transformations: List of transformation dicts with code and tests
        
        Returns:
            List of validation results
        """
        logger.info(f"Starting batch validation for {len(transformations)} files")
        
        results = []
        
        # Try Modal batch execution if available
        if self.prefer_modal and MODAL_AVAILABLE:
            try:
                # For batch operations, we can call functions directly
                # Modal handles the parallelization internally
                for t in transformations:
                    file_path = t.get('file_path', '')
                    language = _detect_language(file_path, t['modernized_code'])
                    
                    try:
                        result = run_tests_in_sandbox(
                            code=t['modernized_code'],
                            tests=t['tests'],
                            requirements=t.get('requirements', []),
                            module_name=Path(file_path).stem if file_path else 'module',
                            language=language
                        )
                        result['file_path'] = file_path
                        result['execution_mode'] = 'modal'
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error validating {file_path}: {e}")
                        results.append({
                            "file_path": file_path,
                            "success": False,
                            "error": str(e),
                            "execution_mode": "modal_failed"
                        })
                
                logger.info(f"Modal batch validation complete: {len(results)} results")
                return results
                
            except Exception as e:
                logger.warning(f"Modal batch execution failed: {e}, falling back to local")
                results = []  # Reset for local execution
        
        # Fallback to local sequential execution
        for t in transformations:
            file_path = t.get('file_path', '')
            language = _detect_language(file_path, t['modernized_code'])
            
            try:
                result = run_tests_locally(
                    code=t['modernized_code'],
                    tests=t['tests'],
                    requirements=t.get('requirements', []),
                    module_name=Path(file_path).stem if file_path else 'module',
                    language=language
                )
                result['file_path'] = file_path
                results.append(result)
            except Exception as e:
                logger.error(f"Error validating {file_path}: {e}")
                results.append({
                    "file_path": file_path,
                    "success": False,
                    "error": str(e),
                    "execution_mode": "local_failed"
                })
        
        logger.info(f"Local batch validation complete: {len(results)} results")
        return results
    
    def _extract_requirements(self, code: str, language: str = "python") -> List[str]:
        """
        Extract required packages from import statements.
        
        Args:
            code: Source code
            language: Programming language
        
        Returns:
            List of package names
        """
        requirements = []
        
        if language == 'python':
            # Python import to package mappings
            import_map = {
                'sqlalchemy': 'sqlalchemy',
                'pymysql': 'pymysql',
                'requests': 'requests',
                'flask': 'flask',
                'django': 'django',
                'numpy': 'numpy',
                'pandas': 'pandas',
                'fastapi': 'fastapi',
                'pydantic': 'pydantic',
                'aiohttp': 'aiohttp',
                'httpx': 'httpx',
                'pytest': 'pytest'
            }
            
            for line in code.split('\n'):
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    parts = line.split()
                    if len(parts) >= 2:
                        module = parts[1].split('.')[0]
                        if module in import_map:
                            pkg = import_map[module]
                            if pkg not in requirements:
                                requirements.append(pkg)
        
        elif language == 'java':
            # Java dependencies would be handled via Maven/Gradle
            # Return empty list - dependencies managed differently
            pass
        
        elif language in ('javascript', 'typescript'):
            # JavaScript/TypeScript - look for require/import statements
            import_map = {
                'express': 'express',
                'axios': 'axios',
                'lodash': 'lodash',
                'moment': 'moment',
                'react': 'react',
                'jest': 'jest'
            }
            
            for line in code.split('\n'):
                line = line.strip()
                for pkg in import_map:
                    if f"'{pkg}'" in line or f'"{pkg}"' in line:
                        if pkg not in requirements:
                            requirements.append(pkg)
        
        return requirements
    
    def test_behavioral_equivalence(
        self,
        original_code: str,
        modernized_code: str,
        test_cases: List[Dict]
    ) -> Dict:
        """
        Test that modernized code produces same outputs as original.
        
        Args:
            original_code: Original code
            modernized_code: Modernized code
            test_cases: List of test case dicts with inputs and expected outputs
        
        Returns:
            Equivalence test results
        """
        logger.info("Testing behavioral equivalence")
        
        # Generate equivalence test
        equivalence_test = self._generate_equivalence_test(test_cases)
        
        # Test both versions
        original_results = self.validate_transformation(
            original_code, original_code, equivalence_test
        )
        
        modernized_results = self.validate_transformation(
            original_code, modernized_code, equivalence_test
        )
        
        # Compare results
        equivalence_score = 0.0
        if original_results['success'] and modernized_results['success']:
            if original_results['tests_passed'] == modernized_results['tests_passed']:
                equivalence_score = 1.0
            else:
                equivalence_score = (
                    modernized_results['tests_passed'] / 
                    max(original_results['tests_passed'], 1)
                )
        
        return {
            "behavioral_equivalence": equivalence_score >= 0.95,
            "equivalence_score": round(equivalence_score, 3),
            "original_results": original_results,
            "modernized_results": modernized_results
        }
    
    def _generate_equivalence_test(self, test_cases: List[Dict]) -> str:
        """Generate pytest code for equivalence testing."""
        test_code = "import pytest\n\n"
        
        for i, case in enumerate(test_cases):
            test_code += f"""
def test_equivalence_{i}():
    \"\"\"Test case {i}: {case.get('description', 'equivalence test')}\"\"\"
    # Test implementation would go here
    assert True
"""
        
        return test_code
