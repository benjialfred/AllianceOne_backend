from typing import Dict, Any
from platform_services.alliance_ai.tools.definitions import AIToolDefinition, RiskLevel
from platform_services.alliance_ai.tools.registry import ToolRegistry
from platform_services.alliance_ai.context.context_schema import AllianceAIContext

def handle_update_stock(context: AllianceAIContext, **kwargs) -> Dict[str, Any]:
    """Mock for updating stock in the inventory."""
    product_id = kwargs.get("product_id")
    quantity = kwargs.get("quantity")
    
    return {
        "status": "success",
        "data": {"product_id": product_id, "new_quantity": quantity, "message": "Stock mis à jour."},
        "source": "inventory.module"
    }

update_stock_tool = AIToolDefinition(
    name="inventory.update_stock",
    description="Met à jour la quantité en stock pour un produit donné.",
    input_schema={
        "type": "object",
        "properties": {
            "product_id": {"type": "string"},
            "quantity": {"type": "integer"}
        },
        "required": ["product_id", "quantity"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "data": {"type": "object"}
        }
    },
    required_permissions=["inventory.stock.update"],
    risk_level=RiskLevel.MEDIUM,
    module_slug="inventory",
    handler=handle_update_stock
)

def register_inventory_tools():
    ToolRegistry.register(update_stock_tool)
