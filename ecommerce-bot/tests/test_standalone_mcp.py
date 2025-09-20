#!/usr/bin/env python3
"""
Test script to verify standalone MCP client connection
"""
import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client.mcp_client import MCPClient
from services.redis.redis_service_enhanced import EnhancedRedisService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_direct_mcp_connection():
    """Test direct MCP client connection"""
    logger.info("Testing standalone MCP client connection...")
    
    # Initialize Redis service for session management
    redis_service = EnhancedRedisService()
    
    # Create MCP client
    client = MCPClient(
        user_id="test_user_123",
        session_manager=redis_service,
        llm_client=None,
        server_manager=None
    )
    
    try:
        # Connect to MCP server
        await client.connect_to_server()
        logger.info(f"Connected! Available tools: {len(client.tools)}")
        
        # List available tools
        for tool in client.tools:
            logger.info(f"  - {tool['name']}: {tool['description']}")
        
        # Test processing a message
        logger.info("\nTesting message processing...")
        result = await client.process_message("Show me some laptops under $1000")
        
        logger.info(f"\nResponse: {result['reply'][:200]}...")
        logger.info(f"Tools used: {result['metadata'].get('tools_used', [])}")
        
        # Test another message
        logger.info("\nTesting cart functionality...")
        result2 = await client.process_message("Add PROD001 to my cart")
        logger.info(f"\nResponse: {result2['reply'][:200]}...")
        
        # Disconnect
        await client.disconnect()
        logger.info("Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)


async def test_with_context_manager():
    """Test MCP client using context manager"""
    logger.info("\nTesting with context manager...")
    
    redis_service = EnhancedRedisService()
    
    client = MCPClient(
        user_id="test_user_456", 
        session_manager=redis_service,
        llm_client=None,
        server_manager=None
    )
    
    try:
        async with client:
            logger.info("Connected via context manager")
            result = await client.process_message("Show me the cart")
            logger.info(f"Response: {result['reply'][:200]}...")
            
    except Exception as e:
        logger.error(f"Context manager test failed: {str(e)}", exc_info=True)


async def main():
    """Run all tests"""
    logger.info("Starting standalone MCP client tests...")
    
    # Test 1: Direct connection
    await test_direct_mcp_connection()
    
    logger.info("-" * 50)
    
    # Test 2: Context manager
    await test_with_context_manager()
    
    logger.info("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(main())