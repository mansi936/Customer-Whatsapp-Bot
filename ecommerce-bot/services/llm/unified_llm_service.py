"""
Unified LLM Service
Provides a single interface for multiple LLM providers (OpenAI, Azure OpenAI, Groq, Anthropic, etc.)
"""
import os
import logging
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import asyncio
from threading import Lock
import json

# Import providers
import openai
from openai import OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI
try:
    from groq import Groq, AsyncGroq
except ImportError:
    Groq = AsyncGroq = None
    
try:
    from anthropic import Anthropic, AsyncAnthropic
except ImportError:
    Anthropic = AsyncAnthropic = None

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Available LLM providers"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    

class LLMResponse:
    """Unified response format"""
    def __init__(self, content: str, provider: str, model: str, 
                 usage: Optional[Dict] = None, raw_response: Any = None):
        self.content = content
        self.provider = provider
        self.model = model
        self.usage = usage or {}
        self.raw_response = raw_response
        
    def to_dict(self):
        return {
            "content": self.content,
            "provider": self.provider,
            "model": self.model,
            "usage": self.usage
        }


class UnifiedLLMService:
    """Unified interface for multiple LLM providers"""
    
    def __init__(self):
        # Load configuration from environment
        self.primary_provider = os.getenv("LLM_PRIMARY_PROVIDER", "azure_openai").lower()
        self.fallback_providers = os.getenv("LLM_FALLBACK_PROVIDERS", "openai,groq").lower().split(",")
        self.pool_size = int(os.getenv("LLM_POOL_SIZE", "3"))
        self.enable_fallback = os.getenv("LLM_ENABLE_FALLBACK", "true").lower() == "true"
        
        # Provider configurations
        self.configs = {
            LLMProvider.AZURE_OPENAI: {
                "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
                "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
                "enabled": os.getenv("AZURE_OPENAI_ENABLED", "true").lower() == "true"
            },
            LLMProvider.OPENAI: {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                "enabled": os.getenv("OPENAI_ENABLED", "true").lower() == "true"
            },
            LLMProvider.GROQ: {
                "api_key": os.getenv("GROQ_API_KEY"),
                "model": os.getenv("GROQ_MODEL", "mixtral-8x7b-32768"),
                "enabled": os.getenv("GROQ_ENABLED", "true").lower() == "true" and Groq is not None
            },
            LLMProvider.ANTHROPIC: {
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "model": os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
                "enabled": os.getenv("ANTHROPIC_ENABLED", "true").lower() == "true" and Anthropic is not None
            }
        }
        
        # Client pools
        self.sync_clients = {}
        self.async_clients = {}
        self._client_indices = {}
        self._lock = Lock()
        
        # Statistics
        self.stats = {
            "requests_by_provider": {},
            "errors_by_provider": {},
            "fallback_count": 0
        }
        
        # Initialize client pools
        self._initialize_pools()
        
    def _initialize_pools(self):
        """Initialize client pools for each enabled provider"""
        for provider in LLMProvider:
            config = self.configs[provider]
            if not config["enabled"] or not config.get("api_key"):
                continue
                
            self.sync_clients[provider] = []
            self.async_clients[provider] = []
            self._client_indices[provider] = {"sync": 0, "async": 0}
            self.stats["requests_by_provider"][provider.value] = 0
            self.stats["errors_by_provider"][provider.value] = 0
            
            logger.info(f"Initializing {self.pool_size} clients for {provider.value}")
            
            for i in range(self.pool_size):
                try:
                    sync_client, async_client = self._create_client_pair(provider, config)
                    if sync_client:
                        self.sync_clients[provider].append(sync_client)
                    if async_client:
                        self.async_clients[provider].append(async_client)
                except Exception as e:
                    logger.error(f"Failed to create client for {provider.value}: {e}")
                    
        logger.info(f"Initialized LLM service with providers: {list(self.sync_clients.keys())}")
        
    def _create_client_pair(self, provider: LLMProvider, config: Dict):
        """Create sync and async client pair for a provider"""
        sync_client = None
        async_client = None
        
        if provider == LLMProvider.AZURE_OPENAI:
            sync_client = AzureOpenAI(
                api_key=config["api_key"],
                azure_endpoint=config["endpoint"],
                api_version=config["api_version"]
            )
            async_client = AsyncAzureOpenAI(
                api_key=config["api_key"],
                azure_endpoint=config["endpoint"],
                api_version=config["api_version"]
            )
            
        elif provider == LLMProvider.OPENAI:
            sync_client = OpenAI(api_key=config["api_key"])
            async_client = AsyncOpenAI(api_key=config["api_key"])
            
        elif provider == LLMProvider.GROQ and Groq:
            sync_client = Groq(api_key=config["api_key"])
            async_client = AsyncGroq(api_key=config["api_key"])
            
        elif provider == LLMProvider.ANTHROPIC and Anthropic:
            sync_client = Anthropic(api_key=config["api_key"])
            async_client = AsyncAnthropic(api_key=config["api_key"])
            
        return sync_client, async_client
        
    def _get_sync_client(self, provider: LLMProvider):
        """Get a sync client from the pool (round-robin)"""
        if provider not in self.sync_clients or not self.sync_clients[provider]:
            return None
            
        with self._lock:
            clients = self.sync_clients[provider]
            idx = self._client_indices[provider]["sync"]
            client = clients[idx]
            self._client_indices[provider]["sync"] = (idx + 1) % len(clients)
            
        return client
        
    def _get_async_client(self, provider: LLMProvider):
        """Get an async client from the pool (round-robin)"""
        if provider not in self.async_clients or not self.async_clients[provider]:
            return None
            
        with self._lock:
            clients = self.async_clients[provider]
            idx = self._client_indices[provider]["async"]
            client = clients[idx]
            self._client_indices[provider]["async"] = (idx + 1) % len(clients)
            
        return client
        
    def generate_response(self, 
                         messages: List[Dict[str, str]],
                         temperature: float = 0.7,
                         max_tokens: Optional[int] = None,
                         tools: Optional[List[Dict]] = None,
                         **kwargs) -> LLMResponse:
        """Generate response using sync client"""
        providers = [self._get_provider_enum(self.primary_provider)]
        if self.enable_fallback:
            providers.extend([self._get_provider_enum(p) for p in self.fallback_providers])
            
        last_error = None
        for provider in providers:
            if provider not in self.sync_clients:
                continue
                
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self._generate_with_provider(
                        provider, messages, temperature, max_tokens, tools, False, **kwargs
                    ))
                finally:
                    loop.close()
            except Exception as e:
                logger.warning(f"Provider {provider.value} failed: {e}")
                self.stats["errors_by_provider"][provider.value] += 1
                last_error = e
                if self.enable_fallback:
                    self.stats["fallback_count"] += 1
                    continue
                else:
                    raise
                    
        raise Exception(f"All providers failed. Last error: {last_error}")
        
    async def generate_response_async(self,
                                    messages: List[Dict[str, str]],
                                    temperature: float = 0.7,
                                    max_tokens: Optional[int] = None,
                                    tools: Optional[List[Dict]] = None,
                                    **kwargs) -> LLMResponse:
        """Generate response using async client"""
        providers = [self._get_provider_enum(self.primary_provider)]
        if self.enable_fallback:
            providers.extend([self._get_provider_enum(p) for p in self.fallback_providers])
            
        last_error = None
        for provider in providers:
            if provider not in self.async_clients:
                continue
                
            try:
                return await self._generate_with_provider(
                    provider, messages, temperature, max_tokens, tools, True, **kwargs
                )
            except Exception as e:
                logger.warning(f"Provider {provider.value} failed: {e}")
                self.stats["errors_by_provider"][provider.value] += 1
                last_error = e
                if self.enable_fallback:
                    self.stats["fallback_count"] += 1
                    continue
                else:
                    raise
                    
        raise Exception(f"All providers failed. Last error: {last_error}")
        
    async def _generate_with_provider(self, provider: LLMProvider, messages: List[Dict],
                               temperature: float, max_tokens: Optional[int],
                               tools: Optional[List[Dict]], is_async: bool, **kwargs):
        """Generate response with specific provider"""
        client = self._get_async_client(provider) if is_async else self._get_sync_client(provider)
        if not client:
            raise ValueError(f"No client available for provider {provider.value}")
            
        config = self.configs[provider]
        self.stats["requests_by_provider"][provider.value] += 1
        
        if provider in [LLMProvider.OPENAI, LLMProvider.AZURE_OPENAI]:
            return await self._generate_openai(client, config, messages, temperature, max_tokens, tools, is_async, **kwargs)
        elif provider == LLMProvider.GROQ:
            return await self._generate_groq(client, config, messages, temperature, max_tokens, tools, is_async, **kwargs)
        elif provider == LLMProvider.ANTHROPIC:
            return await self._generate_anthropic(client, config, messages, temperature, max_tokens, is_async, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
            
    async def _generate_openai(self, client, config: Dict, messages: List[Dict],
                        temperature: float, max_tokens: Optional[int],
                        tools: Optional[List[Dict]], is_async: bool, **kwargs):
        """Generate with OpenAI/Azure OpenAI"""
        model = config.get("deployment") or config.get("model")
        
        params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
            
        if tools:
            params["tools"] = tools
            params["tool_choice"] = kwargs.get("tool_choice", "auto")
            
        if is_async:
            response = await client.chat.completions.create(**params)
        else:
            response = client.chat.completions.create(**params)
            
        # Extract content and tool calls
        message = response.choices[0].message
        content = message.content or ""
        
        # Handle tool calls if present
        response_dict = {"content": content}
        if hasattr(message, 'tool_calls') and message.tool_calls:
            response_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments)
                }
                for tc in message.tool_calls
            ]
            
        return LLMResponse(
            content=content,
            provider="azure_openai" if "deployment" in config else "openai",
            model=model,
            usage=response.usage.model_dump() if response.usage else {},
            raw_response=response_dict
        )
        
    async def _generate_groq(self, client, config: Dict, messages: List[Dict],
                      temperature: float, max_tokens: Optional[int],
                      tools: Optional[List[Dict]], is_async: bool, **kwargs):
        """Generate with Groq"""
        params = {
            "model": config["model"],
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
            
        if tools:
            # Groq uses a different tool format
            params["functions"] = [self._convert_tool_to_function(t) for t in tools]
            params["function_call"] = kwargs.get("tool_choice", "auto")
            
        if is_async:
            response = await client.chat.completions.create(**params)
        else:
            response = client.chat.completions.create(**params)
            
        content = response.choices[0].message.content or ""
        
        return LLMResponse(
            content=content,
            provider="groq",
            model=config["model"],
            usage=response.usage.__dict__ if response.usage else {},
            raw_response={"content": content}
        )
        
    async def _generate_anthropic(self, client, config: Dict, messages: List[Dict],
                           temperature: float, max_tokens: Optional[int],
                           is_async: bool, **kwargs):
        """Generate with Anthropic"""
        # Convert messages to Anthropic format
        anthropic_messages = []
        system_prompt = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
                
        params = {
            "model": config["model"],
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 1024,
        }
        
        if system_prompt:
            params["system"] = system_prompt
            
        if is_async:
            response = await client.messages.create(**params)
        else:
            response = client.messages.create(**params)
            
        content = response.content[0].text if response.content else ""
        
        return LLMResponse(
            content=content,
            provider="anthropic",
            model=config["model"],
            usage={"input_tokens": response.usage.input_tokens,
                   "output_tokens": response.usage.output_tokens},
            raw_response={"content": content}
        )
        
    def _convert_tool_to_function(self, tool: Dict) -> Dict:
        """Convert OpenAI tool format to function format"""
        return {
            "name": tool["function"]["name"],
            "description": tool["function"].get("description", ""),
            "parameters": tool["function"]["parameters"]
        }
        
    def _get_provider_enum(self, provider_str: str) -> LLMProvider:
        """Convert string to provider enum"""
        for provider in LLMProvider:
            if provider.value == provider_str:
                return provider
        raise ValueError(f"Unknown provider: {provider_str}")
        
    async def warm_connections(self):
        """Warm up all client connections"""
        logger.info("Warming LLM connections...")
        
        tasks = []
        for provider in self.async_clients:
            if self.async_clients[provider]:
                tasks.append(self._warm_provider(provider))
                
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        logger.info(f"Warmed {success_count}/{len(tasks)} provider connections")
        
    async def _warm_provider(self, provider: LLMProvider) -> bool:
        """Warm a single provider"""
        try:
            await self.generate_response_async(
                messages=[{"role": "user", "content": "ping"}],
                temperature=0,
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to warm {provider.value}: {e}")
            return False
            
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "primary_provider": self.primary_provider,
            "enabled_providers": list(self.sync_clients.keys()),
            "pool_size": self.pool_size,
            "stats": self.stats
        }
        
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return [p.value for p in self.sync_clients.keys()]


# Singleton instance
_llm_service_instance: Optional[UnifiedLLMService] = None
_llm_service_lock = Lock()


def get_llm_service() -> UnifiedLLMService:
    """Get or create the LLM service singleton"""
    global _llm_service_instance
    
    with _llm_service_lock:
        if _llm_service_instance is None:
            _llm_service_instance = UnifiedLLMService()
            
    return _llm_service_instance