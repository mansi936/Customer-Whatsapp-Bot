#!/usr/bin/env python3
"""
Health check for client pool with MCP integration
"""
import asyncio
import logging
import sys
import os
import traceback

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client.client_pool import ClientPool
from services.redis.redis_service_enhanced import EnhancedRedisService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_pool_initialization():
    """Test basic pool initialization"""
    logger.info("=== Testing Pool Initialization ===")
    
    try:
        redis_service = EnhancedRedisService()
        pool = ClientPool(
            pool_size=3,
            session_manager=redis_service
        )
        
        await pool.initialize()
        stats = pool.get_stats()
        logger.info(f"Pool stats after init: {stats}")
        
        assert stats["total_connections"] >= 2, "Should have at least 2 initial connections"
        logger.info("✅ Pool initialization successful")
        
        await pool.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Pool initialization failed: {str(e)}")
        traceback.print_exc()
        return False


async def test_connection_acquisition():
    """Test getting connections from pool"""
    logger.info("\n=== Testing Connection Acquisition ===")
    
    try:
        redis_service = EnhancedRedisService()
        pool = ClientPool(pool_size=3, session_manager=redis_service)
        await pool.initialize()
        
        # Test getting a connection
        async with pool.get_connection("test_user_1") as client:
            assert client is not None, "Should get a valid client"
            assert client.connected, "Client should be connected to MCP server"
            assert hasattr(client, '_connection_id'), "Client should have connection metadata"
            logger.info(f"✅ Got connection: {client._connection_id}")
            
            # Test that client can list tools
            assert len(client.tools) > 0, "Client should have discovered tools"
            logger.info(f"✅ Client has {len(client.tools)} tools available")
        
        # Test connection reuse
        async with pool.get_connection("test_user_1") as client2:
            assert client2._was_reused == True, "Should reuse connection for same user"
            logger.info("✅ Connection reuse working")
        
        await pool.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection acquisition failed: {str(e)}")
        traceback.print_exc()
        return False


async def test_concurrent_connections():
    """Test multiple concurrent connections"""
    logger.info("\n=== Testing Concurrent Connections ===")
    
    try:
        redis_service = EnhancedRedisService()
        pool = ClientPool(pool_size=3, session_manager=redis_service)
        await pool.initialize()
        
        # Create multiple concurrent tasks
        async def use_connection(user_id: str):
            async with pool.get_connection(user_id) as client:
                logger.info(f"User {user_id} got connection {client._connection_id}")
                # Simulate some work
                await asyncio.sleep(0.5)
                return client._connection_id
        
        # Run concurrent connections
        tasks = [use_connection(f"user_{i}") for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        unique_connections = set(results)
        logger.info(f"Used {len(unique_connections)} unique connections for 5 users")
        
        stats = pool.get_stats()
        logger.info(f"Pool stats: {stats}")
        
        assert stats["total_requests"] == 5, "Should have 5 total requests"
        logger.info("✅ Concurrent connections working")
        
        await pool.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Concurrent connections failed: {str(e)}")
        traceback.print_exc()
        return False


async def test_message_processing():
    """Test actual message processing through pool"""
    logger.info("\n=== Testing Message Processing ===")
    
    try:
        redis_service = EnhancedRedisService()
        pool = ClientPool(pool_size=2, session_manager=redis_service)
        await pool.initialize()
        
        # Test message processing
        async with pool.get_connection("test_user_msg") as client:
            result = await client.process_message("Show me some products")
            
            assert result is not None, "Should get a response"
            assert "reply" in result, "Response should have reply field"
            assert len(result["reply"]) > 0, "Reply should not be empty"
            
            logger.info(f"✅ Message processed successfully")
            logger.info(f"   Reply preview: {result['reply'][:100]}...")
            
            if result["metadata"].get("tools_used"):
                logger.info(f"   Tools used: {[t['name'] for t in result['metadata']['tools_used']]}")
        
        await pool.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Message processing failed: {str(e)}")
        traceback.print_exc()
        return False


async def test_pool_exhaustion():
    """Test behavior when pool is exhausted"""
    logger.info("\n=== Testing Pool Exhaustion ===")
    
    try:
        redis_service = EnhancedRedisService()
        pool = ClientPool(pool_size=1, session_manager=redis_service)  # Small pool
        await pool.initialize()
        
        # Hold one connection
        async with pool.get_connection("user1") as client1:
            # Try to get another connection while first is held
            async with pool.get_connection("user2") as client2:
                # This should create a temporary connection
                assert client2 is not None, "Should get a temporary connection"
                assert "temp_" in client2._connection_id, "Should be a temporary connection"
                logger.info(f"✅ Got temporary connection when pool exhausted: {client2._connection_id}")
        
        stats = pool.get_stats()
        assert stats["pool_exhausted_count"] > 0, "Should track pool exhaustion"
        logger.info("✅ Pool exhaustion handling working")
        
        await pool.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Pool exhaustion test failed: {str(e)}")
        traceback.print_exc()
        return False


async def main():
    """Run all health checks"""
    logger.info("Starting Client Pool Health Checks\n")
    
    tests = [
        test_pool_initialization,
        test_connection_acquisition,
        test_concurrent_connections,
        test_message_processing,
        test_pool_exhaustion
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
        await asyncio.sleep(0.5)  # Brief pause between tests
    
    # Summary
    logger.info("\n=== HEALTH CHECK SUMMARY ===")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        logger.info(f"✅ ALL TESTS PASSED ({passed}/{total})")
    else:
        logger.error(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)