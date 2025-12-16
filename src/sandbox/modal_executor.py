"""
Modal-based test executor using Modal Sandboxes for multi-language support.
Uses Sandbox.exec() API for more flexible and reliable language execution.
Supports: Python, Java, JavaScript, TypeScript, and more.
"""

import logging
import tempfile
import json
from typing import Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import Modal
try:
    import modal
    import os
    
    # Configure Modal authentication from environment if available
    token_id = os.getenv("MODAL_TOKEN_ID")
    token_secret = os.getenv("MODAL_TOKEN_SECRET")
    
    if token_id and token_secret:
        # Set Modal credentials from environment variables
        # This is needed for Hugging Face Spaces deployment
        os.environ["MODAL_TOKEN_ID"] = token_id
        os.environ["MODAL_TOKEN_SECRET"] = token_secret
        logger.info("Modal credentials loaded from environment")
    
    MODAL_AVAILABLE = True
except ImportError:
    MODAL_AVAILABLE = False
    modal = None
    logger.warning("Modal not available - install with: pip install modal")

if MODAL_AVAILABLE:
    from .images import LANGUAGE_IMAGES
    
    def _execute_python_in_sandbox(sb: modal.Sandbox, code: str, tests: str, 
                                    module_name: str) -> Dict:
        """Execute Python tests in Modal Sandbox using pytest."""
        try:
            # Ensure workspace directory exists
            p = sb.exec("mkdir", "-p", "/workspace", timeout=30)
            p.wait()
            
            # Create a combined test file
            test_content = f"""# Test module
{code}

# Tests
{tests}
"""
            
            # Upload files to sandbox
            with sb.open(f"/workspace/test_{module_name}.py", "w") as f:
                f.write(test_content)
            
            # Run pytest
            p = sb.exec("python", "-m", "pytest", f"/workspace/test_{module_name}.py", 
                       "-v", "--tb=short", timeout=120)
            p.wait()
            
            stdout = p.stdout.read()
            stderr = p.stderr.read()
            
            logger.info(f"Python test output: {stdout}")
            
            # Parse results
            success = p.returncode == 0
            
            return {
                "success": success,
                "tests_run": 1,
                "tests_passed": 1 if success else 0,
                "tests_failed": 0 if success else 1,
                "stdout": stdout,
                "stderr": stderr,
                "execution_mode": "modal",
                "language": "python"
            }
        except Exception as e:
            logger.error(f"Python sandbox execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Python execution error: {str(e)}",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "modal",
                "language": "python"
            }
    
    def _execute_java_in_sandbox(sb: modal.Sandbox, code: str, tests: str, 
                                  module_name: str) -> Dict:
        """Execute Java tests in Modal Sandbox using Maven."""
        try:
            # Ensure workspace directory exists
            p = sb.exec("mkdir", "-p", "/workspace", timeout=30)
            p.wait()
            
            # Create Maven project structure
            # Create pom.xml
            pom_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>{module_name}</artifactId>
    <version>1.0.0</version>
    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>5.9.0</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>2.22.2</version>
            </plugin>
        </plugins>
    </build>
</project>"""
            
            # Upload files to sandbox
            with sb.open(f"/workspace/{module_name}.java", "w") as f:
                f.write(code)
            with sb.open(f"/workspace/{module_name}Test.java", "w") as f:
                f.write(tests)
            with sb.open(f"/workspace/pom.xml", "w") as f:
                f.write(pom_xml)
            # Run Maven tests
            p = sb.exec("bash", "-c", "cd /workspace && mvn test -q 2>&1", timeout=120)
            p.wait()
            
            stdout = p.stdout.read()
            stderr = p.stderr.read()
            
            logger.info(f"Maven test output: {stdout}")
            if p.returncode == 0:
                return {
                    "success": True,
                    "tests_run": 1,
                    "tests_passed": 1,
                    "tests_failed": 0,
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_mode": "modal",
                    "language": "java"
                }
            else:
                return {
                    "success": False,
                    "error": f"Tests failed: {stderr}",
                    "tests_run": 1,
                    "tests_passed": 0,
                    "tests_failed": 1,
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_mode": "modal",
                    "language": "java"
                }
        except Exception as e:
            logger.error(f"Java sandbox execution failed: {e}")
            return {
                "success": False,
                "error": f"Java execution error: {str(e)}",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "modal",
                "language": "java"
            }
    
    def _execute_javascript_in_sandbox(sb: modal.Sandbox, code: str, tests: str,
                                       module_name: str, language: str = 'javascript') -> Dict:
        """Execute JavaScript/TypeScript tests in Modal Sandbox using Jest."""
        try:
            # Ensure workspace directory exists
            p = sb.exec("mkdir", "-p", "/workspace", timeout=30)
            p.wait()
            ext = '.ts' if language == 'typescript' else '.js'
            
            # Create package.json
            package_json = {
                "name": module_name.replace('_', '-'),
                "version": "1.0.0",
                "description": "Test suite",
                "scripts": {
                    "test": "jest --json"
                },
                "devDependencies": {
                    "jest": "^29.0.0"
                }
            }
            
            # For JavaScript, use ES modules with proper Jest config
            # For TypeScript, use ts-jest preset
            if language == 'javascript':
                package_json["type"] = "module"
            elif language == 'typescript':
                package_json["devDependencies"]["ts-jest"] = "^29.0.0"
                package_json["devDependencies"]["typescript"] = "^5.0.0"
                package_json["devDependencies"]["@types/jest"] = "^29.0.0"
            
            # Create Jest config
            jest_config = {
                "testEnvironment": "node",
                "testMatch": ["**/*.test.js", "**/*.test.ts"]
            }
            
            if language == 'javascript':
                # Configure Jest for ES modules
                jest_config["transform"] = {}
                jest_config["extensionsToTreatAsEsm"] = [".js"]
            elif language == 'typescript':
                jest_config["preset"] = "ts-jest"
                jest_config["moduleNameMapper"] = {
                    "^(\\.{1,2}/.*)\\.ts$": "$1"
                }
            
            # Upload files to sandbox
            with sb.open(f"/workspace/{module_name}{ext}", "w") as f:
                f.write(code)
            with sb.open(f"/workspace/{module_name}.test{ext}", "w") as f:
                f.write(tests)
            with sb.open(f"/workspace/package.json", "w") as f:
                f.write(json.dumps(package_json, indent=2))
            with sb.open(f"/workspace/jest.config.json", "w") as f:
                f.write(json.dumps(jest_config, indent=2))
            
            # For TypeScript, create tsconfig.json
            if language == 'typescript':
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
                with sb.open(f"/workspace/tsconfig.json", "w") as f:
                    f.write(json.dumps(tsconfig, indent=2))
            
            # Install dependencies and run tests
            p = sb.exec("bash", "-c", 
                       "cd /workspace && npm install --legacy-peer-deps && npm test 2>&1",
                       timeout=180)
            p.wait()
            
            stdout = p.stdout.read()
            stderr = p.stderr.read()
            
            logger.info(f"Jest test output: {stdout}")
            
            # Parse Jest JSON output if available
            try:
                # Extract JSON from output (Jest outputs to stdout)
                lines = stdout.split('\n')
                json_str = None
                for line in lines:
                    if line.strip().startswith('{') and 'numTotalTests' in line:
                        json_str = line
                        break
                
                if json_str:
                    result = json.loads(json_str)
                    tests_run = result.get('numTotalTests', 0)
                    tests_passed = result.get('numPassedTests', 0)
                    tests_failed = result.get('numFailedTests', 0)
                    success = result.get('success', False)
                else:
                    tests_run = 1 if p.returncode == 0 else 1
                    tests_passed = 1 if p.returncode == 0 else 0
                    tests_failed = 0 if p.returncode == 0 else 1
                    success = p.returncode == 0
            except Exception as parse_error:
                logger.warning(f"Could not parse Jest JSON output: {parse_error}")
                tests_run = 1
                tests_passed = 1 if p.returncode == 0 else 0
                tests_failed = 0 if p.returncode == 0 else 1
                success = p.returncode == 0
            
            return {
                "success": success,
                "tests_run": tests_run,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "stdout": stdout,
                "stderr": stderr,
                "execution_mode": "modal",
                "language": language
            }
        except Exception as e:
            logger.error(f"JavaScript sandbox execution failed: {e}")
            return {
                "success": False,
                "error": f"{language} execution error: {str(e)}",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "modal",
                "language": language
            }
    
    def execute_in_modal(code: str, tests: str, requirements: List[str], 
                        module_name: str, language: str) -> Dict:
        """
        Execute tests in Modal Sandbox with proper image configuration.
        Uses Sandbox.exec() for better multi-language support.
        
        Args:
            code: Source code
            tests: Test code
            requirements: Package requirements
            module_name: Module name
            language: Programming language
        
        Returns:
            Test execution results
        """
        lang_lower = language.lower()
        
        if lang_lower not in LANGUAGE_IMAGES:
            return {
                "success": False,
                "error": f"Unsupported language: {language}",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "unsupported",
                "language": language
            }
        
        try:
            logger.info(f"Executing {language} tests in Modal Sandbox...")
            
            # Get the appropriate image for this language
            image = LANGUAGE_IMAGES[lang_lower]
            
            # Create app for this execution
            app = modal.App.lookup("legacy-code-validator", create_if_missing=True)
            
            # Create sandbox with appropriate image
            with modal.enable_output():
                sb = modal.Sandbox.create(
                    image=image,
                    app=app,
                    timeout=300,
                    cpu=2.0,
                    memory=4096
                )
                
                try:
                    # Dispatch to language-specific executor
                    if lang_lower == 'python':
                        result = _execute_python_in_sandbox(sb, code, tests, module_name)
                    elif lang_lower == 'java':
                        result = _execute_java_in_sandbox(sb, code, tests, module_name)
                    elif lang_lower in ('javascript', 'typescript'):
                        result = _execute_javascript_in_sandbox(sb, code, tests, module_name, lang_lower)
                    else:
                        result = {
                            "success": False,
                            "error": f"No executor for language: {language}",
                            "tests_run": 0,
                            "tests_passed": 0,
                            "tests_failed": 0,
                            "execution_mode": "modal",
                            "language": language
                        }
                    
                    result['execution_mode'] = 'modal'
                    return result
                finally:
                    sb.terminate()
            
        except Exception as e:
            logger.error(f"Modal sandbox execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Modal sandbox error: {str(e)}",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "modal_error",
                "language": language
            }

else:
    # Stub when Modal not available
    def execute_in_modal(code: str, tests: str, requirements: List[str], 
                        module_name: str, language: str) -> Dict:
        """Stub function when Modal is not available."""
        return {
            "success": False,
            "error": "Modal not available",
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "execution_mode": "modal_unavailable",
            "language": language
        }
