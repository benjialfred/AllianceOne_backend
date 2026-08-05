# Kernel

## Rôle
Le **Kernel** est le noyau dur d'Alliance One. Il s'agit d'une infrastructure pure, totalement agnostique du métier de l'entreprise. Le Kernel ne connaît ni les utilisateurs, ni les organisations, ni les factures. 

## Responsabilités
- **Configuration & Environnement** : Gestion des variables d'environnement et de la configuration racine.
- **Event Bus** : Le courtier de messages abstrait pour la publication et la souscription d'événements.
- **Feature Flags Engine** : Moteur de bascule dynamique des fonctionnalités.
- **Dependency Injection / Module Loader** : Chargement des composants et gestion du cycle de vie des modules.
- **Security Engine** : Chiffrement, hachage, et utilitaires cryptographiques.
- **Logging & Caching** : Abstractions autour de Redis et des journaux d'audit.

## Dépendances
- **Autorisées :** Librairies Python externes (ex: redis, celery).
- **Interdites :** `Platform Services` (Alliance ID, Cloud, etc.) et `Business Modules` (Education, Health, etc.). Le Kernel ne dépend de personne en interne.

## API & Utilisation
Le Kernel expose des abstractions utilisables par les autres couches :
```python
from kernel.events import EventBus

# Publication d'un événement agnostique
EventBus.publish(event)
```
