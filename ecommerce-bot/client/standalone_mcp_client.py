#!/usr/bin/env python3
"""
Standalone MCP Client for E-commerce Bot
This client follows the MCP tutorial pattern and connects directly to the MCP server
"""
import asyncio
import sys
import os
from typing import Optional, Dict, Any, List
from contextlib import AsyncExitStack
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


class StandaloneMCPClient:
    """Standalone MCP Client that connects directly to the server"""
    
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.tools = []
        
    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = sys.executable if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        logger.info(f"Connecting to MCP server: {command} {server_script_path}")
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        self.tools = response.tools
        logger.info(f"Connected to server with tools: {[tool.name for tool in self.tools]}")
        print(f"\nConnected to server with {len(self.tools)} tools:")
        for tool in self.tools:
            print(f"  - {tool.name}: {tool.description}")
            
    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]
        
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in self.tools]
        
        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=messages,
            tools=available_tools
        )
        
        # Process response and handle tool calls
        final_text = []
        
        assistant_message_content = []
        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input
                
                # Execute tool call
                logger.info(f"Calling tool {tool_name} with args {tool_args}")
                result = await self.session.call_tool(tool_name, tool_args)
                
                # Handle the tool result
                tool_result_text = ""
                if hasattr(result, 'content') and result.content:
                    if isinstance(result.content, list):
                        # Handle list of content blocks
                        for block in result.content:
                            if hasattr(block, 'text'):
                                tool_result_text = block.text
                                break
                    elif isinstance(result.content, str):
                        tool_result_text = result.content
                        
                final_text.append(f"\n[Tool: {tool_name}]\n{tool_result_text}\n")
                
                assistant_message_content.append(content)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": tool_result_text
                        }
                    ]
                })
                
                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )
                
                final_text.append(response.content[0].text)
                
        return "\n".join(final_text)
        
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\n🤖 E-commerce MCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        print("Example queries:")
        print("  - Show me laptops under $1000")
        print("  - Add PROD001 to my cart")
        print("  - Show my cart")
        print("  - Get recommendations for user123")
        print("-" * 50)
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                if not query:
                    continue
                    
                response = await self.process_query(query)
                print("\n" + response)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {str(e)}")
                print(f"\n❌ Error: {str(e)}")
                
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        # Default to the e-commerce MCP server
        server_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "server",
            "mcp_server.py"
        )
        print(f"No server path provided, using default: {server_path}")
    else:
        server_path = sys.argv[1]
        
    client = StandaloneMCPClient()
    try:
        await client.connect_to_server(server_path)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())