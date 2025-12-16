"""
Workflow Orchestrator - Integrates all phases into complete pipeline.
Phase 5: Complete end-to-end workflow with all MCP integrations.
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional
from pathlib import Path

# Phase 1-2: Classification
from src.agents.classifier import CodeClassifier
from src.agents.pattern_integration import PatternMatcherIntegration
from src.utils.file_handler import FileHandler

# Phase 3: Search
from src.search.vector_store import CodeSearchEngine

# Phase 4: Analysis & Transformation
from src.agents.analyzer import CodeAnalyzer
from src.agents.transformer import CodeTransformer

# Phase 5: Testing & GitHub
from src.agents.test_generator import CodeTestGenerator
from src.sandbox.validator import ModalSandboxValidator

# Lazy import to avoid circular dependency
GitHubMCPClient = None

logger = logging.getLogger(__name__)


class ModernizationOrchestrator:
    """
    Orchestrates the complete code modernization workflow.
    Integrates all 5 phases into a seamless pipeline.
    """
    
    def __init__(self, use_intelligent_matcher: bool = True):
        """Initialize orchestrator with all components."""
        logger.info("Initializing ModernizationOrchestrator")
        
        # Phase 1-2 components
        self.use_intelligent_matcher = use_intelligent_matcher
        if use_intelligent_matcher:
            self.pattern_integration = PatternMatcherIntegration(
                use_intelligent_matcher=True,
                cache_dir=".pattern_cache"
            )
            logger.info("Using IntelligentPatternMatcher")
        else:
            self.classifier = CodeClassifier()
            logger.info("Using legacy CodeClassifier")
        
        self.file_handler = FileHandler()
        
        # Phase 3 components
        self.search_engine = None  # Initialized per repo
        
        # Phase 4 components
        self.analyzer = CodeAnalyzer()
        self.transformer = CodeTransformer()
        
        # Phase 5 components
        self.test_generator = CodeTestGenerator()
        self.validator = ModalSandboxValidator()
        
        # Lazy load GitHub client to avoid circular import
        self.github_client = None
        
        logger.info("ModernizationOrchestrator initialized successfully")
    
    async def modernize_repository(
        self,
        repo_path: str,
        target_version: str = "Python 3.14",
        create_pr: bool = False,
        repo_url: Optional[str] = None,
        github_token: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Complete modernization workflow for a repository.
        
        Args:
            repo_path: Path to repository (ZIP or directory)
            target_version: Target language/framework version
            create_pr: Whether to create GitHub PR
            repo_url: GitHub repository URL (required if create_pr=True)
            github_token: GitHub personal access token (optional, uses .env if not provided)
            progress_callback: Optional callback function for progress updates
        
        Returns:
            Dictionary with complete modernization results
        """
        logger.info(f"Starting modernization for {repo_path}")
        
        def update_progress(phase: str, message: str):
            """Helper to call progress callback if provided."""
            if progress_callback:
                progress_callback(phase, message)
        
        results = {
            "success": False,
            "phases": {},
            "statistics": {},
            "errors": []
        }
        
        try:
            # Phase 1: Extract and discover files
            logger.info("Phase 1: File discovery")
            update_progress("Phase 1", "Extracting and discovering files...")
            
            if repo_path.endswith('.zip'):
                extract_path = self.file_handler.extract_repo(repo_path)
            else:
                extract_path = repo_path
            
            files = self.file_handler.list_code_files(extract_path)
            logger.info(f"Discovered {len(files)} code files")
            update_progress("Phase 1", f"Discovered {len(files)} code files")
            
            results['phases']['discovery'] = {
                "files_found": len(files),
                "repo_path": extract_path
            }
            
            # Phase 2: Classify files
            logger.info("Phase 2: File classification")
            update_progress("Phase 2", "Classifying files with AI pattern detection...")
            
            # Read file contents for intelligent matching
            file_contents = {}
            if self.use_intelligent_matcher:
                logger.info("Reading file contents for intelligent pattern matching...")
                for file_path in files[:50]:  # Limit to 50 files for demo
                    try:
                        full_path = os.path.join(extract_path, file_path)
                        content = self.file_handler.read_file(full_path)
                        if content:
                            file_contents[file_path] = content
                    except Exception as e:
                        logger.warning(f"Could not read {file_path}: {e}")
                
                classifications = self.pattern_integration.classify_files(
                    list(file_contents.keys()), 
                    file_contents
                )
                
                # Get detailed statistics
                analyses = self.pattern_integration.pattern_matcher.analyze_batch(file_contents)
                stats = self.pattern_integration.generate_statistics(analyses)
                
                logger.info(f"Intelligent classification: {stats['modernize_high']} high, "
                          f"{stats['modernize_low']} low, {stats['skip']} skip")
                logger.info(f"Detected {stats['patterns_detected']} patterns across {stats['total_files']} files")
            else:
                classifications = self.classifier.classify_files(files)
                stats = None
            
            modernize_high = [f for f, c in classifications.items() if c == 'modernize_high']
            modernize_low = [f for f, c in classifications.items() if c == 'modernize_low']
            skip_files = [f for f, c in classifications.items() if c == 'skip']
            
            logger.info(f"Classification: {len(modernize_high)} high, {len(modernize_low)} low, {len(skip_files)} skip")
            
            results['phases']['classification'] = {
                "modernize_high": len(modernize_high),
                "modernize_low": len(modernize_low),
                "skip": len(skip_files),
                "classifications": classifications,
                "intelligent_stats": stats if self.use_intelligent_matcher else None
            }
            
            # Phase 3: Semantic search and pattern grouping
            logger.info("Phase 3: Semantic search")
            update_progress("Phase 3", "Building semantic index with LlamaIndex...")
            
            self.search_engine = CodeSearchEngine(persist_dir=None)
            
            # Build index for high-priority files
            files_to_modernize = modernize_high + modernize_low
            if files_to_modernize:
                self.search_engine.build_index(extract_path)  # Build index from repo
                
                # Find pattern groups
                pattern_groups = self._find_pattern_groups(files_to_modernize[:20])
                logger.info(f"Found {len(pattern_groups)} pattern groups")
                
                results['phases']['search'] = {
                    "indexed_files": min(len(files_to_modernize), 100),
                    "pattern_groups": len(pattern_groups)
                }
            else:
                pattern_groups = []
                results['phases']['search'] = {"message": "No files to modernize"}
            
            # Phase 4: Analysis and transformation
            logger.info("Phase 4: Code transformation")
            update_progress("Phase 4", "Analyzing and transforming code...")
            
            transformations = []
            
            # Use intelligent pattern data if available
            if self.use_intelligent_matcher and file_contents:
                logger.info("Using intelligent pattern analysis for transformation")
                
                # Get prioritized files from intelligent matcher
                prioritized = self.pattern_integration.pattern_matcher.prioritize_files(analyses)
                
                # Process top priority files
                files_to_transform = [
                    (fp, analysis) for fp, analysis in prioritized 
                    if analysis.requires_modernization
                ][:10]  # Limit to 10 files for demo
                
                logger.info(f"Processing {len(files_to_transform)} high-priority files with detailed pattern data")
                
                total_files = len(files_to_transform)
                for idx, (file_path, file_analysis) in enumerate(files_to_transform, 1):
                    try:
                        update_progress("Phase 4", f"Transforming file {idx}/{total_files}: {Path(file_path).name}")
                        
                        original_code = file_contents.get(file_path, "")
                        if not original_code:
                            continue
                        
                        # Convert intelligent pattern analysis to transformation plan
                        transformation_plan = self.pattern_integration.get_transformation_plan(file_analysis)
                        
                        # Transform using detailed pattern information
                        modernized_code = await self.transformer.transform_code(
                            file_path,
                            original_code,
                            transformation_plan
                        )
                        
                        transformations.append({
                            "file_path": file_path,
                            "original_code": original_code,
                            "modernized_code": modernized_code,
                            "analysis": transformation_plan,
                            "patterns_addressed": [p['pattern'] for p in transformation_plan['steps']],
                            "pattern_details": file_analysis.patterns  # Include detailed pattern info
                        })
                        
                    except Exception as e:
                        logger.error(f"Error transforming {file_path}: {e}")
                        results['errors'].append(f"Transformation error for {file_path}: {e}")
            else:
                # Fallback to legacy pattern grouping
                logger.info("Using legacy pattern grouping for transformation")
                
                file_to_patterns = {}
                for group in pattern_groups[:5]:  # Limit to 5 groups for demo
                    for file_path in group['files'][:3]:
                        if file_path not in file_to_patterns:
                            file_to_patterns[file_path] = []
                        file_to_patterns[file_path].append(group['pattern_name'])
                
                logger.info(f"Processing {len(file_to_patterns)} unique files")
                
                total_files = len(file_to_patterns)
                for idx, (file_path, patterns) in enumerate(file_to_patterns.items(), 1):
                    try:
                        update_progress("Phase 4", f"Transforming file {idx}/{total_files}: {Path(file_path).name}")
                        
                        full_path = os.path.join(extract_path, file_path)
                        original_code = self.file_handler.read_file(full_path)
                        
                        if not original_code:
                            continue
                        
                        # Analyze patterns
                        combined_pattern = " AND ".join(patterns)
                        analysis = await self.analyzer.analyze_pattern(
                            [file_path],
                            combined_pattern,
                            {file_path: original_code}
                        )
                        
                        # Transform file
                        modernized_code = await self.transformer.transform_code(
                            file_path,
                            original_code,
                            analysis
                        )
                        
                        transformations.append({
                            "file_path": file_path,
                            "original_code": original_code,
                            "modernized_code": modernized_code,
                            "analysis": analysis,
                            "patterns_addressed": patterns
                        })
                            
                    except Exception as e:
                        logger.error(f"Error transforming {file_path}: {e}")
                        results['errors'].append(f"Transformation error for {file_path}: {e}")
            
            logger.info(f"Transformed {len(transformations)} files")
            
            # Save transformed files to output directory
            output_dir = Path("modernized_output")
            output_dir.mkdir(exist_ok=True)
            
            for t in transformations:
                try:
                    # Create subdirectories if needed
                    output_file = output_dir / t['file_path']
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Save modernized code
                    output_file.write_text(t['modernized_code'])
                    logger.info(f"Saved: {output_file}")
                    
                    # Also save original for comparison
                    original_file = output_dir / "original" / t['file_path']
                    original_file.parent.mkdir(parents=True, exist_ok=True)
                    original_file.write_text(t['original_code'])
                    
                except Exception as e:
                    logger.error(f"Error saving {t['file_path']}: {e}")
            
            logger.info(f"Output saved to: {output_dir.absolute()}")
            
            results['phases']['transformation'] = {
                "files_transformed": len(transformations),
                "output_directory": str(output_dir.absolute())
            }
            
            # Store transformations for zip file creation
            results['transformations'] = transformations
            
            # Phase 5: Test generation and validation
            logger.info("Phase 5: Test generation and validation")
            update_progress("Phase 5", "Generating tests and validating in Modal sandbox...")
            
            validation_results = []
            
            # Create tests directory
            tests_dir = output_dir / "tests"
            tests_dir.mkdir(exist_ok=True)
            
            total_tests = min(len(transformations), 10)
            for idx, t in enumerate(transformations[:10], 1):  # Limit to 10 for demo
                try:
                    # Update progress
                    update_progress("Phase 5", f"Testing file {idx}/{total_tests}: {Path(t['file_path']).name}")
                    
                    # Generate tests
                    tests = self.test_generator.generate_tests(
                        t['original_code'],
                        t['modernized_code'],
                        t['file_path']
                    )
                    
                    # Validate and auto-fix export issues
                    if tests:
                        from src.agents.code_validator import validate_and_fix_code
                        
                        # Detect language from file extension
                        file_ext = Path(t['file_path']).suffix.lower()
                        language_map = {
                            '.ts': 'typescript',
                            '.js': 'javascript',
                            '.py': 'python',
                            '.java': 'java'
                        }
                        language = language_map.get(file_ext, 'unknown')
                        
                        # Validate and fix
                        fixed_code, is_valid, issues = validate_and_fix_code(
                            t['modernized_code'],
                            tests,
                            language
                        )
                        
                        if not is_valid:
                            logger.warning(f"Code validation issues for {t['file_path']}: {issues}")
                        
                        if fixed_code != t['modernized_code']:
                            logger.info(f"Auto-fixed export issues in {t['file_path']}")
                            t['modernized_code'] = fixed_code
                            
                            # Re-save the fixed source file
                            output_file = output_dir / Path(t['file_path']).name
                            output_file.write_text(fixed_code)
                    
                    # Save test file
                    if tests:
                        test_file = tests_dir / f"test_{Path(t['file_path']).name}"
                        test_file.write_text(tests)
                        logger.info(f"Saved test: {test_file}")
                    
                    # Validate in sandbox
                    validation = self.validator.validate_transformation(
                        t['original_code'],
                        t['modernized_code'],
                        tests,
                        file_path=t['file_path']
                    )
                    
                    validation['file_path'] = t['file_path']
                    validation_results.append(validation)
                    
                except Exception as e:
                    logger.error(f"Error validating {t['file_path']}: {e}")
                    results['errors'].append(f"Validation error: {e}")
            
            # Calculate aggregate test results
            total_tests = sum(v.get('tests_run', 0) for v in validation_results)
            total_passed = sum(v.get('tests_passed', 0) for v in validation_results)
            # Fix: Only average coverage for files that have coverage data
            coverage_values = [v.get('coverage_percent', 0) for v in validation_results if v.get('coverage_percent', 0) > 0]
            avg_coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0
            
            logger.info(f"Validation: {total_passed}/{total_tests} tests passed, {avg_coverage:.1f}% coverage")
            
            results['phases']['validation'] = {
                "files_validated": len(validation_results),
                "total_tests": total_tests,
                "tests_passed": total_passed,
                "tests_failed": total_tests - total_passed,
                "average_coverage": round(avg_coverage, 2),
                "pass_rate": round(total_passed / max(total_tests, 1) * 100, 2)
            }
            
            # Phase 5b: GitHub PR creation (optional)
            if create_pr and repo_url:
                logger.info("Phase 5b: Creating GitHub PR")
                
                # Lazy load GitHub client
                if self.github_client is None:
                    from src.mcp.github_client import GitHubMCPClient
                    self.github_client = GitHubMCPClient(github_token=github_token)
                
                # Prepare changed files
                changed_files = {
                    t['file_path']: t['modernized_code']
                    for t in transformations
                }
                
                # Generate PR summary
                pr_summary = self._generate_pr_summary(results, target_version)
                
                # Create PR
                pr_result = await self.github_client.create_pr(
                    repo_url=repo_url,
                    changed_files=changed_files,
                    pr_summary=pr_summary,
                    test_results=results['phases']['validation']
                )
                
                results['phases']['github_pr'] = pr_result
                logger.info(f"PR creation: {pr_result.get('success', False)}")
            
            # Calculate final statistics
            results['statistics'] = {
                "total_files": len(files),
                "files_modernized": len(transformations),
                "tests_generated": total_tests,
                "test_pass_rate": round(total_passed / max(total_tests, 1) * 100, 2),
                "average_coverage": round(avg_coverage, 2)
            }
            
            # Add output locations
            results['output'] = {
                "modernized_files": str(output_dir.absolute()),
                "original_files": str((output_dir / "original").absolute()),
                "test_files": str((output_dir / "tests").absolute())
            }
            
            results['success'] = True
            logger.info("Modernization workflow completed successfully")
            logger.info(f"📁 Modernized files: {output_dir.absolute()}")
            logger.info(f"📁 Test files: {output_dir / 'tests'}")
            
        except Exception as e:
            logger.error(f"Workflow error: {e}")
            results['errors'].append(f"Workflow error: {e}")
            results['success'] = False
        
        return results
    
    def _find_pattern_groups(self, files: List[str]) -> List[Dict]:
        """
        Find groups of files with similar legacy patterns.
        Detects file languages and uses appropriate pattern queries.
        
        Args:
            files: List of file paths
        
        Returns:
            List of pattern group dictionaries
        """
        # Detect languages present in the files
        languages = self._detect_languages_in_files(files)
        
        # Build language-specific pattern queries
        pattern_queries = self._get_pattern_queries_for_languages(languages)
        
        groups = []
        
        for query in pattern_queries:
            try:
                similar_files = self.search_engine.find_similar_patterns(query, top_k=10)
                
                if similar_files:
                    groups.append({
                        "pattern_name": query,
                        "files": [f['file_path'] for f in similar_files],
                        "similarity_scores": [f['score'] for f in similar_files]
                    })
            except Exception as e:
                logger.error(f"Error searching for pattern '{query}': {e}")
        
        return groups
    
    def _detect_languages_in_files(self, files: List[str]) -> set:
        """Detect programming languages from file extensions."""
        extension_to_language = {
            '.py': 'python',
            '.java': 'java',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.rs': 'rust',
            '.swift': 'swift'
        }
        
        languages = set()
        for file_path in files:
            ext = Path(file_path).suffix.lower()
            if ext in extension_to_language:
                languages.add(extension_to_language[ext])
        
        return languages if languages else {'python'}  # Default to Python if no recognized extensions
    
    def _get_pattern_queries_for_languages(self, languages: set) -> List[str]:
        """Get pattern queries appropriate for the detected languages."""
        # Common patterns for all languages
        common_patterns = [
            "Files with SQL injection vulnerabilities",
            "Files with hardcoded credentials or secrets",
            "Files with security vulnerabilities",
            "Files with deprecated API usage"
        ]
        
        # Language-specific patterns
        language_patterns = {
            'python': [
                "Files using deprecated database libraries like MySQLdb",
                "Files using Python 2 print statements",
                "Files using deprecated urllib2 library",
                "Files missing type hints",
                "Files using old-style string formatting"
            ],
            'java': [
                "Files using deprecated Java APIs like Vector or Hashtable",
                "Files using raw JDBC without prepared statements",
                "Files missing try-with-resources for AutoCloseable",
                "Files using pre-Java 8 patterns without lambdas or streams",
                "Files using deprecated Date and Calendar APIs",
                "Files with missing null checks or Optional usage"
            ],
            'javascript': [
                "Files using var instead of let or const",
                "Files using callback patterns instead of Promises or async/await",
                "Files using jQuery for DOM manipulation",
                "Files with eval() usage",
                "Files using prototype-based inheritance"
            ],
            'typescript': [
                "Files with excessive any type usage",
                "Files missing strict null checks",
                "Files using old module syntax"
            ],
            'cpp': [
                "Files using raw pointers instead of smart pointers",
                "Files with manual memory management",
                "Files using C-style casts",
                "Files missing RAII patterns"
            ],
            'csharp': [
                "Files using deprecated .NET APIs",
                "Files missing async/await patterns",
                "Files using old collection types"
            ],
            'go': [
                "Files missing error handling",
                "Files with goroutine leaks",
                "Files missing context usage"
            ],
            'ruby': [
                "Files using deprecated Ruby syntax",
                "Files missing proper error handling"
            ],
            'php': [
                "Files using deprecated mysql_* functions",
                "Files missing prepared statements",
                "Files with register_globals usage"
            ]
        }
        
        queries = common_patterns.copy()
        
        for lang in languages:
            if lang in language_patterns:
                queries.extend(language_patterns[lang])
        
        return queries
    
    def _generate_pr_summary(self, results: Dict, target_version: str) -> str:
        """Generate PR summary from results."""
        stats = results['statistics']
        
        # Build coverage line only if coverage > 0
        coverage_line = ""
        if stats.get('average_coverage', 0) > 0:
            coverage_line = f"**Code Coverage**: {stats['average_coverage']:.1f}%\n"
        
        summary = f"""Automated migration to {target_version} with security fixes and performance improvements.

**Files Modernized**: {stats['files_modernized']} / {stats['total_files']}
**Tests Generated**: {stats['tests_generated']}
**Test Pass Rate**: {stats['test_pass_rate']:.1f}%
{coverage_line}
This PR includes:
- Syntax modernization to {target_version}
- Security vulnerability fixes
- Deprecated library replacements
- Comprehensive test suite
- Performance optimizations

All changes have been validated in an isolated sandbox environment.
"""
        
        return summary
    
    def generate_report(self, results: Dict) -> str:
        """
        Generate human-readable report from results.
        
        Args:
            results: Workflow results dictionary
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 60)
        report.append("LEGACY CODE MODERNIZATION REPORT")
        report.append("=" * 60)
        report.append("")
        
        if results['success']:
            report.append("✅ Status: SUCCESS")
        else:
            report.append("❌ Status: FAILED")
        
        report.append("")
        report.append("STATISTICS:")
        report.append("-" * 60)
        
        stats = results.get('statistics', {})
        for key, value in stats.items():
            # Skip average_coverage if it's 0
            if key == 'average_coverage' and value == 0:
                continue
            report.append(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Add intelligent pattern statistics if available
        classification_data = results.get('phases', {}).get('classification', {})
        intelligent_stats = classification_data.get('intelligent_stats')
        if intelligent_stats:
            report.append("")
            report.append("INTELLIGENT PATTERN ANALYSIS:")
            report.append("-" * 60)
            report.append(f"  Patterns Detected: {intelligent_stats.get('patterns_detected', 0)}")
            report.append(f"  Average Modernization Score: {intelligent_stats.get('average_modernization_score', 0)}/100")
            report.append(f"  Total Estimated Effort: {intelligent_stats.get('total_estimated_effort_hours', 0)}h")
            
            severity_counts = intelligent_stats.get('severity_counts', {})
            if severity_counts:
                report.append("  Severity Breakdown:")
                for severity, count in severity_counts.items():
                    if count > 0:
                        report.append(f"    {severity.upper()}: {count}")
        
        report.append("")
        report.append("PHASE RESULTS:")
        report.append("-" * 60)
        
        for phase, data in results.get('phases', {}).items():
            report.append(f"\n  {phase.upper()}:")
            if isinstance(data, dict):
                for k, v in data.items():
                    if k not in ['classifications', 'intelligent_stats']:  # Skip large data
                        report.append(f"    {k}: {v}")
        
        # Add output locations
        if results.get('output'):
            report.append("")
            report.append("OUTPUT LOCATIONS:")
            report.append("-" * 60)
            for key, path in results['output'].items():
                report.append(f"  📁 {key.replace('_', ' ').title()}: {path}")
        
        if results.get('errors'):
            report.append("")
            report.append("ERRORS:")
            report.append("-" * 60)
            for error in results['errors']:
                report.append(f"  ⚠️ {error}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
