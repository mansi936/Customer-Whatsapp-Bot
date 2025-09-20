# Complete LLM Prompt Example

This document shows a complete example of what gets sent to the LLM when processing a user message in the e-commerce WhatsApp bot.

## Message Array Structure

```json
[
  {
    "role": "system",
    "content": "You are a helpful e-commerce shopping assistant. You can help users:\n- Search for products\n- Get personalized recommendations  \n- Manage their shopping cart\n- Place orders\n- Answer questions about products\n- Apply discount codes\n- Track orders\n\nBe friendly, concise, and helpful. Use the available tools to fulfill user requests.\nAlways format responses appropriately for WhatsApp with emojis and clear structure.\n\nUser Preferences:\n- Preferred categories: shirts, jeans, sneakers\n- Usual size: M\n- Budget range: ₹500 - ₹3000"
  },
  {
    "role": "system", 
    "content": "Current cart has 2 items with total ₹4998"
  },
  {
    "role": "system",
    "content": "Returning customer with 3 previous orders."
  },
  {
    "role": "user",
    "content": "Hi, I'm looking for some new clothes"
  },
  {
    "role": "assistant",
    "content": "Hello! 👋 Welcome back! I'd be happy to help you find some new clothes. Since you prefer shirts, jeans, and sneakers in size M within your ₹500-₹3000 budget, let me search for some great options.\n\nWould you like to see:\n• Shirts\n• Jeans  \n• Sneakers\n• Or shall I show you recommendations based on your previous orders?"
  },
  {
    "role": "user",
    "content": "Show me some casual shirts"
  },
  {
    "role": "assistant",
    "content": "I'll search for casual shirts in your size. Let me find some great options within your budget!"
  },
  {
    "role": "user", 
    "content": "I like the blue one, add it to cart"
  },
  {
    "role": "assistant",
    "content": "Great choice! I've added the Blue Cotton Casual Shirt (Size M) to your cart at ₹999.\n\n🛒 Your cart now has 3 items with a total of ₹5997.\n\nWould you like to:\n• Continue shopping\n• View your complete cart\n• Proceed to checkout"
  },
  {
    "role": "user",
    "content": "Actually, can you show me what's in my cart?"
  },
  {
    "role": "assistant",
    "content": "Of course! Let me show you what's currently in your cart."
  },
  {
    "role": "user",
    "content": "Remove the first item and then place the order"
  }
]
```

## Available Tools Array

```json
{
  "tools": [
    {
      "name": "search_products",
      "description": "Search for products by name, category, or filters",
      "parameters": {
        "query": "string",
        "category": "string (optional)",
        "min_price": "number (optional)",
        "max_price": "number (optional)",
        "size": "string (optional)"
      }
    },
    {
      "name": "get_recommendations",
      "description": "Get personalized product recommendations",
      "parameters": {
        "category": "string (optional)",
        "limit": "number (optional)"
      }
    },
    {
      "name": "add_to_cart",
      "description": "Add a product to the shopping cart",
      "parameters": {
        "product_id": "string",
        "quantity": "number"
      }
    },
    {
      "name": "remove_from_cart",
      "description": "Remove an item from the shopping cart",
      "parameters": {
        "item_id": "string"
      }
    },
    {
      "name": "show_cart",
      "description": "Display the current shopping cart contents",
      "parameters": {}
    },
    {
      "name": "place_order",
      "description": "Place an order with items in the cart",
      "parameters": {
        "delivery_address": "string",
        "payment_method": "string (optional)"
      }
    },
    {
      "name": "apply_discount",
      "description": "Apply a discount code to the cart",
      "parameters": {
        "code": "string"
      }
    }
  ]
}
```

## Complete API Call

```python
# What actually gets sent to the LLM
response = await llm_client.chat.completions.create(
    model="gpt-4",
    messages=[
        # All messages from above array
    ],
    tools=tools,  # Tool definitions array
    tool_choice="auto",
    temperature=0.7,
    max_tokens=1000
)
```

## Context Building Process

1. **System Prompt Construction**:
   - Base assistant definition from `get_system_prompt()`
   - User preferences appended if available from `get_personalized_system_prompt()`

2. **Context Injection**:
   - Cart summary from `get_context_prompt("cart_summary", {...})`
   - User status from `get_context_prompt("returning_user", {...})`
   - Session state information

3. **Conversation History**:
   - Last 10 messages from session (configurable)
   - Includes user messages, assistant responses, and tool results
   - Maintains conversation continuity

4. **Current Query**:
   - The new user message being processed

## Example LLM Response

```json
{
  "role": "assistant",
  "content": "I'll remove the first item from your cart and then help you place the order.",
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "show_cart",
        "arguments": "{}"
      }
    }
  ]
}
```

## After Tool Execution

The tool results are formatted using the appropriate formatting functions from `prompts.py`:

```python
# If show_cart returns cart data
cart_display = format_cart_display(
    cart_items=[
        {"name": "Blue Cotton Shirt", "quantity": 1, "price": 999},
        {"name": "Classic Jeans", "quantity": 1, "price": 1999}
    ],
    total=2998
)

# Final formatted response sent to WhatsApp:
"""
I'll remove the first item from your cart and then help you place the order.

🛒 *Your Cart:*

• Blue Cotton Shirt
  Qty: 1 × ₹999 = ₹999
• Classic Jeans
  Qty: 1 × ₹1,999 = ₹1,999

*Total: ₹2,998*

Let me remove the first item and proceed with your order.
"""
```

## Key Points

1. **Personalization**: User preferences are embedded in the system prompt
2. **Context Awareness**: Current cart state and user history are included
3. **Tool Integration**: Tools are passed separately, not in the message array
4. **Formatting**: Tool results are formatted specifically for WhatsApp display
5. **History Management**: Only recent messages included to prevent token overflow
6. **Temperature**: Set to 0.7 for balanced creativity vs consistency