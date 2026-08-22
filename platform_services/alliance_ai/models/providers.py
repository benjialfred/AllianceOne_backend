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
    def execute_tool_call_loop(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], tool_registry, context=None) -> str:
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

    def execute_tool_call_loop(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], tool_registry, context=None) -> str:
        # Mock logic: if tools are passed, we just pretend we called one.
        return "Mock loop completed. Tools were provided."

class OllamaProvider(LLMProvider):
    """
    Provider for local Ollama models (e.g. Llama 3.1).
    Supports native tool calling via the /api/chat endpoint.
    """
    def __init__(self, model_name: str = "llama3.1", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def supports_tools(self) -> bool:
        return True

    def generate(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None) -> str:
        import requests
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False
        }
        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
        except Exception as e:
            return f"Error communicating with Ollama: {str(e)}"

    def execute_tool_call_loop(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], tool_registry, context=None) -> str:
        import requests
        import json
        
        current_messages = messages.copy()
        max_iterations = 5
        
        for _ in range(max_iterations):
            payload = {
                "model": self.model_name,
                "messages": current_messages,
                "stream": False
            }
            if tools:
                payload["tools"] = tools

            try:
                response = requests.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                return f"Error communicating with Ollama: {str(e)}"

            message = data.get("message", {})
            tool_calls = message.get("tool_calls")

            if not tool_calls:
                # No more tools to call, return the final response
                return message.get("content", "")

            # Add the assistant's message with tool calls to the history
            current_messages.append(message)

            # Execute all requested tools
            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]
                
                try:
                    if context:
                        tool_result = tool_registry.execute_tool(function_name, arguments, context)
                    else:
                        tool_result = f"Error: No context provided for tool {function_name}"
                except Exception as e:
                    tool_result = f"Error executing tool: {str(e)}"

                # Add the tool response to messages
                current_messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_result)
                })
        
        return "Agentic loop exceeded max iterations without a final answer."

class GroqProvider(LLMProvider):
    """
    Provider for Groq Cloud API.
    Groq provides ultra-fast inference for Llama 3 models and supports native tool calling
    using the standard OpenAI API format.
    """
    def __init__(self, model_name: str = "llama-3.1-8b-instant"):
        import os
        self.model_name = model_name
        self.base_url = "https://api.groq.com/openai/v1"
        self.api_key = os.environ.get("GROQ_API_KEY", "")

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def supports_tools(self) -> bool:
        return True

    def generate(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None) -> str:
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False
        }
        
        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error communicating with Groq API: {str(e)}"

    def execute_tool_call_loop(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], tool_registry, context=None) -> str:
        import requests
        import json
        
        if not self.api_key:
            return "Erreur : La clé GROQ_API_KEY n'est pas configurée dans l'environnement backend."
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        current_messages = messages.copy()
        max_iterations = 5
        
        for _ in range(max_iterations):
            payload = {
                "model": self.model_name,
                "messages": current_messages,
                "stream": False
            }
            if tools:
                payload["tools"] = tools
                # Groq specific requirement sometimes for tools
                payload["tool_choice"] = "auto"

            try:
                response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                return f"Error communicating with Groq API: {str(e)}"

            message = data["choices"][0].get("message", {})
            tool_calls = message.get("tool_calls")

            if not tool_calls:
                # No more tools to call, return the final response
                return message.get("content", "")

            # Add the assistant's message with tool calls to the history
            current_messages.append(message)

            # Execute all requested tools
            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                # Groq returns arguments as a stringified JSON
                arguments_str = tool_call["function"]["arguments"]
                try:
                    arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
                except json.JSONDecodeError:
                    arguments = {}
                
                try:
                    if context:
                        tool_result = tool_registry.execute_tool(function_name, arguments, context)
                    else:
                        tool_result = f"Error: No context provided for tool {function_name}"
                except Exception as e:
                    tool_result = f"Error executing tool: {str(e)}"

                # Add the tool response to messages
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", "call_1"),
                    "name": function_name,
                    "content": json.dumps(tool_result)
                })
        
        return "Agentic loop exceeded max iterations without a final answer."

