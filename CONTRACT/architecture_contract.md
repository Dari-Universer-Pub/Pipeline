# Contrat d’architecture Graph-Driven V2

## Mission

Construire une pipeline de production autonome, documentée, testable et réutilisable pour un nouveau jeu. La pipeline produit les données, manifests, prompts, validateurs et compilateurs nécessaires. Elle ne produit pas le jeu final pendant cette phase.

## Entrées officielles

- `INPUT/game_brief.md` : direction, genre, prémisse et boucles.
- `INPUT/canon_initial.md` : source de vérité narrative et noms non négociables.
- `INPUT/constraints.md` : contraintes techniques, visuelles et runtime.
- `INPUT/open_decisions.md` : décisions créatives encore ouvertes.

Chaque information reçoit un statut : `CANONICAL`, `DERIVED`, `PROPOSED` ou `TO_VALIDATE`.

## Flux obligatoire

```text
Brief + Canon + Contraintes + Décisions ouvertes
    ↓
Analyse et rapport de contradictions
    ↓
Canon central verrouillé
    ↓
Ontologie et schémas
    ↓
Systèmes de gameplay
    ↓
Catalogue fonctionnel
    ↓
Graphe du monde
    ↓
Manifestes objets, maps, placement, assets, animations
    ↓
Prompts spécialisés contextualisés
    ↓
Génération externe par une autre IA
    ↓
Importation
    ↓
Validation
    ↓
Correction ou régénération ciblée
    ↓
Compilation runtime
```

## Obligations de contenu

Les quantités doivent être déduites des systèmes, chaînes de production, progression, canon, états, directions, variantes et contextes. Aucun objet, asset, animation, quête ou dialogue ne doit être créé sans fonction, relation et test.

Les maps doivent inclure structure, terrain, transitions, relief, collisions, navigation, placement, POI et secrets. Les assets doivent être générés par familles quand ils sont interdépendants. Les animations doivent être liées aux états, actions, directions et effets logiques.

## Intégration de bout en bout obligatoire

Un schéma, un validateur ou un fichier de catalogue ne prouve pas qu’une fonctionnalité est intégrée.

Pour chaque type de contenu, fournir une fixture réaliste traversant :

```text
entrée
→ importation
→ validation du schéma
→ validation du canon
→ validation du graphe
→ catalogue
→ état de pipeline
→ compilation
→ sortie runtime
→ vérification finale
```

Une fonctionnalité est incomplète si elle possède un schéma mais aucun import réel, un validateur mais aucun test d’intégration, un catalogue mais aucun chargement par le compilateur, ou un compilateur sans sortie runtime vérifiée.

## Statuts de maturité

Chaque entité doit pouvoir être suivie par :

`SPECIFIED → SCHEMA_VALIDATED → IMPORTED → CATALOGED → GRAPH_CONNECTED → COMPILED → RUNTIME_TESTED → PRODUCTION_READY`

Aucune entité ne peut être déclarée `PRODUCTION_READY` sans `RUNTIME_TESTED`.

## Tests obligatoires

Chaque domaine doit avoir :

- un test nominal ;
- un test de rejet ;
- un test de volume ;
- un test de donnée orpheline ;
- un test de reproductibilité ;
- un test d’intégration runtime.

Tester au minimum : objets, ressources, cultures, recettes, machines, PNJ, dialogues, quêtes, événements, créatures, boss, maps, placement, assets, animations et sauvegardes.

## Prompts spécialisés

Les prompts peuvent être individuels pour des éléments indépendants, par famille pour les éléments visuellement interdépendants et par séquence pour les animations. Aucun prompt ne doit être isolé : il reçoit le canon, l’ontologie, le graphe, le manifest, la fonction, les relations, dimensions, variantes, animations, placement, sortie attendue et validations.

Une information manquante provoque `BLOCKED`, jamais une invention silencieuse.

## Runtime

Le LLM intervient hors ligne pour concevoir, générer, corriger et valider. Le jeu final doit fonctionner sans LLM pour règles, déplacement, navigation, routines, dialogues compilés, quêtes, événements, animations, sauvegardes et progression.

## Reproductibilité et maintenance

Prévoir versionnement, migrations, graines procédurales, sorties déterministes, rapports, sauvegardes, reprise et matrice de traçabilité. Les sorties JSON doivent être stables octet par octet lorsque cela est possible.
