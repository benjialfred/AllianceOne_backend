from typing import Dict
from .providers import LLMProvider, MockProvider

class ModelRouter:
    """
    Routes the AI request to the appropriate LLM provider based on capability, cost, and availability.
    """
    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {
            "mock_local": MockProvider(),
            # Future: "gemini": GeminiProvider(), "openai": OpenAIProvider()
        }
        self._default_provider = "mock_local"

    def register_provider(self, provider: LLMProvider):
        self._providers[provider.provider_name] = provider

    def get_provider(self, strategy: str = "default") -> LLMProvider:
        """
        Returns a provider based on the strategy.
        Strategies could be: "fast", "reasoning", "cost-effective".
        """
        if strategy == "default":
            return self._providers.get(self._default_provider)
        
        # In the future, match strategy to provider capabilities.
        return self._providers.get(self._default_provider)
