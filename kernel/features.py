from typing import Any, Callable, Dict


class FeatureFlagEngine:
    """
    Moteur de Feature Flags.
    Permet d'activer, désactiver ou tester des fonctionnalités sans redéploiement.
    """

    _flags: Dict[str, bool] = {}
    _evaluators: Dict[str, Callable[[Any], bool]] = {}

    @classmethod
    def is_enabled(cls, feature_name: str, context: Any = None) -> bool:
        """
        Vérifie si une fonctionnalité est active.
        Peut évaluer le contexte (ex: utilisateur spécifique, tenant spécifique).
        """
        # Vérification globale
        if cls._flags.get(feature_name) is True:
            return True

        # Évaluation dynamique
        evaluator = cls._evaluators.get(feature_name)
        if evaluator and context:
            return evaluator(context)

        return False

    @classmethod
    def enable(cls, feature_name: str) -> None:
        cls._flags[feature_name] = True

    @classmethod
    def disable(cls, feature_name: str) -> None:
        cls._flags[feature_name] = False

    @classmethod
    def register_evaluator(cls, feature_name: str, evaluator: Callable[[Any], bool]) -> None:
        """
        Enregistre une règle d'évaluation complexe.
        Ex: return context.user.tenant.plan == 'Enterprise'
        """
        cls._evaluators[feature_name] = evaluator
