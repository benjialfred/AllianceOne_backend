from typing import Dict, Any
from platform_services.alliance_ai.tools.definitions import AIToolDefinition, RiskLevel
from platform_services.alliance_ai.tools.registry import ToolRegistry
from platform_services.alliance_ai.context.context_schema import AllianceAIContext

def handle_create_task(context: AllianceAIContext, **kwargs) -> Dict[str, Any]:
    """Mock for creating a task."""
    title = kwargs.get("title")
    description = kwargs.get("description", "")
    
    return {
        "status": "success",
        "data": {"task_id": "tsk_999", "title": title, "status": "TODO"},
        "source": "tasks.module"
    }

create_task_tool = AIToolDefinition(
    name="tasks.create_task",
    description="Crée une nouvelle tâche (to-do) pour l'organisation.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"}
        },
        "required": ["title"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {"type": "object"}
        }
    },
    required_permissions=["tasks.task.create"],
    risk_level=RiskLevel.LOW,
    handler=handle_create_task
)

def register_tasks_tools():
    ToolRegistry.register(create_task_tool)
