"""
LLM Connection Warmer Service
Keeps LLM provider connections warm to reduce cold start latency
"""
import asyncio
import time
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
import os

from .unified_llm_service import get_llm_service, LLMProvider

logger = logging.getLogger(__name__)


class LLMConnectionWarmer:
    """Manages connection warming and keep-alive for LLM providers"""
    
    def __init__(self):
        self.llm_service = get_llm_service()
        self.enabled = os.getenv("LLM_ENABLE_CONNECTION_WARMING", "true").lower() == "true"
        self.keep_alive_interval = int(os.getenv("LLM_KEEP_ALIVE_INTERVAL", "30"))
        self.warm_on_startup = os.getenv("LLM_WARM_ON_STARTUP", "true").lower() == "true"
        
        self._warming_stats = {
            "providers_warmed": {},
            "last_keep_alive": None,
            "total_keep_alive_pings": 0,
            "errors": []
        }
        self._keep_alive_task = None
        self._running = False
        
        # Initialize provider stats
        for provider in self.llm_service.get_available_providers():
            self._warming_stats["providers_warmed"][provider] = {
                "warmed": False,
                "last_ping": None,
                "ping_count": 0,
                "failures": 0
            }
        
    async def start(self):
        """Start the connection warmer"""
        if not self.enabled:
            logger.info("LLM connection warming is disabled")
            return
            
        logger.info("Starting LLM connection warmer service...")
        self._running = True
        
        # Initial warming
        if self.warm_on_startup:
            await self._warm_all_connections()
        
        # Start keep-alive task
        self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
        logger.info(f"LLM keep-alive task started (interval: {self.keep_alive_interval}s)")
        
    async def stop(self):
        """Stop the connection warmer"""
        logger.info("Stopping LLM connection warmer service...")
        self._running = False
        
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            try:
                await self._keep_alive_task
            except asyncio.CancelledError:
                pass
                
    async def _warm_all_connections(self):
        """Warm up all LLM provider connections"""
        start_time = time.time()
        logger.info("Warming all LLM provider connections...")
        
        # Get enabled providers
        providers = self.llm_service.get_available_providers()
        
        # Warm each provider
        tasks = []
        for provider in providers:
            tasks.append(self._warm_provider(provider))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes
        success_count = sum(1 for r in results if r is True)
        
        duration = time.time() - start_time
        logger.info(f"LLM connection warming completed: {success_count}/{len(providers)} providers warmed in {duration:.2f}s")
        
    async def _warm_provider(self, provider_name: str) -> bool:
        """Warm a specific provider's connections"""
        try:
            logger.debug(f"Warming {provider_name} connections...")
            
            # Send a minimal request to warm the connection
            # This will use the pooled clients in round-robin fashion
            response = await self.llm_service.generate_response_async(
                messages=[{"role": "user", "content": "ping"}],
                temperature=0,
                max_tokens=10
            )
            
            if response.content:
                self._warming_stats["providers_warmed"][provider_name]["warmed"] = True
                self._warming_stats["providers_warmed"][provider_name]["last_ping"] = datetime.now().isoformat()
                logger.debug(f"{provider_name} connection warmed successfully")
                return True
            
        except Exception as e:
            logger.warning(f"Failed to warm {provider_name} connection: {e}")
            self._warming_stats["errors"].append({
                "provider": provider_name,
                "error": str(e),
                "time": datetime.now().isoformat(),
                "operation": "warm"
            })
            self._warming_stats["providers_warmed"][provider_name]["failures"] += 1
            
        return False
            
    async def _keep_alive_loop(self):
        """Periodically ping providers to keep connections alive"""
        logger.info(f"LLM keep-alive loop started (interval: {self.keep_alive_interval}s)")
        
        while self._running:
            try:
                await asyncio.sleep(self.keep_alive_interval)
                
                if not self._running:
                    break
                    
                await self._send_keep_alive_pings()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in LLM keep-alive loop: {e}")
                
    async def _send_keep_alive_pings(self):
        """Send keep-alive pings to all providers"""
        start_time = time.time()
        logger.debug("Sending LLM keep-alive pings...")
        
        # Get provider stats to prioritize
        provider_stats = self.llm_service.get_stats()
        providers_by_usage = sorted(
            provider_stats["stats"]["requests_by_provider"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Ping providers in order of usage (most used first)
        tasks = []
        for provider_name, _ in providers_by_usage:
            if provider_name in self._warming_stats["providers_warmed"]:
                tasks.append(self._ping_provider(provider_name))
        
        # Execute all pings concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes
        success_count = sum(1 for r in results if r is True)
        
        duration = time.time() - start_time
        self._warming_stats["last_keep_alive"] = datetime.now().isoformat()
        self._warming_stats["total_keep_alive_pings"] += len(tasks)
        
        logger.debug(f"LLM keep-alive pings completed: {success_count}/{len(tasks)} successful in {duration:.2f}s")
        
    async def _ping_provider(self, provider_name: str) -> bool:
        """Ping a specific provider to keep connection alive"""
        try:
            # Try to use specific provider by temporarily setting it as primary
            original_primary = self.llm_service.primary_provider
            self.llm_service.primary_provider = provider_name
            
            # Send minimal ping
            response = await asyncio.wait_for(
                self.llm_service.generate_response_async(
                    messages=[{"role": "user", "content": "ping"}],
                    temperature=0,
                    max_tokens=5
                ),
                timeout=5.0
            )
            
            # Restore original primary
            self.llm_service.primary_provider = original_primary
            
            if response.content and response.provider == provider_name:
                self._warming_stats["providers_warmed"][provider_name]["ping_count"] += 1
                self._warming_stats["providers_warmed"][provider_name]["last_ping"] = datetime.now().isoformat()
                return True
            
        except asyncio.TimeoutError:
            logger.debug(f"LLM ping timeout for {provider_name}")
            self._warming_stats["providers_warmed"][provider_name]["failures"] += 1
        except Exception as e:
            logger.debug(f"LLM ping failed for {provider_name}: {e}")
            self._warming_stats["providers_warmed"][provider_name]["failures"] += 1
            
        return False
    
    async def warm_specific_provider(self, provider_name: str) -> bool:
        """Manually warm a specific provider"""
        if provider_name not in self._warming_stats["providers_warmed"]:
            logger.warning(f"Provider {provider_name} not found in available providers")
            return False
            
        return await self._warm_provider(provider_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get warming statistics"""
        return {
            "enabled": self.enabled,
            "running": self._running,
            "stats": self._warming_stats,
            "config": {
                "keep_alive_interval": self.keep_alive_interval,
                "warm_on_startup": self.warm_on_startup
            }
        }
    
    def get_provider_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of each provider"""
        health = {}
        current_time = datetime.now()
        
        for provider, stats in self._warming_stats["providers_warmed"].items():
            last_ping_time = None
            if stats["last_ping"]:
                last_ping_time = datetime.fromisoformat(stats["last_ping"])
                time_since_ping = (current_time - last_ping_time).total_seconds()
            else:
                time_since_ping = float('inf')
            
            health[provider] = {
                "status": "healthy" if time_since_ping < self.keep_alive_interval * 2 else "stale",
                "last_ping": stats["last_ping"],
                "seconds_since_ping": time_since_ping if time_since_ping != float('inf') else None,
                "total_pings": stats["ping_count"],
                "failures": stats["failures"],
                "failure_rate": stats["failures"] / max(stats["ping_count"], 1)
            }
            
        return health


# Singleton instance
_warmer_instance: Optional[LLMConnectionWarmer] = None


async def get_llm_warmer() -> LLMConnectionWarmer:
    """Get or create the LLM connection warmer singleton"""
    global _warmer_instance
    if _warmer_instance is None:
        _warmer_instance = LLMConnectionWarmer()
    return _warmer_instance