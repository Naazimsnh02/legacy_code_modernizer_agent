"""
MCP (Model Context Protocol) integration module.
Manages connections to multiple MCP servers.
"""

# Avoid circular import by not importing at module level
# Import these when needed in your code instead

__all__ = ['MCPManager', 'MemoryMCPClient', 'SearchMCPClient', 'GitHubMCPClient']
