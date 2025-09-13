"""
Comprehensive tests for Redis Service
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.redis.redis_service_enhanced import (
    EnhancedRedisSessionService,
    CircuitBreaker,
    CircuitState,
    RetryPolicy,
    with_retry
)

@pytest.fixture
async def redis_service():
    """Create Redis service instance for testing"""
    service = EnhancedRedisSessionService()
    # Mock the Redis clients
    service.clients = {
        "primary": AsyncMock(spec=redis.Redis)
    }
    service._initialized = True
    yield service
    await service.close()

@pytest.fixture
def circuit_breaker():
    """Create circuit breaker for testing"""
    return CircuitBreaker(failure_threshold=3, recovery_timeout=5)

@pytest.fixture
def retry_policy():
    """Create retry policy for testing"""
    return RetryPolicy(max_retries=3, base_delay=0.1)

class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    @pytest.mark.asyncio
    async def test_circuit_closed_on_success(self, circuit_breaker):
        """Test circuit remains closed on successful calls"""
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Test circuit opens after failure threshold"""
        async def failing_func():
            raise ConnectionError("Connection failed")
        
        for i in range(circuit_breaker.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == circuit_breaker.failure_threshold
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(self, circuit_breaker):
        """Test circuit transitions to half-open after timeout"""
        circuit_breaker.state = CircuitState.OPEN
        circuit_breaker.last_failure_time = datetime.utcnow() - timedelta(seconds=10)
        
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED

class TestRetryPolicy:
    """Test retry policy functionality"""
    
    def test_exponential_backoff(self, retry_policy):
        """Test exponential backoff calculation"""
        delays = [retry_policy.get_delay(i) for i in range(3)]
        
        # Check delays are increasing
        assert delays[0] < delays[1] < delays[2]
        
        # Check max delay is respected
        large_retry = retry_policy.get_delay(100)
        assert large_retry <= retry_policy.max_delay * 1.1  # Account for jitter
    
    @pytest.mark.asyncio
    async def test_retry_decorator_success(self):
        """Test retry decorator with successful function"""
        call_count = 0
        
        @with_retry(RetryPolicy(max_retries=3))
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_decorator_with_retries(self):
        """Test retry decorator retries on failure"""
        call_count = 0
        
        @with_retry(RetryPolicy(max_retries=3, base_delay=0.01))
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 3

class TestEnhancedRedisSessionService:
    """Test enhanced Redis session service"""
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, redis_service):
        """Test successful session creation"""
        user_id = "test_user_123"
        phone_number = "+1234567890"
        
        # Mock Redis get to return None (no existing session)
        redis_service.clients["primary"].get.return_value = None
        redis_service.clients["primary"].pipeline.return_value.execute.return_value = [True, True]
        
        session = await redis_service.create_session(user_id, phone_number)
        
        assert session["user_id"] == user_id
        assert session["phone_number"] == phone_number
        assert "created_at" in session
        assert session["version"] == 1
    
    @pytest.mark.asyncio
    async def test_create_session_existing(self, redis_service):
        """Test session creation when session already exists"""
        user_id = "test_user_123"
        phone_number = "+1234567890"
        
        existing_session = {
            "user_id": user_id,
            "phone_number": phone_number,
            "version": 2
        }
        
        # Mock Redis get to return existing session
        redis_service.clients["primary"].get.return_value = json.dumps(existing_session)
        
        session = await redis_service.create_session(user_id, phone_number)
        
        assert session["user_id"] == user_id
        assert session["version"] == 2
        redis_service.metrics["cache_hits"] == 1
    
    @pytest.mark.asyncio
    async def test_get_session_with_fallback(self, redis_service):
        """Test get session with fallback to secondary"""
        user_id = "test_user_123"
        session_data = {"user_id": user_id, "data": "test"}
        
        # Add secondary client
        redis_service.clients["secondary"] = AsyncMock(spec=redis.Redis)
        
        # Primary fails, secondary succeeds
        redis_service.clients["primary"].get.side_effect = ConnectionError()
        redis_service.clients["secondary"].get.return_value = json.dumps(session_data)
        
        session = await redis_service.get_session(user_id)
        
        assert session == session_data
        assert redis_service.clients["primary"].get.called
        assert redis_service.clients["secondary"].get.called
    
    @pytest.mark.asyncio
    async def test_update_session_with_optimistic_locking(self, redis_service):
        """Test session update with optimistic locking"""
        user_id = "test_user_123"
        
        current_session = {
            "user_id": user_id,
            "version": 1,
            "data": "original"
        }
        
        # Mock get_session
        with patch.object(redis_service, 'get_session', return_value=current_session):
            # Mock Lua script execution (success)
            redis_service.clients["primary"].eval.return_value = 1
            
            updates = {"data": "updated"}
            result = await redis_service.update_session(user_id, updates)
            
            assert result["data"] == "updated"
            assert result["version"] == 2
            assert "updated_at" in result
    
    @pytest.mark.asyncio
    async def test_update_session_version_conflict(self, redis_service):
        """Test session update with version conflict"""
        user_id = "test_user_123"
        
        current_session = {
            "user_id": user_id,
            "version": 1,
            "data": "original"
        }
        
        # Mock get_session
        with patch.object(redis_service, 'get_session', return_value=current_session):
            # Mock Lua script execution (version conflict)
            redis_service.clients["primary"].eval.return_value = 0
            
            updates = {"data": "updated"}
            
            with pytest.raises(ValueError, match="Optimistic lock failed"):
                await redis_service.update_session(user_id, updates)
    
    @pytest.mark.asyncio
    async def test_distributed_lock(self, redis_service):
        """Test distributed lock functionality"""
        resource = "test_resource"
        
        # Mock Redis set (lock acquired)
        redis_service.clients["primary"].set.return_value = True
        redis_service.clients["primary"].eval.return_value = 1
        
        async with redis_service.distributed_lock(resource, timeout=10):
            # Lock should be acquired
            assert redis_service.clients["primary"].set.called
            
        # Lock should be released
        assert redis_service.clients["primary"].eval.called
    
    @pytest.mark.asyncio
    async def test_distributed_lock_not_acquired(self, redis_service):
        """Test distributed lock when not acquired"""
        resource = "test_resource"
        
        # Mock Redis set (lock not acquired)
        redis_service.clients["primary"].set.return_value = False
        
        with pytest.raises(ValueError, match="Could not acquire lock"):
            async with redis_service.distributed_lock(resource, timeout=10):
                pass
    
    @pytest.mark.asyncio
    async def test_session_validation(self, redis_service):
        """Test session data validation"""
        invalid_session = {
            "phone_number": "+1234567890"
            # Missing user_id
        }
        
        with pytest.raises(ValueError, match="Missing required field: user_id"):
            redis_service._validate_session_data(invalid_session)
        
        invalid_cart = {
            "user_id": "test",
            "phone_number": "+1234567890",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01",
            "cart": {"total_amount": -100}
        }
        
        with pytest.raises(ValueError, match="Invalid cart total amount"):
            redis_service._validate_session_data(invalid_cart)
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, redis_service):
        """Test metrics tracking"""
        user_id = "test_user_123"
        
        # Mock Redis get
        redis_service.clients["primary"].get.return_value = json.dumps({"user_id": user_id})
        
        async with redis_service._track_operation("test_operation"):
            await redis_service.get_session(user_id)
        
        assert redis_service.metrics["operations"] > 0
        assert redis_service.metrics["cache_hits"] > 0
    
    @pytest.mark.asyncio
    async def test_health_check_loop(self, redis_service):
        """Test health check background task"""
        redis_service._shutdown = False
        
        # Mock ping
        redis_service.clients["primary"].ping.return_value = "PONG"
        
        # Run health check once
        health_task = asyncio.create_task(redis_service._health_check_loop())
        await asyncio.sleep(0.1)
        redis_service._shutdown = True
        health_task.cancel()
        
        try:
            await health_task
        except asyncio.CancelledError:
            pass
        
        assert redis_service.clients["primary"].ping.called

class TestIntegration:
    """Integration tests with real Redis (if available)"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_session_lifecycle(self):
        """Test complete session lifecycle with real Redis"""
        service = EnhancedRedisSessionService()
        
        try:
            # Initialize with local Redis
            await service.initialize([{
                "name": "primary",
                "host": "localhost",
                "port": 6379,
                "db": 15  # Use separate DB for tests
            }])
            
            user_id = "integration_test_user"
            phone_number = "+1234567890"
            
            # Create session
            session = await service.create_session(user_id, phone_number)
            assert session["user_id"] == user_id
            
            # Get session
            retrieved = await service.get_session(user_id)
            assert retrieved["user_id"] == user_id
            
            # Update session
            updates = {"user_data": {"profile": {"name": "Test User"}}}
            updated = await service.update_session(user_id, updates)
            assert updated["user_data"]["profile"]["name"] == "Test User"
            
            # Clean up
            client = service._get_primary_client()
            await client.delete(service._get_session_key(user_id))
            
        except ConnectionError:
            pytest.skip("Redis not available for integration test")
        finally:
            await service.close()

# Performance benchmarks
@pytest.mark.benchmark
class TestPerformance:
    """Performance benchmarks"""
    
    @pytest.mark.asyncio
    async def test_session_creation_performance(self, redis_service, benchmark):
        """Benchmark session creation"""
        async def create_sessions():
            tasks = []
            for i in range(100):
                user_id = f"perf_test_{i}"
                tasks.append(redis_service.create_session(user_id, "+1234567890"))
            await asyncio.gather(*tasks)
        
        # Mock Redis operations
        redis_service.clients["primary"].get.return_value = None
        redis_service.clients["primary"].pipeline.return_value.execute.return_value = [True, True]
        
        await benchmark(create_sessions)
    
    @pytest.mark.asyncio
    async def test_concurrent_updates(self, redis_service):
        """Test concurrent session updates"""
        user_id = "concurrent_test"
        
        # Mock operations
        redis_service.clients["primary"].get.return_value = json.dumps({
            "user_id": user_id,
            "version": 1
        })
        redis_service.clients["primary"].eval.return_value = 1
        
        async def update_session(index):
            return await redis_service.update_session(
                user_id,
                {"data": f"update_{index}"}
            )
        
        # Run concurrent updates
        tasks = [update_session(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0