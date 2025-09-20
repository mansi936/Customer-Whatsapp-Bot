"""
Test MCP Client with Unified LLM Service
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.mcp_client import MCPClient
from services.redis.redis_service_enhanced import EnhancedRedisService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Mock server manager for testing
class MockServerManager:
    async def get_available_tools(self):
        """Return mock tools for testing"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_products",
                    "description": "Search for products",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "show_cart",
                    "description": "Show shopping cart",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]
    
    async def route_tool(self, tool_name: str, **kwargs):
        """Mock tool execution"""
        if tool_name == "search_products":
            return {
                "products": [
                    {"name": "Blue Shirt", "price": 999, "description": "Comfortable cotton shirt"},
                    {"name": "Red Shirt", "price": 899, "description": "Stylish casual shirt"}
                ]
            }
        elif tool_name == "show_cart":
            return {
                "items": [
                    {"name": "Blue Shirt", "quantity": 1, "price": 999}
                ],
                "total": 999
            }
        return {"error": "Unknown tool"}


async def test_mcp_client():
    """Test the MCP client with unified LLM service"""
    logger.info("Testing MCP Client with Unified LLM Service...")
    
    # Initialize services
    redis_service = EnhancedRedisService()
    await redis_service.initialize()
    
    server_manager = MockServerManager()
    
    # Create MCP client (no llm_client needed)
    client = MCPClient(
        user_id="test_user_123",
        session_manager=redis_service,
        server_manager=server_manager
    )
    
    # Test 1: Simple message
    logger.info("\n=== Test 1: Simple message ===")
    response = await client.process_message("Hello! How can you help me?")
    logger.info(f"Response: {response['reply']}")
    
    # Test 2: Product search (should trigger tool use)
    logger.info("\n=== Test 2: Product search ===")
    response = await client.process_message("Show me shirts")
    logger.info(f"Response: {response['reply']}")
    if response['metadata'].get('tools_used'):
        logger.info(f"Tools used: {[t['name'] for t in response['metadata']['tools_used']]}")
    
    # Test 3: Show cart
    logger.info("\n=== Test 3: Show cart ===")
    response = await client.process_message("What's in my cart?")
    logger.info(f"Response: {response['reply']}")
    
    # Test 4: Check LLM service stats
    from services.llm.unified_llm_service import get_llm_service
    llm_service = get_llm_service()
    stats = llm_service.get_stats()
    logger.info(f"\n=== LLM Service Stats ===")
    logger.info(f"Primary provider: {stats['primary_provider']}")
    logger.info(f"Enabled providers: {stats['enabled_providers']}")
    logger.info(f"Requests by provider: {stats['stats']['requests_by_provider']}")


async def test_error_handling():
    """Test error handling and fallback"""
    logger.info("\n\n=== Testing Error Handling ===")
    
    # Create client without server manager to test error handling
    redis_service = EnhancedRedisService()
    await redis_service.initialize()
    
    client = MCPClient(
        user_id="test_user_error",
        session_manager=redis_service,
        server_manager=None  # No server manager
    )
    
    response = await client.process_message("This should handle errors gracefully")
    logger.info(f"Error response: {response['reply']}")
    if 'error' in response:
        logger.info(f"Error details: {response['error']}")


async def main():
    """Run all tests"""
    try:
        await test_mcp_client()
        await test_error_handling()
        logger.info("\n\nAll tests completed!")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())