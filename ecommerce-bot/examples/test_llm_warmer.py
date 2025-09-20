"""
Test script for LLM Connection Warmer
"""
import asyncio
import sys
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm.connection_warmer import get_llm_warmer
from services.llm.unified_llm_service import get_llm_service
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_warmer_startup():
    """Test warmer initialization and startup"""
    logger.info("Testing LLM Connection Warmer startup...")
    
    # Get warmer instance
    warmer = await get_llm_warmer()
    
    # Start warmer
    await warmer.start()
    
    # Get initial stats
    stats = warmer.get_stats()
    logger.info(f"Warmer enabled: {stats['enabled']}")
    logger.info(f"Running: {stats['running']}")
    logger.info(f"Config: {stats['config']}")
    
    # Check provider health
    health = warmer.get_provider_health()
    logger.info("\nProvider Health:")
    for provider, status in health.items():
        logger.info(f"  {provider}: {status['status']} (pings: {status['total_pings']}, failures: {status['failures']})")
    
    return warmer


async def test_manual_warming():
    """Test manual provider warming"""
    logger.info("\n\nTesting manual provider warming...")
    
    warmer = await get_llm_warmer()
    service = get_llm_service()
    
    # Get available providers
    providers = service.get_available_providers()
    logger.info(f"Available providers: {providers}")
    
    # Manually warm each provider
    for provider in providers:
        logger.info(f"\nWarming {provider}...")
        success = await warmer.warm_specific_provider(provider)
        logger.info(f"  Result: {'Success' if success else 'Failed'}")
    
    # Check updated health
    health = warmer.get_provider_health()
    logger.info("\nUpdated Provider Health:")
    for provider, status in health.items():
        logger.info(f"  {provider}: {status}")


async def test_keep_alive():
    """Test keep-alive functionality"""
    logger.info("\n\nTesting keep-alive functionality...")
    
    warmer = await get_llm_warmer()
    
    # Wait for a keep-alive cycle
    keep_alive_interval = warmer.keep_alive_interval
    logger.info(f"Waiting {keep_alive_interval + 5} seconds for keep-alive cycle...")
    
    # Get initial stats
    initial_stats = warmer.get_stats()
    initial_pings = initial_stats['stats']['total_keep_alive_pings']
    
    # Wait
    await asyncio.sleep(keep_alive_interval + 5)
    
    # Check updated stats
    final_stats = warmer.get_stats()
    final_pings = final_stats['stats']['total_keep_alive_pings']
    
    logger.info(f"Initial pings: {initial_pings}")
    logger.info(f"Final pings: {final_pings}")
    logger.info(f"Last keep-alive: {final_stats['stats']['last_keep_alive']}")
    
    if final_pings > initial_pings:
        logger.info("✓ Keep-alive is working!")
    else:
        logger.warning("✗ Keep-alive may not be working")


async def test_performance_impact():
    """Test performance with and without warmer"""
    logger.info("\n\nTesting performance impact...")
    
    service = get_llm_service()
    
    # Test cold start (simulate by using less common provider)
    logger.info("\nTesting cold start response time...")
    start_time = time.time()
    
    response = await service.generate_response_async(
        messages=[{"role": "user", "content": "Say 'hello' in one word"}],
        temperature=0,
        max_tokens=10
    )
    
    cold_time = time.time() - start_time
    logger.info(f"Cold start time: {cold_time:.3f}s (Provider: {response.provider})")
    
    # Test warm response (should be faster)
    logger.info("\nTesting warm response time...")
    start_time = time.time()
    
    response = await service.generate_response_async(
        messages=[{"role": "user", "content": "Say 'world' in one word"}],
        temperature=0,
        max_tokens=10
    )
    
    warm_time = time.time() - start_time
    logger.info(f"Warm response time: {warm_time:.3f}s (Provider: {response.provider})")
    
    improvement = ((cold_time - warm_time) / cold_time) * 100
    logger.info(f"Performance improvement: {improvement:.1f}%")


async def main():
    """Run all tests"""
    logger.info("Starting LLM Connection Warmer Tests\n")
    
    try:
        # Test startup
        warmer = await test_warmer_startup()
        
        # Test manual warming
        await test_manual_warming()
        
        # Test keep-alive
        await test_keep_alive()
        
        # Test performance
        await test_performance_impact()
        
        # Stop warmer
        logger.info("\n\nStopping warmer...")
        await warmer.stop()
        
        # Final stats
        final_stats = warmer.get_stats()
        logger.info("\nFinal Statistics:")
        logger.info(f"Total keep-alive pings: {final_stats['stats']['total_keep_alive_pings']}")
        logger.info(f"Errors: {len(final_stats['stats']['errors'])}")
        
        logger.info("\n\nAll tests completed!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())