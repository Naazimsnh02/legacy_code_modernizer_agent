"""
JavaScript/TypeScript test runner for Modal sandbox execution.
Handles Node.js project structure, package.json generation, and Jest execution.
"""

import subprocess
import tempfile
import time
import logging
import json
import re
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def _create_nodejs_project(tmpdir: Path, module_name: str, code: str, tests: str, language: str):
    """
    Create Node.js project structure with package.json and config files.
    
    Args:
        tmpdir: Temporary directory path
        module_name: Name of the module
        code: Source code
        tests: Test code
        language: 'javascript' or 'typescript'
    """
    ext = '.ts' if language == 'typescript' else '.js'
    
    # Write source files
    (tmpdir / f"{module_name}{ext}").write_text(code, encoding='utf-8')
    (tmpdir / f"{module_name}.test{ext}").write_text(tests, encoding='utf-8')
    
    # Generate package.json
    package_json = {
        "name": module_name.replace('_', '-'),
        "version": "1.0.0",
        "type": "module" if language == 'javascript' else None,
        "description": "Modernized code test suite",
        "main": f"{module_name}{ext}",
        "scripts": {
            "test": "NODE_OPTIONS=--experimental-vm-modules jest --coverage --verbose --no-cache" if language == 'javascript' else "jest --coverage --verbose --no-cache"
        },
        "devDependencies": {
            "jest": "^29.7.0"
        }
    }
    
    # Remove None values
    package_json = {k: v for k, v in package_json.items() if v is not None}
    
    if language == 'typescript':
        package_json["devDependencies"].update({
            "typescript": "^5.3.0",
            "ts-jest": "^29.1.0",
            "@types/jest": "^29.5.0",
            "ts-node": "^10.9.0"
        })
        
        # Generate jest.config.js for TypeScript
        jest_config = """module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testMatch: ['**/*.test.ts'],
  collectCoverageFrom: ['*.ts', '!*.test.ts', '!jest.config.js'],
  coverageReporters: ['text', 'text-summary'],
  verbose: true
};
"""
        (tmpdir / "jest.config.js").write_text(jest_config, encoding='utf-8')
        
        # Generate tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "lib": ["ES2020"],
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "resolveJsonModule": True,
                "moduleResolution": "node",
                "types": ["jest", "node"]
            },
            "include": ["*.ts"],
            "exclude": ["node_modules"]
        }
        (tmpdir / "tsconfig.json").write_text(json.dumps(tsconfig, indent=2), encoding='utf-8')
    else:
        # Generate jest.config.js for JavaScript with ES module support
        jest_config = """module.exports = {
  testEnvironment: 'node',
  testMatch: ['**/*.test.js'],
  collectCoverageFrom: ['*.js', '!*.test.js', '!jest.config.js'],
  coverageReporters: ['text', 'text-summary'],
  verbose: true,
  transform: {},
  extensionsToTreatAsEsm: ['.js'],
  moduleNameMapper: {
    '^(\\\\.{1,2}/.*)\\\\.js$': '$1',
  },
};
"""
        (tmpdir / "jest.config.js").write_text(jest_config, encoding='utf-8')
    
    (tmpdir / "package.json").write_text(json.dumps(package_json, indent=2), encoding='utf-8')


def _validate_javascript_tests(tests: str, language: str) -> tuple:
    """
    Validate JavaScript/TypeScript test code before execution.
    
    Returns:
        (is_valid, error_message)
    """
    # Check for Jest test structure
    if "describe(" not in tests and "test(" not in tests and "it(" not in tests:
        return False, "No Jest test functions found (describe/test/it)"
    
    # Check for imports
    if "import" not in tests and "require" not in tests:
        return False, "No import/require statements found"
    
    # Check for expect assertions
    if "expect(" not in tests:
        return False, "No expect() assertions found"
    
    return True, ""


def run_javascript_tests(code: str, tests: str, requirements: List[str], module_name: str, language: str = 'javascript') -> Dict:
    """
    Run JavaScript/TypeScript tests using Jest in Modal container.
    
    Args:
        code: JavaScript/TypeScript source code
        tests: Jest test code
        requirements: List of npm packages to install (not used currently)
        module_name: Name of the module
        language: 'javascript' or 'typescript'
    
    Returns:
        Dictionary with test results
    """
    # Validate tests before execution
    is_valid, error_msg = _validate_javascript_tests(tests, language)
    if not is_valid:
        logger.error(f"Test validation failed: {error_msg}")
        return {
            "success": False,
            "error": f"Test validation failed: {error_msg}",
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "execution_mode": "modal",
            "language": language
        }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        try:
            # Create Node.js project structure
            _create_nodejs_project(tmpdir_path, module_name, code, tests, language)
            logger.info(f"Created Node.js project for {module_name} ({language})")
        except Exception as e:
            logger.error(f"Failed to create Node.js project: {e}")
            return {
                "success": False,
                "error": f"Project setup failed: {str(e)}",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "modal",
                "language": language
            }
        
        start_time = time.time()
        
        try:
            # Install dependencies
            logger.info("Installing npm dependencies...")
            install_result = subprocess.run(
                ["npm", "install", "--silent", "--no-fund", "--no-audit"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes for npm install
            )
            
            if install_result.returncode != 0:
                logger.error(f"npm install failed with return code: {install_result.returncode}")
                logger.error(f"npm install stderr: {install_result.stderr}")
                logger.error(f"npm install stdout: {install_result.stdout}")
                return {
                    "success": False,
                    "error": f"npm install failed: {install_result.stderr}",
                    "tests_run": 0,
                    "tests_passed": 0,
                    "tests_failed": 0,
                    "execution_mode": "modal",
                    "language": language
                }
            
            # Run tests
            logger.info("Running Jest tests...")
            result = subprocess.run(
                ["npm", "test", "--", "--ci"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes for tests
            )
        except subprocess.TimeoutExpired as e:
            return {
                "success": False,
                "error": f"Test execution timeout: {str(e)}",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_time": 300.0,
                "execution_mode": "modal",
                "language": language
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Node.js/npm not found in container",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "modal",
                "language": language
            }
        
        execution_time = time.time() - start_time
        stdout = result.stdout[:10000]  # Truncate to prevent memory issues
        stderr = result.stderr[:10000]
        
        # Parse Jest output - handle all possible formats
        # Jest format examples:
        # - "Tests: 5 passed, 5 total"
        # - "Tests: 1 failed, 4 passed, 5 total"
        # - "Tests: 2 skipped, 3 passed, 5 total"
        # - "Tests: 1 todo, 4 passed, 5 total"
        # - "Tests: 0 total"
        tests_run = 0
        tests_passed = 0
        tests_failed = 0
        tests_skipped = 0
        
        # Look for "Tests:" line
        tests_line_match = re.search(r'Tests:\s+(.+)', stdout)
        if tests_line_match:
            tests_line = tests_line_match.group(1)
            
            # Extract total
            total_match = re.search(r'(\d+)\s+total', tests_line)
            if total_match:
                tests_run = int(total_match.group(1))
            
            # Extract passed
            passed_match = re.search(r'(\d+)\s+passed', tests_line)
            if passed_match:
                tests_passed = int(passed_match.group(1))
            
            # Extract failed
            failed_match = re.search(r'(\d+)\s+failed', tests_line)
            if failed_match:
                tests_failed = int(failed_match.group(1))
            
            # Extract skipped
            skipped_match = re.search(r'(\d+)\s+skipped', tests_line)
            if skipped_match:
                tests_skipped = int(skipped_match.group(1))
            
            # If we have total but not passed, calculate it
            if tests_run > 0 and tests_passed == 0 and tests_failed == 0:
                tests_passed = tests_run - tests_failed - tests_skipped
        
        # Check for test suite failures (compilation errors, etc.)
        if "Test Suites: " in stdout and " failed" in stdout:
            suite_match = re.search(r'Test Suites:\s+(\d+)\s+failed', stdout)
            if suite_match and tests_run == 0:
                return {
                    "success": False,
                    "error": "Test suite failed to run (compilation/syntax error)",
                    "tests_run": 0,
                    "tests_passed": 0,
                    "tests_failed": 0,
                    "execution_mode": "modal",
                    "language": language,
                    "stdout": stdout,
                    "stderr": stderr
                }
        
        # Extract coverage percentage
        coverage_percent = 0.0
        # Jest coverage format: "All files | 85.71 | 75 | 100 | 85.71 |"
        cov_match = re.search(r'All files\s*\|\s*([\d.]+)', stdout)
        if cov_match:
            coverage_percent = float(cov_match.group(1))
        
        return {
            "success": result.returncode == 0,
            "tests_run": tests_run,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "execution_time": round(execution_time, 2),
            "coverage_percent": coverage_percent,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "execution_mode": "modal",
            "language": language
        }
