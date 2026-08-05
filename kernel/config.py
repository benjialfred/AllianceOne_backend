import os
from typing import Any, Dict


class Configuration:
    """
    Gestionnaire de configuration agnostique pour Alliance One Kernel.
    Centralise l'accès aux variables d'environnement et paramètres globaux.
    """

    _config: Dict[str, Any] = {}

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        # Priorité : 1. En mémoire 2. Variable d'environnement 3. Défaut
        if key in cls._config:
            return cls._config[key]
        return os.getenv(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        cls._config[key] = value

    @classmethod
    def require(cls, key: str) -> str:
        val = cls.get(key)
        if val is None:
            raise ValueError(f"Configuration manquante: la clé {key} est requise.")
        return str(val)
