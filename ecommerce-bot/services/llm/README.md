# Unified LLM Service

A unified interface for multiple LLM providers with automatic failover, connection pooling, and provider management.

## Features

- **Multiple Providers**: Support for OpenAI, Azure OpenAI, Groq, and Anthropic
- **Automatic Failover**: Falls back to secondary providers on failure
- **Connection Pooling**: Maintains pools of client connections for efficiency
- **Round-Robin Load Balancing**: Distributes requests across pooled clients
- **Unified Interface**: Single API for all providers
- **Tool/Function Support**: Supports OpenAI-style function calling
- **Statistics Tracking**: Monitor usage and errors by provider
- **Connection Warming**: Pre-warm connections to reduce latency

## Configuration

Configure the service using environment variables:

```bash
# Primary provider (options: openai, azure_openai, groq, anthropic)
LLM_PRIMARY_PROVIDER=azure_openai

# Fallback providers (comma-separated)
LLM_FALLBACK_PROVIDERS=openai,groq

# Enable automatic fallback
LLM_ENABLE_FALLBACK=true

# Connection pool size per provider
LLM_POOL_SIZE=3
```

### Provider-Specific Configuration

#### Azure OpenAI
```bash
AZURE_OPENAI_ENABLED=true
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

#### OpenAI
```bash
OPENAI_ENABLED=true
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4
```

#### Groq
```bash
GROQ_ENABLED=true
GROQ_API_KEY=your_key
GROQ_MODEL=mixtral-8x7b-32768
```

#### Anthropic
```bash
ANTHROPIC_ENABLED=true
ANTHROPIC_API_KEY=your_key
ANTHROPIC_MODEL=claude-3-opus-20240229
```

## Usage

### Direct Usage

```python
from services.llm.unified_llm_service import get_llm_service

# Get service instance
service = get_llm_service()

# Generate response
response = await service.generate_response_async(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    temperature=0.7,
    max_tokens=100
)

print(f"Response: {response.content}")
print(f"Provider: {response.provider}")
print(f"Model: {response.model}")
```

### Backward Compatible Usage

For existing code expecting the old interface:

```python
from services.llm.unified_llm_client import UnifiedLLMClient

client = UnifiedLLMClient()

response = await client.generate_response(
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response["content"])
```

### With Tools/Functions

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"]
        }
    }
}]

response = await service.generate_response_async(
    messages=[{"role": "user", "content": "What's the weather in Paris?"}],
    tools=tools
)

# Check for tool calls
if response.raw_response and "tool_calls" in response.raw_response:
    for tool_call in response.raw_response["tool_calls"]:
        print(f"Tool: {tool_call['name']}")
        print(f"Args: {tool_call['arguments']}")
```

## Failover Behavior

When `LLM_ENABLE_FALLBACK=true`:

1. Tries the primary provider first
2. On failure, tries each fallback provider in order
3. Returns the first successful response
4. Tracks fallback usage in statistics

## Statistics

Monitor service performance:

```python
stats = service.get_stats()
print(f"Primary provider: {stats['primary_provider']}")
print(f"Requests by provider: {stats['stats']['requests_by_provider']}")
print(f"Errors by provider: {stats['stats']['errors_by_provider']}")
print(f"Fallback count: {stats['stats']['fallback_count']}")
```

## Connection Warming

Pre-warm connections to reduce latency:

```python
# Warm all provider connections
await service.warm_connections()
```

## Testing

Run the test script to verify configuration:

```bash
python examples/test_llm_service.py
```

## Best Practices

1. **Set Primary Provider**: Choose your most reliable/preferred provider
2. **Configure Fallbacks**: Order fallbacks by preference/cost
3. **Pool Size**: Set based on expected concurrent requests
4. **Monitoring**: Check statistics regularly for errors
5. **API Keys**: Keep all API keys secure in environment variables

## Error Handling

The service handles errors gracefully:
- Connection failures trigger fallback
- Rate limits trigger fallback
- Invalid responses trigger fallback
- All errors are logged and tracked

## Performance Tips

1. **Connection Pooling**: Reuses connections for better performance
2. **Round-Robin**: Distributes load across pooled clients
3. **Async Support**: Use async methods for better concurrency
4. **Connection Warming**: Warm connections during startup

## Connection Warmer

The LLM service includes an optional connection warmer that keeps provider connections alive to reduce latency.

### Features

- **Automatic Warming**: Warms all provider connections on startup
- **Keep-Alive Pings**: Periodically pings providers to maintain connections
- **Provider Health Monitoring**: Tracks connection health for each provider
- **Smart Prioritization**: Pings providers based on usage frequency

### Configuration

```bash
# Enable connection warming
LLM_ENABLE_CONNECTION_WARMING=true

# Keep-alive interval in seconds
LLM_KEEP_ALIVE_INTERVAL=30

# Warm connections on startup
LLM_WARM_ON_STARTUP=true
```

### Usage

The connection warmer starts automatically when the webhook initializes:

```python
from services.llm.connection_warmer import get_llm_warmer

# Get warmer instance
warmer = await get_llm_warmer()

# Start warming
await warmer.start()

# Get statistics
stats = warmer.get_stats()

# Check provider health
health = warmer.get_provider_health()

# Stop warming
await warmer.stop()
```

### Health Monitoring

Check provider health status:

```python
health = warmer.get_provider_health()
# Returns:
# {
#   "azure_openai": {
#     "status": "healthy",
#     "last_ping": "2024-01-15T10:30:00",
#     "seconds_since_ping": 15.2,
#     "total_pings": 120,
#     "failures": 2,
#     "failure_rate": 0.016
#   },
#   ...
# }
```

## Supported Models

### OpenAI/Azure OpenAI
- GPT-4
- GPT-4 Turbo
- GPT-3.5 Turbo

### Groq
- Mixtral 8x7B
- LLaMA 2 70B
- And other Groq-supported models

### Anthropic
- Claude 3 Opus
- Claude 3 Sonnet
- Claude 3 Haiku