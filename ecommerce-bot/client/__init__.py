"""
MCP Client Module
Contains the MCP client, prompts, and utilities for WhatsApp e-commerce bot
"""

from .mcp_client import MCPClient
from .prompts import (
    get_system_prompt,
    get_personalized_system_prompt,
    get_error_message,
    format_product_list,
    format_cart_display,
    format_order_confirmation,
    build_conversation_messages,
    truncate_for_whatsapp
)
from .utils import extract_message_text, get_timestamp, Config

__all__ = [
    'MCPClient',
    'get_system_prompt',
    'get_personalized_system_prompt',
    'get_error_message',
    'format_product_list',
    'format_cart_display',
    'format_order_confirmation',
    'build_conversation_messages',
    'truncate_for_whatsapp',
    'extract_message_text',
    'get_timestamp',
    'Config'
]