from typing import Dict, Any, List
from platform_services.alliance_ai.tools.definitions import AIToolDefinition, RiskLevel
from platform_services.alliance_ai.tools.registry import ToolRegistry
from platform_services.alliance_ai.context.context_schema import AllianceAIContext

# Assuming we have a standard model in the Education Bounded Context
# from platform_services.education.students.models import Student

def handle_search_students(context: AllianceAIContext, **kwargs) -> Dict[str, Any]:
    """
    Business logic for searching students.
    Notice that the Context is passed, so we can filter securely by organization.
    """
    query = kwargs.get("query", "")
    
    # Secure Database Query simulation
    # students = Student.objects.filter(
    #     organization_id=context.organization_id, 
    #     name__icontains=query
    # )
    
    # Simulating data for V1 architecture proof
    mock_students = [
        {"id": "stu_01", "name": "Alice Dupont", "class": "6ème 3", "status": "Inscrit"},
        {"id": "stu_02", "name": "Bob Martin", "class": "6ème 3", "status": "Redoublant"},
    ]
    
    # Apply mock filter
    results = [s for s in mock_students if query.lower() in s["name"].lower() or query == ""]
    
    return {
        "status": "success",
        "data": results,
        "count": len(results),
        "source": "education.database"
    }

# -----------------------------------------------------------------------------
# Tool Definition
# -----------------------------------------------------------------------------

search_students_tool = AIToolDefinition(
    name="education.search_students",
    description="Recherche des élèves par nom ou statut dans l'organisation active.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Nom ou prénom de l'élève. Optionnel."
            }
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {"type": "array"},
            "count": {"type": "integer"}
        }
    },
    required_permissions=["education.student.read"],
    risk_level=RiskLevel.LOW,
    handler=handle_search_students
)

# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

def register_education_tools():
    """
    Called during Django app initialization (e.g., in apps.py ready() method)
    to declare the module's capabilities to Alliance AI.
    """
    ToolRegistry.register(search_students_tool)
