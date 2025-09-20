"""
Prompt Templates for MCP Client
This module contains all prompt templates and functions for the e-commerce bot
"""

from typing import Dict, List, Any, Optional
import json
from .utils import Config


def get_system_prompt() -> str:
    """
    Returns the main system prompt that defines the assistant's role and capabilities
    """
    return """You are a helpful e-commerce shopping assistant powered by advanced AI. You can help users with:

        🛍️ **Shopping Features:**
        - Search for products by name, category, or price range
        - Get detailed information about specific products
        - Receive AI-powered personalized recommendations that learn from your preferences
        - Browse product catalogs
        - Discover similar products when viewing items

        🛒 **Cart Management:**
        - Add items to shopping cart
        - View current cart contents and total
        - Remove items from cart
        - Update quantities

        📦 **Order Processing:**
        - Place orders with delivery details
        - Choose payment methods
        - Track order status
        - View order history

        👔 **Virtual Try-On:**
        - Try on clothes virtually using user photos
        - Get tips for best try-on results
        - Save and share try-on results

        **Guidelines:**
        - Be friendly, conversational, and helpful
        - Use emojis appropriately for WhatsApp formatting
        - Provide clear, concise responses
        - Proactively suggest related products when relevant
        - Ask clarifying questions when needed
        - Format prices in local currency (₹)
        - Keep responses under 300 words for WhatsApp

        When users greet you, respond warmly and ask how you can help them shop today.
        For product searches, always use the search_products tool and display results clearly.
        For cart operations, use view_cart to show current contents after any modifications."""


def get_personalized_system_prompt(user_preferences: Optional[Dict[str, Any]] = None) -> str:
    """
    Returns a personalized system prompt based on user preferences
    
    Args:
        user_preferences: Dictionary containing user preferences like categories, budget, etc.
    """
    base_prompt = get_system_prompt()
    
    if user_preferences:
        personalization = "\n\nUser Preferences:"
        if user_preferences.get("preferred_categories"):
            personalization += f"\n- Preferred categories: {', '.join(user_preferences['preferred_categories'])}"
        if user_preferences.get("size"):
            personalization += f"\n- Usual size: {user_preferences['size']}"
        if user_preferences.get("budget_range"):
            min_budget, max_budget = user_preferences["budget_range"]
            personalization += f"\n- Budget range: ₹{min_budget} - ₹{max_budget}"
        
        return base_prompt + personalization
    
    return base_prompt


def get_context_prompt(context_type: str, context_data: Dict[str, Any]) -> str:
    """
    Returns context-specific prompts for different scenarios
    
    Args:
        context_type: Type of context (e.g., "cart_summary", "order_status")
        context_data: Data relevant to the context
    """
    prompts = {
        "cart_summary": lambda data: f"Current cart has {data.get('item_count', 0)} items with total ₹{data.get('total', 0)}",
        "active_session": lambda data: f"This is a continuing conversation. Last activity: {data.get('last_activity', 'Unknown')}",
        "new_user": lambda data: "This is a new user. Be welcoming and offer to help them get started.",
        "returning_user": lambda data: f"Returning customer with {data.get('order_count', 0)} previous orders.",
        "abandoned_cart": lambda data: "User has items in cart from previous session. Gently remind them about their pending items."
    }
    
    prompt_func = prompts.get(context_type)
    if prompt_func:
        return prompt_func(context_data)
    return ""


def get_tool_instruction_prompt(tool_name: str) -> str:
    """
    Returns specific instructions for using tools effectively
    
    Args:
        tool_name: Name of the tool
    """
    tool_instructions = {
        "search_products": "When searching products, consider user's stated preferences and budget. Show top 5 most relevant results with prices and brief descriptions.",
        "get_product_details": "Show comprehensive product information. ALWAYS pass the user_id parameter to track views and get personalized similar items.",
        "get_personalized_recommendations": "Use this tool to get AI-powered personalized recommendations from AWS Personalize. This learns from user behavior.",
        "get_recommendations": "Legacy recommendation tool - prefer using get_personalized_recommendations instead.",
        "add_to_cart": "Confirm the product name and quantity before adding. Always follow up with view_cart to show updated contents.",
        "view_cart": "Display all cart items with quantities, individual prices, and total. Format clearly for WhatsApp.",
        "remove_from_cart": "Confirm which item to remove, then show updated cart contents.",
        "process_order": "Verify all required information: payment method and complete shipping address. Confirm total before processing.",
        "get_order_status": "Provide detailed tracking information with timeline and current status.",
        "virtual_tryon": "Explain the virtual try-on feature clearly. Ensure user provides a full-body or upper-body photo.",
        "get_tryon_tips": "Share helpful tips for getting best virtual try-on results."
    }
    
    return tool_instructions.get(tool_name, "")


def get_error_message(error_type: str, tool_name: str = None, error_details: str = None) -> str:
    """
    Returns user-friendly error messages
    
    Args:
        error_type: Type of error (e.g., "tool_failure", "invalid_input")
        tool_name: Name of the tool that failed (if applicable)
        error_details: Additional error details
    """
    base_messages = {
        "tool_failure": {
            "search_products": "I couldn't search for products right now. Please try again with a different search term.",
            "get_product_details": "I couldn't fetch product details. Please verify the product ID and try again.",
            "get_recommendations": "I couldn't fetch recommendations at the moment. Please try again later.",
            "get_personalized_recommendations": "I couldn't fetch your personalized recommendations. Showing popular items instead.",
            "add_to_cart": "I couldn't add the item to your cart. Please check if the item is still available.",
            "view_cart": "I couldn't retrieve your cart details. Please try again.",
            "remove_from_cart": "I couldn't remove the item from your cart. Please try again.",
            "process_order": "I encountered an error while placing your order. Please verify your details and try again.",
            "get_order_status": "I couldn't fetch the order status. Please check the order ID and try again.",
            "virtual_tryon": "The virtual try-on service is temporarily unavailable. Please try again later.",
            "get_tryon_tips": "I couldn't fetch try-on tips. Please try again."
        },
        "invalid_input": "I didn't understand that request. Could you please rephrase it?",
        "session_error": "I'm having trouble accessing your session. Please try again.",
        "general_error": "I apologize, but I encountered an error. Please try again."
    }
    
    if error_type == "tool_failure" and tool_name:
        return base_messages["tool_failure"].get(
            tool_name, 
            f"I encountered an error while {tool_name.replace('_', ' ')}. Please try again."
        )
    
    return base_messages.get(error_type, base_messages["general_error"])


def format_product_list(products: List[Dict[str, Any]], max_items: int = 5) -> str:
    """
    Formats product search results for WhatsApp display
    
    Args:
        products: List of product dictionaries
        max_items: Maximum number of items to display
    """
    if not products:
        return "No products found matching your criteria. Try a different search term."
    
    formatted = "📦 *Found Products:*\n"
    for idx, product in enumerate(products[:max_items], 1):
        name = product.get('name', 'Unknown Product')
        price = product.get('price', 0)
        description = product.get('description', '')[:50]
        
        formatted += f"\n{idx}. *{name}*\n"
        formatted += f"   ₹{price:,}"
        if description:
            formatted += f" - {description}..."
        formatted += "\n"
    
    if len(products) > max_items:
        formatted += f"\n_Showing top {max_items} of {len(products)} results_"
    
    return formatted


def format_cart_display(cart_items: List[Dict[str, Any]], total: float) -> str:
    """
    Formats shopping cart for WhatsApp display
    
    Args:
        cart_items: List of items in cart
        total: Total cart value
    """
    if not cart_items:
        return "🛒 Your cart is empty. Start shopping to add items!"
    
    formatted = "🛒 *Your Cart:*\n"
    for item in cart_items:
        name = item.get('name', 'Unknown Item')
        quantity = item.get('quantity', 1)
        price = item.get('price', 0)
        item_total = quantity * price
        
        formatted += f"\n• {name}\n"
        formatted += f"  Qty: {quantity} × ₹{price:,} = ₹{item_total:,}"
    
    formatted += f"\n\n*Total: ₹{total:,}*"
    return formatted


def format_order_confirmation(order_details: Dict[str, Any]) -> str:
    """
    Formats order confirmation message
    
    Args:
        order_details: Dictionary containing order information
    """
    order_id = order_details.get('order_id', 'N/A')
    items = order_details.get('items', [])
    total = order_details.get('total', 0)
    delivery_address = order_details.get('delivery_address', 'Not specified')
    
    formatted = f"✅ *Order Placed Successfully!*\n\n"
    formatted += f"Order ID: {order_id}\n"
    formatted += f"Total Amount: ₹{total:,}\n"
    formatted += f"Delivery Address: {delivery_address}\n\n"
    formatted += "*Items:*\n"
    
    for item in items:
        formatted += f"• {item.get('name', 'Unknown')} (Qty: {item.get('quantity', 1)})\n"
    
    formatted += "\nYou'll receive a confirmation SMS shortly."
    return formatted


def get_greeting_message(time_of_day: str = None, user_name: str = None) -> str:
    """
    Returns appropriate greeting message
    
    Args:
        time_of_day: "morning", "afternoon", "evening", or None
        user_name: User's name if available
    """
    greetings = {
        "morning": "Good morning",
        "afternoon": "Good afternoon", 
        "evening": "Good evening",
        "default": "Hello"
    }
    
    greeting = greetings.get(time_of_day, greetings["default"])
    if user_name:
        greeting += f", {user_name}"
    
    greeting += "! 👋 How can I help you today?"
    return greeting


def get_recommendation_prompt(user_history: Dict[str, Any]) -> str:
    """
    Returns prompt for generating personalized recommendations
    
    Args:
        user_history: Dictionary containing user's browsing/purchase history
    """
    base = "Based on your preferences"
    
    if user_history.get("recent_views"):
        categories = list(set([item.get("category", "") for item in user_history["recent_views"]]))
        if categories:
            base += f" and recent interest in {', '.join(categories[:3])}"
    
    if user_history.get("recent_purchases"):
        base += " and purchase history"
    
    base += ", here are my recommendations:"
    return base


def get_conversation_starter(scenario: str) -> str:
    """
    Returns conversation starters for different scenarios
    
    Args:
        scenario: Type of scenario (e.g., "new_arrival", "sale", "abandoned_cart")
    """
    starters = {
        "new_arrival": "🆕 We have new arrivals in your favorite categories! Would you like to see them?",
        "sale": "🎉 Great news! There's a sale on items you might like. Interested in checking them out?",
        "abandoned_cart": "You have items in your cart from your last visit. Would you like to complete your purchase?",
        "recommendation": "Based on your recent activity, I have some personalized recommendations for you!",
        "help": "I'm here to help! You can ask me to search products, show recommendations, or manage your cart."
    }
    
    return starters.get(scenario, starters["help"])


def build_conversation_messages(
    user_message: str,
    session_context: Dict[str, Any],
    include_personalization: bool = True
) -> List[Dict[str, str]]:
    """
    Builds complete conversation message list for LLM
    
    Args:
        user_message: Current user message
        session_context: Session context with history and preferences
        include_personalization: Whether to include user preferences
    """
    messages = []
    
    # Add system prompt
    if include_personalization and session_context.get("preferences"):
        system_prompt = get_personalized_system_prompt(session_context["preferences"])
    else:
        system_prompt = get_system_prompt()
    
    messages.append({"role": "system", "content": system_prompt})
    
    # Add context if available
    if session_context.get("cart_items"):
        cart_context = get_context_prompt("cart_summary", {
            "item_count": len(session_context["cart_items"]),
            "total": sum(item.get("price", 0) * item.get("quantity", 1) 
                        for item in session_context["cart_items"])
        })
        messages.append({"role": "system", "content": cart_context})
    
    # Add conversation history (last N messages for LLM context)
    history = session_context.get("conversation_history", [])[-Config.HISTORY_FOR_LLM_CONTEXT:]
    messages.extend(history)
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    return messages


def truncate_for_whatsapp(text: str, max_length: int = Config.WHATSAPP_MAX_LENGTH) -> str:
    """
    Truncates text to fit WhatsApp message limits
    
    Args:
        text: Text to truncate
        max_length: Maximum character length
    """
    if len(text) <= max_length:
        return text
    
    # Try to truncate at a sentence boundary
    truncated = text[:max_length - 3]
    last_period = truncated.rfind('.')
    last_newline = truncated.rfind('\n')
    
    cut_point = max(last_period, last_newline)
    if cut_point > max_length * 0.8:  # If we can keep at least 80% of the content
        return truncated[:cut_point + 1] + "..."
    
    return truncated + "..."


def get_example_conversations() -> List[Dict[str, Any]]:
    """
    Returns example conversation flows for common scenarios
    These help the LLM understand expected interaction patterns
    """
    return [
        {
            "scenario": "product_search",
            "description": "User searching for products",
            "messages": [
                {"role": "user", "content": "I'm looking for a laptop"},
                {"role": "assistant", "content": "I'll help you find the perfect laptop! Let me search our catalog for you. 🔍", "should_use_tool": "search_products"},
                {"role": "tool_result", "content": "[Found 3 laptops with prices and specs]"},
                {"role": "assistant", "content": "I found 3 great laptops for you:\n\n1. **Dell XPS 13** - ₹89,999\n   Ultra-portable with excellent battery life\n\n2. **MacBook Air M2** - ₹1,14,999\n   Powerful performance, silent operation\n\n3. **HP Pavilion 15** - ₹54,999\n   Great value for everyday use\n\nWould you like more details on any of these, or shall I search for specific features you need?"}
            ]
        },
        {
            "scenario": "add_to_cart_flow",
            "description": "User adding items to cart",
            "messages": [
                {"role": "user", "content": "Add the Dell XPS to my cart"},
                {"role": "assistant", "content": "I'll add the Dell XPS 13 laptop to your cart right away! 🛒", "should_use_tool": "add_to_cart"},
                {"role": "tool_result", "content": "[Item added successfully]"},
                {"role": "assistant", "content": "✅ Added to cart! Let me show you what's in your cart now.", "should_use_tool": "view_cart"},
                {"role": "tool_result", "content": "[Cart with 1 item, total ₹89,999]"},
                {"role": "assistant", "content": "Your cart:\n\n• Dell XPS 13 Laptop\n  Qty: 1 × ₹89,999 = ₹89,999\n\n**Total: ₹89,999**\n\nWould you like to continue shopping or proceed to checkout?"}
            ]
        },
        {
            "scenario": "virtual_tryon",
            "description": "User wants to try on clothes virtually",
            "messages": [
                {"role": "user", "content": "Can I try on that blue shirt virtually?"},
                {"role": "assistant", "content": "Yes! Our virtual try-on feature lets you see how the blue shirt would look on you. 👔\n\nTo get started, I'll need:\n1. A photo of you (full body or upper body works best)\n2. The product ID of the blue shirt\n\nWould you like some tips for the best virtual try-on results first?"}
            ]
        }
    ]


def get_conversation_examples_prompt() -> str:
    """
    Returns a prompt with conversation examples for the LLM
    """
    examples = get_example_conversations()
    prompt = "Here are examples of good conversation flows:\n\n"
    
    for example in examples:
        prompt += f"**{example['description']}:**\n"
        for msg in example['messages']:
            if msg['role'] == 'user':
                prompt += f"User: {msg['content']}\n"
            elif msg['role'] == 'assistant':
                prompt += f"You: {msg['content']}\n"
                if 'should_use_tool' in msg:
                    prompt += f"[Use tool: {msg['should_use_tool']}]\n"
            elif msg['role'] == 'tool_result':
                prompt += f"[Tool result: {msg['content']}]\n"
        prompt += "\n"
    
    return prompt