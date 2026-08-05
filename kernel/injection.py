from typing import Any, Callable, Dict, Type, TypeVar

T = TypeVar("T")


class DependencyContainer:
    """
    Conteneur d'Injection de Dépendances (IoC).
    Garantit que les modules peuvent consommer des services sans connaître leur implémentation concrète.
    """

    _services: Dict[Type[Any], Any] = {}
    _factories: Dict[Type[Any], Callable[[], Any]] = {}

    @classmethod
    def register(cls, interface: Type[T], implementation: Any) -> None:
        """Enregistre un singleton (instance unique)."""
        cls._services[interface] = implementation

    @classmethod
    def register_factory(cls, interface: Type[T], factory: Callable[[], T]) -> None:
        """Enregistre une fabrique (crée une nouvelle instance à chaque appel)."""
        cls._factories[interface] = factory

    @classmethod
    def resolve(cls, interface: Type[T]) -> T:
        """
        Résout une dépendance.
        """
        if interface in cls._services:
            return cls._services[interface]

        if interface in cls._factories:
            return cls._factories[interface]()

        raise Exception(f"Aucune implémentation enregistrée pour l'interface {interface.__name__}")
