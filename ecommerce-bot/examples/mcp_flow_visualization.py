"""
Visual representation of how the MCP Client processes messages with prompts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import prompts
import json


def visualize_mcp_flow():
    """Shows the step-by-step flow of message processing"""
    
    print("🚀 MCP CLIENT MESSAGE PROCESSING FLOW\n")
    print("=" * 80)
    
    # Step 1: User sends message
    print("\n1️⃣ USER SENDS MESSAGE")
    print("└─> 📱 WhatsApp: 'Show me cotton shirts under 1500 rupees'")
    
    # Step 2: Session context retrieved
    print("\n2️⃣ SESSION CONTEXT RETRIEVED")
    session_context = {
        "user_id": "user_12345",
        "preferences": {
            "preferred_categories": ["shirts", "t-shirts"],
            "size": "M",
            "budget_range": [800, 1500]
        },
        "conversation_history": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello! How can I help you shop today?"}
        ],
        "cart_items": []
    }
    print("└─> 📋 Session loaded with:")
    print("    - User preferences: size M, budget ₹800-1500")
    print("    - Conversation history: 2 messages")
    print("    - Cart: empty")
    
    # Step 3: Build conversation with prompts
    print("\n3️⃣ BUILD CONVERSATION USING PROMPTS MODULE")
    messages = prompts.build_conversation_messages(
        user_message="Show me cotton shirts under 1500 rupees",
        session_context=session_context,
        include_personalization=True
    )
    
    print("└─> 🤖 Generated message structure:")
    for i, msg in enumerate(messages):
        if msg['role'] == 'system':
            print(f"    [{i}] SYSTEM: {msg['content'][:80]}...")
        else:
            print(f"    [{i}] {msg['role'].upper()}: {msg['content']}")
    
    # Step 4: Get tools from MCP server
    print("\n4️⃣ DISCOVER TOOLS FROM MCP SERVER")
    available_tools = [
        {"name": "search_products", "description": "Search for products"},
        {"name": "add_to_cart", "description": "Add items to cart"},
        {"name": "show_cart", "description": "Display cart contents"}
    ]
    print("└─> 🔧 Available tools:")
    for tool in available_tools:
        print(f"    - {tool['name']}: {tool['description']}")
    
    # Step 5: LLM processes and decides
    print("\n5️⃣ LLM PROCESSES REQUEST")
    print("└─> 🧠 LLM analyzes:")
    print("    - User wants: cotton shirts")
    print("    - Budget constraint: under ₹1500")
    print("    - User preference matches: shirts category ✓")
    print("└─> 🎯 Decision: Use 'search_products' tool")
    
    # Step 6: Tool execution
    print("\n6️⃣ EXECUTE TOOL CALL")
    print("└─> 🔨 Calling: search_products(query='cotton shirts', filters={'max_price': 1500})")
    tool_result = {
        "products": [
            {"name": "Cotton Comfort Shirt", "price": 1299, "description": "100% cotton, breathable"},
            {"name": "Casual Cotton Shirt", "price": 999, "description": "Soft cotton blend"},
            {"name": "Premium Cotton Formal", "price": 1499, "description": "Egyptian cotton"}
        ]
    }
    print("└─> ✅ Found 3 matching products")
    
    # Step 7: Format response with prompts
    print("\n7️⃣ FORMAT RESPONSE USING PROMPTS MODULE")
    
    # LLM response
    llm_response = "I found some great cotton shirts within your budget!"
    
    # Format products
    product_display = prompts.format_product_list(tool_result["products"])
    
    # Combine
    final_response = llm_response + "\n\n" + product_display
    
    print("└─> 📝 Formatted response:")
    print("-" * 60)
    print(final_response)
    print("-" * 60)
    
    # Step 8: Apply WhatsApp truncation
    print("\n8️⃣ APPLY WHATSAPP FORMATTING")
    whatsapp_response = prompts.truncate_for_whatsapp(final_response)
    print(f"└─> ✂️ Length check: {len(whatsapp_response)} chars (max 1600)")
    
    # Step 9: Update session
    print("\n9️⃣ UPDATE SESSION CONTEXT")
    print("└─> 💾 Saving:")
    print("    - New conversation messages")
    print("    - Last activity timestamp")
    print("    - Tool usage statistics")
    
    # Final output
    print("\n✅ FINAL OUTPUT TO WHATSAPP:")
    print("=" * 80)
    print(whatsapp_response)
    print("=" * 80)
    
    # Show error handling
    print("\n\n🚨 ERROR HANDLING EXAMPLE")
    print("If something goes wrong:")
    error_msg = prompts.get_error_message("tool_failure", "search_products")
    print(f"└─> Error message: {error_msg}")
    
    # Show personalization effect
    print("\n\n🎯 PERSONALIZATION IN ACTION")
    print("System prompt includes user preferences:")
    personalized = prompts.get_personalized_system_prompt(session_context["preferences"])
    print(personalized[200:400] + "...")


def show_prompt_examples():
    """Show various prompt examples"""
    print("\n\n📚 PROMPT EXAMPLES\n")
    print("=" * 80)
    
    # Different scenarios
    scenarios = [
        {
            "title": "NEW USER GREETING",
            "func": lambda: prompts.get_greeting_message("morning", "Raj")
        },
        {
            "title": "EMPTY CART",
            "func": lambda: prompts.format_cart_display([], 0)
        },
        {
            "title": "ORDER CONFIRMATION",
            "func": lambda: prompts.format_order_confirmation({
                "order_id": "ORD789",
                "items": [{"name": "Cotton Shirt", "quantity": 2}],
                "total": 2598,
                "delivery_address": "Mumbai, Maharashtra"
            })
        },
        {
            "title": "RECOMMENDATION PROMPT",
            "func": lambda: prompts.get_recommendation_prompt({
                "recent_views": [{"category": "shirts"}, {"category": "jeans"}]
            })
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['title']}:")
        print("-" * 40)
        print(scenario['func']())


if __name__ == "__main__":
    visualize_mcp_flow()
    show_prompt_examples()