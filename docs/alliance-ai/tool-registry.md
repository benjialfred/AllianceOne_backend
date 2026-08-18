# Guide du Tool Registry

Le Tool Registry (`platform_services/alliance_ai/tools/registry.py`) est le contrat entre l'intelligence d'Alliance One (l'IA) et le noyau métier (les Bounded Contexts).

## Comment exposer une capacité à l'IA

Vous développez le module Inventory et souhaitez que l'IA puisse rechercher des produits.

**1. Créez un gestionnaire (Handler)**

```python
def handle_search_products(context: AllianceAIContext, **kwargs):
    query = kwargs.get("query", "")
    # Exécutez votre logique métier, en filtrant OBLIGATOIREMENT 
    # par context.organization_id pour respecter le multi-tenant.
    return {"data": [...]}
```

**2. Définissez l'outil (AIToolDefinition)**

```python
from platform_services.alliance_ai.tools.definitions import AIToolDefinition, RiskLevel

search_products_tool = AIToolDefinition(
    name="inventory.search_products",
    description="Recherche des produits dans le stock.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        }
    },
    output_schema={},
    required_permissions=["inventory.product.read"],
    risk_level=RiskLevel.LOW,
    handler=handle_search_products
)
```

**3. Enregistrez-le au démarrage de Django (ex: dans `apps.py`)**

```python
from platform_services.alliance_ai.tools.registry import ToolRegistry
ToolRegistry.register(search_products_tool)
```

Et voilà ! L'IA sait maintenant comment rechercher des produits.
