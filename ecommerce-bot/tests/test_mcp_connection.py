#!/usr/bin/env python3
"""
Test script to verify MCP server connection and tool execution
"""
import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.mcp_client import MCPClient
from services.redis.redis_service_enhanced import EnhancedRedisService
from client.client_pool import ClientPool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_server_connection():
    """Test direct server connection using standalone MCP client"""
    logger.info("Testing direct MCP server connection...")
    
    try:
        # Create standalone MCP client
        redis_service = EnhancedRedisService()
        client = MCPClient(
            user_id="test_direct_connection",
            session_manager=redis_service,
            llm_client=None,
            server_manager=None
        )
        
        # Connect to server
        await client.connect_to_server()
        
        # Get available tools
        logger.info(f"Available tools: {[tool['name'] for tool in client.tools]}")
        
        # Test a simple tool call via session
        if client.tools:
            test_tool = client.tools[0]['name']
            logger.info(f"Testing tool: {test_tool}")
            
            # Test search_products directly
            if test_tool == "search_products":
                result = await client.session.call_tool(
                    "search_products",
                    {"query": "laptop", "limit": 3}
                )
                logger.info(f"Tool result: {result}")
        
        # Test message processing
        response = await client.process_message("Show me some laptops")
        logger.info(f"Message processing result: {response['reply'][:100]}...")
        
        # Disconnect
        await client.disconnect()
        logger.info("Server connection test completed successfully!")
        
    except Exception as e:
        logger.error(f"Server connection test failed: {str(e)}", exc_info=True)


async def test_client_pool():
    """Test client pool with MCP server"""
    logger.info("Testing client pool with MCP server...")
    
    try:
        # Initialize Redis service
        redis_service = EnhancedRedisService()
        
        # Create client pool (clients will connect to MCP server automatically)
        client_pool = ClientPool(
            pool_size=3,
            session_manager=redis_service,
            llm_client=None,
            server_manager=None  # Not used in standalone mode
        )
        
        # Initialize the pool
        await client_pool.initialize()
        
        # Get pool stats
        stats = client_pool.get_stats()
        logger.info(f"Pool stats: {stats}")
        
        # Test getting a client
        async with client_pool.get_connection("test_user_123") as client:
            logger.info(f"Got client for test_user_123")
            
            # Process a test message
            result = await client.process_message("Show me some laptops under $1000")
            logger.info(f"Message processing result: {result}")
        
        # Close the pool
        await client_pool.close()
        logger.info("Client pool test completed successfully!")
        
    except Exception as e:
        logger.error(f"Client pool test failed: {str(e)}", exc_info=True)


async def main():
    """Run all tests"""
    logger.info("Starting MCP connection tests...")
    
    # Test 1: Direct server connection
    await test_server_connection()
    
    logger.info("-" * 50)
    
    # Test 2: Client pool with server
    await test_client_pool()
    
    logger.info("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())