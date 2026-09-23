# Bootstrap Specification

Generated: 2026-09-23T08:53:32

## Input status

[
  {
    "file": "game_brief.md",
    "status": "LOADED",
    "characters": 1235
  },
  {
    "file": "canon_initial.md",
    "status": "LOADED",
    "characters": 1297
  },
  {
    "file": "constraints.md",
    "status": "LOADED",
    "characters": 1023
  },
  {
    "file": "open_decisions.md",
    "status": "LOADED",
    "characters": 589
  }
]

## Mandatory classification
Every fact must be classified as CANONICAL, DERIVED, PROPOSED or TO_VALIDATE. Creative unknowns must not be silently invented.

## Required integration proof
Every content type must pass import → schema → canon → graph → catalog → compiler → runtime fixture.

## Brief
# Brief exemple — Les Jardins de l’Écho

## Identité

Nom provisoire : Les Jardins de l’Écho
Genre : simulation agricole, exploration et narration
Perspective : jeu 2D vue du dessus
Plateforme : PC
Style général : contemplatif, mystérieux, chaleureux

## Prémisse

Le joueur est le dernier gardien d’un jardin construit autour d’un ancien puits de mémoire. Chaque culture fait remonter un fragment du passé de la vallée.

## Rôle du joueur

Cultiver, explorer les environs, aider les habitants et décider quels souvenirs doivent être conservés, transformés ou oubliés.

## Boucles principales

1. Explorer et trouver des graines ou des fragments.
2. Planter, arroser, faire pousser et récolter.
3. Transformer les récoltes et les fragments dans des machines.
4. Offrir, vendre ou utiliser les productions.
5. Modifier les relations et débloquer des lieux.

## Systèmes souhaités

- agriculture ;
- saisons ;
- météo ;
- exploration ;
- relations avec les PNJ ;
- artisanat ;
- cuisine ;
- économie simple ;
- refuge améliorable ;
- secrets ;
- événements contextuels.

## Contenu souhaité

Le nombre exact d’objets, de cultures, de PNJ et de quêtes doit être déduit par la pipeline à partir des systèmes et non inventé arbitrairement.


## Canon
# Canon initial — Les Jardins de l’Écho

## Faits immuables

- Le monde s’appelle Valdore.
- Le joueur est appelé le Jardinier.
- Le refuge principal s’appelle la Maison-Racine.
- Les souvenirs existent sous forme de fragments physiques.
- Les graines d’écho peuvent faire pousser des plantes mémorielles.
- Le jeu ne possède pas de magie de combat traditionnelle.

## Lieux connus

- La Maison-Racine : refuge et atelier principal.
- La Vallée Claire : zone de départ et terres cultivables.
- Le Bois des Retours : forêt où certains événements se répètent.
- Le Lac Muet : zone d’exploration et de pêche.

## Personnages connus

- Alba : soigneuse des plantes et première guide du joueur.
- Marin : artisan qui fabrique les machines agricoles.
- Nox : pêcheur qui refuse de parler de son passé.

## Objets canoniques

- Graine d’Écho.
- Houe de départ.
- Arrosoir de cuivre.
- Fragment de souvenir.
- Carnet du Jardinier.

## Règles de nommage

Les noms doivent être simples, évocateurs et cohérents avec un monde rural mystérieux. Éviter les noms de fantasy génériques, les objets cosmiques et les termes technologiques modernes.

## Éléments ouverts

- Les noms des saisons supplémentaires.
- Les recettes exactes.
- Les secrets du Bois des Retours.
- Le nombre final de cultures et de quêtes.


## Constraints
# Contraintes de production

## Technique

- Moteur cible : Godot 4.
- Jeu 2D vue du dessus.
- Tuiles logiques : 16 × 16 pixels.
- Rendu pixel art avec mise à l’échelle entière.
- Données exportables en JSON ou ressources Godot.

## Architecture

- Le canon est une source de vérité.
- Les entités sont reliées dans un graphe.
- Les objets sont générés depuis les systèmes et les chaînes d’utilisation.
- Les assets sont dérivés des entités et des actions.
- Les animations sont dérivées des états, actions, directions et contextes.
- Les maps doivent inclure terrain, placement, collisions, navigation et points d’intérêt.

## IA

- Le LLM est utilisé hors ligne pour concevoir, générer, vérifier et corriger.
- Le jeu final ne doit pas dépendre d’un LLM en permanence.
- Aucun prompt ne doit fonctionner sans contexte canonique.

## Qualité

- Aucun objet orphelin.
- Aucun asset non référencé.
- Aucune animation sans action ou état.
- Aucune quête impossible à atteindre.
- Toute sortie doit être validée avant import.


## Open decisions
# Décisions encore ouvertes

Ces points peuvent être proposés par l’IA sous forme de recommandations, mais ils doivent être signalés comme décisions ouvertes :

- nombre exact de biomes ;
- nombre exact de cultures ;
- nombre exact de PNJ ;
- nombre exact de recettes ;
- nombre exact de quêtes ;
- niveau de génération procédurale ;
- durée d’une journée ;
- nombre de saisons ;
- importance de la pêche ;
- présence ou non d’un système de combat.

L’IA peut choisir des valeurs techniques par défaut, mais ne doit pas transformer silencieusement une décision créative en fait canonique.


## Architecture contract
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


## First deliverables
Produce the architecture, ontology, schemas, canon registry, decision report, graph, catalogs, manifests, prompt templates, importers, validators, traceability matrix and end-to-end fixtures before mass content generation.
