# Spécification initiale de pipeline

Générée le : 2026-09-22T21:45:48

Cette sortie est une spécification de fabrication. Elle ne constitue pas le jeu final.

## Statut des entrées

- brief : chargé
- canon : chargé
- contraintes : chargées
- décisions ouvertes : chargées
- contrat architectural : chargé

## Règles de travail

1. Ne jamais inventer silencieusement un élément canonique.
2. Déduire les quantités depuis les systèmes et les chaînes de gameplay.
3. Générer des prompts contextualisés à partir du graphe et des manifests.
4. Refuser les objets, assets, animations et quêtes orphelins.
5. Importer et valider chaque sortie externe.
6. Préparer un jeu fonctionnant sans LLM runtime.

## Modules à construire

- extraction du canon ;
- ontologie ;
- schémas ;
- catalogue fonctionnel ;
- graphe du monde ;
- manifestes ;
- placement de map ;
- assets par familles ;
- animations par états et actions ;
- prompts contextualisés ;
- importateur ;
- validateurs ;
- simulateur de partie ;
- compilateur moteur.

## Canon et contexte

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


## Contraintes

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


## Décisions ouvertes

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


## Contrat architectural

# Contrat d’architecture Graph-Driven

Construire une pipeline de production autonome, documentée et réutilisable, pas le jeu final.

Flux obligatoire :

```text
Brief + Canon + Contraintes
    ↓
Canon central verrouillé
    ↓
Ontologie
    ↓
Schémas
    ↓
Systèmes de gameplay
    ↓
Catalogue fonctionnel
    ↓
Graphe du monde
    ↓
Manifestes objets, maps, assets, animations
    ↓
Prompts spécialisés contextualisés
    ↓
Génération externe par une autre IA
    ↓
Importation
    ↓
Validation
    ↓
Correction ciblée
    ↓
Compilation pour le moteur
```

La pipeline doit calculer les quantités, noms, assets, variantes, animations, directions, états, transitions, placements et tests à partir du canon et des systèmes.

Elle doit produire des scripts, schémas, générateurs, templates, validateurs, rapports et documentation. Elle ne doit pas générer massivement le jeu à cette étape.

Le LLM ne doit pas être obligatoire pendant l’exécution finale du jeu.


## Première étape obligatoire

Produire d’abord l’arborescence, les schémas, l’ontologie, le graphe initial, les manifests et les rapports de décisions. Ne pas générer massivement le contenu final.
