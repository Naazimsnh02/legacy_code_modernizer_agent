"""
Python test runner for Modal sandbox execution.
Handles pytest execution with proper path setup and result parsing.
"""

import subprocess
import tempfile
import time
import logging
import re
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def _validate_python_tests(tests: str) -> tuple:
    """
    Validate Python test code before execution.
    
    Returns:
        (is_valid, error_message)
    """
    # Check for basic pytest structure
    if "def test_" not in tests and "class Test" not in tests:
        return False, "No test functions found (must start with 'test_' or be in 'Test' class)"
    
    # Check for imports
    if "import" not in tests:
        return False, "No import statements found"
    
    # Check for basic syntax issues
    try:
        compile(tests, '<string>', 'exec')
    except SyntaxError as e:
        return False, f"Syntax error in test code: {str(e)}"
    
    return True, ""


def run_python_tests(code: str, tests: str, requirements: List[str], module_name: str) -> Dict:
    """
    Run Python tests using pytest in Modal container.
    
    Args:
        code: Python source code
        tests: Pytest test code
        requirements: List of pip packages to install
        module_name: Name of the module
    
    Returns:
        Dictionary with test results
    """
    # Validate tests before execution
    is_valid, error_msg = _validate_python_tests(tests)
    if not is_valid:
        logger.error(f"Test validation failed: {error_msg}")
        return {
            "success": False,
            "error": f"Test validation failed: {error_msg}",
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "execution_mode": "modal",
            "language": "python"
        }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Write code and tests in same directory for proper imports
        code_file = tmpdir_path / f"{module_name}.py"
        test_file = tmpdir_path / f"test_{module_name}.py"
        
        # Ensure tests have proper path setup
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
                logger.info(f"Installing requirements: {requirements}")
                install_result = subprocess.run(
                    ["pip", "install", "-q", "--no-cache-dir"] + requirements,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                if install_result.returncode != 0:
                    logger.warning(f"Some requirements failed to install: {install_result.stderr}")
            except Exception as e:
                logger.warning(f"Failed to install requirements: {e}")
        
        start_time = time.time()
        
        try:
            # Run pytest with coverage and verbose output
            result = subprocess.run(
                [
                    "pytest",
                    str(test_file),
                    "-v",
                    "--tb=short",
                    "--timeout=30",
                    "-p", "no:warnings",
                    "--cov=" + module_name,
                    "--cov-report=term-missing"
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
                "execution_mode": "modal",
                "language": "python"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "pytest not found in container",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "modal",
                "language": "python"
            }
        
        execution_time = time.time() - start_time
        stdout = result.stdout[:10000]  # Truncate to prevent memory issues
        stderr = result.stderr[:10000]
        
        # Parse pytest output from summary line (more reliable than counting)
        # Format: "3 passed, 1 failed, 1 skipped in 0.5s" or "3 passed in 0.5s"
        tests_run = 0
        tests_passed = 0
        tests_failed = 0
        tests_errors = 0
        tests_skipped = 0
        
        # Look for summary line
        summary_match = re.search(r'=+\s*(.*?)\s+in\s+[\d.]+s\s*=+', stdout)
        if summary_match:
            summary = summary_match.group(1)
            
            # Parse each component
            passed_match = re.search(r'(\d+)\s+passed', summary)
            if passed_match:
                tests_passed = int(passed_match.group(1))
            
            failed_match = re.search(r'(\d+)\s+failed', summary)
            if failed_match:
                tests_failed = int(failed_match.group(1))
            
            error_match = re.search(r'(\d+)\s+error', summary)
            if error_match:
                tests_errors = int(error_match.group(1))
            
            skipped_match = re.search(r'(\d+)\s+skipped', summary)
            if skipped_match:
                tests_skipped = int(skipped_match.group(1))
            
            tests_run = tests_passed + tests_failed + tests_errors + tests_skipped
        
        # Fallback: count individual test results if summary not found
        if tests_run == 0:
            passed = stdout.count(" PASSED\n")
            failed = stdout.count(" FAILED\n")
            errors = stdout.count(" ERROR\n")
            skipped = stdout.count(" SKIPPED\n")
            tests_run = passed + failed + errors
            tests_passed = passed
            tests_failed = failed
            tests_errors = errors
            tests_skipped = skipped
        
        # Extract coverage percentage from summary
        coverage_percent = 0.0
        # Look for coverage summary: "TOTAL    100   20    80%"
        cov_match = re.search(r'TOTAL\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)%', stdout)
        if cov_match:
            coverage_percent = float(cov_match.group(1))
        else:
            # Alternative format: "TOTAL    80%"
            cov_match = re.search(r'TOTAL.*?(\d+)%', stdout)
            if cov_match:
                coverage_percent = float(cov_match.group(1))
        
        return {
            "success": result.returncode == 0,
            "tests_run": tests_run,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "tests_errors": tests_errors,
            "tests_skipped": tests_skipped,
            "execution_time": round(execution_time, 2),
            "coverage_percent": coverage_percent,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "execution_mode": "modal",
            "language": "python"
        }
