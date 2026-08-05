# ADR-0001: Architecture Core & Choix Technologiques

## Statut
Approuvé

## Contexte
Alliance One est un Operating System d'entreprise (ERP étendu) qui doit soutenir la croissance d'organisations sur 10 à 20 ans (100k orgs, 5M users). La plateforme doit être extrêmement stable, évolutive, et pouvoir accueillir un très grand nombre de modules (Bounded Contexts) développés par différentes équipes ou des tiers.

## Décisions

1. **Framework Backend : Django / DRF**
   - **Pourquoi :** Rapidité d'exécution, richesse de l'écosystème, ORM puissant, standard de fait pour 80% des applications d'origine. Les applications Node.js existantes seront réécrites pour uniformiser la stack.
   - **Impact :** Une seule convention, une seule manière d'authentifier et de tester.

2. **Topologie : Modular Monolith (Kernel / Platform / Modules)**
   - **Pourquoi :** Les microservices ajoutent une complexité d'infrastructure (Kubernetes, Tracing, API Gateway) non justifiée au jour 0. Un monolithe modulaire impose des frontières dures au sein d'un même dépôt, avec une possibilité d'extraction future si nécessaire.

3. **Base de données : PostgreSQL**
   - **Pourquoi :** Fiabilité transactionnelle, fonctionnalités JSONB, robustesse.
   - **Clés primaires :** Utilisation systématique d'**UUIDv4/ULID**. Indispensable pour l'architecture Offline-First et la fusion de données sans collision.

4. **Architecture Événementielle (Event-Driven)**
   - **Pourquoi :** Pour garantir l'isolation des modules. Le module A ne requête jamais la base du module B en synchrone.
   - **Implémentation :** Les événements du domaine sont définis en tant que classes Python pures (`class DomainEvent`), avant d'être expédiés via un broker (Redis / Celery ultérieurement).

5. **Sécurité et Permissions : Policy Engine (RBAC + ABAC)**
   - **Pourquoi :** Éviter les conditions dispersées dans le code (`if user.is_admin:`). Toute vérification d'accès passe par un Policy Engine formel.

6. **Frontend : React (Web & Native)**
   - **Pourquoi :** API-First approach. Le même backend sert le Web et le Mobile, garantissant la même logique métier et d'authentification.

## Conséquences
- Les développeurs doivent respecter la règle de dépendance stricte : `Kernel` <- `Platform` <- `Modules`. Jamais l'inverse.
- La CI/CD (Ruff, MyPy, Pytest) s'assure du respect de l'isolation et des standards dès le premier commit.
