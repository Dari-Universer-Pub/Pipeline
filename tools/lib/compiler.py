"""Compilation des sorties pour le moteur de jeu (Godot 4).

Étape finale du flux : Canon -> ... -> Validation -> **Compilation moteur**.

Produit dans ENGINE_OUT/ un bundle de données DÉTERMINISTE et SANS LLM que le
jeu final charge à l'exécution :
- runtime_data.json : toutes les entités + relations + manifests ;
- dialogs_compiled.json : dialogues essentiels compilés en données conditionnelles ;
- rules_compiled.json : tables déterministes conditions/effets pour le moteur ;
- save_schema.json : schéma de sauvegarde + table de migration + versionnement ;
- godot/ : amorces minimales (autoload de chargement de données, SANS logique
  LLM) — la pipeline ne développe PAS le jeu, elle prépare ses données.

Contrat (constraints#IA) : le jeu final fonctionne sans LLM obligatoire ; un
LLM éventuel en runtime ne peut jamais modifier canon, progression, règles,
stats, sauvegardes, objets, quêtes majeures ni secrets non débloqués.
"""
from __future__ import annotations

from typing import Any

from .common import (
    DIRS, PIPELINE_VERSION, SCHEMA_VERSION, Status, make_id, write_json, write_text,
    versioned_envelope, unwrap, read_json, fingerprint, DEFAULT_SEED,
)

ROOT = DIRS["input"].parent
ENGINE_OUT = ROOT / "ENGINE_OUT"


def compile_dialogs(state: dict) -> list[dict]:
    """Compile les dialogues en données conditionnelles (sans LLM runtime).

    Chaque dialogue devient un arbre déterministe : conditions -> lignes ->
    choix -> effets. Le moteur évalue les conditions et applique les effets.
    """
    compiled = []
    npcs = {n["id"]: n for n in state["catalogs"].get("npcs", [])}
    dialogues = state["manifests"].get("dialogues", []) + state["catalogs"].get("dialogues", [])

    # Si aucun dialogue importé, générer des dialogues essentiels dérivés des
    # PNJ (salutation contextuelle) — toujours en données conditionnelles.
    if not dialogues:
        dialogues = _derive_essential_dialogs(npcs)

    for d in dialogues:
        spk = npcs.get(d.get("speaker_id"), {})
        compiled.append({
            "id": d.get("id"),
            "speaker_id": d.get("speaker_id"),
            "voice": spk.get("voice", ""),
            "priority": d.get("priority", 0),
            "conditions": d.get("conditions", []),
            "lines": d.get("lines", []),
            "knowledge_boundary": {
                "allowed": spk.get("knowledge", []),
                "forbidden": spk.get("forbidden_knowledge", []),
            },
        })
    return compiled


def _derive_essential_dialogs(npcs: dict) -> list[dict]:
    """Dialogues essentiels déterministes dérivés des PNJ (salutation + don)."""
    out = []
    for nid, n in npcs.items():
        out.append({
            "id": make_id("dialogue", f"{nid}_salutation"),
            "speaker_id": nid, "priority": 0,
            "conditions": [{"type": "location", "params": {"lieu_id": n.get("home") or ""}}],
            "lines": [{"text": f"Bonjour, Jardinier. ({n.get('function','habitant')})",
                       "reveals": [], "choices": []}],
        })
    return out


def compile_rules(state: dict) -> dict[str, Any]:
    """Tables déterministes conditions/effets pour le moteur (sans LLM)."""
    onto = state["ontology"]
    return {
        "deterministic": True,
        "llm_required_at_runtime": False,
        "condition_types": onto.get("condition_types", {}),
        "effect_types": onto.get("effect_types", {}),
        "event_trigger_types": onto.get("event_trigger_types", {}),
        "evaluation_contract": {
            "conditions": "évaluées en booléen depuis l'état du monde (voir simulator).",
            "effects": "appliqués de façon déterministe et réversible si marqué.",
            "no_free_mutation": "un LLM runtime éventuel ne peut PAS modifier canon, "
                                "progression, règles, stats, sauvegardes, objets, "
                                "quêtes majeures, secrets non débloqués.",
        },
    }


def compile_runtime_data(state: dict) -> dict[str, Any]:
    """Bundle runtime complet : entités + relations + manifests, versionné."""
    entities = {}
    for coll_name, coll in state["catalogs"].items():
        entities[coll_name] = coll
    return {
        "meta": {
            "game": "Les Jardins de l'Écho",
            "world": state["canon"].get("world", {}).get("display_name", "Valdore"),
            "engine": "Godot 4",
            "pipeline_version": PIPELINE_VERSION,
            "schema_version": SCHEMA_VERSION,
            "seed": DEFAULT_SEED,
            "llm_required_at_runtime": False,
            "deterministic": True,
            "tile_size": state["canon"].get("technical_constraints", {}).get("tile_size",
                                                                             {"w": 16, "h": 16}),
        },
        "canon_locked": state["canon"],
        "entities": entities,
        "relations": state["graph"].get("edges", []),
        "nodes": state["graph"].get("nodes", []),
        "assets_manifest": state["manifests"].get("assets", []),
        "animations_manifest": state["manifests"].get("animations", []),
        "maps_manifest": state["manifests"].get("maps", []),
        "placement_manifest": state["manifests"].get("placement", []),
        "navigation_manifest": state["manifests"].get("navigation", []),
        "transitions_manifest": state["manifests"].get("transitions", []),
        "effects_manifest": state["manifests"].get("effects", []),
        "fingerprint": fingerprint({"entities": sorted(
            e["id"] for coll in entities.values() for e in coll
            if isinstance(e, dict) and "id" in e)}),
    }


def compile_save_schema(state: dict) -> dict[str, Any]:
    """Schéma de sauvegarde + versionnement + table de migration."""
    return {
        "save_version": SCHEMA_VERSION,
        "schema": {
            "time": {"day": "int", "hour": "int", "season_index": "int",
                     "weather": "string"},
            "player": {"location": "string", "inventory": "{item_id:int}",
                       "money": "int", "relationships": "{pnj_id:int}",
                       "flags": "{flag_id:any}", "unlocked_locations": "[string]",
                       "known_facts": "[string]"},
            "world": {"discovered_secrets": "[string]", "active_quests": "[string]",
                      "completed_quests": "[string]", "crops": "{crop_id:obj}",
                      "global_flags": "{flag_id:any}"},
        },
        "compatibility": {
            "policy": "Une sauvegarde est compatible si save_version == version "
                      "courante OU si une migration existe.",
            "migrations": [
                {"from": "0.0.0", "to": SCHEMA_VERSION,
                 "changes": "Migration initiale : crée la structure de sauvegarde V5."},
            ],
        },
        "reproducibility": {
            "seed_stored": True,
            "note": "La graine procédurale est stockée pour régénérer les maps "
                    "de façon identique (reproductibilité).",
        },
        "llm_mutation_forbidden": ["canon", "progression", "rules", "stats",
                                   "saves", "objects", "major_quests",
                                   "unlocked_secrets"],
    }


def compile_godot_stubs(state: dict) -> dict[str, str]:
    """Amorces Godot minimales (chargement de données, SANS logique LLM).

    La pipeline ne développe PAS le jeu ; elle fournit de quoi charger les
    données compilées dans Godot 4 de façon déterministe.
    """
    autoload = '''# engine/autoload/pipeline_data.gd
# Amorce FOURNIE PAR LA PIPELINE (chargement de données, sans LLM runtime).
extends Node
## Charge le bundle runtime compilé par la pipeline. Le jeu final n'a pas
## besoin d'un LLM : toutes les règles/effets/dialogues sont des données.

const DATA_PATH := "res://engine/data/runtime_data.json"
const DIALOGS_PATH := "res://engine/data/dialogs_compiled.json"
const RULES_PATH := "res://engine/data/rules_compiled.json"

var runtime: Dictionary = {}
var dialogs: Array = []
var rules: Dictionary = {}

func _ready() -> void:
\truntime = _load_json(DATA_PATH)
\tdialogs = _load_json(DIALOGS_PATH)
\trules = _load_json(RULES_PATH)

func _load_json(path: String) -> Variant:
\tvar f := FileAccess.open(path, FileAccess.READ)
\tif f == null:
\t\tpush_error("PipelineData: fichier manquant " + path)
\t\treturn {}
\treturn JSON.parse_string(f.get_as_text())

func get_entity(kind: String, id: String) -> Dictionary:
\tfor e in runtime.get("entities", {}).get(kind, []):
\t\tif e.get("id") == id:
\t\t\treturn e
\treturn {}
'''
    project_cfg = '''; engine/project.godot (amorce fournie par la pipeline)
; Jeu 2D vue du dessus, Godot 4, pixel art échelle entière.
; Les données sont compilées par la pipeline (engine/data/*.json).
config_version=5

[application]
config/name="Les Jardins de l'Écho"
run/main_scene=""

[autoload]
PipelineData="*res://engine/autoload/pipeline_data.gd"

[display]
window/size/viewport_width=640
window/size/viewport_height=360
window/stretch/mode="viewport"
window/stretch/aspect="keep"

[rendering]
textures/canvas_textures/default_texture_filter=0
'''
    readme = '''# ENGINE_OUT — Sorties compilées pour le moteur (Godot 4)

Ces fichiers sont produits par la **pipeline**, pas par le jeu. Ils constituent
le bundle de données déterministe que le jeu final charge à l'exécution.

## Contenu
- `runtime_data.json` : entités, relations, manifests (canon verrouillé inclus).
- `dialogs_compiled.json` : dialogues essentiels en données conditionnelles.
- `rules_compiled.json` : tables conditions/effets pour un moteur déterministe.
- `save_schema.json` : schéma de sauvegarde, versionnement, migrations.
- `godot/` : amorces minimales de chargement (autoload + project.godot).

## Contrat sans LLM
Le jeu final **ne requiert aucun LLM** à l'exécution. Un LLM éventuel ne peut
jamais modifier : canon, progression, règles, statistiques, sauvegardes,
objets, quêtes majeures, secrets non débloqués.

## Important
La pipeline **ne développe pas le jeu**. Ces amorces montrent uniquement
comment charger les données compilées dans Godot 4. Le développement du jeu
(Vertical Slice, scènes, sprites finaux) est une étape ultérieure, hors du
périmètre de cette pipeline.
'''
    return {
        "godot/autoload/pipeline_data.gd": autoload,
        "godot/project.godot": project_cfg,
        "godot/README.md": readme,
    }


def run_stage(state: dict, write: bool = True) -> dict[str, Any]:
    runtime = compile_runtime_data(state)
    dialogs = compile_dialogs(state)
    rules = compile_rules(state)
    save_schema = compile_save_schema(state)
    stubs = compile_godot_stubs(state)

    if write:
        ENGINE_OUT.mkdir(parents=True, exist_ok=True)
        write_json(ENGINE_OUT / "runtime_data.json", runtime)
        write_json(ENGINE_OUT / "dialogs_compiled.json",
                   versioned_envelope(dialogs, kind="dialogs_compiled"))
        write_json(ENGINE_OUT / "rules_compiled.json",
                   versioned_envelope(rules, kind="rules_compiled"))
        write_json(ENGINE_OUT / "save_schema.json",
                   versioned_envelope(save_schema, kind="save_schema"))
        for rel, content in stubs.items():
            write_text(ENGINE_OUT / rel, content)

    return {
        "runtime_entities": sum(len(c) for c in runtime["entities"].values()),
        "relations": len(runtime["relations"]),
        "dialogs": len(dialogs),
        "assets": len(runtime["assets_manifest"]),
        "animations": len(runtime["animations_manifest"]),
        "llm_required_at_runtime": False,
        "fingerprint": runtime["fingerprint"],
    }


if __name__ == "__main__":
    from . import validator
    st = validator.load_state()
    print(run_stage(st))
