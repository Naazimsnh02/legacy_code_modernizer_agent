"""
Production-grade pattern matching system with AI-powered file type detection.
Replaces the simple primary/secondary classification with intelligent pattern detection.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
from dataclasses import dataclass
from enum import Enum

from src.config import AIManager, GeminiSchemas

logger = logging.getLogger(__name__)


class PatternSeverity(Enum):
    """Severity levels for detected patterns."""
    CRITICAL = "critical"  # Security issues, breaking changes
    HIGH = "high"  # Deprecated APIs, performance issues
    MEDIUM = "medium"  # Code quality, maintainability
    LOW = "low"  # Style, minor improvements
    INFO = "info"  # Informational only


@dataclass
class DetectedPattern:
    """Represents a detected legacy pattern."""
    pattern_type: str
    severity: PatternSeverity
    file_path: str
    language: str
    description: str
    line_numbers: List[int]
    confidence: float  # 0.0 to 1.0
    recommendation: str
    estimated_effort_hours: float


@dataclass
class FileAnalysis:
    """Complete analysis of a single file."""
    file_path: str
    language: str
    framework: Optional[str]
    patterns: List[DetectedPattern]
    overall_priority: PatternSeverity
    modernization_score: float  # 0-100, higher = more modern
    requires_modernization: bool


class IntelligentPatternMatcher:
    """
    Production-grade pattern matcher using AI for intelligent detection.
    
    Features:
    - Language-agnostic pattern detection
    - Context-aware analysis
    - Confidence scoring
    - Batch processing optimization
    - Caching for performance
    """
    
    # Language detection patterns
    LANGUAGE_PATTERNS = {
        # Python
        '.py': 'Python',
        '.pyw': 'Python',
        '.pyx': 'Python (Cython)',
        # Java
        '.java': 'Java',
        # JavaScript/TypeScript
        '.js': 'JavaScript',
        '.jsx': 'JavaScript (React)',
        '.mjs': 'JavaScript (ES Module)',
        '.cjs': 'JavaScript (CommonJS)',
        '.ts': 'TypeScript',
        '.tsx': 'TypeScript (React)',
        # PHP
        '.php': 'PHP',
        '.php3': 'PHP',
        '.php4': 'PHP',
        '.php5': 'PHP',
        '.phtml': 'PHP',
        # Ruby
        '.rb': 'Ruby',
        '.rbw': 'Ruby',
        # Go
        '.go': 'Go',
        # C/C++
        '.c': 'C',
        '.h': 'C/C++ Header',
        '.cpp': 'C++',
        '.cc': 'C++',
        '.cxx': 'C++',
        '.c++': 'C++',
        '.hpp': 'C++ Header',
        '.hh': 'C++ Header',
        '.hxx': 'C++ Header',
        '.h++': 'C++ Header',
        # C#
        '.cs': 'C#',
        # Rust
        '.rs': 'Rust',
        # Kotlin
        '.kt': 'Kotlin',
        '.kts': 'Kotlin Script',
        # Swift
        '.swift': 'Swift',
        # Scala
        '.scala': 'Scala',
        '.sc': 'Scala Script',
        # R
        '.r': 'R',
        '.R': 'R',
        # Perl
        '.pl': 'Perl',
        '.pm': 'Perl Module',
        '.t': 'Perl Test',
        '.pod': 'Perl Documentation',
        # Shell
        '.sh': 'Shell',
        '.bash': 'Bash',
        '.zsh': 'Zsh',
        '.fish': 'Fish Shell'
    }
    
    # Common legacy patterns by language
    LEGACY_PATTERNS = {
        'Python': [
            'Python 2 syntax (print statements, old-style classes)',
            'Deprecated libraries (MySQLdb, urllib2, optparse)',
            'Missing type hints',
            'Hardcoded credentials',
            'SQL injection vulnerabilities',
            'Insecure cryptography (MD5, SHA1 for passwords)',
            'Global variables and mutable defaults',
            'Missing error handling',
            'Synchronous I/O in async contexts'
        ],
        'Java': [
            'Pre-Java 8 code (no lambdas, streams)',
            'Deprecated APIs (Vector, Hashtable, Date)',
            'Missing generics',
            'Raw JDBC without ORM',
            'Synchronization issues',
            'Resource leaks (missing try-with-resources)',
            'Hardcoded configuration',
            'Missing null checks'
        ],
        'JavaScript': [
            'var instead of let/const',
            'Callback hell (no Promises/async-await)',
            'jQuery for DOM manipulation',
            'eval() usage',
            'Missing strict mode',
            'Prototype-based inheritance',
            'Global namespace pollution',
            'XSS vulnerabilities'
        ],
        'TypeScript': [
            'any type overuse',
            'Missing strict mode',
            'Old module syntax',
            'Missing null checks',
            'Implicit any',
            'Type assertions instead of guards'
        ],
        'PHP': [
            'mysql_* functions (deprecated)',
            'No prepared statements',
            'register_globals usage',
            'eval() and create_function()',
            'Missing input validation',
            'Outdated PHP version syntax',
            'No namespace usage',
            'Missing error handling'
        ],
        'Ruby': [
            'Ruby 1.8/1.9 syntax',
            'Missing bundler',
            'Deprecated gem versions',
            'Missing RSpec/Minitest',
            'Global variables',
            'Missing error handling',
            'Synchronous I/O'
        ],
        'Go': [
            'Missing error handling',
            'Deprecated packages',
            'No context usage',
            'Missing defer for cleanup',
            'Goroutine leaks',
            'Race conditions'
        ],
        'C++': [
            'Raw pointers instead of smart pointers',
            'Manual memory management',
            'Missing RAII',
            'C-style casts',
            'Missing const correctness',
            'No move semantics',
            'Deprecated C++98/03 features'
        ],
        'C#': [
            'Missing async/await patterns',
            'Old collection types',
            'Missing LINQ usage',
            'Deprecated .NET Framework APIs',
            'Missing nullable reference types',
            'Old string concatenation',
            'Missing using statements'
        ],
        'Rust': [
            'Deprecated Rust 2015/2018 syntax',
            'Missing error handling with Result',
            'Unsafe code blocks',
            'Missing lifetime annotations',
            'Deprecated crate versions',
            'Missing async/await'
        ],
        'Kotlin': [
            'Java-style code in Kotlin',
            'Missing null safety',
            'Not using coroutines',
            'Missing data classes',
            'Old collection APIs',
            'Missing extension functions'
        ],
        'Swift': [
            'Objective-C style code',
            'Missing optionals',
            'Old closure syntax',
            'Missing guard statements',
            'Deprecated Swift 4 features',
            'Missing Codable protocol'
        ],
        'Scala': [
            'Scala 2.x syntax',
            'Missing for-comprehensions',
            'Old collection APIs',
            'Missing implicit conversions',
            'Deprecated Future usage',
            'Missing case classes'
        ],
        'R': [
            'Old R syntax',
            'Missing tidyverse usage',
            'Deprecated package versions',
            'Missing pipe operators',
            'Old data.frame usage',
            'Missing ggplot2'
        ],
        'Perl': [
            'Perl 4 syntax',
            'Missing strict and warnings',
            'Old module system',
            'Deprecated CPAN modules',
            'Missing Moose/Moo',
            'Old regex syntax'
        ],
        'Shell': [
            'Missing error handling (set -e)',
            'Unquoted variables',
            'Missing shellcheck compliance',
            'Deprecated commands',
            'Missing function usage',
            'Security vulnerabilities'
        ]
    }
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize pattern matcher.
        
        Args:
            cache_dir: Optional directory for caching analysis results
        """
        # Use centralized AI manager
        self.ai_manager = AIManager()
        self.cache_dir = Path(cache_dir) if cache_dir else None
        
        if self.cache_dir:
            self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        logger.info(
            f"IntelligentPatternMatcher initialized with provider: {self.ai_manager.provider_name}, "
            f"model: {self.ai_manager.model_name}"
        )
    
    def detect_language(self, file_path: str, code_sample: str) -> Tuple[str, Optional[str]]:
        """
        Detect programming language and framework using AI.
        
        Args:
            file_path: Path to the file
            code_sample: Sample of code (first 500 chars)
        
        Returns:
            Tuple of (language, framework)
        """
        # First try extension-based detection
        ext = Path(file_path).suffix.lower()
        base_language = self.LANGUAGE_PATTERNS.get(ext, 'Unknown')
        
        # Use AI for framework detection
        prompt = f"""Analyze this code and identify:
1. Programming language (confirm or correct: {base_language})
2. Framework/library being used (if any)

FILE: {file_path}
CODE SAMPLE:
```
{code_sample[:500]}
```

Respond in JSON format:
{{
  "language": "detected language",
  "framework": "framework name or null",
  "confidence": 0.0-1.0
}}
"""
        
        try:
            # Use JSON schema for guaranteed structure
            schema = GeminiSchemas.language_detection()
            
            response_text = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_PRECISE,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_SMALL,
                response_format="json",
                response_schema=schema if self.ai_manager.provider_type == "gemini" else None
            )
            
            result = json.loads(response_text)
            language = result.get('language', base_language)
            framework = result.get('framework')
            
            logger.info(f"Language detection: {language}, Framework: {framework}, Confidence: {result.get('confidence', 0)}")
            return language, framework
            
        except Exception as e:
            logger.warning(f"AI language detection failed: {e}, using extension-based")
            return base_language, None
    
    def analyze_file(self, file_path: str, code: str) -> FileAnalysis:
        """
        Perform comprehensive pattern analysis on a single file.
        
        Args:
            file_path: Path to the file
            code: File contents
        
        Returns:
            FileAnalysis object with detected patterns
        """
        logger.info(f"Analyzing patterns in {file_path}")
        
        # Check cache
        if self.cache_dir:
            cache_file = self.cache_dir / f"{hash(file_path + code)}.json"
            if cache_file.exists():
                try:
                    cached = json.loads(cache_file.read_text())
                    return self._deserialize_analysis(cached)
                except Exception as e:
                    logger.warning(f"Cache read failed: {e}")
        
        # Detect language and framework
        language, framework = self.detect_language(file_path, code[:500])
        
        # Get relevant patterns for this language
        relevant_patterns = self.LEGACY_PATTERNS.get(language, [])
        
        # Build analysis prompt - limit code size to prevent output token overflow
        # For large files, we need to be more conservative to leave room for detailed analysis
        code_limit = 4000 if len(code) > 6000 else 6000
        
        prompt = f"""You are a senior code auditor. Analyze this code for legacy patterns and modernization opportunities.

FILE: {file_path}
LANGUAGE: {language}
FRAMEWORK: {framework or 'None detected'}

PATTERNS TO CHECK:
{json.dumps(relevant_patterns, indent=2)}

CODE:
```{language.lower()}
{code[:code_limit]}
```

IMPORTANT: Focus on the MOST CRITICAL patterns. Limit your response to the top 10 most important issues.

For each detected pattern, provide:
1. Pattern type (from the list above or new if discovered)
2. Severity (critical/high/medium/low/info)
3. Line numbers where pattern appears (first occurrence only)
4. Confidence score (0.0-1.0)
5. Brief description (max 100 chars)
6. Concise recommendation (max 100 chars)
7. Estimated effort in hours

Also provide:
- Overall modernization score (0-100, where 100 is fully modern)
- Whether modernization is required (true/false)
- Overall priority (critical/high/medium/low/info)

Respond in JSON format:
{{
  "patterns": [
    {{
      "pattern_type": "string",
      "severity": "critical|high|medium|low|info",
      "line_numbers": [1],
      "confidence": 0.95,
      "description": "brief description",
      "recommendation": "concise fix",
      "estimated_effort_hours": 2.5
    }}
  ],
  "modernization_score": 65,
  "requires_modernization": true,
  "overall_priority": "high"
}}
"""
        
        try:
            # Use JSON schema for guaranteed structure - no more parsing failures!
            # Use LARGE token limit for detailed pattern analysis
            schema = GeminiSchemas.pattern_analysis()
            
            response_text = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_PRECISE,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_LARGE,
                response_format="json",
                response_schema=schema if self.ai_manager.provider_type == "gemini" else None
            )
            
            if not response_text:
                logger.error(f"Empty response from AI for {file_path}")
                raise ValueError(f"Empty response from AI API for {file_path}")
            
            # With JSON schema, response is guaranteed to be valid JSON
            result = json.loads(response_text)
            logger.info(f"Pattern analysis successful for {file_path}: {len(result.get('patterns', []))} patterns found")
            
            # Convert to DetectedPattern objects
            patterns = []
            for p in result.get('patterns', []):
                patterns.append(DetectedPattern(
                    pattern_type=p['pattern_type'],
                    severity=PatternSeverity(p['severity']),
                    file_path=file_path,
                    language=language,
                    description=p['description'],
                    line_numbers=p.get('line_numbers', []),
                    confidence=p.get('confidence', 0.8),
                    recommendation=p['recommendation'],
                    estimated_effort_hours=p.get('estimated_effort_hours', 1.0)
                ))
            
            analysis = FileAnalysis(
                file_path=file_path,
                language=language,
                framework=framework,
                patterns=patterns,
                overall_priority=PatternSeverity(result.get('overall_priority', 'medium')),
                modernization_score=result.get('modernization_score', 50),
                requires_modernization=result.get('requires_modernization', True)
            )
            
            # Cache the result
            if self.cache_dir:
                try:
                    cache_file = self.cache_dir / f"{hash(file_path + code)}.json"
                    cache_file.write_text(json.dumps(self._serialize_analysis(analysis), indent=2))
                except Exception as e:
                    logger.warning(f"Cache write failed: {e}")
            
            logger.info(f"Found {len(patterns)} patterns in {file_path}")
            return analysis
            
        except Exception as e:
            logger.error(f"Pattern analysis failed for {file_path}: {e}")
            # Return minimal analysis on error
            return FileAnalysis(
                file_path=file_path,
                language=language,
                framework=framework,
                patterns=[],
                overall_priority=PatternSeverity.INFO,
                modernization_score=100,
                requires_modernization=False
            )
    
    def analyze_batch(self, files: Dict[str, str], batch_size: int = 3) -> Dict[str, FileAnalysis]:
        """
        Analyze multiple files efficiently by batching API calls.
        
        Args:
            files: Dictionary mapping file paths to contents
            batch_size: Number of files to analyze per API call (default: 3)
        
        Returns:
            Dictionary mapping file paths to FileAnalysis objects
        """
        logger.info(f"Batch analyzing {len(files)} files with batch_size={batch_size}")
        
        results = {}
        file_items = list(files.items())
        
        # Process in batches to reduce API calls
        for i in range(0, len(file_items), batch_size):
            batch = file_items[i:i + batch_size]
            
            if len(batch) == 1:
                # Single file - use individual analysis
                file_path, code = batch[0]
                try:
                    analysis = self.analyze_file(file_path, code)
                    results[file_path] = analysis
                except Exception as e:
                    logger.error(f"Failed to analyze {file_path}: {e}")
            else:
                # Multiple files - use batch analysis
                try:
                    batch_results = self._analyze_batch_api(batch)
                    results.update(batch_results)
                except Exception as e:
                    logger.error(f"Batch analysis failed: {e}, falling back to individual")
                    # Fallback to individual analysis
                    for file_path, code in batch:
                        try:
                            analysis = self.analyze_file(file_path, code)
                            results[file_path] = analysis
                        except Exception as e2:
                            logger.error(f"Failed to analyze {file_path}: {e2}")
        
        logger.info(f"Batch analysis complete: {len(results)} files analyzed")
        return results
    
    def _analyze_batch_api(self, batch: List[Tuple[str, str]]) -> Dict[str, FileAnalysis]:
        """
        Analyze multiple files in a single API call.
        
        Args:
            batch: List of (file_path, code) tuples
        
        Returns:
            Dictionary mapping file paths to FileAnalysis objects
        """
        logger.info(f"Analyzing {len(batch)} files in single API call")
        
        # Build combined prompt for all files
        # Reduce code sample size for batch processing to prevent token overflow
        files_info = []
        for file_path, code in batch:
            ext = Path(file_path).suffix.lower()
            language = self.LANGUAGE_PATTERNS.get(ext, 'Unknown')
            
            # Use smaller samples for batch to leave room for multiple file analyses
            code_sample_size = 2000 if len(batch) > 2 else 3000
            
            files_info.append({
                'file_path': file_path,
                'language': language,
                'code_sample': code[:code_sample_size]
            })
        
        prompt = f"""Analyze these {len(batch)} code files for legacy patterns and modernization opportunities.

For EACH file, provide a complete analysis with patterns, scores, and priorities.
IMPORTANT: Limit to top 5 most critical patterns per file to keep response concise.

FILES TO ANALYZE:
{json.dumps(files_info, indent=2)}

For each file, detect:
- Deprecated libraries and APIs
- Security vulnerabilities (SQL injection, XSS, hardcoded credentials)
- Code quality issues (missing type hints, error handling)
- Performance problems

Keep descriptions and recommendations brief (max 80 chars each).

Respond in JSON format with this structure:
{{
  "files": [
    {{
      "file_path": "file1.py",
      "language": "Python",
      "framework": "Flask or null",
      "patterns": [
        {{
          "pattern_type": "SQL injection vulnerability",
          "severity": "critical",
          "line_numbers": [10, 11],
          "confidence": 0.95,
          "description": "Direct string concatenation in SQL query",
          "recommendation": "Use parameterized queries",
          "estimated_effort_hours": 2.0
        }}
      ],
      "modernization_score": 35,
      "requires_modernization": true,
      "overall_priority": "critical"
    }}
  ]
}}
"""
        
        try:
            # Use JSON schema for guaranteed structure
            schema = GeminiSchemas.batch_pattern_analysis()
            
            response_text = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_PRECISE,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_LARGE,
                response_format="json",
                response_schema=schema if self.ai_manager.provider_type == "gemini" else None
            )
            
            # With JSON schema, response is guaranteed to be valid JSON
            result = json.loads(response_text)
            logger.info(f"Batch analysis successful: received data for {len(result.get('files', []))} files")
            
            # Schema guarantees 'files' key exists
            files_data = result.get('files', [])
            
            # Convert to FileAnalysis objects
            analyses = {}
            for file_data in files_data:
                file_path = file_data['file_path']
                language = file_data.get('language', 'Unknown')
                framework = file_data.get('framework')
                
                patterns = []
                for p in file_data.get('patterns', []):
                    patterns.append(DetectedPattern(
                        pattern_type=p['pattern_type'],
                        severity=PatternSeverity(p['severity']),
                        file_path=file_path,
                        language=language,
                        description=p['description'],
                        line_numbers=p.get('line_numbers', []),
                        confidence=p.get('confidence', 0.8),
                        recommendation=p['recommendation'],
                        estimated_effort_hours=p.get('estimated_effort_hours', 1.0)
                    ))
                
                analysis = FileAnalysis(
                    file_path=file_path,
                    language=language,
                    framework=framework,
                    patterns=patterns,
                    overall_priority=PatternSeverity(file_data.get('overall_priority', 'medium')),
                    modernization_score=file_data.get('modernization_score', 50),
                    requires_modernization=file_data.get('requires_modernization', True)
                )
                
                analyses[file_path] = analysis
            
            logger.info(f"Batch API call successful: analyzed {len(analyses)} files")
            return analyses
            
        except Exception as e:
            logger.error(f"Batch API call failed: {e}")
            raise
    
    def prioritize_files(self, analyses: Dict[str, FileAnalysis]) -> List[Tuple[str, FileAnalysis]]:
        """
        Prioritize files for modernization based on analysis.
        
        Args:
            analyses: Dictionary of file analyses
        
        Returns:
            Sorted list of (file_path, analysis) tuples, highest priority first
        """
        # Define priority weights
        severity_weights = {
            PatternSeverity.CRITICAL: 100,
            PatternSeverity.HIGH: 75,
            PatternSeverity.MEDIUM: 50,
            PatternSeverity.LOW: 25,
            PatternSeverity.INFO: 10
        }
        
        def calculate_priority_score(analysis: FileAnalysis) -> float:
            """Calculate priority score for an analysis."""
            # Base score from overall priority
            base_score = severity_weights.get(analysis.overall_priority, 50)
            
            # Add points for each pattern weighted by severity and confidence
            pattern_score = sum(
                severity_weights.get(p.severity, 25) * p.confidence
                for p in analysis.patterns
            )
            
            # Factor in modernization score (lower = higher priority)
            modernization_penalty = (100 - analysis.modernization_score) / 10
            
            return base_score + pattern_score + modernization_penalty
        
        # Sort by priority score
        prioritized = sorted(
            analyses.items(),
            key=lambda x: calculate_priority_score(x[1]),
            reverse=True
        )
        
        return prioritized
    
    def generate_report(self, analyses: Dict[str, FileAnalysis]) -> str:
        """
        Generate human-readable report from analyses.
        
        Args:
            analyses: Dictionary of file analyses
        
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 80)
        report.append("INTELLIGENT PATTERN MATCHING REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary statistics
        total_files = len(analyses)
        files_needing_modernization = sum(1 for a in analyses.values() if a.requires_modernization)
        total_patterns = sum(len(a.patterns) for a in analyses.values())
        avg_modernization_score = sum(a.modernization_score for a in analyses.values()) / max(total_files, 1)
        
        report.append("SUMMARY:")
        report.append(f"  Total Files Analyzed: {total_files}")
        report.append(f"  Files Requiring Modernization: {files_needing_modernization}")
        report.append(f"  Total Patterns Detected: {total_patterns}")
        report.append(f"  Average Modernization Score: {avg_modernization_score:.1f}/100")
        report.append("")
        
        # Language breakdown
        language_counts = {}
        for analysis in analyses.values():
            language_counts[analysis.language] = language_counts.get(analysis.language, 0) + 1
        
        report.append("LANGUAGES:")
        for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
            report.append(f"  {lang}: {count} files")
        report.append("")
        
        # Severity breakdown
        severity_counts = {s: 0 for s in PatternSeverity}
        for analysis in analyses.values():
            for pattern in analysis.patterns:
                severity_counts[pattern.severity] += 1
        
        report.append("PATTERNS BY SEVERITY:")
        for severity in [PatternSeverity.CRITICAL, PatternSeverity.HIGH, 
                        PatternSeverity.MEDIUM, PatternSeverity.LOW, PatternSeverity.INFO]:
            count = severity_counts[severity]
            if count > 0:
                report.append(f"  {severity.value.upper()}: {count}")
        report.append("")
        
        # Top priority files
        prioritized = self.prioritize_files(analyses)[:10]
        report.append("TOP 10 PRIORITY FILES:")
        for i, (file_path, analysis) in enumerate(prioritized, 1):
            report.append(f"  {i}. {file_path}")
            report.append(f"     Priority: {analysis.overall_priority.value}")
            report.append(f"     Modernization Score: {analysis.modernization_score}/100")
            report.append(f"     Patterns: {len(analysis.patterns)}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def _serialize_analysis(self, analysis: FileAnalysis) -> dict:
        """Serialize FileAnalysis to dict for caching."""
        return {
            'file_path': analysis.file_path,
            'language': analysis.language,
            'framework': analysis.framework,
            'patterns': [
                {
                    'pattern_type': p.pattern_type,
                    'severity': p.severity.value,
                    'file_path': p.file_path,
                    'language': p.language,
                    'description': p.description,
                    'line_numbers': p.line_numbers,
                    'confidence': p.confidence,
                    'recommendation': p.recommendation,
                    'estimated_effort_hours': p.estimated_effort_hours
                }
                for p in analysis.patterns
            ],
            'overall_priority': analysis.overall_priority.value,
            'modernization_score': analysis.modernization_score,
            'requires_modernization': analysis.requires_modernization
        }
    
    def _deserialize_analysis(self, data: dict) -> FileAnalysis:
        """Deserialize dict to FileAnalysis."""
        patterns = [
            DetectedPattern(
                pattern_type=p['pattern_type'],
                severity=PatternSeverity(p['severity']),
                file_path=p['file_path'],
                language=p['language'],
                description=p['description'],
                line_numbers=p['line_numbers'],
                confidence=p['confidence'],
                recommendation=p['recommendation'],
                estimated_effort_hours=p['estimated_effort_hours']
            )
            for p in data['patterns']
        ]
        
        return FileAnalysis(
            file_path=data['file_path'],
            language=data['language'],
            framework=data['framework'],
            patterns=patterns,
            overall_priority=PatternSeverity(data['overall_priority']),
            modernization_score=data['modernization_score'],
            requires_modernization=data['requires_modernization']
        )
