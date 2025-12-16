"""
MCP Manager - Central orchestrator for multiple MCP server connections.
"""

import os
import logging
from typing import Dict, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPManager:
    """
    Manages multiple MCP server connections and sessions.
    Provides centralized connection pooling and session management.
    """
    
    def __init__(self):
        """Initialize MCP Manager."""
        self.servers: Dict[str, StdioServerParameters] = {}
        self.sessions: Dict[str, ClientSession] = {}
        self.active_connections: Dict[str, bool] = {}
        
        logger.info("MCPManager initialized")
    
    def register_server(self, name: str, command: str, args: list, env: Optional[Dict] = None):
        """
        Register an MCP server configuration.
        
        Args:
            name: Unique name for the server
            command: Command to start the server
            args: Arguments for the command
            env: Optional environment variables
        """
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env or {}
        )
        
        self.servers[name] = server_params
        self.active_connections[name] = False
        
        logger.info(f"Registered MCP server: {name}")
    
    def register_github_server(self):
        """Register GitHub MCP server."""
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logger.warning("GITHUB_TOKEN not set, GitHub MCP will not be available")
            return
        
        self.register_server(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": github_token}
        )
    
    def register_tavily_server(self):
        """Register Tavily Search MCP server."""
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            logger.warning("TAVILY_API_KEY not set, Tavily MCP will not be available")
            return
        
        self.register_server(
            name="tavily",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-tavily"],
            env={"TAVILY_API_KEY": tavily_key}
        )
    
    def register_memory_server(self):
        """Register Memory MCP server."""
        self.register_server(
            name="memory",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"]
        )
    
    def register_filesystem_server(self, allowed_directories: Optional[list] = None):
        """
        Register Filesystem MCP server.
        
        Args:
            allowed_directories: List of allowed directories for file access
        """
        args = ["-y", "@modelcontextprotocol/server-filesystem"]
        
        if allowed_directories:
            args.extend(allowed_directories)
        
        self.register_server(
            name="filesystem",
            command="npx",
            args=args
        )
    
    def get_server_params(self, name: str) -> Optional[StdioServerParameters]:
        """
        Get server parameters by name.
        
        Args:
            name: Server name
        
        Returns:
            Server parameters or None if not found
        """
        return self.servers.get(name)
    
    def is_server_registered(self, name: str) -> bool:
        """
        Check if a server is registered.
        
        Args:
            name: Server name
        
        Returns:
            True if registered, False otherwise
        """
        return name in self.servers
    
    def list_servers(self) -> list:
        """
        List all registered servers.
        
        Returns:
            List of server names
        """
        return list(self.servers.keys())
    
    async def initialize_all_servers(self):
        """Initialize all registered MCP servers."""
        logger.info("Initializing all MCP servers...")
        
        for name in self.servers:
            try:
                logger.info(f"Initializing {name} MCP server...")
                # Note: Actual initialization happens when clients connect
                self.active_connections[name] = True
            except Exception as e:
                logger.error(f"Failed to initialize {name}: {e}")
                self.active_connections[name] = False
        
        logger.info("MCP server initialization complete")
    
    def get_active_servers(self) -> list:
        """
        Get list of active server connections.
        
        Returns:
            List of active server names
        """
        return [name for name, active in self.active_connections.items() if active]

    def register_all_standard_servers(self):
        """Register all standard MCP servers."""
        logger.info("Registering all standard MCP servers...")
        
        self.register_github_server()
        self.register_tavily_server()
        self.register_memory_server()
        self.register_filesystem_server()
        
        logger.info(f"Registered {len(self.servers)} MCP servers")
