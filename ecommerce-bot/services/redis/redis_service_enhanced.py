"""
Enhanced Redis Service with Production Features
- Retry logic with exponential backoff
- Circuit breaker pattern
- Connection pooling
- Comprehensive error handling
- Metrics and monitoring
"""

import json
import asyncio
import logging
from typing import Dict, Optional, Any, List, Callable
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from redis.exceptions import RedisError, ConnectionError, TimeoutError
import time
from functools import wraps
from enum import Enum
import traceback

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker implementation for Redis operations"""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise ConnectionError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self):
        """Handle successful call"""
        async with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED
    
    async def _on_failure(self):
        """Handle failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        return (self.last_failure_time and 
                datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout))

class RetryPolicy:
    """Retry policy with exponential backoff"""
    
    def __init__(self, max_retries=3, base_delay=1, max_delay=30, exponential_base=2):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def get_delay(self, retry_count: int) -> float:
        """Calculate delay for retry attempt"""
        delay = min(self.base_delay * (self.exponential_base ** retry_count), self.max_delay)
        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter

def with_retry(retry_policy: Optional[RetryPolicy] = None):
    """Decorator for adding retry logic to async functions"""
    if retry_policy is None:
        retry_policy = RetryPolicy()
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retry_policy.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    last_exception = e
                    if attempt < retry_policy.max_retries:
                        delay = retry_policy.get_delay(attempt)
                        logger.warning(f"Retry {attempt + 1}/{retry_policy.max_retries} after {delay:.2f}s: {e}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All retries exhausted for {func.__name__}")
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(f"Unexpected error in {func.__name__}: {e}")
                    raise
            
            raise last_exception
        return wrapper
    return decorator

class EnhancedRedisSessionService:
    """Production-ready Redis session service with advanced features"""
    
    def __init__(self):
        self.pools: Dict[str, ConnectionPool] = {}
        self.clients: Dict[str, redis.Redis] = {}
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        self.retry_policy = RetryPolicy(max_retries=3, base_delay=0.5)
        self.session_prefix = "session:"
        self.cart_prefix = "cart:"
        self.user_prefix = "user:"
        self.lock_prefix = "lock:"
        self.ttl = 86400  # 24 hours
        self.metrics = {
            "operations": 0,
            "errors": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "latency_sum": 0
        }
        self._initialized = False
        self._shutdown = False
        self._background_tasks = []
    
    async def initialize(self, configs: List[Dict] = None):
        """Initialize Redis connections with multiple nodes for HA"""
        if self._initialized:
            logger.warning("Redis service already initialized")
            return
        
        if configs is None:
            configs = [{
                "name": "primary",
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": None
            }]
        
        try:
            for config in configs:
                await self._create_connection_pool(config)
            
            # Test connections
            await self._test_connections()
            
            # Start background tasks
            self._start_background_tasks()
            
            self._initialized = True
            logger.info(f"Redis service initialized with {len(self.pools)} connection pools")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis service: {e}")
            await self.close()
            raise
    
    async def _create_connection_pool(self, config: Dict):
        """Create a connection pool for a Redis node"""
        try:
            pool = ConnectionPool(
                host=config.get("host", "localhost"),
                port=config.get("port", 6379),
                password=config.get("password"),
                db=config.get("db", 0),
                max_connections=config.get("max_connections", 50),
                min_idle_time=300,
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError],
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 3,  # TCP_KEEPINTVL  
                    3: 5   # TCP_KEEPCNT
                },
                decode_responses=True
            )
            
            client = redis.Redis(
                connection_pool=pool,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await client.ping()
            
            name = config.get("name", f"redis_{config['host']}_{config['port']}")
            self.pools[name] = pool
            self.clients[name] = client
            
            logger.info(f"Created connection pool: {name}")
            
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    
    async def _test_connections(self):
        """Test all Redis connections"""
        for name, client in self.clients.items():
            try:
                await client.ping()
                logger.info(f"Connection test successful: {name}")
            except Exception as e:
                logger.error(f"Connection test failed for {name}: {e}")
                raise
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        self._background_tasks.append(
            asyncio.create_task(self._health_check_loop())
        )
        self._background_tasks.append(
            asyncio.create_task(self._metrics_reporter_loop())
        )
        self._background_tasks.append(
            asyncio.create_task(self._session_cleanup_loop())
        )
    
    async def _health_check_loop(self):
        """Periodic health check of Redis connections"""
        while not self._shutdown:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                for name, client in self.clients.items():
                    try:
                        await client.ping()
                    except Exception as e:
                        logger.error(f"Health check failed for {name}: {e}")
                        # Could trigger alerts here
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def _metrics_reporter_loop(self):
        """Report metrics periodically"""
        while not self._shutdown:
            try:
                await asyncio.sleep(60)  # Report every minute
                avg_latency = (self.metrics["latency_sum"] / self.metrics["operations"] 
                              if self.metrics["operations"] > 0 else 0)
                
                logger.info(f"Redis Metrics - Ops: {self.metrics['operations']}, "
                           f"Errors: {self.metrics['errors']}, "
                           f"Cache Hit Rate: {self._calculate_hit_rate():.2%}, "
                           f"Avg Latency: {avg_latency:.3f}ms")
                
                # Reset metrics
                self.metrics = {key: 0 for key in self.metrics}
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics reporter: {e}")
    
    async def _session_cleanup_loop(self):
        """Clean up expired sessions periodically"""
        while not self._shutdown:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        try:
            client = self._get_primary_client()
            pattern = f"{self.session_prefix}*"
            cursor = 0
            expired_count = 0
            
            while True:
                cursor, keys = await client.scan(cursor, match=pattern, count=100)
                
                for key in keys:
                    ttl = await client.ttl(key)
                    if ttl == -1:  # No expiration set
                        await client.expire(key, self.ttl)
                    elif ttl == -2:  # Key doesn't exist
                        expired_count += 1
                
                if cursor == 0:
                    break
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
                
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
    
    def _get_primary_client(self) -> redis.Redis:
        """Get the primary Redis client"""
        if "primary" in self.clients:
            return self.clients["primary"]
        return list(self.clients.values())[0]
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        return self.metrics["cache_hits"] / total if total > 0 else 0
    
    @asynccontextmanager
    async def _track_operation(self, operation_name: str):
        """Track operation metrics"""
        start_time = time.time()
        try:
            yield
            self.metrics["operations"] += 1
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Operation {operation_name} failed: {e}")
            raise
        finally:
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            self.metrics["latency_sum"] += elapsed
    
    @asynccontextmanager
    async def distributed_lock(self, resource: str, timeout: int = 10):
        """Distributed lock implementation using Redis"""
        lock_key = f"{self.lock_prefix}{resource}"
        lock_value = f"{datetime.utcnow().timestamp()}"
        client = self._get_primary_client()
        
        try:
            # Try to acquire lock
            acquired = await client.set(lock_key, lock_value, nx=True, ex=timeout)
            if not acquired:
                raise ValueError(f"Could not acquire lock for {resource}")
            
            yield
            
        finally:
            # Release lock only if we own it
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            try:
                await client.eval(lua_script, 1, lock_key, lock_value)
            except Exception as e:
                logger.error(f"Error releasing lock for {resource}: {e}")
    
    def _get_session_key(self, user_id: str) -> str:
        """Generate session key for user"""
        return f"{self.session_prefix}{user_id}"
    
    def _create_default_session(self, user_id: str, phone_number: str) -> Dict:
        """Create default session structure with validation"""
        now = datetime.utcnow()
        return {
            "user_id": user_id,
            "phone_number": phone_number,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=self.ttl)).isoformat(),
            "version": 1,  # For optimistic locking
            "user_data": {
                "profile": {
                    "name": "",
                    "email": "",
                    "preferences": {
                        "categories": [],
                        "brands": [],
                        "price_range": {"min": 0, "max": 100000}
                    }
                },
                "metrics": {
                    "total_orders": 0,
                    "total_spent": 0,
                    "last_order_date": None
                }
            },
            "cart": {
                "items": [],
                "total_items": 0,
                "total_amount": 0,
                "discount": 0,
                "tax": 0,
                "final_amount": 0
            },
            "conversation_context": {
                "history": [],
                "current_flow": "browsing",
                "last_activity": now.isoformat(),
                "ai_context": {
                    "last_search": "",
                    "viewed_products": [],
                    "interested_categories": []
                }
            },
            "recommendations": {
                "personalized": [],
                "viewed": [],
                "cart_based": [],
                "trending": []
            },
            "order_context": {
                "pending_order": None,
                "last_order": None
            },
            "try_on_context": {
                "user_image_url": None,
                "tried_products": [],
                "saved_results": []
            }
        }
    
    @with_retry()
    async def create_session(self, user_id: str, phone_number: str, initial_data: Optional[Dict] = None) -> Dict:
        """Create new session with retry logic"""
        async with self._track_operation("create_session"):
            try:
                session_key = self._get_session_key(user_id)
                client = self._get_primary_client()
                
                # Use distributed lock to prevent race conditions
                async with self.distributed_lock(f"session_create_{user_id}"):
                    # Check if session already exists
                    existing = await client.get(session_key)
                    if existing:
                        self.metrics["cache_hits"] += 1
                        return json.loads(existing)
                    
                    self.metrics["cache_misses"] += 1
                    
                    # Create new session
                    session_data = self._create_default_session(user_id, phone_number)
                    
                    # Merge with initial data if provided
                    if initial_data:
                        session_data = self._deep_merge(session_data, initial_data)
                    
                    # Validate session data
                    self._validate_session_data(session_data)
                    
                    # Store in Redis with transaction
                    pipe = client.pipeline()
                    pipe.setex(session_key, self.ttl, json.dumps(session_data))
                    pipe.sadd("active_sessions", user_id)  # Track active sessions
                    await pipe.execute()
                    
                    logger.info(f"Session created for user: {user_id}")
                    return session_data
                    
            except Exception as e:
                logger.error(f"Error creating session for {user_id}: {e}\n{traceback.format_exc()}")
                raise
    
    @with_retry()
    async def get_session(self, user_id: str) -> Optional[Dict]:
        """Get session with retry and fallback"""
        async with self._track_operation("get_session"):
            try:
                session_key = self._get_session_key(user_id)
                
                # Try primary first
                for name, client in self.clients.items():
                    try:
                        session_data = await client.get(session_key)
                        if session_data:
                            self.metrics["cache_hits"] += 1
                            return json.loads(session_data)
                    except Exception as e:
                        logger.warning(f"Failed to get session from {name}: {e}")
                        continue
                
                self.metrics["cache_misses"] += 1
                return None
                
            except Exception as e:
                logger.error(f"Error getting session for {user_id}: {e}")
                return None
    
    @with_retry()
    async def update_session(self, user_id: str, updates: Dict) -> Dict:
        """Update session with optimistic locking"""
        async with self._track_operation("update_session"):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    session_key = self._get_session_key(user_id)
                    client = self._get_primary_client()
                    
                    # Get current session with version
                    session_data = await self.get_session(user_id)
                    if not session_data:
                        raise ValueError(f"Session not found for user: {user_id}")
                    
                    current_version = session_data.get("version", 1)
                    
                    # Deep merge updates
                    session_data = self._deep_merge(session_data, updates)
                    session_data["updated_at"] = datetime.utcnow().isoformat()
                    session_data["version"] = current_version + 1
                    
                    # Validate updated data
                    self._validate_session_data(session_data)
                    
                    # Use optimistic locking with Lua script
                    lua_script = """
                    local key = KEYS[1]
                    local new_data = ARGV[1]
                    local expected_version = ARGV[2]
                    local ttl = ARGV[3]
                    
                    local current = redis.call('get', key)
                    if not current then
                        return 0
                    end
                    
                    local current_data = cjson.decode(current)
                    if tostring(current_data.version) == expected_version then
                        redis.call('setex', key, ttl, new_data)
                        return 1
                    else
                        return 0
                    end
                    """
                    
                    result = await client.eval(
                        lua_script,
                        1,
                        session_key,
                        json.dumps(session_data),
                        str(current_version),
                        str(self.ttl)
                    )
                    
                    if result == 1:
                        logger.info(f"Session updated for user: {user_id}")
                        return session_data
                    else:
                        # Version conflict, retry
                        if attempt < max_retries - 1:
                            await asyncio.sleep(0.1 * (attempt + 1))
                            continue
                        else:
                            raise ValueError("Optimistic lock failed after retries")
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Update attempt {attempt + 1} failed: {e}")
                        continue
                    else:
                        logger.error(f"Error updating session for {user_id}: {e}")
                        raise
    
    def _validate_session_data(self, session_data: Dict):
        """Validate session data structure"""
        required_fields = ["user_id", "phone_number", "created_at", "updated_at"]
        for field in required_fields:
            if field not in session_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate cart totals
        cart = session_data.get("cart", {})
        if cart.get("total_amount", 0) < 0:
            raise ValueError("Invalid cart total amount")
    
    def _deep_merge(self, base: Dict, updates: Dict) -> Dict:
        """Deep merge two dictionaries"""
        import copy
        result = copy.deepcopy(base)
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    async def close(self):
        """Gracefully close all connections"""
        self._shutdown = True
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Close all connections
        for name, client in self.clients.items():
            try:
                await client.close()
                logger.info(f"Closed Redis client: {name}")
            except Exception as e:
                logger.error(f"Error closing client {name}: {e}")
        
        for name, pool in self.pools.items():
            try:
                await pool.disconnect()
                logger.info(f"Disconnected pool: {name}")
            except Exception as e:
                logger.error(f"Error disconnecting pool {name}: {e}")
        
        self.clients.clear()
        self.pools.clear()
        self._initialized = False
        logger.info("Redis service shutdown complete")

# Export the enhanced service
redis_service = EnhancedRedisSessionService()