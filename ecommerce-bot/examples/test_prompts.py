"""
Example demonstrating how prompts are used in the MCP client
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client import prompts


def demonstrate_prompts():
    """Demonstrate various prompt functions"""
    
    print("=== SYSTEM PROMPT ===")
    print(prompts.get_system_prompt())
    print("\n")
    
    print("=== PERSONALIZED SYSTEM PROMPT ===")
    user_prefs = {
        "preferred_categories": ["shirts", "jeans"],
        "size": "M",
        "budget_range": [500, 2000]
    }
    print(prompts.get_personalized_system_prompt(user_prefs))
    print("\n")
    
    print("=== ERROR MESSAGES ===")
    print("Tool failure:", prompts.get_error_message("tool_failure", "search_products"))
    print("General error:", prompts.get_error_message("general_error"))
    print("\n")
    
    print("=== PRODUCT LIST FORMATTING ===")
    products = [
        {"name": "Cotton Shirt", "price": 999, "description": "Comfortable cotton shirt for casual wear"},
        {"name": "Denim Jeans", "price": 1499, "description": "Classic blue denim jeans with modern fit"},
        {"name": "Polo T-Shirt", "price": 699, "description": "Premium quality polo t-shirt"}
    ]
    print(prompts.format_product_list(products))
    print("\n")
    
    print("=== CART FORMATTING ===")
    cart_items = [
        {"name": "Cotton Shirt", "quantity": 2, "price": 999},
        {"name": "Denim Jeans", "quantity": 1, "price": 1499}
    ]
    total = sum(item["quantity"] * item["price"] for item in cart_items)
    print(prompts.format_cart_display(cart_items, total))
    print("\n")
    
    print("=== ORDER CONFIRMATION ===")
    order_details = {
        "order_id": "ORD123456",
        "items": cart_items,
        "total": total,
        "delivery_address": "123 Main St, Mumbai 400001"
    }
    print(prompts.format_order_confirmation(order_details))
    print("\n")
    
    print("=== CONVERSATION BUILDING ===")
    session_context = {
        "preferences": user_prefs,
        "cart_items": cart_items,
        "conversation_history": [
            {"role": "user", "content": "Show me shirts"},
            {"role": "assistant", "content": "Here are some shirts for you..."}
        ]
    }
    messages = prompts.build_conversation_messages(
        "Add the first one to my cart",
        session_context
    )
    for msg in messages:
        print(f"{msg['role'].upper()}: {msg['content'][:100]}...")
    

if __name__ == "__main__":
    demonstrate_prompts()