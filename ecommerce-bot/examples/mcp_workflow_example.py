"""
Complete example demonstrating how the MCP client works with prompts
This shows the full flow from user message to WhatsApp response
"""

import asyncio
import json
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import prompts


# Mock classes to simulate the actual components
class MockSessionManager:
    """Mock session manager for demonstration"""
    def __init__(self):
        self.sessions = {}
    
    async def get_session(self, user_id):
        if user_id not in self.sessions:
            return None
        return self.sessions[user_id]
    
    async def set_session(self, user_id, context):
        self.sessions[user_id] = context


class MockServerManager:
    """Mock server manager that simulates MCP server tools"""
    async def get_available_tools(self):
        """Returns tools available from MCP server"""
        return [
            {
                "name": "search_products",
                "description": "Search for products in the catalog",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "filters": {
                            "type": "object",
                            "properties": {
                                "min_price": {"type": "number"},
                                "max_price": {"type": "number"},
                                "category": {"type": "string"}
                            }
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "add_to_cart",
                "description": "Add a product to the shopping cart",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID to add"},
                        "quantity": {"type": "integer", "description": "Quantity to add"}
                    },
                    "required": ["product_id"]
                }
            },
            {
                "name": "show_cart",
                "description": "Show the current shopping cart",
                "parameters": {"type": "object", "properties": {}}
            }
        ]
    
    async def route_tool(self, tool_name, **kwargs):
        """Simulates tool execution"""
        if tool_name == "search_products":
            return {
                "products": [
                    {
                        "id": "SHIRT001",
                        "name": "Premium Cotton Shirt",
                        "price": 1299,
                        "description": "100% cotton shirt with modern fit, perfect for office or casual wear",
                        "category": "shirts",
                        "available": True
                    },
                    {
                        "id": "SHIRT002", 
                        "name": "Linen Blend Casual Shirt",
                        "price": 999,
                        "description": "Breathable linen blend shirt, ideal for summer",
                        "category": "shirts",
                        "available": True
                    },
                    {
                        "id": "SHIRT003",
                        "name": "Formal Cotton Shirt",
                        "price": 1599,
                        "description": "Classic formal shirt with spread collar",
                        "category": "shirts", 
                        "available": True
                    }
                ]
            }
        elif tool_name == "add_to_cart":
            return {
                "success": True,
                "message": "Item added to cart",
                "cart_count": 1
            }
        elif tool_name == "show_cart":
            return {
                "items": [
                    {
                        "id": "SHIRT001",
                        "name": "Premium Cotton Shirt",
                        "price": 1299,
                        "quantity": 1
                    }
                ],
                "total": 1299,
                "item_count": 1
            }
        return {}


class MockLLMResponse:
    """Mock LLM response object"""
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.raw_response = {}
        if tool_calls:
            self.raw_response["tool_calls"] = tool_calls


class MockLLMService:
    """Mock LLM service for demonstration"""
    async def generate_response_async(self, messages, tools=None, temperature=0.7):
        # Simulate LLM decision making based on the last user message
        last_user_msg = next((m for m in reversed(messages) if m["role"] == "user"), None)
        
        if not last_user_msg:
            return MockLLMResponse("How can I help you today?")
        
        user_content = last_user_msg["content"].lower()
        
        # Simulate different LLM behaviors
        if "search" in user_content or "show me" in user_content or "cotton shirts" in user_content:
            return MockLLMResponse(
                "I'll search for cotton shirts for you.",
                tool_calls=[{
                    "id": "call_001",
                    "name": "search_products",
                    "arguments": {"query": "cotton shirts"}
                }]
            )
        
        elif "add" in user_content and ("first" in user_content or "1" in user_content):
            return MockLLMResponse(
                "I'll add the Premium Cotton Shirt to your cart.",
                tool_calls=[{
                    "id": "call_002", 
                    "name": "add_to_cart",
                    "arguments": {"product_id": "SHIRT001", "quantity": 1}
                }]
            )
        
        elif "cart" in user_content:
            return MockLLMResponse(
                "Let me show you what's in your cart.",
                tool_calls=[{
                    "id": "call_003",
                    "name": "show_cart",
                    "arguments": {}
                }]
            )
        
        # When tool results are in context, generate final response
        if any(m.get("role") == "tool" for m in messages):
            tool_msg = next(m for m in reversed(messages) if m.get("role") == "tool")
            tool_result = json.loads(tool_msg["content"])
            
            if "products" in tool_result:
                return MockLLMResponse(
                    "I found some great cotton shirts for you! Here are the top options that match what you're looking for."
                )
            elif "success" in tool_result and tool_result["success"]:
                return MockLLMResponse(
                    "Perfect! I've added the Premium Cotton Shirt to your cart. It's a great choice - 100% cotton with a modern fit. Would you like to see more shirts or checkout?"
                )
            elif "items" in tool_result:
                return MockLLMResponse(
                    "Here's what you have in your shopping cart. The Premium Cotton Shirt is a fantastic choice! Would you like to continue shopping or proceed to checkout?"
                )
        
        return MockLLMResponse("I'm here to help you shop! You can ask me to search for products, manage your cart, or get recommendations.")


async def demonstrate_mcp_workflow():
    """Demonstrates the complete MCP client workflow"""
    
    print("=== MCP CLIENT WORKFLOW DEMONSTRATION ===\n")
    
    # Initialize components
    session_manager = MockSessionManager()
    server_manager = MockServerManager()
    llm_service = MockLLMService()
    
    # Simulate a user session
    user_id = "user_12345"
    
    # Create session context with preferences
    session_context = {
        "user_id": user_id,
        "conversation_history": [],
        "cart_items": [],
        "preferences": {
            "preferred_categories": ["shirts", "t-shirts"],
            "size": "M",
            "budget_range": [800, 1500]
        },
        "created_at": datetime.utcnow().isoformat()
    }
    
    await session_manager.set_session(user_id, session_context)
    
    print("📱 USER SESSION INITIALIZED")
    print(f"User ID: {user_id}")
    print(f"Preferences: {json.dumps(session_context['preferences'], indent=2)}\n")
    
    # Simulate conversation flow
    conversations = [
        {
            "user_input": "Hi, I'm looking for cotton shirts",
            "description": "User searches for products"
        },
        {
            "user_input": "Add the first one to my cart",
            "description": "User adds item to cart"
        },
        {
            "user_input": "Show me my cart",
            "description": "User views cart"
        }
    ]
    
    for conv in conversations:
        print(f"\n{'='*60}")
        print(f"📤 USER MESSAGE: {conv['user_input']}")
        print(f"   ({conv['description']})")
        print(f"{'='*60}\n")
        
        # STEP 1: Build conversation history
        print("1️⃣ BUILDING CONVERSATION HISTORY")
        
        # Get current session
        current_session = await session_manager.get_session(user_id)
        
        # Build messages using prompts module
        messages = prompts.build_conversation_messages(
            user_message=conv["user_input"],
            session_context=current_session,
            include_personalization=True
        )
        
        print(f"   Messages in context: {len(messages)}")
        for msg in messages[-3:]:  # Show last 3 messages
            role = msg['role'].upper()
            content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            print(f"   - {role}: {content_preview}")
        
        # STEP 2: Get available tools
        print("\n2️⃣ GETTING AVAILABLE TOOLS FROM MCP SERVER")
        tools = await server_manager.get_available_tools()
        print(f"   Available tools: {[t['name'] for t in tools]}")
        
        # STEP 3: Call LLM with context and tools
        print("\n3️⃣ CALLING LLM WITH CONTEXT AND TOOLS")
        llm_response = await llm_service.generate_response_async(messages, tools)
        print(f"   LLM Response: {llm_response.content}")
        
        if llm_response.raw_response.get("tool_calls"):
            print(f"   Tool calls requested: {[tc['name'] for tc in llm_response.raw_response['tool_calls']]}")
        
        # STEP 4: Process tool calls if any
        tools_used = []
        final_content = llm_response.content
        
        if llm_response.raw_response.get("tool_calls"):
            print("\n4️⃣ EXECUTING TOOL CALLS")
            
            for tool_call in llm_response.raw_response["tool_calls"]:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("arguments", {})
                
                print(f"   Executing {tool_name} with args: {tool_args}")
                
                # Execute tool
                tool_result = await server_manager.route_tool(tool_name, **tool_args)
                tools_used.append({
                    "name": tool_name,
                    "args": tool_args,
                    "result": tool_result
                })
                
                print(f"   Tool result: {json.dumps(tool_result, indent=2)[:200]}...")
                
                # Add tool interaction to messages
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", tool_name),
                    "content": json.dumps(tool_result)
                })
                
                # Get final response from LLM
                print("\n   Getting final response from LLM...")
                final_llm_response = await llm_service.generate_response_async(messages)
                final_content = final_llm_response.content
        
        # STEP 5: Format response for WhatsApp
        print("\n5️⃣ FORMATTING RESPONSE FOR WHATSAPP")
        
        # Build response object
        response = {
            "content": final_content,
            "tools_used": tools_used
        }
        
        # Format using prompts module
        formatted_content = final_content
        
        if tools_used:
            for tool_use in tools_used:
                result = tool_use.get("result", {})
                
                if tool_use["name"] == "search_products" and "products" in result:
                    product_display = prompts.format_product_list(result["products"])
                    formatted_content += f"\n\n{product_display}"
                
                elif tool_use["name"] == "show_cart" and "items" in result:
                    cart_display = prompts.format_cart_display(
                        result["items"],
                        result.get("total", 0)
                    )
                    formatted_content += f"\n\n{cart_display}"
        
        # Truncate for WhatsApp
        final_whatsapp_response = prompts.truncate_for_whatsapp(formatted_content)
        
        print("\n📱 FINAL WHATSAPP RESPONSE:")
        print("-" * 40)
        print(final_whatsapp_response)
        print("-" * 40)
        
        # STEP 6: Update session
        print("\n6️⃣ UPDATING SESSION CONTEXT")
        
        # Add to conversation history
        current_session["conversation_history"].append({"role": "user", "content": conv["user_input"]})
        current_session["conversation_history"].append({"role": "assistant", "content": final_content})
        
        # Update cart if needed
        if any(tu["name"] == "add_to_cart" for tu in tools_used):
            current_session["cart_items"].append({
                "id": "SHIRT001",
                "name": "Premium Cotton Shirt",
                "price": 1299,
                "quantity": 1
            })
        
        current_session["last_activity"] = datetime.utcnow().isoformat()
        
        # Save session
        await session_manager.set_session(user_id, current_session)
        print("   Session updated successfully")
        
        # Add delay for readability
        await asyncio.sleep(0.5)
    
    print("\n\n=== DEMONSTRATION COMPLETE ===")
    print("\n📊 FINAL SESSION STATE:")
    final_session = await session_manager.get_session(user_id)
    print(f"- Conversation messages: {len(final_session['conversation_history'])}")
    print(f"- Cart items: {len(final_session.get('cart_items', []))}")
    print(f"- Last activity: {final_session.get('last_activity', 'Unknown')}")


if __name__ == "__main__":
    asyncio.run(demonstrate_mcp_workflow())