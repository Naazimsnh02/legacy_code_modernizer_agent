"""
Language-specific test runners for Modal sandbox execution.
Each runner handles project structure, build files, and test execution for its language.
"""

from .python_runner import run_python_tests
from .java_runner import run_java_tests
from .javascript_runner import run_javascript_tests

__all__ = [
    'run_python_tests',
    'run_java_tests',
    'run_javascript_tests',
]

# Registry of all available runners
LANGUAGE_RUNNERS = {
    'python': run_python_tests,
    'java': run_java_tests,
    'javascript': run_javascript_tests,
    'typescript': run_javascript_tests,  # TypeScript uses JS runner
}


def get_runner_for_language(language: str):
    """Get the appropriate test runner function for a language."""
    return LANGUAGE_RUNNERS.get(language.lower())


def is_runner_available(language: str) -> bool:
    """Check if a test runner is available for a language."""
    return language.lower() in LANGUAGE_RUNNERS
