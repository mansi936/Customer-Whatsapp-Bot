"""
Test script for Unified LLM Service
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm.unified_llm_service import get_llm_service
from services.llm.unified_llm_client import UnifiedLLMClient
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_unified_service():
    """Test the unified LLM service directly"""
    logger.info("Testing Unified LLM Service...")
    
    service = get_llm_service()
    
    # Show available providers
    logger.info(f"Available providers: {service.get_available_providers()}")
    
    # Test simple generation
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2+2? Reply in one word."}
    ]
    
    try:
        response = await service.generate_response_async(
            messages=messages,
            temperature=0,
            max_tokens=10
        )
        
        logger.info(f"Response from {response.provider}: {response.content}")
        logger.info(f"Model used: {response.model}")
        logger.info(f"Usage: {response.usage}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        
    # Test with tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Perform a calculation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Math expression to evaluate"}
                    },
                    "required": ["expression"]
                }
            }
        }
    ]
    
    messages_with_tool = [
        {"role": "user", "content": "Calculate 15 * 23"}
    ]
    
    try:
        response = await service.generate_response_async(
            messages=messages_with_tool,
            tools=tools,
            temperature=0
        )
        
        logger.info(f"\nTool response from {response.provider}:")
        logger.info(f"Content: {response.content}")
        if response.raw_response and "tool_calls" in response.raw_response:
            logger.info(f"Tool calls: {response.raw_response['tool_calls']}")
            
    except Exception as e:
        logger.error(f"Tool error: {e}")
        
    # Show statistics
    logger.info(f"\nService statistics: {service.get_stats()}")


async def test_adapter_compatibility():
    """Test backward compatibility through adapter"""
    logger.info("\n\nTesting Backward Compatibility Adapter...")
    
    # This mimics how existing code would use it
    client = UnifiedLLMClient()
    
    messages = [
        {"role": "user", "content": "Hello! Tell me a joke in one sentence."}
    ]
    
    response = await client.generate_response(messages)
    logger.info(f"Adapter response: {response}")
    
    # Test with tools
    tools = [
        {
            "type": "function", 
            "function": {
                "name": "get_weather",
                "description": "Get weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    }
                }
            }
        }
    ]
    
    messages = [
        {"role": "user", "content": "What's the weather in New York?"}
    ]
    
    response = await client.generate_response(messages, tools=tools)
    logger.info(f"Adapter response with tools: {response}")


async def test_fallback():
    """Test fallback functionality"""
    logger.info("\n\nTesting Fallback Functionality...")
    
    # Temporarily break primary provider to test fallback
    service = get_llm_service()
    
    # Save original primary
    original_primary = service.primary_provider
    
    # Set primary to non-existent provider
    service.primary_provider = "nonexistent"
    
    messages = [
        {"role": "user", "content": "Testing fallback. Say 'fallback worked'."}
    ]
    
    try:
        response = await service.generate_response_async(messages)
        logger.info(f"Fallback response from {response.provider}: {response.content}")
    except Exception as e:
        logger.error(f"Fallback failed: {e}")
    finally:
        # Restore original
        service.primary_provider = original_primary


async def test_connection_warming():
    """Test connection warming"""
    logger.info("\n\nTesting Connection Warming...")
    
    service = get_llm_service()
    
    # Warm connections
    await service.warm_connections()
    
    logger.info("Connections warmed successfully")


async def main():
    """Run all tests"""
    logger.info("Starting LLM Service Tests\n")
    
    # Test unified service
    await test_unified_service()
    
    # Test backward compatibility
    await test_adapter_compatibility()
    
    # Test fallback
    await test_fallback()
    
    # Test warming
    await test_connection_warming()
    
    logger.info("\n\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(main())