import asyncio
import logging
import os
import sys
from collections import deque
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
import time
from datetime import datetime
from .mcp_client import MCPClient

logger = logging.getLogger(__name__)


class ClientConnection:
    """Wrapper for MCP client with connection metadata"""
    def __init__(self, client: MCPClient, connection_id: str):
        self.client = client
        self.connection_id = connection_id
        self.created_at = datetime.utcnow()
        self.last_used = datetime.utcnow()
        self.use_count = 0
        self.is_busy = False
        self.current_user = None
        
    def mark_used(self, user_id: str):
        """Mark connection as used"""
        self.last_used = datetime.utcnow()
        self.use_count += 1
        self.is_busy = True
        self.current_user = user_id
        
    def mark_released(self):
        """Mark connection as released"""
        self.is_busy = False
        self.current_user = None


class ClientPool:
    """Connection pool for MCP clients"""
    
    def __init__(self, pool_size: int = 5, 
                 session_manager=None, 
                 llm_client=None,  # Kept for backward compatibility but not used
                 server_manager=None):
        self.pool_size = pool_size
        self.session_manager = session_manager
        self.llm_client = None  # Not used anymore, MCP client uses unified service directly
        self.server_manager = server_manager
        
        # Pool of available connections
        self.available_connections = deque()
        
        # All connections (both available and in use)
        self.all_connections: Dict[str, ClientConnection] = {}
        
        # User to connection mapping
        self.user_connections: Dict[str, str] = {}
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            "connections_created": 0,
            "connections_reused": 0,
            "total_requests": 0,
            "pool_exhausted_count": 0
        }
        
        logger.info(f"Initialized ClientPool with size {pool_size}")

    async def initialize(self):
        """Initialize the pool with connections"""
        async with self._lock:
            # Create initial connections
            for i in range(min(2, self.pool_size)):  # Start with 2 connections
                await self._create_connection(f"init_{i}")
            logger.info(f"Created {len(self.all_connections)} initial connections")

    async def _create_connection(self, user_id: str) -> ClientConnection:
        """Create a new MCP client connection"""
        connection_id = f"conn_{user_id}_{int(time.time() * 1000)}"
        
        # Create new MCP client (standalone with STDIO connection)
        client = MCPClient(
            user_id=user_id,
            session_manager=self.session_manager,
            llm_client=None,
            server_manager=None  # Not used in standalone mode
        )
        
        # Connect to MCP server
        await client.connect_to_server()
        
        # Wrap in connection object
        connection = ClientConnection(client, connection_id)
        
        # Add to pool
        self.all_connections[connection_id] = connection
        self.available_connections.append(connection_id)
        
        self.stats["connections_created"] += 1
        
        logger.info(f"Created new connection {connection_id} for user {user_id}")
        return connection

    @asynccontextmanager
    async def get_connection(self, user_id: str):
        """Get a connection from the pool for a specific user"""
        connection = None
        acquisition_start = time.time()
        
        try:
            async with self._lock:
                self.stats["total_requests"] += 1
                
                # Check if user already has a connection
                if user_id in self.user_connections:
                    connection_id = self.user_connections[user_id]
                    if connection_id in self.all_connections:
                        connection = self.all_connections[connection_id]
                        if not connection.is_busy:
                            # Reuse existing connection for this user
                            connection.mark_used(user_id)
                            self.stats["connections_reused"] += 1
                            
                            # Add metadata for tracking
                            connection.client._connection_id = connection_id
                            connection.client._was_reused = True
                            connection.client._acquisition_time_seconds = time.time() - acquisition_start
                            
                            logger.info(f"Reusing connection {connection_id} for user {user_id}")
                            yield connection.client
                            return
                
                # Try to get an available connection
                while self.available_connections:
                    connection_id = self.available_connections.popleft()
                    connection = self.all_connections.get(connection_id)
                    
                    if connection and not connection.is_busy:
                        # Update the client's user_id
                        connection.client.user_id = user_id
                        connection.mark_used(user_id)
                        self.user_connections[user_id] = connection_id
                        
                        # Add metadata
                        connection.client._connection_id = connection_id
                        connection.client._was_reused = False
                        connection.client._acquisition_time_seconds = time.time() - acquisition_start
                        
                        logger.info(f"Assigned connection {connection_id} to user {user_id}")
                        yield connection.client
                        return
                
                # No available connections, create new one if under limit
                if len(self.all_connections) < self.pool_size:
                    connection = await self._create_connection(user_id)
                    connection.mark_used(user_id)
                    self.user_connections[user_id] = connection.connection_id
                    
                    # Remove from available since it's now in use
                    if connection.connection_id in self.available_connections:
                        self.available_connections.remove(connection.connection_id)
                    
                    # Add metadata
                    connection.client._connection_id = connection.connection_id
                    connection.client._was_reused = False
                    connection.client._acquisition_time_seconds = time.time() - acquisition_start
                    
                    yield connection.client
                    return
                else:
                    # Pool exhausted
                    self.stats["pool_exhausted_count"] += 1
                    logger.warning(f"Pool exhausted for user {user_id}, creating temporary connection")
                    
                    # Create temporary connection outside pool limit
                    temp_client = MCPClient(
                        user_id=user_id,
                        session_manager=self.session_manager,
                        llm_client=None,
                        server_manager=None
                    )
                    
                    # Connect to MCP server
                    await temp_client.connect_to_server()
                    
                    # Add metadata
                    temp_client._connection_id = f"temp_{user_id}_{int(time.time() * 1000)}"
                    temp_client._was_reused = False
                    temp_client._acquisition_time_seconds = time.time() - acquisition_start
                    
                    try:
                        yield temp_client
                    finally:
                        # Disconnect temporary client
                        await temp_client.disconnect()
                    return
                    
        finally:
            # Release connection back to pool
            if connection:
                async with self._lock:
                    connection.mark_released()
                    if connection.connection_id not in self.available_connections:
                        self.available_connections.append(connection.connection_id)
                    logger.debug(f"Released connection {connection.connection_id}")

    async def acquire(self, user_id: str) -> MCPClient:
        """Legacy acquire method - use get_connection context manager instead"""
        logger.warning("Using deprecated acquire() method, use get_connection() context manager instead")
        
        async with self._lock:
            # Try to find available connection
            if self.available_connections:
                connection_id = self.available_connections.popleft()
                connection = self.all_connections[connection_id]
                connection.client.user_id = user_id
                connection.mark_used(user_id)
                self.user_connections[user_id] = connection_id
                return connection.client
            
            # Create new if under limit
            if len(self.all_connections) < self.pool_size:
                connection = await self._create_connection(user_id)
                connection.mark_used(user_id)
                self.user_connections[user_id] = connection.connection_id
                return connection.client
            
            # Return None if pool exhausted
            return None

    async def release(self, client: MCPClient):
        """Legacy release method - use get_connection context manager instead"""
        logger.warning("Using deprecated release() method, use get_connection() context manager instead")
        
        async with self._lock:
            # Find connection by client
            for conn_id, connection in self.all_connections.items():
                if connection.client == client:
                    connection.mark_released()
                    if conn_id not in self.available_connections:
                        self.available_connections.append(conn_id)
                    break

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        busy_count = sum(1 for conn in self.all_connections.values() if conn.is_busy)
        
        return {
            **self.stats,
            "pool_size": self.pool_size,
            "total_connections": len(self.all_connections),
            "available_connections": len(self.available_connections),
            "busy_connections": busy_count,
            "users_mapped": len(self.user_connections)
        }

    async def close(self):
        """Close all connections in the pool"""
        async with self._lock:
            logger.info("Closing client pool...")
            
            # Disconnect all MCP clients
            for connection in self.all_connections.values():
                try:
                    await connection.client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting client: {str(e)}")
            
            # Clear all connections
            self.available_connections.clear()
            self.all_connections.clear()
            self.user_connections.clear()
            
            logger.info("Client pool closed")
