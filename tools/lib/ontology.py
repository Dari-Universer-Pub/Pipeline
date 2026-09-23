"""Ontologie et schémas de données de la Pipeline V5.

Étape 15-16 : construire l'ontologie (types d'entités, relations, états,
événements, conditions, effets) puis les schémas JSON qui en dérivent.

Principe : l'ontologie est la SOURCE des schémas. Les schémas JSON sont
générés depuis les définitions de champs de l'ontologie pour garantir
qu'ontologie et schémas ne divergent jamais.

Les schémas produits sont des documents JSON Schema draft-07标准, mais la
validation est faite par un interpréteur stdlib (validator.py) pour rester
autonome.
"""
from __future__ import annotations

from typing import Any

from .common import DIRS, SCHEMA_VERSION, write_json, versioned_envelope


# --- Types de champs réutilisables ------------------------------------------

def _id_field(prefix: str) -> dict:
    return {"type": "string", "pattern": f"^{prefix}_[a-z0-9_]+$",
            "description": f"Identifiant interne stable (préfixe '{prefix}_')."}


def _name_field() -> dict:
    return {"type": "string", "minLength": 1,
            "description": "Nom affiché (peut contenir accents/langue du jeu)."}


def _status_field() -> dict:
    return {"type": "string", "enum": ["CANONIQUE", "DEDUITE", "PROPOSEE", "A_VALIDER"],
            "description": "Statut de l'information."}


def _provenance() -> dict:
    return {
        "status": _status_field(),
        "source": {"type": "string", "description": "Fichier/section d'origine."},
        "justification": {"type": "string", "description": "Pourquoi cet élément existe."},
    }


# --- Ontologie : types d'entités --------------------------------------------

# Chaque type d'entité définit ses champs (nom -> spec JSON Schema).
ENTITY_TYPES: dict[str, dict[str, Any]] = {
    "monde": {
        "prefix": "monde", "label": "Monde",
        "fields": {"id": _id_field("monde"), "display_name": _name_field(), **_provenance()},
        "required": ["id", "display_name", "status"],
    },
    "lieu": {
        "prefix": "lieu", "label": "Lieu / zone",
        "fields": {
            "id": _id_field("lieu"), "display_name": _name_field(), **_provenance(),
            "kind": {"type": "string", "enum": ["carte", "region", "zone", "interet", "batiment", "secret"]},
            "map_id": {"type": ["string", "null"], "description": "Carte propriétaire si zone/POI."},
            "function": {"type": "string", "description": "Fonction gameplay du lieu."},
            "terrain": {"type": "array", "items": {"type": "string"}},
            "walkable": {"type": "boolean"},
        },
        "required": ["id", "display_name", "status", "function"],
    },
    "pnj": {
        "prefix": "pnj", "label": "PNJ / agent",
        "fields": {
            "id": _id_field("pnj"), "display_name": _name_field(), **_provenance(),
            "function": {"type": "string"},
            "goals": {"type": "array", "items": {"type": "string"}},
            "needs": {"type": "array", "items": {"type": "string"}},
            "beliefs": {"type": "array", "items": {"type": "string"}},
            "knowledge": {"type": "array", "items": {"type": "string"},
                          "description": "Faits connus (limite ce que le dialogue peut révéler)."},
            "forbidden_knowledge": {"type": "array", "items": {"type": "string"},
                                    "description": "Faits que le PNJ ignore/taise."},
            "emotions": {"type": "array", "items": {"type": "string"}},
            "routines": {"type": "array", "items": {"type": "object"}},
            "frequented_places": {"type": "array", "items": {"type": "string"}},
            "voice": {"type": "string", "description": "Signature de voix (validation narrative)."},
            "home": {"type": ["string", "null"]},
        },
        "required": ["id", "display_name", "status", "function"],
    },
    "creature": {
        "prefix": "creature", "label": "Créature / animal",
        "fields": {
            "id": _id_field("creature"), "display_name": _name_field(), **_provenance(),
            "kind": {"type": "string", "enum": ["animal", "creature", "boss"]},
            "behavior": {"type": "string"},
            "habitat": {"type": "array", "items": {"type": "string"}},
            "yields": {"type": "array", "items": {"type": "string"},
                       "description": "Ressources produites ( IDs objet/ressource)."},
            "hostile": {"type": "boolean"},
        },
        "required": ["id", "display_name", "status", "kind"],
    },
    "objet": {
        "prefix": "objet", "label": "Objet",
        "fields": {
            "id": _id_field("objet"), "display_name": _name_field(), **_provenance(),
            "category": {"type": "string",
                         "enum": ["outil", "graine", "ressource", "produit", "fragment",
                                  "consommable", "artisanat", "cle", "decoratif", "quotidien"]},
            "function": {"type": "string", "description": "Fonction de l'objet."},
            "gameplay_verb": {"type": "string", "description": "Verbe de gameplay associé."},
            "obtention": {"type": "array", "items": {"type": "string"},
                          "description": "Moyens d'obtention ( IDs recette/lieu/événement)."},
            "loop_stage": {"type": ["integer", "null"], "description": "Étape de la boucle (1-5)."},
            "users": {"type": "array", "items": {"type": "string"},
                      "description": "Entités qui consomment/utilisent cet objet."},
            "transforms_into": {"type": "array", "items": {"type": "string"}},
            "stackable": {"type": "boolean"},
            "base_value": {"type": ["number", "null"], "description": "Valeur économique de base."},
            "asset_id": {"type": ["string", "null"]},
            "animation_ids": {"type": "array", "items": {"type": "string"}},
            "decorative_only": {"type": "boolean"},
        },
        "required": ["id", "display_name", "status", "category", "function", "gameplay_verb"],
    },
    "ressource": {
        "prefix": "ressource", "label": "Ressource",
        "fields": {
            "id": _id_field("ressource"), "display_name": _name_field(), **_provenance(),
            "category": {"type": "string"},
            "producers": {"type": "array", "items": {"type": "string"}},
            "consumers": {"type": "array", "items": {"type": "string"}},
            "seasonal": {"type": "boolean"},
            "base_value": {"type": ["number", "null"]},
        },
        "required": ["id", "display_name", "status", "category"],
    },
    "culture": {
        "prefix": "culture", "label": "Culture / plante",
        "fields": {
            "id": _id_field("culture"), "display_name": _name_field(), **_provenance(),
            "seed_id": {"type": "string", "description": "ID graine requise."},
            "yield_id": {"type": "string", "description": "ID produit récolté."},
            "seasons": {"type": "array", "items": {"type": "string"}},
            "growth_days": {"type": "integer", "minimum": 1},
            "stages": {"type": "array", "items": {"type": "string"},
                       "description": "États de croissance (pour animations/assets)."},
            "water_needed": {"type": "boolean"},
            "memory_plant": {"type": "boolean",
                             "description": "True si fait remonter un fragment (canon)."},
            "regrows": {"type": "boolean"},
        },
        "required": ["id", "display_name", "status", "seed_id", "yield_id", "growth_days"],
    },
    "machine": {
        "prefix": "machine", "label": "Machine / station",
        "fields": {
            "id": _id_field("machine"), "display_name": _name_field(), **_provenance(),
            "function": {"type": "string"},
            "built_by": {"type": ["string", "null"], "description": "PNJ/artisan (canon: Marin)."},
            "inputs": {"type": "array", "items": {"type": "string"}},
            "outputs": {"type": "array", "items": {"type": "string"}},
            "recipe_ids": {"type": "array", "items": {"type": "string"}},
            "placement_id": {"type": ["string", "null"]},
            "animation_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "display_name", "status", "function"],
    },
    "recette": {
        "prefix": "recette", "label": "Recette / transformation",
        "fields": {
            "id": _id_field("recette"), "display_name": _name_field(), **_provenance(),
            "station_id": {"type": ["string", "null"], "description": "Machine requise."},
            "inputs": {"type": "array", "items": {"type": "object"},
                       "description": "Ingrédients {item_id, qty}."},
            "outputs": {"type": "array", "items": {"type": "object"},
                        "description": "Résultats {item_id, qty}."},
            "duration": {"type": ["number", "null"]},
            "unlocked_by": {"type": ["string", "null"]},
        },
        "required": ["id", "display_name", "status", "inputs", "outputs"],
    },
    "quete": {
        "prefix": "quete", "label": "Quête",
        "fields": {
            "id": _id_field("quete"), "display_name": _name_field(), **_provenance(),
            "giver_id": {"type": ["string", "null"]},
            "trigger": {"type": "object"},
            "preconditions": {"type": "array", "items": {"type": "object"}},
            "participants": {"type": "array", "items": {"type": "string"}},
            "location_id": {"type": ["string", "null"]},
            "steps": {"type": "array", "items": {"type": "object"}},
            "choices": {"type": "array", "items": {"type": "object"}},
            "effects": {"type": "array", "items": {"type": "object"}},
            "consequences": {"type": "array", "items": {"type": "string"}},
            "fallback": {"type": ["string", "null"]},
            "failure_conditions": {"type": "array", "items": {"type": "object"}},
            "missable": {"type": "boolean"},
            "discovery": {"type": ["string", "null"]},
        },
        "required": ["id", "display_name", "status", "trigger", "effects"],
    },
    "evenement": {
        "prefix": "evenement", "label": "Événement",
        "fields": {
            "id": _id_field("evenement"), "display_name": _name_field(), **_provenance(),
            "trigger": {"type": "object"},
            "preconditions": {"type": "array", "items": {"type": "object"}},
            "participants": {"type": "array", "items": {"type": "string"}},
            "location_id": {"type": ["string", "null"]},
            "timing": {"type": "object"},
            "effects": {"type": "array", "items": {"type": "object"}},
            "missable": {"type": "boolean"},
            "repeatable": {"type": "boolean"},
        },
        "required": ["id", "display_name", "status", "trigger", "effects"],
    },
    "dialogue": {
        "prefix": "dialogue", "label": "Dialogue contextuel",
        "fields": {
            "id": _id_field("dialogue"), "display_name": _name_field(), **_provenance(),
            "speaker_id": {"type": "string"},
            "conditions": {"type": "array", "items": {"type": "object"}},
            "lines": {"type": "array", "items": {"type": "object"}},
            "reveals": {"type": "array", "items": {"type": "string"},
                        "description": "Faits révélés (doivent être dans knowledge du PNJ)."},
            "priority": {"type": "integer"},
        },
        "required": ["id", "speaker_id", "conditions", "lines"],
    },
    "asset": {
        "prefix": "asset", "label": "Asset visuel",
        "fields": {
            "id": _id_field("asset"), "display_name": _name_field(), **_provenance(),
            "entity_id": {"type": "string", "description": "Entité rattachée (jamais isolé)."},
            "family": {"type": "string", "description": "Famille visuelle cohérente."},
            "function": {"type": "string"},
            "kind": {"type": "string",
                     "enum": ["sprite", "tileset", "tile", "transition", "objet", "portrait",
                              "particule", "ui", "icone"]},
            "width": {"type": "integer", "minimum": 1},
            "height": {"type": "integer", "minimum": 1},
            "resolution": {"type": "string"},
            "style": {"type": "string"},
            "palette": {"type": "array", "items": {"type": "string"}},
            "variants": {"type": "array", "items": {"type": "string"}},
            "usage_rules": {"type": "array", "items": {"type": "string"}},
            "fingerprint": {"type": "string", "description": "Empreinte unique (dédoublonnage)."},
            "validation": {"type": "object"},
        },
        "required": ["id", "display_name", "status", "entity_id", "family", "kind",
                     "width", "height"],
    },
    "animation": {
        "prefix": "anim", "label": "Animation",
        "fields": {
            "id": _id_field("anim"), "display_name": _name_field(), **_provenance(),
            "entity_id": {"type": "string"},
            "state_or_action": {"type": "string", "description": "État/action déclencheur."},
            "direction": {"type": ["string", "null"],
                            "enum": ["down", "up", "left", "right", None]},
            "frames": {"type": "integer", "minimum": 1},
            "fps": {"type": "number", "minimum": 1},
            "loop": {"type": "boolean"},
            "impact_event": {"type": ["integer", "string", "null"],
                             "description": "Frame d'impact (synchronisation gameplay) : entier (indice de frame) ou chaîne 'effet:<flag>'."},
            "logic_effect": {"type": ["string", "null"],
                             "description": "Effet logique déclenché ( ID effet)."},
            "transitions": {"type": "array", "items": {"type": "string"}},
            "required_assets": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "entity_id", "state_or_action", "frames", "fps", "loop"],
    },
    "map": {
        "prefix": "map", "label": "Carte",
        "fields": {
            "id": _id_field("map"), "display_name": _name_field(), **_provenance(),
            "size": {"type": "object", "description": "{w,h} en tuiles."},
            "regions": {"type": "array", "items": {"type": "object"}},
            "zones": {"type": "array", "items": {"type": "object"}},
            "paths": {"type": "array", "items": {"type": "object"}},
            "entrances": {"type": "array", "items": {"type": "object"}},
            "exits": {"type": "array", "items": {"type": "object"}},
            "collisions": {"type": "array", "items": {"type": "object"}},
            "height_levels": {"type": "array", "items": {"type": "integer"}},
            "terrains": {"type": "array", "items": {"type": "string"},
                         "description": "Noms de terrains présents (tilesets dérivés)."},
            "transitions": {"type": "array", "items": {"type": "object"}},
            "points_of_interest": {"type": "array", "items": {"type": "object"}},
            "buildings": {"type": "array", "items": {"type": "object"}},
            "secret_zones": {"type": "array", "items": {"type": "object"}},
            "resources": {"type": "array", "items": {"type": "object"}},
            "placement_rules": {"type": "array", "items": {"type": "object"}},
            "navigation_rules": {"type": "array", "items": {"type": "object"}},
            "spawn_rules": {"type": "array", "items": {"type": "object"}},
            "seasonal_conditions": {"type": "array", "items": {"type": "object"}},
            "linked_maps": {"type": "array", "items": {"type": "string"}},
            "seed": {"type": "integer", "description": "Graine procédurale (reproductibilité)."},
        },
        "required": ["id", "display_name", "status", "size", "terrains",
                     "placement_rules", "navigation_rules"],
    },
    "system": {
        "prefix": "system", "label": "Système de gameplay",
        "fields": {
            "id": _id_field("system"), "display_name": _name_field(), **_provenance(),
            "description": {"type": "string"},
            "depends_on": {"type": "array", "items": {"type": "string"}},
            "produces": {"type": "array", "items": {"type": "string"}},
            "consumes": {"type": "array", "items": {"type": "string"}},
            "verbs": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "display_name", "status", "description"],
    },
    "saison": {
        "prefix": "saison", "label": "Saison",
        "fields": {
            "id": _id_field("saison"), "display_name": _name_field(), **_provenance(),
            "order": {"type": "integer", "minimum": 1},
            "length_days": {"type": "integer", "minimum": 1},
            "weather_pool": {"type": "array", "items": {"type": "string"}},
            "growable": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "display_name", "status", "order"],
    },
}

# --- Ontologie : types de relations -----------------------------------------

# name -> {source, target, cardinality, meaning, implies_usage}
RELATION_TYPES: dict[str, dict[str, Any]] = {
    "contient": {"source": ["lieu", "map"], "target": ["lieu", "zone", "objet", "pnj", "creature"],
                 "cardinality": "1-n", "meaning": "Contenement spatial.",
                 "implies_usage": False},
    "produit": {"source": ["machine", "culture", "creature", "lieu"], "target": ["objet", "ressource"],
                "cardinality": "n-n", "meaning": "Production d'un objet/ressource.",
                "implies_usage": True},
    "consomme": {"source": ["recette", "machine", "quete"], "target": ["objet", "ressource"],
                 "cardinality": "n-n", "meaning": "Consommation d'un objet/ressource.",
                 "implies_usage": True},
    "transforme": {"source": ["recette"], "target": ["objet", "ressource"],
                   "cardinality": "n-n", "meaning": "Entrée transformée en sortie.",
                   "implies_usage": True},
    "requiert": {"source": ["quete", "recette", "culture", "evenement"],
                 "target": ["objet", "condition", "lieu", "pnj"],
                 "cardinality": "n-n", "meaning": "Prérequis.", "implies_usage": True},
    "declenche": {"source": ["evenement", "quete", "effet"], "target": ["effet", "quete", "evenement"],
                  "cardinality": "n-n", "meaning": "Déclenchement causal.", "implies_usage": True},
    "habite": {"source": ["pnj", "creature"], "target": ["lieu"],
               "cardinality": "n-1", "meaning": "Résidence.", "implies_usage": True},
    "frequente": {"source": ["pnj"], "target": ["lieu"],
                  "cardinality": "n-n", "meaning": "Lieu de routine.", "implies_usage": True},
    "donne": {"source": ["pnj"], "target": ["quete"],
              "cardinality": "1-n", "meaning": "Donneur de quête.", "implies_usage": True},
    "affecte": {"source": ["effet"], "target": ["objet", "pnj", "lieu", "quete", "system"],
                "cardinality": "n-n", "meaning": "Effet appliqué à une entité.", "implies_usage": True},
    "adjacent_a": {"source": ["terrain"], "target": ["terrain"],
                   "cardinality": "n-n", "meaning": "Adjacence de terrain (transitions).",
                   "implies_usage": False},
    "utilise": {"source": ["system"], "target": ["objet", "machine", "pnj", "lieu", "culture"],
                "cardinality": "n-n", "meaning": "Le système utilise l'entité.", "implies_usage": True},
    "obtenu_par": {"source": ["objet", "ressource"], "target": ["recette", "lieu", "evenement", "culture"],
                   "cardinality": "n-n", "meaning": "Moyen d'obtention.", "implies_usage": True},
    "evolue_vers": {"source": ["culture"], "target": ["culture"],
                    "cardinality": "1-n", "meaning": "Transition d'état de croissance.",
                    "implies_usage": False},
    "releve_de": {"source": ["objet", "culture", "machine", "recette", "pnj", "quete"],
                  "target": ["system"], "cardinality": "n-n",
                  "meaning": "Rattachement à un système de gameplay.", "implies_usage": True},
    "connecte_a": {"source": ["map", "lieu"], "target": ["map", "lieu"],
                   "cardinality": "n-n", "meaning": "Connexion de navigation entre cartes.",
                   "implies_usage": True},
    "decrit": {"source": ["fait"], "target": ["monde", "joueur", "lieu", "objet",
                                               "pnj", "system", "culture"],
               "cardinality": "n-n", "meaning": "Un fait canonique décrit une entité.",
               "implies_usage": False},
    "pousse_dans": {"source": ["culture"], "target": ["saison"],
                    "cardinality": "n-n", "meaning": "Saison de croissance d'une culture.",
                    "implies_usage": True},
}

# --- Ontologie : états du monde ---------------------------------------------

WORLD_STATE_SCHEMA: dict[str, Any] = {
    "time": {"day": "int>=1", "season": "saison_id", "weather": "weather_id",
             "hour": "0-23", "minute": "0-59"},
    "player": {"location": "lieu_id", "inventory": "{item_id: qty}",
               "relationships": "{pnj_id: 0-100}", "flags": "[flag_id]",
               "unlocked_locations": "[lieu_id]", "known_facts": "[fait_id]"},
    "world": {"discovered_secrets": "[secret_id]", "active_quests": "[quete_id]",
              "completed_quests": "[quete_id]", "global_flags": "[flag_id]",
              "crops_state": "{crop_instance: stage}", "machines_state": "{machine_id: state}"},
}

# --- Ontologie : types de conditions ----------------------------------------

CONDITION_TYPES: dict[str, dict[str, Any]] = {
    "flag": {"params": ["flag_id", "expected"], "desc": "État d'un drapeau monde."},
    "item_count": {"params": ["item_id", "op", "qty"], "desc": "Quantité d'un objet en inventaire."},
    "relationship": {"params": ["pnj_id", "op", "value"], "desc": "Niveau de relation."},
    "season": {"params": ["season_id"], "desc": "Saison courante."},
    "weather": {"params": ["weather_id"], "desc": "Météo courante."},
    "time_of_day": {"params": ["op", "hour"], "desc": "Heure de la journée."},
    "location": {"params": ["lieu_id"], "desc": "Joueur présent dans un lieu."},
    "quest_state": {"params": ["quete_id", "state"], "desc": "État d'une quête."},
    "fact_known": {"params": ["fait_id"], "desc": "Fait connu du joueur/PNJ."},
    "secret_discovered": {"params": ["secret_id"], "desc": "Secret découvert."},
    "crop_stage": {"params": ["crop_id", "op", "stage"], "desc": "Stade de croissance."},
    "and": {"params": ["conditions"], "desc": "Conjonction."},
    "or": {"params": ["conditions"], "desc": "Disjonction."},
    "not": {"params": ["condition"], "desc": "Négation."},
}

# --- Ontologie : types d'effets ---------------------------------------------

EFFECT_TYPES: dict[str, dict[str, Any]] = {
    "add_item": {"params": ["item_id", "qty"], "desc": "Ajoute un objet.", "reversible": True},
    "remove_item": {"params": ["item_id", "qty"], "desc": "Retire un objet.", "reversible": True},
    "set_flag": {"params": ["flag_id", "value"], "desc": "Positionne un drapeau.", "reversible": True},
    "change_relationship": {"params": ["pnj_id", "delta"], "desc": "Modifie une relation.", "reversible": True},
    "unlock_location": {"params": ["lieu_id"], "desc": "Débloque un lieu.", "reversible": False},
    "trigger_event": {"params": ["evenement_id"], "desc": "Déclenche un événement.", "reversible": False},
    "advance_quest": {"params": ["quete_id", "step"], "desc": "Fait avancer une quête.", "reversible": True},
    "reveal_fact": {"params": ["fait_id", "to"], "desc": "Révèle un fait (mémoire PNJ).", "reversible": False},
    "discover_secret": {"params": ["secret_id"], "desc": "Marque un secret découvert.", "reversible": False},
    "spawn_entity": {"params": ["entity_id", "lieu_id"], "desc": "Fait apparaître une entité.", "reversible": True},
    "transform_item": {"params": ["from_id", "to_id", "qty"], "desc": "Transforme un objet.", "reversible": True},
    "modify_economy": {"params": ["amount"], "desc": "Modifie la monnaie du joueur.", "reversible": True},
}

# --- Ontologie : types d'événements (déclencheurs) --------------------------

EVENT_TRIGGER_TYPES: dict[str, dict[str, Any]] = {
    "on_enter_location": {"params": ["lieu_id"]},
    "on_day_start": {"params": []},
    "on_season_change": {"params": ["season_id"]},
    "on_weather": {"params": ["weather_id"]},
    "on_item_acquired": {"params": ["item_id"]},
    "on_quest_complete": {"params": ["quete_id"]},
    "on_relationship_threshold": {"params": ["pnj_id", "value"]},
    "on_crop_harvest": {"params": ["culture_id"]},
    "on_time": {"params": ["hour", "minute"]},
    "on_secret_discovered": {"params": ["secret_id"]},
    "random_daily": {"params": ["probability"]},
}

# --- Météo (DEDUITE des saisons) --------------------------------------------

WEATHER_TYPES = ["ensoleille", "nuageux", "pluie", "orage", "vent", "brouillard", "neige"]


def build_ontology() -> dict[str, Any]:
    """Construit l'ontologie complète (artefact de référence)."""
    return {
        "entity_types": ENTITY_TYPES,
        "relation_types": RELATION_TYPES,
        "world_state_schema": WORLD_STATE_SCHEMA,
        "condition_types": CONDITION_TYPES,
        "effect_types": EFFECT_TYPES,
        "event_trigger_types": EVENT_TRIGGER_TYPES,
        "weather_types": WEATHER_TYPES,
        "naming_policy": {
            "internal_id": "minuscules, sans accents, sans espaces, [a-z0-9_], préfixe de catégorie.",
            "display_name": "accents et langue du jeu autorisés.",
            "world_tone": "rural mystérieux ; éviter fantasy générique, cosmique, tech moderne.",
        },
    }


# --- Génération des schémas JSON (draft-07) depuis l'ontologie --------------

def _schema_for_entity(key: str, spec: dict) -> dict:
    props = {}
    for fname, fspec in spec["fields"].items():
        props[fname] = fspec
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"https://pipeline.local/schemas/{key}.schema.json",
        "title": spec["label"],
        "description": f"Schéma d'entité '{key}' dérivé de l'ontologie V5.",
        "type": "object",
        "properties": props,
        "required": spec["required"],
        "additionalProperties": True,
    }


def build_schemas() -> dict[str, dict]:
    """Génère les schémas JSON depuis les types d'entités de l'ontologie."""
    schemas: dict[str, dict] = {}
    for key, spec in ENTITY_TYPES.items():
        schemas[key] = _schema_for_entity(key, spec)

    # Schéma de relation (générique, contraint par RELATION_TYPES au runtime).
    schemas["relation"] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://pipeline.local/schemas/relation.schema.json",
        "title": "Relation",
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string", "enum": sorted(RELATION_TYPES.keys())},
            "source": {"type": "string"},
            "target": {"type": "string"},
            "status": _status_field(),
            "weight": {"type": "number"},
            "metadata": {"type": "object"},
        },
        "required": ["type", "source", "target"],
        "additionalProperties": True,
    }

    # Schéma de condition.
    schemas["condition"] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://pipeline.local/schemas/condition.schema.json",
        "title": "Condition",
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": sorted(CONDITION_TYPES.keys())},
            "params": {"type": "object"},
        },
        "required": ["type"],
        "additionalProperties": True,
    }

    # Schéma d'effet.
    schemas["effect"] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://pipeline.local/schemas/effect.schema.json",
        "title": "Effet",
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": sorted(EFFECT_TYPES.keys())},
            "params": {"type": "object"},
        },
        "required": ["type"],
        "additionalProperties": True,
    }

    # Schéma d'état du monde.
    schemas["world_state"] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://pipeline.local/schemas/world_state.schema.json",
        "title": "État du monde",
        "type": "object",
        "properties": {
            "time": {"type": "object"},
            "player": {"type": "object"},
            "world": {"type": "object"},
        },
        "required": ["time", "player", "world"],
        "additionalProperties": True,
    }

    # Schéma de règle de placement (contrat V2 : domaine 'placement' testable
    # de bout en bout). Dérivé de la structure réelle du manifest_placement.
    schemas["placement_rule"] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://pipeline.local/schemas/placement_rule.schema.json",
        "title": "Règle de placement",
        "type": "object",
        "properties": {
            "id": {"type": "string", "pattern": "^placement_[a-z0-9_]+$",
                   "description": "Identifiant interne stable (préfixe 'placement_')."},
            "display_name": {"type": "string", "minLength": 1},
            "status": _status_field(),
            "places": {"type": "string", "minLength": 1,
                       "description": "Type/entité placée (culture, machine, ...)."},
            "allowed_terrain": {"type": "array", "items": {"type": "string"}},
            "forbidden_terrain": {"type": "array", "items": {"type": "string"}},
            "min_distance": {"type": "integer", "minimum": 0},
            "density": {"type": "string"},
            "clustering": {"type": "string"},
            "season": {"type": "string"},
            "weather": {"type": "string"},
            "accessibility": {"type": "string"},
            "poi_relation": {"type": "string"},
            "discovery_conditions": {"type": "string"},
            "source": {"type": "string"},
            "justification": {"type": "string"},
            "validation": {"type": "object"},
        },
        "required": ["id", "status", "places", "allowed_terrain",
                     "forbidden_terrain", "min_distance"],
        "additionalProperties": True,
    }

    return schemas


def run_stage(write: bool = True) -> dict[str, Any]:
    """Écrit l'ontologie et tous les schémas. Retourne les artefacts."""
    ontology = build_ontology()
    schemas = build_schemas()

    if write:
        write_json(DIRS["ontology"] / "ontology.json",
                   versioned_envelope(ontology, kind="ontology"))
        for name, sch in schemas.items():
            sch = dict(sch)
            sch["x_schema_version"] = SCHEMA_VERSION
            write_json(DIRS["schemas"] / f"{name}.schema.json", sch)

    return {"ontology": ontology, "schemas": schemas}


if __name__ == "__main__":
    res = run_stage()
    print("types d'entités :", len(res["ontology"]["entity_types"]))
    print("types de relations :", len(res["ontology"]["relation_types"]))
    print("schémas générés :", len(res["schemas"]))
