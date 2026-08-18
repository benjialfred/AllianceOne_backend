# Architecture Alliance AI V1

Alliance AI n'est pas un simple chatbot ajouté à l'interface, c'est le **moteur d'intelligence transverse** d'Alliance One. Il agit comme un chef d'orchestre intelligent capable de comprendre le contexte utilisateur, de s'interfacer avec les capacités de l'OS (Tools) et de générer des réponses utiles, tout en respectant strictement le système RBAC.

## Principes Fondamentaux

1.  **Isolation des Fournisseurs** : Aucun Bounded Context (Education, Finance, etc.) ne doit appeler directement l'API OpenAI, Gemini ou Claude. Ils passent toujours par `AllianceAIGateway`.
2.  **Transversalité** : Alliance AI est le seul composant capable d'analyser les données de tous les modules (s'il y est autorisé par l'utilisateur).
3.  **Permissions par Conception** : Le contexte d'exécution est construit avant tout appel à l'IA. Si un outil requiert `education.student.read`, et que le contexte ne l'a pas, le LLM ne pourra jamais exécuter cet outil.

## Flux de Données (Data Flow)

```text
USER REQUEST
      │
      ▼
[ AllianceAIGateway ]
      │  └─ Construit l'objet `AllianceAIContext` (Tenant, RBAC, Module actif) via `ContextEngine`
      ▼
[ AgentOrchestrator ]
      │  └─ Demande la liste des outils autorisés au `ToolRegistry`
      │  └─ Formate le Prompt Système avec le contexte.
      ▼
[ ModelRouter ]
      │  └─ Sélectionne le `LLMProvider` (ex: Gemini)
      ▼
[ Tool Execution Loop ]
      │  └─ Le LLM demande `education.search_students({"query": ""})`
      │  └─ L'ApprovalEngine vérifie le niveau de risque (LOW).
      │  └─ Le `ToolRegistry` exécute l'outil et renvoie les données.
      ▼
[ Response ]
```

## Intégration d'un Nouveau Module

Pour intégrer un nouveau Bounded Context à Alliance AI, il ne faut **pas** modifier le moteur IA.
Il suffit de créer un fichier `ai_tools.py` dans le Bounded Context et d'y enregistrer des outils via `ToolRegistry.register()`.

Voir `tool-registry.md` pour plus de détails.
