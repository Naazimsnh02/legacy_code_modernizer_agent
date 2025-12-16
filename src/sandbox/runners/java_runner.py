"""
Java test runner for Modal sandbox execution.
Handles Maven project structure, pom.xml generation, and JUnit 5 execution.
"""

import subprocess
import tempfile
import time
import logging
import re
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def _extract_class_name(code: str, module_name: str) -> str:
    """Extract Java class name from code."""
    match = re.search(r'public\s+class\s+(\w+)', code)
    if match:
        return match.group(1)
    
    # Fallback: convert module_name to PascalCase
    return ''.join(word.capitalize() for word in module_name.split('_'))


def _create_maven_project(tmpdir: Path, module_name: str, code: str, tests: str) -> str:
    """
    Create Maven project structure with proper directory layout.
    
    Returns:
        Class name extracted from code
    """
    # Extract class names
    main_class = _extract_class_name(code, module_name)
    test_class = _extract_class_name(tests, f"{module_name}Test")
    
    # Create Maven directory structure
    src_main = tmpdir / "src" / "main" / "java" / "com" / "modernizer"
    src_test = tmpdir / "src" / "test" / "java" / "com" / "modernizer"
    src_main.mkdir(parents=True)
    src_test.mkdir(parents=True)
    
    # Add package declaration if not present
    if "package " not in code:
        code = "package com.modernizer;\n\n" + code
    if "package " not in tests:
        tests = "package com.modernizer;\n\n" + tests
    
    # Write source files
    (src_main / f"{main_class}.java").write_text(code, encoding='utf-8')
    (src_test / f"{test_class}.java").write_text(tests, encoding='utf-8')
    
    # Generate pom.xml
    pom_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.modernizer</groupId>
    <artifactId>{module_name}</artifactId>
    <version>1.0-SNAPSHOT</version>
    <packaging>jar</packaging>
    
    <properties>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <junit.version>5.10.1</junit.version>
    </properties>
    
    <dependencies>
        <!-- JUnit 5 -->
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>${{junit.version}}</version>
            <scope>test</scope>
        </dependency>
        
        <!-- Mockito for mocking -->
        <dependency>
            <groupId>org.mockito</groupId>
            <artifactId>mockito-core</artifactId>
            <version>5.7.0</version>
            <scope>test</scope>
        </dependency>
        
        <dependency>
            <groupId>org.assertj</groupId>
            <artifactId>assertj-core</artifactId>
            <version>3.24.2</version>
            <scope>test</scope>
        </dependency>

        <!-- Servlet API -->
        <dependency>
            <groupId>javax.servlet</groupId>
            <artifactId>javax.servlet-api</artifactId>
            <version>4.0.1</version>
            <scope>provided</scope>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <!-- Maven Compiler Plugin -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
                <configuration>
                    <source>17</source>
                    <target>17</target>
                </configuration>
            </plugin>
            
            <!-- Maven Surefire Plugin for running tests -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.2.2</version>
                <configuration>
                    <includes>
                        <include>**/*Test.java</include>
                    </includes>
                </configuration>
            </plugin>
            
            <!-- JaCoCo for code coverage -->
            <plugin>
                <groupId>org.jacoco</groupId>
                <artifactId>jacoco-maven-plugin</artifactId>
                <version>0.8.11</version>
                <executions>
                    <execution>
                        <goals>
                            <goal>prepare-agent</goal>
                        </goals>
                    </execution>
                    <execution>
                        <id>report</id>
                        <phase>test</phase>
                        <goals>
                            <goal>report</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>
"""
    (tmpdir / "pom.xml").write_text(pom_xml, encoding='utf-8')
    
    return main_class


def _validate_java_tests(tests: str) -> tuple:
    """
    Validate Java test code before execution.
    
    Returns:
        (is_valid, error_message)
    """
    # Check for JUnit 5 annotations
    if "@Test" not in tests:
        return False, "No @Test annotations found (required for JUnit 5)"
    
    # Check for JUnit imports
    if "org.junit" not in tests:
        return False, "Missing JUnit imports (import org.junit.jupiter.api.Test)"
    
    # Check for test class
    if "class" not in tests:
        return False, "No test class found"
    
    return True, ""


def run_java_tests(code: str, tests: str, requirements: List[str], module_name: str) -> Dict:
    """
    Run Java tests using Maven and JUnit 5 in Modal container.
    
    Args:
        code: Java source code
        tests: JUnit test code
        requirements: List of Maven dependencies (not used currently)
        module_name: Name of the module
    
    Returns:
        Dictionary with test results
    """
    # Validate tests before execution
    is_valid, error_msg = _validate_java_tests(tests)
    if not is_valid:
        logger.error(f"Test validation failed: {error_msg}")
        return {
            "success": False,
            "error": f"Test validation failed: {error_msg}",
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "execution_mode": "modal",
            "language": "java"
        }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        try:
            # Create Maven project structure
            class_name = _create_maven_project(tmpdir_path, module_name, code, tests)
            logger.info(f"Created Maven project for class: {class_name}")
        except Exception as e:
            logger.error(f"Failed to create Maven project: {e}")
            return {
                "success": False,
                "error": f"Project setup failed: {str(e)}",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "modal",
                "language": "java"
            }
        
        start_time = time.time()
        
        try:
            # Run Maven clean test
            logger.info("Running Maven tests...")
            result = subprocess.run(
                ["mvn", "clean", "test", "-B", "-q"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for Maven
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Maven test execution timeout (>5 minutes)",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_time": 300.0,
                "execution_mode": "modal",
                "language": "java"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Maven (mvn) not found in container",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "modal",
                "language": "java"
            }
        
        execution_time = time.time() - start_time
        stdout = result.stdout[:10000]  # Truncate to prevent memory issues
        stderr = result.stderr[:10000]
        
        # Check for compilation/build failures first
        if "BUILD FAILURE" in stdout or "COMPILATION ERROR" in stdout or "BUILD FAILURE" in stderr:
            error_msg = "Maven build failed"
            # Try to extract specific error
            if "COMPILATION ERROR" in stdout:
                error_msg = "Java compilation error"
            elif "[ERROR]" in stdout:
                # Extract first error line
                for line in stdout.split('\n'):
                    if '[ERROR]' in line and 'Failed to execute goal' not in line:
                        error_msg = line.strip()
                        break
            
            return {
                "success": False,
                "error": error_msg,
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "modal",
                "language": "java",
                "stdout": stdout,
                "stderr": stderr
            }
        
        # Parse Maven Surefire output
        # Format: "Tests run: X, Failures: Y, Errors: Z, Skipped: W"
        tests_run = 0
        tests_passed = 0
        tests_failed = 0
        tests_errors = 0
        tests_skipped = 0
        
        match = re.search(r'Tests run: (\d+),\s*Failures: (\d+),\s*Errors: (\d+),\s*Skipped: (\d+)', stdout)
        if match:
            tests_run = int(match.group(1))
            failures = int(match.group(2))
            tests_errors = int(match.group(3))
            tests_skipped = int(match.group(4))
            tests_failed = failures + tests_errors
            tests_passed = tests_run - tests_failed - tests_skipped
        elif tests_run == 0 and result.returncode == 0:
            # Maven succeeded but no tests found - this is suspicious
            logger.warning("Maven succeeded but no tests were detected")
            return {
                "success": False,
                "error": "No tests detected by Maven Surefire (missing @Test annotations?)",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "execution_mode": "modal",
                "language": "java",
                "stdout": stdout,
                "stderr": stderr
            }
        
        # Try to extract coverage from JaCoCo report
        coverage_percent = 0.0
        jacoco_report = tmpdir_path / "target" / "site" / "jacoco" / "index.html"
        if jacoco_report.exists():
            try:
                report_content = jacoco_report.read_text()
                # Extract coverage percentage from JaCoCo HTML report
                cov_match = re.search(r'Total.*?(\d+)%', report_content)
                if cov_match:
                    coverage_percent = float(cov_match.group(1))
            except Exception as e:
                logger.warning(f"Failed to parse JaCoCo coverage: {e}")
        
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
            "language": "java"
        }
