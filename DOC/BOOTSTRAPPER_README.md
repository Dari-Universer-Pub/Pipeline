# Bootstrapper de pipeline Graph-Driven

Ce dossier est un modèle réutilisable pour démarrer une pipeline de production IA pour un nouveau jeu.

## Utilisation

1. Remplacer ou modifier les quatre fichiers dans `INPUT/`.
2. Lire `CONTRACT/architecture_contract.md`.
3. Exécuter :

```bash
python tools/bootstrap_pipeline.py
```

Le script génère `OUTPUT/BOOTSTRAP_SPEC.md`, une spécification initiale de pipeline à transmettre à une autre IA.

Ce bootstrapper ne génère pas le jeu final et ne produit pas d'assets. Il prépare la pipeline : canon, ontologie, graphe, catalogues, manifests, prompts et validations.
