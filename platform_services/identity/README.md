# Alliance Identity (Platform Service)

## Rôle
**Alliance ID** est le produit gérant l'identité et les habilitations au sein de l'écosystème Alliance One. C'est l'équivalent interne de "Google Account" ou "Microsoft Entra ID".

## Responsabilités
- **Authentification Globale (SSO) :** Vérification des identités (JWT, Sessions).
- **Modèles Universels d'Identité :** Gestion de la classe mère `Person` et des utilisateurs (`User`).
- **Gestion des Organisations (Tenants) :** Modélisation des espaces de travail (`Organization`, `Workspace`).
- **Gestion des Habilitations :** `Role`, `Membership`, et moteur de règles avancées (Policy Engine pour RBAC et ABAC).
- **Gestion des Équipes :** `Team`.

## Dépendances
- **Autorisées :** `Kernel`.
- **Interdites :** Autres `Platform Services` (sauf abstraction stricte) et tout `Business Module` (Education, Fashion, etc.). Alliance ID ne sait pas qu'il existe un module "Santé" ou "Couture".

## Événements Émis
- `UserCreated`, `UserAuthenticated`, `OrganizationCreated`, `RoleAssigned`, `PermissionDenied`

## Philosophie
Aucun module métier ne gère ses propres utilisateurs ou ses propres mots de passe. Lorsqu'un module a besoin de restreindre un accès, il demande au Policy Engine d'Alliance ID.
```python
from platform.identity.policy import PolicyEngine

if not PolicyEngine.can(user, 'read', invoice):
    raise PermissionDenied()
```
