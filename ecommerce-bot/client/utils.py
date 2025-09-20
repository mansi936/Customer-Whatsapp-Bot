"""
Utility functions for MCP Client
Shared utilities to avoid code duplication
"""

from typing import Union, Dict, Any
from datetime import datetime


def extract_message_text(message: Union[str, Dict[str, Any]]) -> str:
    """
    Extract text from various message formats
    
    Args:
        message: Message in string or dict format
        
    Returns:
        Extracted message text
    """
    if isinstance(message, str):
        return message
    elif isinstance(message, dict):
        return message.get("text", str(message))
    else:
        return str(message)


def get_timestamp() -> str:
    """
    Get current UTC timestamp in ISO format
    
    Returns:
        ISO formatted timestamp
    """
    return datetime.utcnow().isoformat()


# Configuration constants
class Config:
    """Configuration constants to avoid magic numbers"""
    # Conversation history limits
    HISTORY_FOR_LLM_CONTEXT = 10  # Messages to include in LLM context
    HISTORY_TO_STORE = 20  # Total messages to store in session
    
    # WhatsApp limits
    WHATSAPP_MAX_LENGTH = 1600
    
    # LLM settings
    DEFAULT_TEMPERATURE = 0.7
    
    # Session defaults
    DEFAULT_SESSION_CONTEXT = {
        "conversation_history": [],
        "cart_items": [],
        "preferences": {},
    }