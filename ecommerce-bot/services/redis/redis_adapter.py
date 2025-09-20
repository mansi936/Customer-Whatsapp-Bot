"""
Redis Adapter to provide compatibility between EnhancedRedisSessionService and generic Redis operations
"""

import json
import logging
from typing import Any, Optional, Dict
from .redis_service_enhanced import EnhancedRedisSessionService

logger = logging.getLogger(__name__)


class RedisAdapter(EnhancedRedisSessionService):
    """
    Adapter class that provides both session-specific methods and generic Redis operations
    """
    
    async def get(self, key: str) -> Optional[str]:
        """
        Generic Redis GET operation
        
        Args:
            key: Redis key
            
        Returns:
            String value or None if key doesn't exist
        """
        try:
            # Get the primary client and execute
            client = self._get_primary_client()
            result = await client.get(key)
            return result
        except Exception as e:
            logger.error(f"Error getting key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None, ex: Optional[int] = None) -> bool:
        """
        Generic Redis SET operation
        
        Args:
            key: Redis key
            value: String value to set
            ttl: Time to live in seconds (same as ex)
            ex: Expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle both ttl and ex parameters (ex takes precedence)
            expiration = ex or ttl
            
            # Get the primary client and execute
            client = self._get_primary_client()
            if expiration:
                result = await client.set(key, value, ex=expiration)
            else:
                result = await client.set(key, value)
            
            return bool(result)
        except Exception as e:
            logger.error(f"Error setting key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Generic Redis DELETE operation
        
        Args:
            key: Redis key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        try:
            client = self._get_primary_client()
            result = await client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Error deleting key {key}: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis
        
        Args:
            key: Redis key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            client = self._get_primary_client()
            result = await client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Error checking if key {key} exists: {str(e)}")
            return False
    
    # For backward compatibility with the MCP client
    async def get_session(self, user_id: str) -> Optional[Dict]:
        """
        Override to provide compatibility with MCP client expectations
        """
        # First try the session-specific method
        session = await super().get_session(user_id)
        if session:
            return session
            
        # If no session found, try generic key format
        try:
            session_key = f"session:{user_id}"
            data = await self.get(session_key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error getting session for {user_id}: {str(e)}")
            
        return None
    
    async def set_session(self, user_id: str, session_data: Dict) -> bool:
        """
        Set session data (compatibility method for MCP client)
        
        Args:
            user_id: User identifier
            session_data: Session data dictionary
            
        Returns:
            True if successful
        """
        try:
            # Use generic set for simple session storage
            session_key = f"session:{user_id}"
            return await self.set(
                session_key,
                json.dumps(session_data),
                ttl=self.ttl  # Use the configured TTL
            )
        except Exception as e:
            logger.error(f"Error setting session for {user_id}: {str(e)}")
            return False