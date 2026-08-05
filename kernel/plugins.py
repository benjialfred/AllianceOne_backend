import importlib
import logging
from typing import List

logger = logging.getLogger("kernel.plugins")


class PluginLoader:
    """
    Moteur de chargement de plugins.
    S'assure que les modules (Bounded Contexts) sont chargés dynamiquement 
    et qu'ils respectent les contrats de la plateforme (sans dépendance dure dans le Core).
    """

    _loaded_plugins: List[str] = []

    @classmethod
    def load_plugin(cls, module_name: str) -> None:
        """
        Charge un module Python de manière dynamique et initialise son point d'entrée.
        """
        if module_name in cls._loaded_plugins:
            return

        try:
            # Importation dynamique du module
            plugin_module = importlib.import_module(f"{module_name}.apps")

            # Recherche d'une méthode d'initialisation spécifique à Alliance One
            if hasattr(plugin_module, "initialize_plugin"):
                plugin_module.initialize_plugin()

            cls._loaded_plugins.append(module_name)
            logger.info(f"Plugin chargé avec succès: {module_name}")

        except ImportError as e:
            logger.error(f"Échec du chargement du plugin {module_name}: {str(e)}")
            raise

    @classmethod
    def get_loaded_plugins(cls) -> List[str]:
        return cls._loaded_plugins.copy()
