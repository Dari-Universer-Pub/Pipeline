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
