#!/usr/bin/env python3
"""
Standalone MCP Client for E-commerce WhatsApp Bot
This client connects directly to the MCP server via STDIO transport
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Union
import traceback
import sys
import os
from contextlib import AsyncExitStack

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from services.llm.unified_llm_service import get_llm_service
from client import prompts
from client.utils import extract_message_text, get_timestamp, Config

# Configure logging to stderr to avoid interfering with STDIO
logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self, user_id: str, session_manager, llm_client=None, server_manager=None):
        self.user_id = user_id
        self.session_manager = session_manager
        # Use unified LLM service directly, ignore passed llm_client
        self.llm_service = get_llm_service()
        
        # MCP connection attributes
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        self.stdio = None
        self.write = None
        self.connected = False
        
        # Tools will be dynamically loaded from MCP server
        self.tools = []

    async def connect_to_server(self, server_path: Optional[str] = None):
        """Connect to the MCP server via STDIO transport
        
        Args:
            server_path: Path to the MCP server script. If not provided, uses default path.
        """
        if self.connected:
            logger.info("Already connected to MCP server")
            return
            
        try:
            # Default to the e-commerce MCP server
            if server_path is None:
                # Get the correct path relative to the current file
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_dir)  # This gets us to ecommerce-bot/
                server_path = os.path.join(project_root, "server", "mcp_server.py")
            
            # Verify server script exists
            if not os.path.exists(server_path):
                raise FileNotFoundError(f"MCP server script not found: {server_path}")
            
            # Configure server parameters for STDIO transport
            server_params = StdioServerParameters(
                command=sys.executable,
                args=[server_path],
                env=None
            )
            
            logger.info(f"Connecting to MCP server: {server_path}")
            
            # Create AsyncExitStack within this async context
            self.exit_stack = AsyncExitStack()
            
            # Establish STDIO connection
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            self.stdio, self.write = stdio_transport
            
            # Create MCP session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            
            # Initialize the session
            await self.session.initialize()
            
            # Discover available tools
            response = await self.session.list_tools()
            self.tools = self._format_tools_for_llm(response.tools)
            
            self.connected = True
            logger.info(f"Connected to MCP server with {len(self.tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {str(e)}")
            # Clean up exit stack if connection failed
            if self.exit_stack:
                await self.exit_stack.aclose()
                self.exit_stack = None
            raise
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.connected and self.exit_stack:
            try:
                await self.exit_stack.aclose()
            except Exception as e:
                logger.warning(f"Error during disconnect: {str(e)}")
            finally:
                self.exit_stack = None
                self.connected = False
                self.session = None
                self.stdio = None
                self.write = None
                logger.info("Disconnected from MCP server")
    
    async def process_message(self, message: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process incoming message and generate appropriate response.
        
        1. Ensure connected to MCP server
        2. Build prompt + context
        3. Call unified LLM with dynamic tools
        4. Parse intent and execute tool calls via MCP session
        5. Format and return response
        """
        try:
            # Log incoming message
            message_text = extract_message_text(message)
            logger.info(f"📱 Processing message from {self.user_id}: {message_text}")
            # Ensure we're connected to the MCP server
            if not self.connected:
                await self.connect_to_server()
            
            # Get or create session context
            session_context = await self._get_session_context()
            
            # Build conversation history
            conversation_history = await self._build_conversation_history(message, session_context)
            
            # Call LLM with dynamically discovered tools
            llm_response_obj = await self.llm_service.generate_response_async(
                messages=conversation_history,
                tools=self.tools,
                temperature=Config.DEFAULT_TEMPERATURE
            )
            
            # Convert to expected format
            llm_response = {"content": llm_response_obj.content}
            if llm_response_obj.raw_response and "tool_calls" in llm_response_obj.raw_response:
                llm_response["tool_calls"] = llm_response_obj.raw_response["tool_calls"]
            
            # Process LLM response and handle tool calls
            final_response = await self._process_llm_response(llm_response, conversation_history)
            
            # Update session context
            await self._update_session_context(message, final_response, session_context)
            
            # Format the response for WhatsApp
            formatted_response = self._format_response_for_whatsapp(final_response)
            
            # Log summary of processing
            tools_summary = [f"{t['name']}" for t in final_response.get("tools_used", [])]
            if tools_summary:
                logger.info(f"✅ Message processed successfully | Tools used: {', '.join(tools_summary)}")
            else:
                logger.info(f"✅ Message processed successfully | No tools used")
            
            return {
                "reply": formatted_response,
                "metadata": {
                    "user_id": self.user_id,
                    "timestamp": get_timestamp(),
                    "tools_used": final_response.get("tools_used", [])
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing message for user {self.user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "reply": prompts.get_error_message("general_error"),
                "error": str(e)
            }

    def _format_tools_for_llm(self, mcp_tools) -> List[Dict[str, Any]]:
        """Format MCP tools for LLM consumption"""
        formatted_tools = []
        for tool in mcp_tools:
            formatted_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema if hasattr(tool, 'inputSchema') else {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            formatted_tools.append(formatted_tool)
        return formatted_tools

    async def _get_session_context(self) -> Dict[str, Any]:
        """Retrieve or initialize session context from session manager"""
        try:
            context = await self.session_manager.get_session(self.user_id)
            if not context:
                context = {
                    "user_id": self.user_id,
                    **Config.DEFAULT_SESSION_CONTEXT,
                    "created_at": get_timestamp()
                }
                await self.session_manager.set_session(self.user_id, context)
            return context
        except Exception as e:
            logger.warning(f"Error getting session context: {str(e)}")
            return {"user_id": self.user_id, "conversation_history": []}

    async def _build_conversation_history(self, message: Union[str, Dict], session_context: Dict) -> List[Dict]:
        """Build conversation history for LLM context"""
        # Use utility to extract message text
        message_text = extract_message_text(message)
        
        # Use the prompts module to build conversation messages
        history = prompts.build_conversation_messages(
            user_message=message_text,
            session_context=session_context,
            include_personalization=True
        )
        
        return history

    async def _process_llm_response(self, llm_response: Dict, conversation_history: List[Dict]) -> Dict[str, Any]:
        """Process LLM response and execute any tool calls"""
        response_content = llm_response.get("content", "")
        tools_used = []
        
        # Check if LLM wants to use tools
        if "tool_calls" in llm_response:
            for tool_call in llm_response["tool_calls"]:
                # Handle both old and new tool call formats
                if "function" in tool_call:
                    tool_name = tool_call["function"]["name"]
                    tool_args = tool_call["function"].get("arguments", {})
                else:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("arguments", {})
                
                # Parse arguments if they're a string
                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except:
                        tool_args = {}
                
                # Execute tool through MCP session
                try:
                    # Log tool call details
                    logger.info(f"🔧 Tool Call: {tool_name}")
                    logger.info(f"   Input: {json.dumps(tool_args, indent=2)}")
                    
                    # Call tool via MCP session
                    result = await self.session.call_tool(tool_name, tool_args)
                    
                    # Extract the actual result from MCP response
                    tool_result = self._extract_tool_result(result)
                    
                    # Log tool output
                    if isinstance(tool_result, str):
                        logger.info(f"   Output: {tool_result[:200]}{'...' if len(tool_result) > 200 else ''}")
                    else:
                        logger.info(f"   Output: {json.dumps(tool_result, indent=2) if isinstance(tool_result, dict) else str(tool_result)[:200]}")
                    
                    tools_used.append({
                        "name": tool_name,
                        "args": tool_args,
                        "result": tool_result
                    })
                    
                    # Add tool result to conversation and get final response
                    # Format tool call for conversation history
                    formatted_tool_call = {
                        "id": tool_call.get("id", f"call_{tool_name}_{len(tools_used)}"),
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(tool_args) if isinstance(tool_args, dict) else tool_args
                        }
                    }
                    
                    conversation_history.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [formatted_tool_call]
                    })
                    conversation_history.append({
                        "role": "tool",
                        "tool_call_id": formatted_tool_call["id"],
                        "content": json.dumps(tool_result)
                    })
                    
                    # Get final response from LLM with tool results
                    final_llm_response_obj = await self.llm_service.generate_response_async(
                        messages=conversation_history,
                        temperature=Config.DEFAULT_TEMPERATURE
                    )
                    response_content = final_llm_response_obj.content or response_content
                    
                except Exception as e:
                    logger.error(f"❌ Error executing tool {tool_name}: {str(e)}")
                    logger.error(f"   Failed Input: {json.dumps(tool_args, indent=2)}")
                    error_msg = prompts.get_error_message("tool_failure", tool_name, str(e))
                    response_content += f"\n\n{error_msg}"
        
        return {
            "content": response_content,
            "tools_used": tools_used
        }


    async def _update_session_context(self, message: Any, response: Dict, session_context: Dict):
        """Update session context with new message and response"""
        try:
            # Add to conversation history
            message_text = extract_message_text(message)
            session_context["conversation_history"].append({"role": "user", "content": message_text})
            session_context["conversation_history"].append({"role": "assistant", "content": response["content"]})
            
            # Keep only last N messages to prevent context from growing too large
            session_context["conversation_history"] = session_context["conversation_history"][-Config.HISTORY_TO_STORE:]
            
            # Update last activity timestamp
            session_context["last_activity"] = get_timestamp()
            
            # Save updated context
            await self.session_manager.set_session(self.user_id, session_context)
            
        except Exception as e:
            logger.warning(f"Error updating session context: {str(e)}")

    def _format_response_for_whatsapp(self, response: Dict) -> str:
        """Format the response for WhatsApp display"""
        content = response.get("content", "")
        
        # Add tool results formatting if needed
        if response.get("tools_used"):
            for tool_use in response["tools_used"]:
                result = tool_use.get("result", {})
                
                # Skip if result is just a string (already handled by LLM)
                if isinstance(result, str):
                    continue
                
                # Only format if result is a dictionary with expected structure
                if isinstance(result, dict):
                    if tool_use["name"] == "view_cart" and "items" in result:
                        # Use prompts module for cart formatting
                        cart_display = prompts.format_cart_display(
                            cart_items=result["items"],
                            total=result.get("total", 0)
                        )
                        content += f"\n\n{cart_display}"
                            
                    elif tool_use["name"] == "search_products" and "products" in result:
                        # Use prompts module for product list formatting
                        product_display = prompts.format_product_list(
                            products=result["products"],
                            max_items=5
                        )
                        content += f"\n\n{product_display}"
                    
                    elif tool_use["name"] == "place_order" and "order_id" in result:
                        # Use prompts module for order confirmation
                        order_confirmation = prompts.format_order_confirmation(result)
                        content += f"\n\n{order_confirmation}"
        
        # Use prompts module to truncate for WhatsApp
        return prompts.truncate_for_whatsapp(content)
    
    def _extract_tool_result(self, mcp_result) -> Any:
        """Extract the actual result from MCP tool response"""
        try:
            if hasattr(mcp_result, 'content') and mcp_result.content:
                if isinstance(mcp_result.content, list):
                    # Handle list of content blocks
                    for block in mcp_result.content:
                        if hasattr(block, 'text'):
                            return json.loads(block.text) if block.text.startswith('{') else block.text
                elif isinstance(mcp_result.content, str):
                    return json.loads(mcp_result.content) if mcp_result.content.startswith('{') else mcp_result.content
            return str(mcp_result)
        except json.JSONDecodeError:
            # If it's not JSON, return as string
            return str(mcp_result.content if hasattr(mcp_result, 'content') else mcp_result)
        except Exception as e:
            logger.warning(f"Error extracting tool result: {str(e)}")
            return str(mcp_result)
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect_to_server()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
