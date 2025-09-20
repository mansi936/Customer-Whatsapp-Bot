"""
Example showing complete prompt structure sent to LLM
This demonstrates how the MCP client builds the full conversation context
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import prompts
from client.utils import Config


def show_complete_prompt_structure():
    """Demonstrate the complete prompt structure sent to LLM"""
    
    # 1. Simulate a rich session context
    session_context = {
        "user_id": "user_12345",
        "preferences": {
            "preferred_categories": ["shirts", "jeans", "sneakers"],
            "size": "M",
            "budget_range": [500, 3000],
            "favorite_brands": ["Nike", "Adidas", "Puma"]
        },
        "cart_items": [
            {"name": "Nike Sports Shirt", "quantity": 2, "price": 1299, "id": "prod_001"},
            {"name": "Adidas Running Shoes", "quantity": 1, "price": 4999, "id": "prod_002"}
        ],
        "conversation_history": [
            {"role": "user", "content": "Hi, I'm looking for some workout clothes"},
            {"role": "assistant", "content": "Hello! I'd be happy to help you find workout clothes. Based on your preferences for Nike, Adidas, and Puma brands in size M, I can show you some great options. What specific type of workout clothes are you looking for - shirts, shorts, or complete sets?"},
            {"role": "user", "content": "Show me some running shirts"},
            {"role": "assistant", "content": "I'll search for running shirts from your preferred brands. Let me find the best options for you."},
            {"role": "tool", "tool_call_id": "search_1", "content": json.dumps({
                "products": [
                    {"name": "Nike Dri-FIT Running Shirt", "price": 1299, "description": "Breathable mesh fabric"},
                    {"name": "Adidas Climacool Tee", "price": 1499, "description": "Moisture-wicking technology"},
                    {"name": "Puma Running Essential", "price": 999, "description": "Lightweight performance fabric"}
                ]
            })},
            {"role": "assistant", "content": "Here are some great running shirts I found:\n\n1. Nike Dri-FIT Running Shirt - ₹1,299\n2. Adidas Climacool Tee - ₹1,499\n3. Puma Running Essential - ₹999\n\nAll are available in size M. Which one would you like to add to your cart?"},
            {"role": "user", "content": "I'll take the Nike one, add 2 to my cart"},
            {"role": "assistant", "content": "Great choice! I've added 2 Nike Dri-FIT Running Shirts to your cart. Your cart now has 4 items with a total of ₹7,596."}
        ],
        "order_history": [
            {"order_id": "ORD_9876", "date": "2024-01-15", "total": 3499}
        ],
        "last_activity": "2024-01-20T10:30:00Z"
    }
    
    # 2. Current user message
    current_message = "Can you recommend some running shorts to go with the shirts?"
    
    # 3. Build complete conversation messages
    messages = prompts.build_conversation_messages(
        user_message=current_message,
        session_context=session_context,
        include_personalization=True
    )
    
    # 4. Display the complete prompt structure
    print("=== COMPLETE PROMPT STRUCTURE SENT TO LLM ===\n")
    print("Total messages:", len(messages))
    print("\n" + "="*80 + "\n")
    
    for i, msg in enumerate(messages):
        print(f"Message {i+1}:")
        print(f"Role: {msg['role']}")
        print(f"Content: {msg['content']}")
        if 'tool_call_id' in msg:
            print(f"Tool Call ID: {msg['tool_call_id']}")
        print("\n" + "-"*40 + "\n")
    
    # 5. Show what tools would be available
    print("\n=== AVAILABLE TOOLS (passed separately to LLM) ===\n")
    example_tools = [
        {
            "type": "function",
            "function": {
                "name": "search_products",
                "description": "Search for products in the catalog",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "category": {"type": "string", "description": "Product category"},
                        "price_range": {"type": "array", "items": {"type": "number"}}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function", 
            "function": {
                "name": "get_recommendations",
                "description": "Get personalized product recommendations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "based_on": {"type": "string", "description": "Item to base recommendations on"},
                        "limit": {"type": "integer", "description": "Number of recommendations"}
                    }
                }
            }
        }
    ]
    
    print(json.dumps(example_tools, indent=2))
    
    # 6. Show complete API call structure
    print("\n=== COMPLETE API CALL TO LLM ===\n")
    api_call = {
        "messages": messages,
        "tools": example_tools,
        "temperature": Config.DEFAULT_TEMPERATURE,
        "model": "gpt-4"  # or whatever model is configured
    }
    
    print("API Call Structure:")
    print(f"- Messages: {len(api_call['messages'])} messages")
    print(f"- Tools: {len(api_call['tools'])} tools available")
    print(f"- Temperature: {api_call['temperature']}")
    print(f"- Model: {api_call['model']}")
    
    # 7. Explain the flow
    print("\n=== PROMPT CONSTRUCTION FLOW ===\n")
    print("1. System Prompt: Defines the assistant's role and capabilities")
    print("2. Context Prompt: Adds current cart summary (2 items, ₹7,596 total)")
    print("3. Conversation History: Last 10 messages from session (configurable)")
    print("4. Current User Message: The new query about running shorts")
    print("5. Tools: Passed separately, allowing LLM to call functions")
    print("\nThe LLM processes all this context to generate a relevant response,")
    print("potentially making tool calls to search for running shorts that match")
    print("the user's preferences (Nike/Adidas/Puma, size M, budget ₹500-3000).")


if __name__ == "__main__":
    show_complete_prompt_structure()