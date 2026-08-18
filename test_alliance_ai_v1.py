"""
End-to-End Test for Alliance AI V1 Architecture
Run with: python test_alliance_ai_v1.py
"""

import sys
import os
import django

# Add the project root to sys.path so we can import platform_services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django before importing anything else
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alliance_platform.settings")
django.setup()

from platform_services.alliance_ai.gateway.gateway import AllianceAIGateway
from platform_services.alliance_ai.tools.registry import ToolRegistry
from platform_services.education.ai_tools import register_education_tools

# -----------------------------------------------------------------------------
# 1. Setup Environment
# -----------------------------------------------------------------------------
print("[1/5] Registering Capabilities (Bounded Contexts)...")
register_education_tools()

# -----------------------------------------------------------------------------
# 2. Mocking Django User
# -----------------------------------------------------------------------------
class MockOrganization:
    id = "org_12345"
    name = "Collège & Lycée Émergence"

class MockUser:
    def __init__(self, is_super=False):
        self.id = "user_001"
        self.email = "admin@emergence.edu"
        self.is_superuser = is_super
        self.organization = MockOrganization()
        
    class _RolesManager:
        def all(self):
            class MockRole:
                name = "Director"
                class _PermManager:
                    def all(self):
                        class MockPerm:
                            code = "education.student.read"
                        return [MockPerm()]
                permissions = _PermManager()
            return [MockRole()]
    
    roles = _RolesManager()

user = MockUser(is_super=False)

# -----------------------------------------------------------------------------
# 3. Frontend Client Context
# -----------------------------------------------------------------------------
print("[2/5] Simulating Frontend Context...")
client_context = {
    "active_module": "education",
    "active_route": "/app/education/students",
    "academic_year": "2026-2027",
    "selected_object_id": None
}

# -----------------------------------------------------------------------------
# 4. The User Request
# -----------------------------------------------------------------------------
user_prompt = "Quels sont les redoublants ?"
print(f"[3/5] User asks: '{user_prompt}'")

# -----------------------------------------------------------------------------
# 5. Alliance AI Gateway Execution
# -----------------------------------------------------------------------------
print("[4/5] Passing request to Alliance AI Gateway...")
try:
    # This will trigger: Context Engine -> Orchestrator -> Model Router
    response = AllianceAIGateway.ask(user, user_prompt, client_context)
    print("\n[5/5] Gateway Response:")
    print("-" * 50)
    print("Status:", response["status"])
    print("Content:", response["content"])
    print("-" * 50)
    
    # Manually testing the tool registry execution just to prove isolation works
    print("\n[Security Audit] Validating Tool execution...")
    context = AllianceAIGateway.ask.__globals__['ContextEngine'].build_context(user, client_context)
    print("Constructed Context:", context.organization_name, "| Permissions:", context.permissions)
    
    # Let's manually trigger the tool with our secure context
    tool_result = ToolRegistry.execute_tool("education.search_students", {"query": ""}, context)
    print("Raw Tool Execution Result:", tool_result["data"])
    
except Exception as e:
    print("\n[ERROR]", str(e))
