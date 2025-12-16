"""
Search MCP Client - Find migration guides and documentation using Tavily MCP server.
"""

import logging
from typing import List, Dict, Optional
from mcp import ClientSession
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class SearchMCPClient:
    """
    Client for Tavily Search MCP server to find migration guides and best practices.
    """
    
    def __init__(self, mcp_manager):
        """
        Initialize Search MCP client.
        
        Args:
            mcp_manager: MCPManager instance
        """
        self.mcp_manager = mcp_manager
        self.server_name = "tavily"
        
        logger.info("SearchMCPClient initialized")
    
    async def find_migration_guide(self, from_tech: str, to_tech: str, max_results: int = 5) -> List[Dict]:
        """
        Find migration documentation for technology upgrade.
        
        Args:
            from_tech: Source technology (e.g., "Python 2.7")
            to_tech: Target technology (e.g., "Python 3.12")
            max_results: Maximum number of results to return
        
        Returns:
            List of search results with URLs and snippets
        """
        try:
            server_params = self.mcp_manager.get_server_params(self.server_name)
            if not server_params:
                logger.warning(f"{self.server_name} MCP server not registered, returning empty results")
                return []
            
            query = f"{from_tech} to {to_tech} migration guide best practices"
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    result = await session.call_tool(
                        "search",
                        arguments={
                            "query": query,
                            "max_results": max_results
                        }
                    )
                    
                    # Parse results
                    results = []
                    if result and hasattr(result, 'content'):
                        for item in result.content:
                            if hasattr(item, 'text'):
                                results.append({
                                    'title': item.text.get('title', ''),
                                    'url': item.text.get('url', ''),
                                    'snippet': item.text.get('snippet', ''),
                                    'score': item.text.get('score', 0)
                                })
                    
                    logger.info(f"Found {len(results)} migration guides for {from_tech} to {to_tech}")
                    return results
                    
        except Exception as e:
            logger.error(f"Error finding migration guide: {e}")
            return []
    
    async def find_library_documentation(self, library_name: str, version: Optional[str] = None) -> List[Dict]:
        """
        Find official documentation for a library.
        
        Args:
            library_name: Name of the library
            version: Optional specific version
        
        Returns:
            List of documentation links
        """
        try:
            server_params = self.mcp_manager.get_server_params(self.server_name)
            if not server_params:
                logger.warning(f"{self.server_name} MCP server not registered, returning empty results")
                return []
            
            query = f"{library_name} official documentation"
            if version:
                query += f" version {version}"
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    result = await session.call_tool(
                        "search",
                        arguments={
                            "query": query,
                            "max_results": 3
                        }
                    )
                    
                    results = []
                    if result and hasattr(result, 'content'):
                        for item in result.content:
                            if hasattr(item, 'text'):
                                results.append({
                                    'title': item.text.get('title', ''),
                                    'url': item.text.get('url', ''),
                                    'snippet': item.text.get('snippet', '')
                                })
                    
                    logger.info(f"Found {len(results)} documentation links for {library_name}")
                    return results
                    
        except Exception as e:
            logger.error(f"Error finding library documentation: {e}")
            return []
    
    async def find_best_practices(self, topic: str, language: str = "python") -> List[Dict]:
        """
        Find best practices for a specific topic.
        
        Args:
            topic: Topic to search for (e.g., "database connection pooling")
            language: Programming language
        
        Returns:
            List of best practice resources
        """
        try:
            server_params = self.mcp_manager.get_server_params(self.server_name)
            if not server_params:
                logger.warning(f"{self.server_name} MCP server not registered, returning empty results")
                return []
            
            query = f"{language} {topic} best practices 2024"
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    result = await session.call_tool(
                        "search",
                        arguments={
                            "query": query,
                            "max_results": 5
                        }
                    )
                    
                    results = []
                    if result and hasattr(result, 'content'):
                        for item in result.content:
                            if hasattr(item, 'text'):
                                results.append({
                                    'title': item.text.get('title', ''),
                                    'url': item.text.get('url', ''),
                                    'snippet': item.text.get('snippet', '')
                                })
                    
                    logger.info(f"Found {len(results)} best practice resources for {topic}")
                    return results
                    
        except Exception as e:
            logger.error(f"Error finding best practices: {e}")
            return []
    
    async def find_security_vulnerabilities(self, pattern: str, language: str = "python") -> List[Dict]:
        """
        Find information about security vulnerabilities in a code pattern.
        
        Args:
            pattern: Code pattern to check (e.g., "SQL string interpolation")
            language: Programming language
        
        Returns:
            List of security resources
        """
        try:
            server_params = self.mcp_manager.get_server_params(self.server_name)
            if not server_params:
                logger.warning(f"{self.server_name} MCP server not registered, returning empty results")
                return []
            
            query = f"{language} {pattern} security vulnerability CVE"
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    result = await session.call_tool(
                        "search",
                        arguments={
                            "query": query,
                            "max_results": 5
                        }
                    )
                    
                    results = []
                    if result and hasattr(result, 'content'):
                        for item in result.content:
                            if hasattr(item, 'text'):
                                results.append({
                                    'title': item.text.get('title', ''),
                                    'url': item.text.get('url', ''),
                                    'snippet': item.text.get('snippet', ''),
                                    'severity': self._extract_severity(item.text.get('snippet', ''))
                                })
                    
                    logger.info(f"Found {len(results)} security resources for {pattern}")
                    return results
                    
        except Exception as e:
            logger.error(f"Error finding security vulnerabilities: {e}")
            return []
    
    def _extract_severity(self, text: str) -> str:
        """
        Extract severity level from text.
        
        Args:
            text: Text to analyze
        
        Returns:
            Severity level (critical, high, medium, low, unknown)
        """
        text_lower = text.lower()
        if 'critical' in text_lower:
            return 'critical'
        elif 'high' in text_lower:
            return 'high'
        elif 'medium' in text_lower or 'moderate' in text_lower:
            return 'medium'
        elif 'low' in text_lower:
            return 'low'
        return 'unknown'
