"""Génération de prompts spécialisés contextualisés (étapes 26-27, 50-55).

Principe fondamental (constraints#IA) : AUCUN prompt ne fonctionne sans
contexte canonique. Chaque prompt est construit automatiquement à partir de :
canon central, ontologie, graphe (relations entrantes/sortantes), manifest,
fiche fonctionnelle, contraintes visuelles, dimensions, variantes, animations,
règles de placement, critères de validation, dépendances, sortie attendue.

Modes de génération :
- par identifiant (generate_by_id) : un asset/objet/animation indépendant ;
- par famille (generate_by_family) : éléments visuellement interdépendants ;
- par séquence animée (generate_by_animation_sequence) : une action × directions.

Comportement en cas d'information manquante : BLOCKED (jamais d'invention).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import DIRS, Status, read_json, unwrap, write_text, make_id
from . import manifest as manifest_mod

_PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


# --- Chargement de l'état de la pipeline ------------------------------------

def load_state() -> dict[str, Any]:
    """Charge canon, ontologie, graphe, catalogues et manifests écrits."""
    catalogs = {}
    for name in ("objects", "resources", "crops", "machines", "recipes", "quests",
                 "npcs", "creatures", "locations", "seasons", "events", "secrets",
                 "maps"):
        catalogs[name] = unwrap(read_json(DIRS["catalogs"] / f"{name}.json", []))
    manifests = {}
    for name in ("objects", "assets", "animations", "maps", "placement",
                 "navigation", "transitions", "effects"):
        manifests[name] = unwrap(read_json(DIRS["manifests"] / f"manifest_{name}.json", []))
    graph = unwrap(read_json(DIRS["graph"] / "world_graph.json", {"nodes": [], "edges": []}))
    canon = unwrap(read_json(DIRS["canon"] / "canon_locked.json", {}))
    ontology = unwrap(read_json(DIRS["ontology"] / "ontology.json", {}))
    return {"catalogs": catalogs, "manifests": manifests, "graph": graph,
            "canon": canon, "ontology": ontology}


def _index(state: dict) -> dict[str, dict]:
    """Indexe toutes les entités (catalogues + manifests + nœuds) par ID."""
    idx: dict[str, dict] = {}
    for coll in state["catalogs"].values():
        for e in coll:
            if isinstance(e, dict) and "id" in e:
                idx[e["id"]] = e
    for coll in state["manifests"].values():
        for e in coll:
            if isinstance(e, dict) and "id" in e:
                idx.setdefault(e["id"], e)
    for n in state["graph"].get("nodes", []):
        idx.setdefault(n["id"], n)
    return idx


# --- Construction du contexte (injecteur) -----------------------------------

def _canon_context(canon: dict) -> str:
    if not canon:
        return "MANQUANT: canon central non chargé."
    lines = [
        f"- Monde : **{canon.get('world',{}).get('display_name','?')}** (canonique).",
        f"- Joueur : **{canon.get('player',{}).get('display_name','?')}** (canonique).",
        f"- Refuge : **{canon.get('refuge',{}).get('display_name','?')}** (canonique).",
        "- Faits immuables :",
    ]
    for f in canon.get("immutable_facts", []):
        lines.append(f"  - {f['statement']}")
    lines.append(f"- Règles de nommage : {canon.get('naming_rules','(non spécifiées)')}")
    lines.append("- Éléments INTERDITS : fantasy générique, objets cosmiques, "
                 "termes technologiques modernes, magie de combat traditionnelle.")
    return "\n".join(lines)


def _ontology_context(ontology: dict, entity_type: str | None) -> str:
    if not ontology:
        return "MANQUANT: ontologie non chargée."
    lines = []
    if entity_type and entity_type in ontology.get("entity_types", {}):
        et = ontology["entity_types"][entity_type]
        lines.append(f"- Type d'entité `{entity_type}` : champs requis = "
                     f"{', '.join(et.get('required', []))}.")
    lines.append("- Types de relations disponibles : "
                 + ", ".join(sorted(ontology.get("relation_types", {}).keys())))
    lines.append("- Types d'effets disponibles : "
                 + ", ".join(sorted(ontology.get("effect_types", {}).keys())))
    lines.append("- Types de conditions disponibles : "
                 + ", ".join(sorted(ontology.get("condition_types", {}).keys())))
    return "\n".join(lines)


def _relations(state: dict, entity_id: str) -> tuple[str, str]:
    incoming, outgoing = [], []
    for e in state["graph"].get("edges", []):
        if e["target"] == entity_id:
            incoming.append(f"  - `{e['source']}` —[{e['type']}]→ **{entity_id}**")
        if e["source"] == entity_id:
            outgoing.append(f"  - **{entity_id}** —[{e['type']}]→ `{e['target']}`")
    return ("\n".join(incoming) or "  - (aucune)",
            "\n".join(outgoing) or "  - (aucune)")


def _visual_constraints(entity: dict | None) -> str:
    return "\n".join([
        f"- Style : {manifest_mod.STYLE}",
        f"- Palette imposée : {', '.join(manifest_mod.PALETTE)}",
        f"- Résolution : {manifest_mod.RESOLUTION}",
        f"- Tuile logique : 16×16 px ; échelle entière obligatoire.",
        ("- Dimensions de l'entité : "
         f"{entity.get('width')}×{entity.get('height')} px."
         if entity and entity.get("width") else
         "- Dimensions : voir la fiche entité ci-dessus (ne pas inventer)."),
    ])


def _dependencies(idx: dict, entity: dict | None) -> str:
    """Liste les dépendances déjà produites à respecter."""
    if not entity:
        return "- (aucune dépendance identifiée)"
    deps = []
    for field in ("required_assets", "asset_id", "spritesheet_asset", "portrait_asset",
                  "seed_id", "yield_id", "station_id", "giver_id", "location_id"):
        v = entity.get(field)
        if isinstance(v, str) and v in idx:
            deps.append(f"- `{v}` ({idx[v].get('display_name', idx[v].get('type','?'))})")
        elif isinstance(v, list):
            for x in v:
                if x in idx:
                    deps.append(f"- `{x}` ({idx[x].get('display_name','?')})")
    for ing in entity.get("inputs", []) or []:
        iid = ing.get("item_id") if isinstance(ing, dict) else ing
        if iid in idx:
            deps.append(f"- `{iid}` ({idx[iid].get('display_name','?')})")
    return "\n".join(sorted(set(deps))) or "- (aucune dépendance identifiée)"


def build_context(state: dict, entity_id: str, task_type: str) -> dict[str, Any]:
    """Assemble le contexte complet injecté dans le prompt.

    Retourne un dict de variables + un champ '_blocked' si une information
    nécessaire manque (auquel cas le prompt sera BLOCKED, jamais inventé).
    """
    idx = _index(state)
    entity = idx.get(entity_id)
    missing = []
    if entity is None:
        missing.append(f"entité '{entity_id}' introuvable dans le graphe/catalogues")

    etype = entity.get("type") if entity else None
    incoming, outgoing = _relations(state, entity_id)

    # Vérifications spécifiques par type de tâche (anti-invention).
    if task_type == "asset" and entity:
        if not entity.get("width") or not entity.get("height"):
            missing.append("dimensions de l'asset non spécifiées")
        if not entity.get("entity_id") or entity.get("entity_id") not in idx:
            missing.append("entité propriétaire de l'asset non résolue")
    if task_type == "animation" and entity:
        if not entity.get("entity_id") or entity.get("entity_id") not in idx:
            missing.append("entité propriétaire de l'animation non résolue")
        if not entity.get("frames") or not entity.get("fps"):
            missing.append("frames/fps de l'animation non spécifiés")

    var = {
        "TASK_TYPE": task_type,
        "ENTITY_ID": entity_id,
        "ENTITY_NAME": (entity or {}).get("display_name", entity_id),
        "FAMILY": (entity or {}).get("family", ""),
        "ACTION": (entity or {}).get("state_or_action", ""),
        "DIRECTION": str((entity or {}).get("direction", "")),
        "SPEAKER_ID": (entity or {}).get("speaker_id", entity_id),
        "CANON_CONTEXT": _canon_context(state["canon"]),
        "ONTOLOGY_CONTEXT": _ontology_context(state["ontology"], etype),
        "ENTITY_CONTEXT": _json_block(entity) if entity else "MANQUANT: entité introuvable.",
        "INCOMING_RELATIONS": incoming,
        "OUTGOING_RELATIONS": outgoing,
        "VISUAL_CONSTRAINTS": _visual_constraints(entity),
        "DEPENDENCIES": _dependencies(idx, entity),
        "DIALOGUE_CONTEXT": _dialogue_context(idx, entity),
    }
    var["_blocked"] = missing
    var["_entity"] = entity
    return var


def _json_block(entity: dict | None) -> str:
    import json
    if entity is None:
        return "MANQUANT"
    # Retirer les champs internes lourds pour la lisibilité du prompt.
    light = {k: v for k, v in entity.items() if k not in ("derivation",)}
    return "```json\n" + json.dumps(light, ensure_ascii=False, indent=2) + "\n```"


def _dialogue_context(idx: dict, entity: dict | None) -> str:
    if not entity:
        return "MANQUANT: entité de dialogue introuvable."
    spk = idx.get(entity.get("speaker_id", ""), {})
    return "\n".join([
        f"- Locuteur : {spk.get('display_name','?')} ({entity.get('speaker_id')})",
        f"- Voix : {spk.get('voice','(non spécifiée)')}",
        f"- Connaissances (révélables) : {', '.join(spk.get('knowledge', [])) or '(aucune)'}",
        f"- Interdits (non révélables) : {', '.join(spk.get('forbidden_knowledge', [])) or '(aucun)'}",
        "- Contexte : lieu, heure, météo, événement récent, relation, objectifs.",
    ])


# --- Rendu -------------------------------------------------------------------

def load_template(name: str) -> str:
    header = (DIRS["prompt_templates"] / "_context_header.md").read_text(encoding="utf-8")
    footer = (DIRS["prompt_templates"] / "_task_footer.md").read_text(encoding="utf-8")
    body = (DIRS["prompt_templates"] / f"{name}.md").read_text(encoding="utf-8")
    body = body.replace("{{CONTEXT_HEADER}}", header)
    body = body.replace("{{TASK_FOOTER}}", footer)
    return body


def render(template_name: str, variables: dict[str, Any]) -> str:
    tpl = load_template(template_name)

    def repl(m):
        key = m.group(1)
        return str(variables.get(key, f"MANQUANT:{key}"))
    return _PLACEHOLDER.sub(repl, tpl)


_TEMPLATE_BY_TASK = {
    "objet": "prompt_object", "asset": "prompt_asset", "animation": "prompt_animation",
    "map": "prompt_map", "pnj": "prompt_npc", "dialogue": "prompt_dialogue",
    "quete": "prompt_quest", "recette": "prompt_recipe", "famille": "prompt_family",
    "ressource": "prompt_object", "culture": "prompt_object", "machine": "prompt_object",
    "creature": "prompt_npc", "evenement": "prompt_quest",
}


# --- Génération par identifiant ---------------------------------------------

def generate_by_id(state: dict, entity_id: str, task_type: str) -> dict[str, Any]:
    """Génère UN prompt contextualisé pour une entité et un type de tâche."""
    ctx = build_context(state, entity_id, task_type)
    if ctx["_blocked"]:
        return {"status": "BLOCKED", "entity_id": entity_id, "task_type": task_type,
                "reason": "; ".join(ctx["_blocked"]),
                "content": f"BLOCKED: {'; '.join(ctx['_blocked'])}"}
    tpl = _TEMPLATE_BY_TASK.get(task_type, "prompt_object")
    content = render(tpl, ctx)
    return {"status": "OK", "entity_id": entity_id, "task_type": task_type,
            "template": tpl, "content": content}


# --- Génération par famille --------------------------------------------------

def generate_by_family(state: dict, family: str) -> dict[str, Any]:
    """Génère UN prompt pour une famille visuelle interdépendante."""
    assets = [a for a in state["manifests"].get("assets", []) if a.get("family") == family]
    if not assets:
        return {"status": "BLOCKED", "family": family,
                "reason": f"aucun asset dans la famille '{family}'",
                "content": f"BLOCKED: famille '{family}' vide ou inexistante"}
    # Vérif cohérence : tous les assets doivent avoir des dimensions.
    missing = [a["id"] for a in assets if not a.get("width")]
    if missing:
        return {"status": "BLOCKED", "family": family,
                "reason": f"assets sans dimensions : {missing}",
                "content": f"BLOCKED: assets de '{family}' sans dimensions"}
    members = "\n".join(
        f"- `{a['id']}` ({a.get('display_name')}) — {a.get('width')}×{a.get('height')}, "
        f"variantes {a.get('variants')}" for a in assets)
    ctx = {
        "TASK_TYPE": "famille", "ENTITY_ID": family, "ENTITY_NAME": family,
        "FAMILY": family, "FAMILY_MEMBERS": members,
        "CANON_CONTEXT": _canon_context(state["canon"]),
        "ONTOLOGY_CONTEXT": _ontology_context(state["ontology"], "asset"),
        "ENTITY_CONTEXT": f"Famille `{family}` — {len(assets)} membres interdépendants.",
        "INCOMING_RELATIONS": "  - (famille transverse)",
        "OUTGOING_RELATIONS": "  - (famille transverse)",
        "VISUAL_CONSTRAINTS": _visual_constraints(None),
        "DEPENDENCIES": "- Tous les membres doivent partager palette/style/échelle.",
        "DIALOGUE_CONTEXT": "", "ACTION": "", "DIRECTION": "", "SPEAKER_ID": "",
    }
    content = render("prompt_family", ctx)
    return {"status": "OK", "family": family, "member_count": len(assets),
            "template": "prompt_family", "content": content}


# --- Génération par séquence animée -----------------------------------------

def generate_by_animation_sequence(state: dict, entity_id: str, action: str) -> dict[str, Any]:
    """Génère UN prompt pour une séquence animée (action × toutes directions)."""
    anims = [a for a in state["manifests"].get("animations", [])
             if a.get("entity_id") == entity_id and a.get("state_or_action") == action]
    if not anims:
        return {"status": "BLOCKED", "entity_id": entity_id, "action": action,
                "reason": f"aucune animation pour ({entity_id}, {action})",
                "content": f"BLOCKED: pas d'animation ({entity_id}, {action})"}
    missing = [a["id"] for a in anims if not a.get("frames") or not a.get("fps")]
    if missing:
        return {"status": "BLOCKED", "entity_id": entity_id, "action": action,
                "reason": f"animations incomplètes : {missing}",
                "content": f"BLOCKED: animations incomplètes pour ({entity_id}, {action})"}
    seq = "\n".join(
        f"- `{a['id']}` direction={a.get('direction')} frames={a.get('frames')} "
        f"fps={a.get('fps')} loop={a.get('loop')} impact={a.get('impact_event')} "
        f"effet={a.get('logic_effect')}" for a in anims)
    idx = _index(state)
    entity = idx.get(entity_id)
    ctx = {
        "TASK_TYPE": "animation", "ENTITY_ID": entity_id,
        "ENTITY_NAME": (entity or {}).get("display_name", entity_id),
        "ACTION": action, "DIRECTION": "toutes (séquence)",
        "FAMILY": "", "SPEAKER_ID": "",
        "CANON_CONTEXT": _canon_context(state["canon"]),
        "ONTOLOGY_CONTEXT": _ontology_context(state["ontology"], "animation"),
        "ENTITY_CONTEXT": f"Séquence `{action}` de `{entity_id}` — {len(anims)} animations :\n{seq}",
        "INCOMING_RELATIONS": _relations(state, entity_id)[0],
        "OUTGOING_RELATIONS": _relations(state, entity_id)[1],
        "VISUAL_CONSTRAINTS": _visual_constraints(entity),
        "DEPENDENCIES": _dependencies(idx, entity),
        "DIALOGUE_CONTEXT": "",
    }
    content = render("prompt_animation", ctx)
    return {"status": "OK", "entity_id": entity_id, "action": action,
            "animation_count": len(anims), "template": "prompt_animation",
            "content": content}


# --- Écriture des exemples ---------------------------------------------------

def write_prompt(path: Path, result: dict) -> Path:
    header = (f"<!-- statut: {result['status']} -->\n"
              f"<!-- généré par la Pipeline V5 (injecteur de contexte) -->\n\n")
    return write_text(path, header + result["content"])


def generate_examples(state: dict | None = None, write: bool = True) -> dict[str, Any]:
    """Génère un jeu d'exemples de prompts contextualisés (livrable 27)."""
    state = state or load_state()
    examples = {}

    # Par identifiant : un objet canonique, un asset, une map, un PNJ, une recette.
    by_id_targets = [
        ("objet_graine_d_echo", "objet"),
        ("asset_icone_objet_fragment_de_souvenir", "asset"),
        ("map_vallee_claire", "map"),
        ("pnj_alba", "pnj"),
        ("recette_soupe_de_navet", "recette"),
    ]
    for eid, task in by_id_targets:
        examples[f"by_id_{eid}"] = generate_by_id(state, eid, task)

    # Par famille : terrains (tileset) et personnages.
    for fam in ("famille_terrains", "famille_personnages"):
        examples[f"by_family_{fam}"] = generate_by_family(state, fam)

    # Par séquence animée : marche du joueur, actif d'une machine.
    examples["by_seq_joueur_marche"] = generate_by_animation_sequence(
        state, "joueur_jardinier", "marche")
    examples["by_seq_machine_actif"] = generate_by_animation_sequence(
        state, "machine_puits_de_memoire", "actif")

    # Démonstration BLOCKED : entité inexistante.
    examples["blocked_demo"] = generate_by_id(state, "objet_inexistant_xyz", "objet")

    if write:
        for name, res in examples.items():
            write_prompt(DIRS["prompt_examples"] / f"{name}.md", res)
    return examples


def run_stage(write: bool = True) -> dict[str, Any]:
    state = load_state()
    examples = generate_examples(state, write=write)
    ok = sum(1 for r in examples.values() if r["status"] == "OK")
    blocked = sum(1 for r in examples.values() if r["status"] == "BLOCKED")
    summary = {"total": len(examples), "ok": ok, "blocked": blocked,
               "names": sorted(examples.keys())}
    if write:
        from .common import versioned_envelope, write_json
        write_json(DIRS["prompt_generated"] / "index.json",
                   versioned_envelope(summary, kind="prompt_index"))
    return {"examples": examples, "summary": summary}


if __name__ == "__main__":
    res = run_stage()
    print("prompts d'exemple :", res["summary"])
