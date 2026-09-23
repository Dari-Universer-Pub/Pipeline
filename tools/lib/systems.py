"""Catalogue des systèmes de gameplay (étape 17).

Les systèmes sont DEDUITS du brief (section 'Systèmes souhaités') et du
canon (prémisse mémorielle). Chaque système déclare :
- ses dépendances ;
- ses verbes de gameplay ;
- les types d'entités qu'il utilise ;
- ce qu'il exige en contenu (qui pilote la dérivation des quantités).

Le champ 'requires' est la clé : il permet au module catalog de calculer
combien d'objets/cultures/machines/recettes/PNJ/quêtes sont nécessaires,
de façon justifiée plutôt qu'arbitraire.
"""
from __future__ import annotations

from typing import Any

from .common import DIRS, Status, make_id, write_json, versioned_envelope

SRC_BRIEF = "INPUT/game_brief.md#Systèmes souhaités"
SRC_CANON = "INPUT/canon_initial.md#Faits immuables"


def _system(name: str, desc: str, *, depends_on=None, verbs=None,
            entity_types=None, requires=None, produces=None, consumes=None,
            status=Status.DEDUITE, source=SRC_BRIEF) -> dict[str, Any]:
    return {
        "id": make_id("system", name),
        "display_name": name,
        "status": status,
        "source": source,
        "justification": f"Système requis par la boucle de gameplay / le brief.",
        "description": desc,
        "depends_on": [make_id("system", d) for d in (depends_on or [])],
        "verbs": verbs or [],
        "entity_types": entity_types or [],
        "requires": requires or [],
        "produces": produces or [],
        "consumes": consumes or [],
    }


def build_systems() -> list[dict[str, Any]]:
    """Construit le catalogue des systèmes de gameplay."""
    systems = [
        _system(
            "temps", "Gère le cycle jour/saison/météo. Socle temporel de tous "
            "les autres systèmes.",
            verbs=["attendre", "observer"],
            entity_types=["saison"],
            requires=[{"entity_type": "saison", "role": "cycle", "min": 1}],
            produces=["contexte_temporel"],
        ),
        _system(
            "meteo", "États météo dérivés des saisons, affecte la croissance et "
            "l'exploration.",
            depends_on=["temps"],
            verbs=["observer"],
            entity_types=["saison"],
            requires=[{"entity_type": "saison", "role": "weather_pool", "min": 1}],
        ),
        _system(
            "agriculture", "Planter, arroser, faire pousser, récolter. Cœur de la "
            "boucle principale ; chaque culture mémorielle fait remonter un fragment.",
            depends_on=["temps", "meteo"],
            verbs=["planter", "arroser", "recolter", "cultiver"],
            entity_types=["culture", "objet", "lieu"],
            requires=[
                {"entity_type": "culture", "role": "crop", "min": 1},
                {"entity_type": "objet", "role": "tool", "min": 2},  # houe + arrosoir (canon)
                {"entity_type": "objet", "role": "seed", "min": 1},
                {"entity_type": "lieu", "role": "farmland", "min": 1},
            ],
            produces=["objet:produit", "ressource"],
            consumes=["objet:graine"],
        ),
        _system(
            "memoire", "Système canonique : les souvenirs existent en fragments "
            "physiques ; les graines d'écho font pousser des plantes mémorielles.",
            depends_on=["agriculture"],
            verbs=["commemorer", "transformer", "oublier"],
            entity_types=["objet", "evenement", "pnj"],
            requires=[
                {"entity_type": "objet", "role": "fragment", "min": 1},
                {"entity_type": "culture", "role": "memory_plant", "min": 1},
            ],
            produces=["narration"],
            status=Status.DEDUITE, source=SRC_CANON,
        ),
        _system(
            "artisanat", "Fabriquer machines et objets via des recettes et des "
            "stations. Marin (canon) fabrique les machines agricoles.",
            depends_on=["agriculture"],
            verbs=["fabriquer", "ameliorer", "reparer"],
            entity_types=["machine", "recette", "objet", "ressource"],
            requires=[
                {"entity_type": "machine", "role": "station", "min": 1},
                {"entity_type": "recette", "role": "craft", "min": 1},
                {"entity_type": "ressource", "role": "material", "min": 1},
            ],
            produces=["objet:artisanat", "machine"],
            consumes=["ressource"],
        ),
        _system(
            "cuisine", "Transformer les récoltes en plats via des recettes de "
            "cuisine ; effets sur relations/énergie.",
            depends_on=["artisanat", "agriculture"],
            verbs=["cuisiner", "offrir"],
            entity_types=["recette", "machine", "objet"],
            requires=[
                {"entity_type": "machine", "role": "kitchen", "min": 1},
                {"entity_type": "recette", "role": "cook", "min": 1},
            ],
            produces=["objet:consommable"],
            consumes=["objet:produit"],
        ),
        _system(
            "exploration", "Explorer les environs, découvrir lieux, ressources et "
            "secrets. Nécessite des cartes navigables.",
            depends_on=["temps"],
            verbs=["explorer", "decouvrir", "voyager"],
            entity_types=["map", "lieu", "ressource", "objet"],
            requires=[
                {"entity_type": "map", "role": "explorable", "min": 1},
                {"entity_type": "lieu", "role": "poi", "min": 1},
            ],
            produces=["objet:graine", "objet:fragment", "ressource"],
        ),
        _system(
            "navigation", "Règles de déplacement, collisions, adjacences de "
            "terrain et transitions entre cartes.",
            depends_on=["exploration"],
            verbs=["marcher", "courir"],
            entity_types=["map", "lieu"],
            requires=[{"entity_type": "map", "role": "navigable", "min": 1}],
        ),
        _system(
            "relations", "Relations avec les PNJ, modifiées par dons, quêtes et "
            "événements ; débloquent des lieux et dialogues.",
            depends_on=["exploration"],
            verbs=["parler", "offrir", "aider"],
            entity_types=["pnj", "dialogue", "objet"],
            requires=[
                {"entity_type": "pnj", "role": "agent", "min": 1},
                {"entity_type": "dialogue", "role": "conversation", "min": 1},
            ],
            produces=["acces_lieu"],
        ),
        _system(
            "economie", "Économie simple : monnaie, prix, vente/achat, boucles "
            "d'argent. (Monnaie À_VALIDER : non définie dans le canon.)",
            depends_on=["artisanat", "relations"],
            verbs=["vendre", "acheter", "echanger"],
            entity_types=["objet", "pnj", "ressource"],
            requires=[
                {"entity_type": "objet", "role": "tradable", "min": 1},
                {"entity_type": "pnj", "role": "merchant", "min": 1},
            ],
            produces=["monnaie"],
        ),
        _system(
            "refuge", "Refuge améliorable : la Maison-Racine (canon), améliorée "
            "via recettes d'upgrade.",
            depends_on=["artisanat"],
            verbs=["ameliorer", "amenager"],
            entity_types=["lieu", "machine", "recette"],
            requires=[
                {"entity_type": "lieu", "role": "refuge", "min": 1},
                {"entity_type": "recette", "role": "upgrade", "min": 1},
            ],
        ),
        _system(
            "secrets", "Secrets et zones cachées découvrables ; le Bois des "
            "Retours (canon) contient des événements qui se répètent.",
            depends_on=["exploration", "memoire"],
            verbs=["decouvrir", "enqueter"],
            entity_types=["lieu", "evenement", "objet"],
            requires=[
                {"entity_type": "lieu", "role": "secret", "min": 1},
                {"entity_type": "evenement", "role": "discovery", "min": 1},
            ],
            produces=["objet:fragment"],
        ),
        _system(
            "evenements", "Événements contextuels déclenchés par le temps, le "
            "lieu, la météo, les relations ou les récoltes.",
            depends_on=["temps", "relations", "exploration"],
            verbs=["assister"],
            entity_types=["evenement", "quete"],
            requires=[{"entity_type": "evenement", "role": "contextual", "min": 1}],
        ),
        _system(
            "progression", "Quêtes, déblocages et avancement ; relie les systèmes "
            "entre eux et donne des conséquences durables.",
            depends_on=["relations", "evenements", "exploration"],
            verbs=["accomplir", "choisir"],
            entity_types=["quete", "evenement", "pnj", "lieu"],
            requires=[
                {"entity_type": "quete", "role": "quest", "min": 1},
            ],
            produces=["deblocage"],
        ),
        _system(
            "peche", "Pêche au Lac Muet (canon). Système mineur : existence "
            "DEDUITE du canon, ampleur À_VALIDER.",
            depends_on=["exploration"],
            verbs=["pecher"],
            entity_types=["objet", "creature", "lieu"],
            requires=[
                {"entity_type": "objet", "role": "fishing_tool", "min": 1},
                {"entity_type": "creature", "role": "fish", "min": 1},
                {"entity_type": "lieu", "role": "fishing_spot", "min": 1},
            ],
            produces=["objet:ressource"],
        ),
    ]
    return systems


def systems_by_id(systems: list[dict]) -> dict[str, dict]:
    return {s["id"]: s for s in systems}


def compute_system_requirements(systems: list[dict]) -> dict[str, int]:
    """Agrège les exigences minimales par (entity_type, role).

    Sert de plancher à la dérivation des quantités dans catalog.py : la
    quantité d'un type d'entité est au moins la somme des 'min' exigés par
    les systèmes qui l'utilisent pour un rôle donné.
    """
    req: dict[str, int] = {}
    for s in systems:
        for r in s["requires"]:
            key = f"{r['entity_type']}:{r['role']}"
            req[key] = max(req.get(key, 0), r.get("min", 1))
    return req


def run_stage(write: bool = True) -> dict[str, Any]:
    systems = build_systems()
    reqs = compute_system_requirements(systems)
    artifact = {
        "systems": systems,
        "requirements": reqs,
        "count": len(systems),
    }
    if write:
        write_json(DIRS["systems"] / "systems.json",
                   versioned_envelope(artifact, kind="systems_catalog"))
    return artifact


if __name__ == "__main__":
    res = run_stage()
    print("systèmes :", res["count"])
    for s in res["systems"]:
        print(" -", s["display_name"], "->", s["id"])
