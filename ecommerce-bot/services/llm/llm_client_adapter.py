"""
LLM Client Adapter
Provides backward compatibility for existing code expecting unified_llm_client
"""
import logging
from typing import Dict, List, Any, Optional
from .unified_llm_service import get_llm_service, LLMResponse

logger = logging.getLogger(__name__)


class UnifiedLLMClient:
    """Adapter class for backward compatibility"""
    
    def __init__(self, providers=None):
        self.llm_service = get_llm_service()
        # Ignore providers parameter - configuration comes from environment
        
    async def generate_response(self, messages: List[Dict[str, str]], 
                               tools: Optional[List[Dict]] = None,
                               **kwargs) -> Dict[str, Any]:
        """Generate response maintaining the original interface"""
        try:
            # Use the unified service
            response = await self.llm_service.generate_response_async(
                messages=messages,
                tools=tools,
                **kwargs
            )
            
            # Convert to expected format
            result = {"content": response.content}
            
            # Add tool calls if present in raw response
            if response.raw_response and "tool_calls" in response.raw_response:
                result["tool_calls"] = response.raw_response["tool_calls"]
                
            return result
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Return a fallback response
            return {"content": "I apologize, but I'm having trouble processing your request. Please try again."}
            
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return self.llm_service.get_stats()