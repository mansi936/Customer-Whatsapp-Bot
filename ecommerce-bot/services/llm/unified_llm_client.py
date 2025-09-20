# Import from the new implementation
from .llm_client_adapter import UnifiedLLMClient

# Re-export for backward compatibility
__all__ = ['UnifiedLLMClient']
