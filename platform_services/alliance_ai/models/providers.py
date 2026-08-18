from abc import ABC, abstractmethod
from typing import Dict, Any, List

class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers (Gemini, OpenAI, Claude, etc.).
    This ensures Alliance AI is not tightly coupled to any specific vendor.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def supports_tools(self) -> bool:
        pass

    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None) -> str:
        """
        Generates a standard text response.
        If tools are provided, the provider must handle tool calling format.
        """
        pass

    @abstractmethod
    def execute_tool_call_loop(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], tool_registry) -> str:
        """
        Executes a loop where the LLM requests a tool, the provider runs it via the registry,
        and feeds the result back until a final answer is generated.
        """
        pass

class MockProvider(LLMProvider):
    """
    A mock provider for testing and V1 local development.
    """
    @property
    def provider_name(self) -> str:
        return "mock_local"

    @property
    def supports_tools(self) -> bool:
        return True

    def generate(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None) -> str:
        return "This is a mock response from Alliance AI."

    def execute_tool_call_loop(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], tool_registry) -> str:
        # Mock logic: if tools are passed, we just pretend we called one.
        return "Mock loop completed. Tools were provided."
