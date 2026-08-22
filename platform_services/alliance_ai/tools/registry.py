from typing import Dict, List, Any
from .definitions import AIToolDefinition, RiskLevel
from platform_services.alliance_ai.context.context_schema import AllianceAIContext

class ToolExecutionError(Exception):
    pass

class PermissionDeniedError(Exception):
    pass

class ToolRegistry:
    """
    Central registry where Bounded Contexts declare their capabilities.
    """
    _tools: Dict[str, AIToolDefinition] = {}

    @classmethod
    def register(cls, tool: AIToolDefinition) -> None:
        if tool.name in cls._tools:
            raise ValueError(f"Tool {tool.name} is already registered.")
        cls._tools[tool.name] = tool

    @classmethod
    def get_tool(cls, name: str) -> AIToolDefinition:
        if name not in cls._tools:
            raise ValueError(f"Tool {name} not found.")
        return cls._tools[name]

    @classmethod
    def get_all_tools_schema(cls, context: AllianceAIContext) -> List[Dict[str, Any]]:
        """
        Returns JSON schema representations of tools the user is actually allowed to execute.
        """
        allowed_tools = []
        for tool in cls._tools.values():
            # Filter tools by permissions
            if all(context.has_permission(p) for p in tool.required_permissions):
                allowed_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema
                    }
                })
        return allowed_tools

    @classmethod
    def execute_tool(cls, name: str, args: Dict[str, Any], context: AllianceAIContext) -> Any:
        """
        Executes a tool within the secure bounds of the context.
        """
        tool = cls.get_tool(name)
        
        # Security Check
        for perm in tool.required_permissions:
            if not context.has_permission(perm):
                raise PermissionDeniedError(f"User lacks permission {perm} to execute {tool.name}")
        
        # Risk Check (Gateway/Orchestrator should have handled approval if needed)
        # We just execute it here.
        try:
            return tool.handler(context, **args)
        except Exception as e:
            raise ToolExecutionError(f"Failed to execute {tool.name}: {str(e)}") from e
