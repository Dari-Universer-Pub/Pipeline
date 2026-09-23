"""Aide de test : construit un état de pipeline complet en mémoire.

Permet aux tests d'être autonomes (sans dépendre de fichiers pré-écrits) et
de muter l'état pour les tests de DÉTECTION (orphelin, asset non référencé,
animation sans action, résultat invalide).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Rend `lib` importable depuis tests/.
_TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from lib import (  # noqa: E402
    canon as canon_mod, systems as systems_mod, catalog as catalog_mod,
    graph as graph_mod, manifest as manifest_mod, validator as validator_mod,
)


# Collections d'entités réelles (exclut quantity_plan / functional_catalog).
ENTITY_COLLECTIONS = ("seasons", "locations", "crops", "resources", "machines",
                      "recipes", "objects", "npcs", "creatures", "quests",
                      "events", "secrets", "maps")


def _clean_catalogs(cats: dict) -> dict:
    return {k: cats.get(k, []) for k in ENTITY_COLLECTIONS}


def build_state(*, with_graph: bool = True) -> dict:
    """Construit canon -> systèmes -> catalogues -> graphe -> manifests -> état."""
    ca = canon_mod.run_stage(write=False)
    sy = systems_mod.run_stage(write=False)["systems"]
    cats_full = catalog_mod.run_stage(ca, sy, write=False)
    cats = dict(cats_full)
    # state['catalogs'] ne contient QUE des listes d'entités (comme load_state).
    cats = _clean_catalogs(cats_full)
    if with_graph:
        gr = graph_mod.run_stage(cats, sy, ca["canon"], write=False)
        mf = manifest_mod.run_stage(cats, write=False)
        state = {
            "catalogs": cats,
            "manifests": mf["manifests"],
            "schemas": _load_schemas(),
            "graph": gr["graph"],
            "canon": ca["locked_canon"],
            "ontology": _load_ontology(),
            "connectivity": gr["connectivity"],
        }
        return state
    mf = manifest_mod.run_stage(cats, write=False)
    return {
        "catalogs": cats, "manifests": mf["manifests"], "schemas": _load_schemas(),
        "graph": {"nodes": [], "edges": []}, "canon": ca["locked_canon"],
        "ontology": _load_ontology(), "connectivity": {},
    }


def _load_schemas() -> dict:
    # Régénère les schémas en mémoire (déterministe).
    from lib import ontology as ontology_mod
    return ontology_mod.build_schemas()


def _load_ontology() -> dict:
    from lib import ontology as ontology_mod
    return ontology_mod.build_ontology()


def rebuild_connectivity(state: dict) -> dict:
    """Recalcule la connectivité d'un état (éventuellement muté)."""
    # Reconstruit un objet Graph depuis state['graph'].
    g = graph_mod.Graph()
    for n in state["graph"]["nodes"]:
        g.add_node(n["id"], n["type"], display_name=n.get("display_name", ""),
                   status=n.get("status", "PROPOSEE"))
    for e in state["graph"]["edges"]:
        g.add_edge(e["type"], e["source"], e["target"], status=e.get("status", "DEDUITE"),
                   implies_usage=e.get("implies_usage"))
    start = ["joueur_jardinier", "lieu_maison_racine"]
    return graph_mod.analyze_connectivity(g, start)
