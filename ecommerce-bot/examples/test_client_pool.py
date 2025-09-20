"""
Test script for ClientPool functionality
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.client_pool import ClientPool
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def simulate_user_request(pool: ClientPool, user_id: str, message: str):
    """Simulate a user request using the pool"""
    logger.info(f"User {user_id} sending: {message}")
    
    try:
        async with pool.get_connection(user_id) as client:
            # In real usage, this would call client.process_message()
            logger.info(f"Got connection {client._connection_id} for user {user_id}")
            logger.info(f"Connection reused: {client._was_reused}")
            
            # Simulate processing time
            await asyncio.sleep(0.5)
            
            return f"Response to {user_id}: Processed '{message}'"
    except Exception as e:
        logger.error(f"Error for user {user_id}: {e}")
        return f"Error: {str(e)}"


async def test_pool():
    """Test the client pool with various scenarios"""
    
    # Create pool with size 3
    pool = ClientPool(pool_size=3)
    await pool.initialize()
    
    logger.info("Initial pool stats:")
    logger.info(pool.get_stats())
    
    # Test 1: Single user, multiple requests (should reuse connection)
    logger.info("\n=== Test 1: Single user, multiple requests ===")
    for i in range(3):
        result = await simulate_user_request(pool, "user1", f"Message {i+1}")
        logger.info(result)
    
    logger.info("\nPool stats after Test 1:")
    logger.info(pool.get_stats())
    
    # Test 2: Multiple users concurrent requests
    logger.info("\n=== Test 2: Multiple users concurrent requests ===")
    tasks = []
    for i in range(5):  # 5 users (more than pool size)
        user_id = f"user_{i+1}"
        task = simulate_user_request(pool, user_id, f"Hello from {user_id}")
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    for result in results:
        logger.info(result)
    
    logger.info("\nPool stats after Test 2:")
    logger.info(pool.get_stats())
    
    # Test 3: Same users again (should reuse connections)
    logger.info("\n=== Test 3: Same users again (connection reuse) ===")
    tasks = []
    for i in range(3):  # First 3 users
        user_id = f"user_{i+1}"
        task = simulate_user_request(pool, user_id, f"Second message from {user_id}")
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    for result in results:
        logger.info(result)
    
    logger.info("\nFinal pool stats:")
    logger.info(pool.get_stats())
    
    # Cleanup
    await pool.close()
    logger.info("\nPool closed")


if __name__ == "__main__":
    asyncio.run(test_pool())