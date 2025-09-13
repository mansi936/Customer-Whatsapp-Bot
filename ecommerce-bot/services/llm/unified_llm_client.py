class UnifiedLLMClient:
    def __init__(self, providers=None):
        self.providers = providers or ["azure", "openai"]

    async def generate_response(self, messages, tools=None):
        # TODO: call LLM provider(s)
        return {"content": "LLM placeholder response"}
