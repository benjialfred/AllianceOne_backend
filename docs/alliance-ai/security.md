# Sécurité dans Alliance AI

La sécurité est le pilier central de l'intelligence d'Alliance One. Un modèle d'IA ne doit **jamais** permettre à un utilisateur d'accéder à des données qu'il ne pourrait pas voir via l'interface standard.

## 1. Le Contexte Fortifié (`AllianceAIContext`)

Au lieu de faire confiance au modèle pour "filtrer", nous filtrons au niveau de l'infrastructure. 
Avant d'arriver au LLM, la requête de l'utilisateur passe par le `ContextEngine` qui résout l'identité exacte de l'utilisateur.

Si l'utilisateur est un professeur du *Collège Bilingue Émergence*, l'organisation `org_123` est hardcodée dans le contexte.

## 2. Validation des Outils (Tool Level Security)

Les LLM ont tendance aux hallucinations et pourraient essayer d'appeler un outil avec de mauvais paramètres, ou d'appeler un outil non autorisé.

1. **Filtrage de schéma** : L'AgentOrchestrator ne fournit au LLM **que** les définitions JSON Schema des outils que l'utilisateur est autorisé à exécuter (via `context.has_permission()`).
2. **Double Validation** : Même si le LLM tente d'appeler l'outil `finance.get_revenue`, le `ToolRegistry.execute_tool` vérifie à nouveau les permissions avant l'exécution.

## 3. Le Moteur d'Approbation (Approval Engine)

Les actions ne sont pas égales.
Nous avons défini 4 niveaux de risque (`RiskLevel`) :

- **LOW** : Lecture simple. L'IA exécute immédiatement (ex: `education.search_students`).
- **MEDIUM** : Actions réversibles (Création de brouillons). L'IA exécute.
- **HIGH** / **CRITICAL** : Actions destructrices ou sensibles (Paiements, Suppressions).

Pour les niveaux HIGH/CRITICAL, ou si un outil a `requires_confirmation=True`, le moteur d'approbation interrompt l'agent, et retourne un état `APPROVAL_REQUIRED` au frontend. L'interface affiche alors une modale d'autorisation humaine.
L'IA ne peut reprendre l'exécution qu'avec le token d'approbation.
