"""
Integration layer for the new IntelligentPatternMatcher with existing workflow.
Provides backward compatibility while enabling advanced pattern detection.
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path

from .pattern_matcher import (
    IntelligentPatternMatcher,
    FileAnalysis,
    PatternSeverity
)
from .classifier import CodeClassifier

logger = logging.getLogger(__name__)


class PatternMatcherIntegration:
    """
    Integrates IntelligentPatternMatcher with existing workflow.
    Provides compatibility layer for gradual migration.
    """
    
    def __init__(self, use_intelligent_matcher: bool = True, cache_dir: Optional[str] = None):
        """
        Initialize integration layer.
        
        Args:
            use_intelligent_matcher: If True, use new AI-powered matcher
            cache_dir: Optional cache directory for pattern analysis
        """
        self.use_intelligent_matcher = use_intelligent_matcher
        
        if use_intelligent_matcher:
            self.pattern_matcher = IntelligentPatternMatcher(cache_dir=cache_dir)
            logger.info("Using IntelligentPatternMatcher")
        else:
            self.classifier = CodeClassifier()
            logger.info("Using legacy CodeClassifier")
    
    def classify_files(self, files: List[str], file_contents: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Classify files using either intelligent matcher or legacy classifier.
        
        Args:
            files: List of file paths
            file_contents: Optional dict of file contents (required for intelligent matcher)
        
        Returns:
            Dictionary mapping filenames to categories
            Categories: 'modernize_high', 'modernize_low', 'skip'
        """
        if self.use_intelligent_matcher:
            return self._classify_with_intelligent_matcher(files, file_contents)
        else:
            return self.classifier.classify_files(files)
    
    def _classify_with_intelligent_matcher(
        self, 
        files: List[str], 
        file_contents: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        """
        Classify files using intelligent pattern matcher.
        
        Args:
            files: List of file paths
            file_contents: Dictionary of file contents
        
        Returns:
            Dictionary mapping filenames to categories
        """
        if not file_contents:
            logger.warning("No file contents provided, falling back to legacy classifier")
            return self.classifier.classify_files(files)
        
        classifications = {}
        
        # Analyze files
        analyses = self.pattern_matcher.analyze_batch(file_contents)
        
        # Convert analyses to legacy classification format
        for file_path, analysis in analyses.items():
            category = self._analysis_to_category(analysis)
            classifications[file_path] = category
        
        return classifications
    
    def _analysis_to_category(self, analysis: FileAnalysis) -> str:
        """
        Convert FileAnalysis to legacy category format.
        
        Args:
            analysis: FileAnalysis object
        
        Returns:
            Category string: 'modernize_high', 'modernize_low', or 'skip'
        """
        if not analysis.requires_modernization:
            return 'skip'
        
        # Check for critical or high severity patterns
        has_critical = any(
            p.severity == PatternSeverity.CRITICAL 
            for p in analysis.patterns
        )
        has_high = any(
            p.severity == PatternSeverity.HIGH 
            for p in analysis.patterns
        )
        
        # Check modernization score
        if has_critical or analysis.modernization_score < 50:
            return 'modernize_high'
        elif has_high or analysis.modernization_score < 75:
            return 'modernize_high'
        elif analysis.requires_modernization:
            return 'modernize_low'
        else:
            return 'skip'
    
    def get_detailed_analysis(self, file_path: str, code: str) -> FileAnalysis:
        """
        Get detailed pattern analysis for a single file.
        
        Args:
            file_path: Path to the file
            code: File contents
        
        Returns:
            FileAnalysis object with detailed pattern information
        """
        if not self.use_intelligent_matcher:
            raise ValueError("Detailed analysis requires intelligent matcher")
        
        return self.pattern_matcher.analyze_file(file_path, code)
    
    def get_transformation_plan(self, analysis: FileAnalysis) -> Dict:
        """
        Convert FileAnalysis to transformation plan format.
        
        Args:
            analysis: FileAnalysis object
        
        Returns:
            Transformation plan dictionary compatible with CodeTransformer
        """
        # Group patterns by type
        pattern_groups = {}
        for pattern in analysis.patterns:
            if pattern.pattern_type not in pattern_groups:
                pattern_groups[pattern.pattern_type] = []
            pattern_groups[pattern.pattern_type].append(pattern)
        
        # Build transformation steps
        steps = []
        total_effort = 0
        
        for pattern_type, patterns in pattern_groups.items():
            # Get highest severity pattern for this type
            highest_severity = max(patterns, key=lambda p: self._severity_to_int(p.severity))
            
            steps.append({
                'pattern': pattern_type,
                'severity': highest_severity.severity.value,
                'description': highest_severity.description,
                'recommendation': highest_severity.recommendation,
                'line_numbers': highest_severity.line_numbers,
                'confidence': highest_severity.confidence
            })
            
            total_effort += highest_severity.estimated_effort_hours
        
        return {
            'file_path': analysis.file_path,
            'language': analysis.language,
            'framework': analysis.framework,
            'pattern': f"{analysis.language} modernization",
            'steps': steps,
            'estimated_effort_hours': total_effort,
            'priority': analysis.overall_priority.value,
            'modernization_score': analysis.modernization_score
        }
    
    def _severity_to_int(self, severity: PatternSeverity) -> int:
        """Convert severity to integer for comparison."""
        severity_map = {
            PatternSeverity.CRITICAL: 5,
            PatternSeverity.HIGH: 4,
            PatternSeverity.MEDIUM: 3,
            PatternSeverity.LOW: 2,
            PatternSeverity.INFO: 1
        }
        return severity_map.get(severity, 0)
    
    def generate_statistics(self, analyses: Dict[str, FileAnalysis]) -> Dict:
        """
        Generate statistics from pattern analyses.
        
        Args:
            analyses: Dictionary of file analyses
        
        Returns:
            Statistics dictionary
        """
        total_files = len(analyses)
        
        # Count by category
        modernize_high = sum(
            1 for a in analyses.values() 
            if self._analysis_to_category(a) == 'modernize_high'
        )
        modernize_low = sum(
            1 for a in analyses.values() 
            if self._analysis_to_category(a) == 'modernize_low'
        )
        skip = total_files - modernize_high - modernize_low
        
        # Count patterns by severity
        severity_counts = {s.value: 0 for s in PatternSeverity}
        for analysis in analyses.values():
            for pattern in analysis.patterns:
                severity_counts[pattern.severity.value] += 1
        
        # Calculate average scores
        avg_modernization_score = (
            sum(a.modernization_score for a in analyses.values()) / max(total_files, 1)
        )
        
        # Estimate total effort
        total_effort = sum(
            sum(p.estimated_effort_hours for p in a.patterns)
            for a in analyses.values()
        )
        
        return {
            'total_files': total_files,
            'modernize_high': modernize_high,
            'modernize_low': modernize_low,
            'skip': skip,
            'severity_counts': severity_counts,
            'average_modernization_score': round(avg_modernization_score, 2),
            'total_estimated_effort_hours': round(total_effort, 2),
            'patterns_detected': sum(len(a.patterns) for a in analyses.values())
        }


def migrate_to_intelligent_matcher(
    orchestrator,
    repo_path: str,
    file_contents: Dict[str, str]
) -> Dict:
    """
    Helper function to migrate existing orchestrator to use intelligent matcher.
    
    Args:
        orchestrator: ModernizationOrchestrator instance
        repo_path: Path to repository
        file_contents: Dictionary of file contents
    
    Returns:
        Enhanced results with detailed pattern analysis
    """
    logger.info("Migrating to IntelligentPatternMatcher")
    
    # Create integration layer
    integration = PatternMatcherIntegration(
        use_intelligent_matcher=True,
        cache_dir=Path(repo_path) / ".pattern_cache"
    )
    
    # Analyze all files
    analyses = integration.pattern_matcher.analyze_batch(file_contents)
    
    # Generate prioritized list
    prioritized = integration.pattern_matcher.prioritize_files(analyses)
    
    # Convert to transformation plans
    transformation_plans = {}
    for file_path, analysis in prioritized:
        if analysis.requires_modernization:
            plan = integration.get_transformation_plan(analysis)
            transformation_plans[file_path] = plan
    
    # Generate report
    report = integration.pattern_matcher.generate_report(analyses)
    
    return {
        'analyses': analyses,
        'prioritized_files': prioritized,
        'transformation_plans': transformation_plans,
        'statistics': integration.generate_statistics(analyses),
        'report': report
    }
