"""
Code Validator - Validates generated code for common issues.
Catches problems before they reach the sandbox execution phase.
"""

import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class CodeValidator:
    """Validates generated code for common issues and inconsistencies."""
    
    @staticmethod
    def validate_typescript_module_system(source_code: str) -> Tuple[bool, List[str]]:
        """
        Validate that TypeScript code is compatible with Jest/ts-jest (CommonJS).
        
        Args:
            source_code: TypeScript source code
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for ES module-only features that break Jest/ts-jest
        if 'import.meta' in source_code:
            issues.append(
                "Code uses 'import.meta' which requires ES modules. "
                "Jest/ts-jest uses CommonJS. Remove import.meta usage."
            )
        
        if re.search(r'\btop-level\s+await\b', source_code) or re.search(r'^await\s+', source_code, re.MULTILINE):
            issues.append(
                "Code uses top-level await which requires ES modules. "
                "Jest/ts-jest uses CommonJS. Wrap in async function."
            )
        
        # Check for CLI execution patterns that shouldn't be in library code
        if 'process.argv[1]' in source_code or 'if (require.main === module)' in source_code:
            issues.append(
                "Code includes CLI execution logic. "
                "Library code should not include main execution blocks."
            )
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_typescript_exports(source_code: str, test_code: str) -> Tuple[bool, List[str]]:
        """
        Validate that all TypeScript types/enums/interfaces imported in tests are exported in source.
        
        Args:
            source_code: TypeScript source code
            test_code: TypeScript test code
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Extract imports from test code
        import_pattern = r'import\s+\{([^}]+)\}\s+from\s+["\']\./'
        test_imports = re.findall(import_pattern, test_code)
        
        if not test_imports:
            return True, []
        
        # Get all imported names
        imported_names = set()
        for import_group in test_imports:
            names = [name.strip() for name in import_group.split(',')]
            imported_names.update(names)
        
        # Check if each imported name is exported in source
        for name in imported_names:
            # Check for export function/class/enum/interface/type
            export_patterns = [
                rf'export\s+(function|class|enum|interface|type)\s+{name}\b',
                rf'export\s+\{{\s*[^}}]*\b{name}\b[^}}]*\}}',
                rf'export\s+const\s+{name}\s*=',
            ]
            
            is_exported = any(re.search(pattern, source_code) for pattern in export_patterns)
            
            if not is_exported:
                # Check if it's declared but not exported
                declaration_patterns = [
                    rf'\b(function|class|enum|interface|type)\s+{name}\b',
                    rf'\bconst\s+{name}\s*=',
                ]
                is_declared = any(re.search(pattern, source_code) for pattern in declaration_patterns)
                
                if is_declared:
                    issues.append(
                        f"'{name}' is declared in source but not exported. "
                        f"Add 'export' keyword before the declaration."
                    )
                else:
                    issues.append(
                        f"'{name}' is imported in tests but not found in source code."
                    )
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_javascript_exports(source_code: str, test_code: str) -> Tuple[bool, List[str]]:
        """
        Validate that all JavaScript functions/classes imported in tests are exported in source.
        
        Args:
            source_code: JavaScript source code
            test_code: JavaScript test code
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Extract imports from test code (ES6 imports)
        import_pattern = r'import\s+\{([^}]+)\}\s+from\s+["\']\./'
        test_imports = re.findall(import_pattern, test_code)
        
        if not test_imports:
            return True, []
        
        # Get all imported names
        imported_names = set()
        for import_group in test_imports:
            names = [name.strip() for name in import_group.split(',')]
            imported_names.update(names)
        
        # Check if each imported name is exported in source
        for name in imported_names:
            # Check for various export patterns
            export_patterns = [
                rf'export\s+(function|class|const|let|var)\s+{name}\b',
                rf'export\s+\{{\s*[^}}]*\b{name}\b[^}}]*\}}',
                rf'module\.exports\s*=\s*\{{[^}}]*\b{name}\b[^}}]*\}}',
                rf'exports\.{name}\s*=',
            ]
            
            is_exported = any(re.search(pattern, source_code) for pattern in export_patterns)
            
            if not is_exported:
                issues.append(
                    f"'{name}' is imported in tests but not exported in source. "
                    f"Add it to the export statement."
                )
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_python_imports(source_code: str, test_code: str) -> Tuple[bool, List[str]]:
        """
        Validate that all Python functions/classes imported in tests exist in source.
        
        Args:
            source_code: Python source code
            test_code: Python test code
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Extract imports from test code
        import_patterns = [
            r'from\s+\w+\s+import\s+([^#\n]+)',
            r'import\s+(\w+)',
        ]
        
        imported_names = set()
        for pattern in import_patterns:
            matches = re.findall(pattern, test_code)
            for match in matches:
                names = [name.strip() for name in match.split(',')]
                imported_names.update(names)
        
        # Check if each imported name is defined in source
        for name in imported_names:
            # Check for function/class definitions
            definition_patterns = [
                rf'^def\s+{name}\s*\(',
                rf'^class\s+{name}\b',
                rf'^{name}\s*=',
            ]
            
            is_defined = any(re.search(pattern, source_code, re.MULTILINE) for pattern in definition_patterns)
            
            if not is_defined:
                issues.append(
                    f"'{name}' is imported in tests but not defined in source code."
                )
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_code(source_code: str, test_code: str, language: str) -> Tuple[bool, List[str]]:
        """
        Validate code based on language.
        
        Args:
            source_code: Source code
            test_code: Test code
            language: Programming language
        
        Returns:
            (is_valid, list_of_issues)
        """
        language = language.lower()
        all_issues = []
        
        if language == 'typescript':
            # Check module system compatibility
            is_valid_module, module_issues = CodeValidator.validate_typescript_module_system(source_code)
            all_issues.extend(module_issues)
            
            # Check exports
            is_valid_exports, export_issues = CodeValidator.validate_typescript_exports(source_code, test_code)
            all_issues.extend(export_issues)
            
            return len(all_issues) == 0, all_issues
        elif language == 'javascript':
            return CodeValidator.validate_javascript_exports(source_code, test_code)
        elif language == 'python':
            return CodeValidator.validate_python_imports(source_code, test_code)
        else:
            # No validation for other languages yet
            return True, []
    
    @staticmethod
    def auto_fix_typescript_module_system(source_code: str) -> str:
        """
        Remove ES module-only features that break Jest/ts-jest.
        
        Args:
            source_code: TypeScript source code
        
        Returns:
            Fixed source code
        """
        fixed_code = source_code
        
        # Remove import.meta usage and related code
        if 'import.meta' in fixed_code:
            # Remove the entire CLI execution block that uses import.meta
            # Pattern: from import statement to the end of the if block
            pattern = r'\n// Modern ES module.*?\n.*?import.*?from [\'"]url[\'"];.*?\n.*?import.*?from [\'"]path[\'"];.*?\n\nconst __filename.*?import\.meta\.url\);.*?\n.*?if \(process\.argv\[1\].*?\{.*?\n.*?\n.*?\n\}'
            fixed_code = re.sub(pattern, '', fixed_code, flags=re.DOTALL)
            
            # Fallback: remove just the import.meta line
            if 'import.meta' in fixed_code:
                fixed_code = re.sub(r'.*import\.meta.*\n', '', fixed_code)
            
            logger.info("Auto-fixed: Removed import.meta usage")
        
        # Remove CLI execution patterns
        if 'process.argv[1]' in fixed_code:
            # Remove if (process.argv[1] === __filename) blocks
            pattern = r'\nif \(process\.argv\[1\].*?\{[^}]*\}'
            fixed_code = re.sub(pattern, '', fixed_code, flags=re.DOTALL)
            logger.info("Auto-fixed: Removed CLI execution block")
        
        return fixed_code
    
    @staticmethod
    def auto_fix_typescript_exports(source_code: str, missing_exports: List[str]) -> str:
        """
        Automatically add export keywords to TypeScript declarations.
        
        Args:
            source_code: TypeScript source code
            missing_exports: List of names that need to be exported
        
        Returns:
            Fixed source code
        """
        fixed_code = source_code
        
        for name in missing_exports:
            # Try to add export keyword before declaration
            patterns = [
                (rf'(\n)(enum\s+{name}\b)', r'\1export \2'),
                (rf'(\n)(interface\s+{name}\b)', r'\1export \2'),
                (rf'(\n)(type\s+{name}\b)', r'\1export \2'),
                (rf'(\n)(class\s+{name}\b)', r'\1export \2'),
                (rf'(\n)(function\s+{name}\b)', r'\1export \2'),
                (rf'(\n)(const\s+{name}\s*=)', r'\1export \2'),
            ]
            
            for pattern, replacement in patterns:
                new_code = re.sub(pattern, replacement, fixed_code)
                if new_code != fixed_code:
                    logger.info(f"Auto-fixed: Added 'export' to '{name}'")
                    fixed_code = new_code
                    break
        
        return fixed_code


def validate_and_fix_code(source_code: str, test_code: str, language: str) -> Tuple[str, bool, List[str]]:
    """
    Validate code and attempt to auto-fix common issues.
    
    Args:
        source_code: Source code
        test_code: Test code
        language: Programming language
    
    Returns:
        (fixed_source_code, is_valid, list_of_remaining_issues)
    """
    validator = CodeValidator()
    is_valid, issues = validator.validate_code(source_code, test_code, language)
    
    if not is_valid and language.lower() == 'typescript':
        fixed_code = source_code
        
        # Auto-fix module system issues (import.meta, etc.)
        module_issues = [issue for issue in issues if 'import.meta' in issue or 'top-level await' in issue or 'CLI execution' in issue]
        if module_issues:
            logger.info(f"Attempting to auto-fix {len(module_issues)} module system issues")
            fixed_code = validator.auto_fix_typescript_module_system(fixed_code)
        
        # Auto-fix export issues
        missing_names = []
        for issue in issues:
            # Extract name from issue message
            match = re.search(r"'(\w+)'", issue)
            if match and "not exported" in issue:
                missing_names.append(match.group(1))
        
        if missing_names:
            logger.info(f"Attempting to auto-fix {len(missing_names)} export issues")
            fixed_code = validator.auto_fix_typescript_exports(fixed_code, missing_names)
        
        # Re-validate if we made any fixes
        if fixed_code != source_code:
            is_valid, issues = validator.validate_code(fixed_code, test_code, language)
            return fixed_code, is_valid, issues
    
    return source_code, is_valid, issues
