"""
Deep code analyzer using AI with RAG and MCP integration.
Supports multiple AI providers (Gemini, Nebius, OpenAI).
"""

import os
import json
import logging
from typing import Dict, List, Optional

from src.config import AIManager, GeminiSchemas

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """
    Deep analyzer for legacy code patterns using AI + RAG.
    Integrates with MCP servers for enhanced analysis.
    """
    
    def __init__(self, mcp_manager=None, search_engine=None):
        """
        Initialize Code Analyzer.
        
        Args:
            mcp_manager: Optional MCPManager instance
            search_engine: Optional CodeSearchEngine instance
        """
        self.mcp_manager = mcp_manager
        self.search_engine = search_engine
        
        # Use centralized AI manager
        self.ai_manager = AIManager()
        
        logger.info(
            f"CodeAnalyzer initialized with provider: {self.ai_manager.provider_name}, "
            f"model: {self.ai_manager.model_name}"
        )

    
    async def analyze_pattern(self, files: List[str], pattern_name: str, 
                             file_contents: Dict[str, str]) -> Dict:
        """
        Deep analysis of legacy pattern with full context.
        
        Args:
            files: List of file paths to analyze
            pattern_name: Name of the pattern (e.g., "MySQLdb usage")
            file_contents: Dictionary mapping file paths to their contents
        
        Returns:
            Analysis result dictionary
        """
        logger.info(f"Analyzing pattern: {pattern_name} in {len(files)} files")
        
        # Check cache first (if MCP manager available)
        if self.mcp_manager:
            try:
                from src.mcp.memory_client import MemoryMCPClient
                memory_client = MemoryMCPClient(self.mcp_manager)
                
                pattern_id = self._generate_pattern_id(pattern_name, files)
                cached_analysis = await memory_client.retrieve_pattern_analysis(pattern_id)
                
                if cached_analysis:
                    logger.info(f"Using cached analysis for {pattern_name}")
                    return cached_analysis
            except Exception as e:
                logger.warning(f"Could not retrieve cached analysis: {e}")
        
        # Get context from search engine if available
        context = ""
        if self.search_engine:
            try:
                similar_files = self.search_engine.find_similar_patterns(
                    f"Files with {pattern_name}",
                    top_k=10
                )
                context = f"\n\nSimilar patterns found in: {', '.join([f['file_path'] for f in similar_files[:5]])}"
            except Exception as e:
                logger.warning(f"Could not get search context: {e}")
        
        # Get migration guides from Tavily if available
        migration_guides = ""
        if self.mcp_manager:
            try:
                from src.mcp.search_client import SearchMCPClient
                search_client = SearchMCPClient(self.mcp_manager)
                
                # Extract technologies from pattern name
                guides = await search_client.find_migration_guide(
                    from_tech=pattern_name.split()[0],
                    to_tech="modern alternative",
                    max_results=3
                )
                
                if guides:
                    migration_guides = "\n\nRelevant migration guides:\n"
                    for guide in guides:
                        migration_guides += f"- {guide['title']}: {guide['url']}\n"
            except Exception as e:
                logger.warning(f"Could not fetch migration guides: {e}")
        
        # Combine file contents
        code_samples = "\n\n".join([
            f"=== {file_path} ===\n{content[:1000]}..."  # Limit to first 1000 chars per file
            for file_path, content in list(file_contents.items())[:5]  # Limit to 5 files
        ])
        
        # Build analysis prompt
        prompt = f"""You are a senior software architect analyzing legacy code for modernization.

PATTERN TO ANALYZE: {pattern_name}

FILES AFFECTED: {', '.join(files)}

CODE SAMPLES:
{code_samples}

{context}
{migration_guides}

TASK: Provide a comprehensive analysis with:
1. **Current Implementation**: What the code currently does
2. **Issues**: Specific problems (security, performance, maintainability)
3. **Modern Recommendation**: Recommended library/pattern with version
4. **Migration Steps**: Detailed step-by-step migration plan
5. **Risk Assessment**: Potential risks and mitigation strategies
6. **Estimated Effort**: Time estimate for migration

Respond in JSON format with these exact keys:
{{
  "pattern": "{pattern_name}",
  "files": {json.dumps(files)},
  "analysis": "detailed analysis",
  "issues": ["issue1", "issue2", ...],
  "recommendation": "recommended approach",
  "steps": ["step1", "step2", ...],
  "risks": "risk assessment",
  "effort_hours": estimated_hours
}}
"""
        
        try:
            # Use JSON schema for guaranteed structure
            schema = GeminiSchemas.code_analysis()
            
            # Call AI with configured model
            response_text = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_PRECISE,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_MEDIUM,
                response_format="json",
                response_schema=schema
            )
            
            # Parse JSON response
            analysis = json.loads(response_text)
            
            # Cache the analysis
            if self.mcp_manager:
                try:
                    from src.mcp.memory_client import MemoryMCPClient
                    memory_client = MemoryMCPClient(self.mcp_manager)
                    pattern_id = self._generate_pattern_id(pattern_name, files)
                    await memory_client.store_pattern_analysis(pattern_id, analysis)
                except Exception as e:
                    logger.warning(f"Could not cache analysis: {e}")
            
            logger.info(f"Analysis complete for {pattern_name}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            # Return fallback analysis
            return {
                "pattern": pattern_name,
                "files": files,
                "analysis": f"Error during analysis: {str(e)}",
                "issues": ["Analysis failed"],
                "recommendation": "Manual review required",
                "steps": ["Review error logs", "Retry analysis"],
                "risks": "High - analysis incomplete",
                "effort_hours": 0
            }
    
    def _generate_pattern_id(self, pattern_name: str, files: List[str]) -> str:
        """
        Generate unique ID for a pattern.
        
        Args:
            pattern_name: Name of the pattern
            files: List of files
        
        Returns:
            Unique pattern ID
        """
        import hashlib
        
        # Create hash from pattern name and sorted file list
        content = f"{pattern_name}:{'|'.join(sorted(files))}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def analyze_security_issues(self, file_path: str, code: str) -> Dict:
        """
        Analyze code for security vulnerabilities.
        
        Args:
            file_path: Path to the file
            code: Code content
        
        Returns:
            Security analysis result
        """
        logger.info(f"Analyzing security issues in {file_path}")
        
        prompt = f"""Analyze this code for security vulnerabilities:

FILE: {file_path}

CODE:
{code[:2000]}

Identify:
1. SQL injection risks
2. Hardcoded credentials
3. Insecure cryptography
4. Path traversal vulnerabilities
5. Command injection risks
6. Other security issues

Respond in JSON format:
{{
  "vulnerabilities": [
    {{
      "type": "vulnerability type",
      "severity": "critical|high|medium|low",
      "line_number": estimated_line,
      "description": "description",
      "recommendation": "how to fix"
    }}
  ],
  "security_score": 0-100
}}
"""
        
        try:
            response_text = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_PRECISE,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_SMALL,
                response_format="json"
            )
            
            return json.loads(response_text)
            
        except Exception as e:
            logger.error(f"Error during security analysis: {e}")
            return {
                "vulnerabilities": [],
                "security_score": 0
            }
    
    async def suggest_refactoring(self, file_path: str, code: str) -> Dict:
        """
        Suggest code refactoring improvements.
        
        Args:
            file_path: Path to the file
            code: Code content
        
        Returns:
            Refactoring suggestions
        """
        logger.info(f"Suggesting refactoring for {file_path}")
        
        prompt = f"""Suggest refactoring improvements for this code:

FILE: {file_path}

CODE:
{code[:2000]}

Focus on:
1. Code duplication
2. Complex functions (high cyclomatic complexity)
3. Poor naming conventions
4. Missing error handling
5. Performance optimizations
6. Type hints and documentation

Respond in JSON format:
{{
  "suggestions": [
    {{
      "category": "category",
      "priority": "high|medium|low",
      "description": "what to improve",
      "benefit": "why improve it"
    }}
  ],
  "code_quality_score": 0-100
}}
"""
        
        try:
            response_text = self.ai_manager.generate_content(
                prompt=prompt,
                temperature=AIManager.TEMPERATURE_PRECISE,
                max_tokens=AIManager.MAX_OUTPUT_TOKENS_SMALL,
                response_format="json"
            )
            
            return json.loads(response_text)
            
        except Exception as e:
            logger.error(f"Error during refactoring analysis: {e}")
            return {
                "suggestions": [],
                "code_quality_score": 0
            }
