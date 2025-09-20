#!/usr/bin/env python3
"""
Interactive CLI for testing the E-commerce Bot client
"""
import asyncio
import json
import sys
from datetime import datetime
from typing import Optional
import httpx
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.redis.redis_service_enhanced import redis_service as get_redis_service
from services.llm.unified_llm_service import get_llm_service
from client.prompts import get_system_prompt, get_greeting_message, format_cart_display


class CLIClient:
    def __init__(self):
        self.webhook_url = "http://localhost:8000"
        self.phone_number = "+1234567890"  # Test phone number
        self.session_data = {
            "user_id": "cli_test_user",
            "conversation_history": [],
            "cart": [],
            "conversation_state": "greeting"
        }
        self.redis_service = None
        self.llm_service = None
        
    async def initialize(self):
        """Initialize services"""
        try:
            # Initialize Redis
            self.redis_service = get_redis_service
            await self.redis_service.initialize()
            print("✅ Redis service connected")
            
            # Initialize LLM
            self.llm_service = get_llm_service()
            print("✅ LLM service initialized")
            
            # Show LLM stats
            stats = self.llm_service.get_stats()
            print(f"📊 LLM providers: {stats.get('enabled_providers', [])}")
            
            # Load or create session
            await self.load_session()
            
            return True
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            return False
    
    async def load_session(self):
        """Load existing session or create new one"""
        existing_session = await self.redis_service.get_session(self.phone_number)
        
        if existing_session:
            # Update our local session data with relevant fields
            self.session_data["conversation_history"] = existing_session.get("conversation_context", {}).get("history", [])
            self.session_data["cart"] = existing_session.get("cart", {}).get("items", [])
            self.session_data["user_id"] = existing_session.get("user_id", self.phone_number)
            print("📂 Loaded existing session")
        else:
            # Create new session
            await self.redis_service.create_session(
                user_id=self.phone_number,
                phone_number=self.phone_number,
                initial_data={"conversation_context": {"history": []}}
            )
            print("🆕 Created new session")
    
    async def save_session(self):
        """Save session to Redis"""
        # Update the Redis session with our local data
        await self.redis_service.update_session(
            user_id=self.phone_number,
            updates={
                "conversation_context": {
                    "history": self.session_data["conversation_history"]
                },
                "cart": {
                    "items": self.session_data["cart"],
                    "total_items": len(self.session_data["cart"])
                }
            }
        )
    
    async def process_message(self, message: str, is_image: bool = False):
        """Process a user message"""
        # Add to conversation history
        self.session_data["conversation_history"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 20 messages
        if len(self.session_data["conversation_history"]) > 20:
            self.session_data["conversation_history"] = self.session_data["conversation_history"][-20:]
        
        # Get current state
        state = self.session_data.get("conversation_state", "greeting")
        
        # Build messages for LLM
        messages = [
            {"role": "system", "content": get_system_prompt()}
        ]
        
        # Add conversation history
        for msg in self.session_data["conversation_history"]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Generate response
        print("🤔 Thinking...")
        
        try:
            response = await self.llm_service.generate_response_async(
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            # Add assistant response to history
            self.session_data["conversation_history"].append({
                "role": "assistant",
                "content": response.content,
                "timestamp": datetime.now().isoformat()
            })
            
            # Save session
            await self.save_session()
            
            return response.content
            
        except Exception as e:
            print(f"❌ Error generating response: {e}")
            import traceback
            traceback.print_exc()
            
            # Try to provide a helpful response even if LLM fails
            if "shirts" in message.lower() or "clothes" in message.lower():
                return "I'd be happy to help you find clothing! While I'm having technical issues, you can browse our collection including shirts, pants, and more. What type of clothing are you looking for?"
            elif "cart" in message.lower():
                return self.show_cart()
            else:
                return "I'm sorry, I'm experiencing technical difficulties. Please try again in a moment."
    
    async def handle_command(self, command: str):
        """Handle special commands"""
        if command == "/cart":
            return self.show_cart()
        elif command == "/clear":
            self.session_data["cart"] = []
            await self.save_session()
            return "🛒 Cart cleared!"
        elif command == "/session":
            return json.dumps(self.session_data, indent=2)
        elif command == "/history":
            history = "\n".join([
                f"{'User' if msg['role'] == 'user' else 'Bot'}: {msg['content']}"
                for msg in self.session_data["conversation_history"]
            ])
            return history or "No conversation history yet."
        elif command == "/reset":
            self.session_data = {
                "user_id": "cli_test_user",
                "conversation_history": [],
                "cart": [],
                "conversation_state": "greeting"
            }
            await self.save_session()
            return "🔄 Session reset!"
        elif command == "/help":
            return self.get_help()
        return None
    
    def show_cart(self):
        """Display cart contents"""
        cart_items = self.session_data.get("cart", [])
        if not cart_items:
            return "🛒 Your cart is empty"
        
        # Calculate total
        total = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)
        
        # Use the formatted cart display from prompts
        return format_cart_display(cart_items, total)
    
    def get_help(self):
        """Get help text"""
        return """
📖 E-commerce Bot CLI Help

Commands:
  /help     - Show this help message
  /cart     - Show current cart contents
  /clear    - Clear the cart
  /session  - Show raw session data
  /history  - Show conversation history
  /reset    - Reset the session
  /exit     - Exit the CLI

Example Messages:
  - "Show me blue shirts"
  - "I'm looking for jeans under $50"
  - "Add the first one to my cart, size M"
  - "I want to checkout"
  - "What's in my cart?"

Tips:
  - The bot remembers your conversation
  - You can ask for product recommendations
  - Specify sizes when adding to cart
  - Ask about specific features or prices
        """
    
    async def run_interactive(self):
        """Run interactive CLI session"""
        print("\n🛍️ Welcome to E-commerce Bot CLI")
        print("Type '/help' for available commands")
        print("Type '/exit' to quit\n")
        
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                # Check for exit
                if user_input.lower() in ['/exit', 'exit', 'quit']:
                    print("\n👋 Goodbye!")
                    break
                
                # Skip empty input
                if not user_input:
                    continue
                
                # Check for commands
                if user_input.startswith('/'):
                    result = await self.handle_command(user_input)
                    if result:
                        print(f"\n{result}\n")
                        continue
                
                # Process as regular message
                response = await self.process_message(user_input)
                print(f"\nBot: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")


async def test_webhook_mode():
    """Test by sending messages through the webhook"""
    print("\n🌐 Testing through webhook API...\n")
    
    test_messages = [
        "Hi, I'm looking for shirts",
        "Show me blue cotton shirts",
        "What about jeans?",
        "Add the first shirt to my cart, size L"
    ]
    
    async with httpx.AsyncClient() as client:
        for message in test_messages:
            print(f"📤 Sending: {message}")
            
            payload = {
                "channel": "whatsapp",
                "from": "+1234567890",
                "to": "919599425455",
                "message_id": f"cli_test_{datetime.now().timestamp()}",
                "timestamp": datetime.now().isoformat(),
                "type": "text",
                "message": {"text": message}
            }
            
            try:
                response = await client.post(
                    "http://localhost:8000/webhook/whatsapp",
                    json=payload
                )
                print(f"📊 Status: {response.status_code}")
                print(f"📥 Response: {response.json()}\n")
                
                # Wait a bit between messages
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Error: {e}\n")


async def main():
    """Main CLI entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "webhook":
        # Test through webhook
        await test_webhook_mode()
    else:
        # Interactive CLI mode
        cli = CLIClient()
        
        print("🔄 Initializing services...")
        if await cli.initialize():
            await cli.run_interactive()
        else:
            print("❌ Failed to initialize CLI client")


if __name__ == "__main__":
    asyncio.run(main())