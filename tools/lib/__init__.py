"""Bibliothèque interne de la Pipeline V5 Graph-Driven (Les Jardins de l'Écho).

Modules :
- common     : utilitaires partagés (IDs, statuts, versionnement, graines).
- canon      : extraction et verrouillage du canon, rapports de décisions.
- ontology   : construction de l'ontologie et des schémas.
- systems    : catalogue des systèmes de gameplay.
- catalog    : catalogue fonctionnel + dérivation des quantités.
- graph      : graphe du monde, connectivité, profondeur causale.
- manifest   : manifests objets/assets/animations/maps/placement/etc.
- prompt     : templates, injection de contexte, génération par id/famille.
- importer   : import des résultats produits par une autre IA.
- validator  : validateurs structurels/logiques/narratifs/canoniques/etc.
- simulator  : simulateur abstrait de parties et de routines.
- report     : rapports de maturité, manquants, isolés, contradictions.
- compiler   : compilation des sorties pour le moteur (Godot 4).
"""
from . import common  # noqa: F401

__all__ = [
    "common",
]
