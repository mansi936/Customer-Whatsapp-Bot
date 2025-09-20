# import os
# from strands import Agent
# from strands.tools.mcp import MCPClient
# from strands.models.openai import OpenAIModel
# # from client.prompts import get_system_prompt
# from mcp.client.streamable_http import streamablehttp_client


# ECOMMERCE_MCP_SERVER=os.getenv("ECOMMERCE_MCP_SERVER", "http://localhost:8002")
# api_key=os.getenv("OPENAI_API_KEY")
# model_id=os.getenv("OPENAI_MODEL", "gpt-4.1")

# mcp_client = MCPClient(lambda: streamablehttp_client(ECOMMERCE_MCP_SERVER))

# model = OpenAIModel(
#     client_args={
#         "api_key": api_key,
#     },
#     # **model_config
#     model_id=model_id
# )

# system_prompt="You are a helpful e-commerce shopping assistant powered by advanced AI."

# async def process_user_query(user_query):
#     try:
#         with mcp_client as client:
#             tools=mcp_client.list_tools_sync()
#             agent=Agent(tools=tools, model=model, system_prompt=system_prompt)
#             return agent(user_query)
#     except Exception as e:
#         print(f"Error processing user query: {e}")
#         return str(e)

# if __name__ == "__main__":
#     import asyncio
#     print(asyncio.run(process_user_query("Hello")))



# import os
# # import asyncio
# from strands import Agent
# from strands.tools.mcp import MCPClient
# from strands.models.openai import OpenAIModel
# from mcp.client.streamable_http import streamablehttp_client

# ECOMMERCE_MCP_SERVER = os.getenv("ECOMMERCE_MCP_SERVER", "http://localhost:8002")
# api_key = os.getenv("OPENAI_API_KEY")
# model_id = os.getenv("OPENAI_MODEL", "gpt-4.1")

# if not api_key:
#     raise RuntimeError("OPENAI_API_KEY is not set")

# model = OpenAIModel(
#     client_args={"api_key": api_key},
#     model_id=model_id,
# )

# system_prompt = "You are a helpful e-commerce shopping assistant powered by advanced AI."

# def process_user_query(user_query: str):
#     # Ensure the server URL looks sane (optional guardrail)
#     if not ECOMMERCE_MCP_SERVER.startswith(("http://", "https://")):
#         raise ValueError(f"ECOMMERCE_MCP_SERVER must start with http(s)://, got: {ECOMMERCE_MCP_SERVER}")

#     mcp_client = MCPClient(lambda: streamablehttp_client(ECOMMERCE_MCP_SERVER))

#     try:
#         with mcp_client as client:
#             # Prefer the async method; fall back if your version only has sync
#             try:
#                 tools = mcp_client.list_tools()
#             except AttributeError:
#                 # older version compatibility
#                 tools = mcp_client.list_tools_sync()

#             agent = Agent(tools=tools, model=model, system_prompt=system_prompt)

#             # Depending on your `strands` version, Agent may be async-callable:
#             # try the async path first, fall back to sync __call__
#             if hasattr(agent, "aask"):
#                 return agent.aask(user_query)
#             else:
#                 return agent(user_query)

#     except Exception as e:
#         # Distinguish connection failures for easier debugging
#         msg = str(e)
#         if "ConnectError" in msg or "All connection attempts failed" in msg:
#             return (
#                 f"Could not connect to MCP server at {ECOMMERCE_MCP_SERVER}. "
#                 "Make sure the server is running and reachable (port open, URL correct)."
#             )
#         return f"Error processing user query: {msg}"

# if __name__ == "__main__":
#     print(process_user_query("Hello"))



import os
import time
from strands import Agent
from strands.tools.mcp import MCPClient
from strands.models.openai import OpenAIModel
from mcp.client.streamable_http import streamablehttp_client

ECOMMERCE_MCP_SERVER = os.getenv("ECOMMERCE_MCP_SERVER", "http://localhost:8002/mcp")  # <-- add /mcp
api_key = os.getenv("OPENAI_API_KEY")
model_id = os.getenv("OPENAI_MODEL", "gpt-4.1")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")

model = OpenAIModel(client_args={"api_key": api_key}, model_id=model_id)
system_prompt = "You are a helpful e-commerce shopping assistant powered by advanced AI."

def process_user_query(user_query: str):
    mcp_client = MCPClient(lambda: streamablehttp_client(
        ECOMMERCE_MCP_SERVER,
        # headers={"Authorization": f"Bearer {os.getenv('MCP_TOKEN')}"},  # uncomment if your server requires it
    ))
    try:
        with mcp_client:
            tools = mcp_client.list_tools_sync()
            agent = Agent(tools=tools, model=model, system_prompt=system_prompt)
            # If Agent is async in your version, you can wrap this in asyncio.run(...)
            return agent(user_query)
    except Exception as e:
        msg = str(e)
        if "Session terminated" in msg or "ConnectError" in msg:
            return (
                f"MCP init failed at {ECOMMERCE_MCP_SERVER}. "
                "Confirm the server is running, the transport matches (Streamable HTTP vs SSE), "
                "and the URL path (/mcp or /sse) and headers are correct."
            )
        return f"Error processing user query: {msg}"

if __name__ == "__main__":

    while True:
        user_query = input("User: ")
        time1=time.time()
        print(process_user_query(user_query))
        print("Time taken: ", time.time() - time1)
