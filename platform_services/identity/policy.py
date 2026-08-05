from typing import Any, List


class PolicyEngine:
    """
    Moteur de règles pour l'autorisation dans Alliance One (RBAC + ABAC).
    Aucune vue métier ne doit contenir de "if user.is_admin:".
    Toute vérification d'accès passe obligatoirement par PolicyEngine.can()
    """

    @classmethod
    def can(cls, user: Any, action: str, resource: Any = None) -> bool:
        """
        Vérifie si l'utilisateur peut effectuer une action sur une ressource.
        """
        if not user or not user.is_authenticated:
            return False

        # Si l'utilisateur est un super administrateur global du Kernel (rare)
        if getattr(user, 'is_superuser', False):
            return True

        # Recherche des politiques (Policies) applicables à la ressource
        policies = cls._get_policies_for_resource(resource)
        for policy in policies:
            if policy.check(user, action, resource):
                return True

        return False

    @classmethod
    def _get_policies_for_resource(cls, resource: Any) -> List[Any]:
        """
        Récupère les classes de Policy associées dynamiquement à la ressource.
        Pour ce prototype, retourne une liste vide.
        Les Bounded Contexts enregistreront leurs policies ici.
        """
        return []


class BasePolicy:
    """
    Classe de base que chaque module implémentera pour définir ses règles ABAC.
    """
    def check(self, user: Any, action: str, resource: Any) -> bool:
        raise NotImplementedError("Les policies doivent implémenter la méthode check().")
