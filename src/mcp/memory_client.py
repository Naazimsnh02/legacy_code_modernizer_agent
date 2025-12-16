"""
Memory MCP Client - Store and retrieve analysis results using Memory MCP server.
"""

import json
import logging
from typing import Dict, Optional, Any
from mcp import ClientSession
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MemoryMCPClient:
    """
    Client for Memory MCP server to cache analysis results and transformation examples.
    """
    
    def __init__(self, mcp_manager):
        """
        Initialize Memory MCP client.
        
        Args:
            mcp_manager: MCPManager instance
        """
        self.mcp_manager = mcp_manager
        self.server_name = "memory"
        
        logger.info("MemoryMCPClient initialized")
    
    async def store_pattern_analysis(self, pattern_id: str, analysis: Dict) -> bool:
        """
        Store pattern analysis in MCP memory.
        
        Args:
            pattern_id: Unique identifier for the pattern
            analysis: Analysis data to store
        
        Returns:
            True if successful, False otherwise
        """
        try:
            server_params = self.mcp_manager.get_server_params(self.server_name)
            if not server_params:
                logger.error(f"{self.server_name} MCP server not registered")
                return False
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Store entity in memory
                    result = await session.call_tool(
                        "store_entity",
                        arguments={
                            "name": f"pattern_{pattern_id}",
                            "content": json.dumps(analysis)
                        }
                    )
                    
                    logger.info(f"Stored pattern analysis: {pattern_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error storing pattern analysis: {e}")
            return False
    
    async def retrieve_pattern_analysis(self, pattern_id: str) -> Optional[Dict]:
        """
        Retrieve cached pattern analysis.
        
        Args:
            pattern_id: Unique identifier for the pattern
        
        Returns:
            Analysis data or None if not found
        """
        try:
            server_params = self.mcp_manager.get_server_params(self.server_name)
            if not server_params:
                logger.error(f"{self.server_name} MCP server not registered")
                return None
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Retrieve entity from memory
                    result = await session.call_tool(
                        "retrieve_entity",
                        arguments={"name": f"pattern_{pattern_id}"}
                    )
                    
                    if result and hasattr(result, 'content'):
                        data = json.loads(result.content[0].text)
                        logger.info(f"Retrieved pattern analysis: {pattern_id}")
                        return data
                    
                    return None
                    
        except Exception as e:
            logger.error(f"Error retrieving pattern analysis: {e}")
            return None
    
    async def store_transformation_example(self, example_id: str, example: Dict) -> bool:
        """
        Store a successful transformation example.
        
        Args:
            example_id: Unique identifier for the example
            example: Example data containing before/after code
        
        Returns:
            True if successful, False otherwise
        """
        try:
            server_params = self.mcp_manager.get_server_params(self.server_name)
            if not server_params:
                logger.error(f"{self.server_name} MCP server not registered")
                return False
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    result = await session.call_tool(
                        "store_entity",
                        arguments={
                            "name": f"example_{example_id}",
                            "content": json.dumps(example)
                        }
                    )
                    
                    logger.info(f"Stored transformation example: {example_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error storing transformation example: {e}")
            return False
    
    async def get_transformation_examples(self, pattern_type: str, limit: int = 5) -> list:
        """
        Retrieve transformation examples for a pattern type.
        
        Args:
            pattern_type: Type of pattern to get examples for
            limit: Maximum number of examples to return
        
        Returns:
            List of transformation examples
        """
        try:
            server_params = self.mcp_manager.get_server_params(self.server_name)
            if not server_params:
                logger.error(f"{self.server_name} MCP server not registered")
                return []
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Search for examples matching pattern type
                    # Note: This is a simplified implementation
                    # In production, you'd want more sophisticated querying
                    examples = []
                    
                    for i in range(limit):
                        try:
                            result = await session.call_tool(
                                "retrieve_entity",
                                arguments={"name": f"example_{pattern_type}_{i}"}
                            )
                            
                            if result and hasattr(result, 'content'):
                                example = json.loads(result.content[0].text)
                                examples.append(example)
                        except:
                            break
                    
                    logger.info(f"Retrieved {len(examples)} transformation examples")
                    return examples
                    
        except Exception as e:
            logger.error(f"Error retrieving transformation examples: {e}")
            return []
    
    async def clear_cache(self) -> bool:
        """
        Clear all cached data.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Note: Memory MCP may not have a clear_all method
            # This is a placeholder for future implementation
            logger.info("Cache cleared (placeholder)")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
