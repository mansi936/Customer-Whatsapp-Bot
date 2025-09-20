# Client Components

This directory contains the client-side components for the e-commerce bot.

## ClientPool

The `ClientPool` class manages a pool of MCP client connections for efficient resource utilization.

### Features

- **Connection Pooling**: Maintains a pool of reusable MCP client connections
- **User Affinity**: Attempts to reuse the same connection for the same user
- **Automatic Scaling**: Creates new connections up to the pool size limit
- **Overflow Handling**: Creates temporary connections when pool is exhausted
- **Thread Safety**: Uses asyncio locks for concurrent access
- **Statistics Tracking**: Monitors pool usage and performance

### Usage

```python
from client.client_pool import ClientPool

# Initialize pool
pool = ClientPool(
    pool_size=5,
    session_manager=redis_service,
    llm_client=llm_client,
    server_manager=server_manager
)
await pool.initialize()

# Use connection with context manager (recommended)
async with pool.get_connection(user_id) as client:
    result = await client.process_message(message)
    
# Get pool statistics
stats = pool.get_stats()
print(f"Total connections: {stats['total_connections']}")
print(f"Connections reused: {stats['connections_reused']}")

# Clean up
await pool.close()
```

### Connection Lifecycle

1. **Connection Request**: When a user requests a connection
2. **User Check**: Pool checks if user already has an assigned connection
3. **Reuse or Assign**: Reuses existing connection or assigns available one
4. **Create if Needed**: Creates new connection if under pool limit
5. **Overflow**: Creates temporary connection if pool exhausted
6. **Auto-release**: Connection automatically returned to pool after use

### Statistics

The pool tracks the following metrics:
- `connections_created`: Total connections created
- `connections_reused`: Times connections were reused
- `total_requests`: Total connection requests
- `pool_exhausted_count`: Times pool was at capacity
- `total_connections`: Current number of connections
- `available_connections`: Free connections in pool
- `busy_connections`: Connections currently in use

## MCPClient

The `MCPClient` class handles the actual message processing logic.

### Features

- **Dynamic Tool Discovery**: Fetches available tools from server
- **Session Management**: Maintains conversation context
- **LLM Integration**: Processes messages with AI assistance
- **Tool Execution**: Routes tool calls to appropriate servers
- **Response Formatting**: Formats responses for WhatsApp

### Usage

```python
from client.mcp_client import MCPClient

# Create client
client = MCPClient(
    user_id=user_phone,
    session_manager=session_manager,
    llm_client=llm_client,
    server_manager=server_manager
)

# Process message
result = await client.process_message("Show me shirts")
print(result["reply"])
```

## Testing

Run the test script to see the pool in action:

```bash
python examples/test_client_pool.py
```

This will demonstrate:
- Connection creation and initialization
- Connection reuse for same user
- Handling multiple concurrent users
- Pool exhaustion and overflow
- Statistics tracking