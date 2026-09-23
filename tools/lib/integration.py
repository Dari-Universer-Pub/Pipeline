"""Couche d'intégration de bout en bout (contrat V2).

Un schéma, un validateur ou un fichier de catalogue ne prouve pas qu'une
fonctionnalité est intégrée. Ce module exécute le PARCOURS RÉEL exigé par le
contrat V2 pour chaque domaine de contenu :

    entrée (fixture réaliste)
    → importation (importateur : schéma + canon + références du graphe)
    → validation (16 familles de validateurs sur l'état complet)
    → catalogue / manifest (intégration dans les collections)
    → graphe (reconstruction : nœuds, arêtes, connectivité)
    → état de pipeline (état complet cohérent)
    → compilation (runtime_data, dialogues, règles, schéma de sauvegarde)
    → sortie runtime (présence vérifiée dans le bundle compilé)
    → test runtime (le simulateur exécute la donnée compilée, SANS LLM)

Chaque parcours produit des PREUVES (pas des déclarations) : le statut de
maturité V2 (SPECIFIED → … → PRODUCTION_READY) est calculé depuis ces preuves
via `common.Maturity.from_evidence`.

Utilisé par : `tests/test_e2e_domains.py`, `lib/traceability.py`,
`tools/traceability.py` et l'étape 'traceability' de la pipeline.
"""
from __future__ import annotations

import contextlib
import copy
import json
import tempfile
from pathlib import Path
from typing import Any

from . import canon as canon_mod
from . import catalog as catalog_mod
from . import compiler as compiler_mod
from . import graph as graph_mod
from . import importer as importer_mod
from . import manifest as manifest_mod
from . import ontology as ontology_mod
from . import simulator as simulator_mod
from . import systems as systems_mod
from . import validator as validator_mod
from .common import Maturity, derive_seed, fingerprint

# Collections d'entités chargées dans l'état (comme validator.load_state).
ENTITY_COLLECTIONS = ("seasons", "locations", "crops", "resources", "machines",
                      "recipes", "objects", "npcs", "creatures", "quests",
                      "events", "secrets", "maps", "dialogues")

# Type d'entité -> collection catalogue (pour les preuves de graphe/placement).
TYPE_TO_COLLECTION = {
    "objet": "objects", "ressource": "resources", "culture": "crops",
    "machine": "machines", "recette": "recipes", "pnj": "npcs",
    "creature": "creatures", "quete": "quests", "evenement": "events",
    "map": "maps", "lieu": "locations", "saison": "seasons",
    "secret": "secrets", "dialogue": "dialogues",
}

# Les 16 domaines exigés par le contrat V2 (« Tests obligatoires »).
DOMAINS: dict[str, dict] = {
    "objets":      {"schema": "objet", "prefix": "objet", "kind": "catalog",
                    "collection": "objects", "node_type": "objet"},
    "ressources":  {"schema": "ressource", "prefix": "ressource", "kind": "catalog",
                    "collection": "resources", "node_type": "ressource"},
    "cultures":    {"schema": "culture", "prefix": "culture", "kind": "catalog",
                    "collection": "crops", "node_type": "culture"},
    "recettes":    {"schema": "recette", "prefix": "recette", "kind": "catalog",
                    "collection": "recipes", "node_type": "recette"},
    "machines":    {"schema": "machine", "prefix": "machine", "kind": "catalog",
                    "collection": "machines", "node_type": "machine"},
    "pnj":         {"schema": "pnj", "prefix": "pnj", "kind": "catalog",
                    "collection": "npcs", "node_type": "pnj"},
    "dialogues":   {"schema": "dialogue", "prefix": "dialogue", "kind": "catalog",
                    "collection": "dialogues", "node_type": None},
    "quetes":      {"schema": "quete", "prefix": "quete", "kind": "catalog",
                    "collection": "quests", "node_type": "quete"},
    "evenements":  {"schema": "evenement", "prefix": "evenement", "kind": "catalog",
                    "collection": "events", "node_type": "evenement"},
    "creatures":   {"schema": "creature", "prefix": "creature", "kind": "catalog",
                    "collection": "creatures", "node_type": "creature"},
    "boss":        {"schema": "creature", "prefix": "creature", "kind": "catalog",
                    "collection": "creatures", "node_type": "creature",
                    "marker": ("kind", "boss")},
    "maps":        {"schema": "map", "prefix": "map", "kind": "catalog",
                    "collection": "maps", "node_type": "map"},
    "placement":   {"schema": "placement_rule", "prefix": "placement",
                    "kind": "manifest", "collection": "placement",
                    "runtime_key": "placement_manifest"},
    "assets":      {"schema": "asset", "prefix": "asset", "kind": "manifest",
                    "collection": "assets", "runtime_key": "assets_manifest"},
    "animations":  {"schema": "animation", "prefix": "anim", "kind": "manifest",
                    "collection": "animations", "runtime_key": "animations_manifest"},
    "sauvegardes": {"schema": "world_state", "prefix": "sauvegarde",
                    "kind": "save", "collection": None},
}

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "e2e"


# =============================================================================
# ÉTAT DE BASE (pipeline en mémoire, sans écriture disque)
# =============================================================================

def base_state() -> dict[str, Any]:
    """Construit l'état de pipeline complet en mémoire (déterministe).

    Reproduit la chaîne canon -> systèmes -> catalogues -> graphe -> manifests
    sans rien écrire sur disque. Sert de socle aux parcours d'intégration.
    """
    ca = canon_mod.run_stage(write=False)
    sy = systems_mod.run_stage(write=False)["systems"]
    cats_full = catalog_mod.run_stage(ca, sy, write=False)
    cats = {k: list(cats_full.get(k, [])) for k in ENTITY_COLLECTIONS}
    gr = graph_mod.run_stage(cats, sy, ca["canon"], write=False)
    mf = manifest_mod.run_stage(cats, write=False)
    return {
        "catalogs": cats,
        "manifests": mf["manifests"],
        "schemas": ontology_mod.build_schemas(),
        "graph": gr["graph"],
        "canon": ca["locked_canon"],
        "ontology": ontology_mod.build_ontology(),
        "connectivity": gr["connectivity"],
        "_systems": sy,
        "_canon_artifacts": ca,
    }


def domain_of(obj: dict) -> str | None:
    """Résout le domaine V2 d'un objet importé (préfixe d'id + marqueurs)."""
    eid = str(obj.get("id", ""))
    # Cas particuliers d'abord.
    if eid.startswith("creature_") and obj.get("kind") == "boss":
        return "boss"
    for name, cfg in DOMAINS.items():
        if cfg.get("marker"):
            continue
        if eid.startswith(cfg["prefix"] + "_"):
            return name
    return None


# =============================================================================
# INTÉGRATION (catalogue / manifest) + RECONSTRUCTION (graphe, manifests)
# =============================================================================

def integrate(state: dict, objects: list[dict]) -> tuple[dict, list[dict]]:
    """Intègre des entités validées dans l'état (catalogue ou manifest).

    Retourne (nouvel_état, rapport_de_routage). Les entités manifestes
    (assets, animations, placement) sont des AJOUTS aux manifests dérivés :
    elles fusionnent par id après reconstruction (les manifests dérivés ne
    sont jamais écrasés silencieusement).
    """
    new = copy.deepcopy(state)
    new.setdefault("_extra_manifests", {})
    routing = []
    for obj in objects:
        dom = domain_of(obj)
        cfg = DOMAINS.get(dom or "", {})
        kind = cfg.get("kind")
        if kind == "catalog":
            coll = new["catalogs"].setdefault(cfg["collection"], [])
            _upsert(coll, obj)
        elif kind == "manifest":
            coll = new["_extra_manifests"].setdefault(cfg["collection"], [])
            _upsert(coll, obj)
        elif kind == "save":
            pass  # une sauvegarde n'est pas une entité de catalogue
        routing.append({"id": obj.get("id"), "domain": dom, "kind": kind,
                        "collection": cfg.get("collection"),
                        "routed": kind in ("catalog", "manifest", "save")})
    return new, routing


def _upsert(coll: list, obj: dict) -> None:
    for i, e in enumerate(coll):
        if isinstance(e, dict) and e.get("id") == obj.get("id"):
            coll[i] = obj
            return
    coll.append(obj)


def rebuild(state: dict) -> dict[str, Any]:
    """Reconstruit graphe + connectivité + manifests depuis les catalogues
    intégrés, puis fusionne les entités manifestes intégrées (par id)."""
    cats = state["catalogs"]
    gr = graph_mod.run_stage(cats, state["_systems"],
                             state["_canon_artifacts"]["canon"], write=False)
    mf = manifest_mod.run_stage(cats, write=False)
    manifests = mf["manifests"]
    for coll, extras in state.get("_extra_manifests", {}).items():
        target = manifests.setdefault(coll, [])
        for e in extras:
            _upsert(target, e)
    new = dict(state)
    new["graph"] = gr["graph"]
    new["connectivity"] = gr["connectivity"]
    new["manifests"] = manifests
    return new


def compile_all(state: dict) -> dict[str, Any]:
    """Compile l'état intégré : bundle runtime + dialogues + règles + saves."""
    return {
        "runtime": compiler_mod.compile_runtime_data(state),
        "dialogs": compiler_mod.compile_dialogs(state),
        "rules": compiler_mod.compile_rules(state),
        "save_schema": compiler_mod.compile_save_schema(state),
    }


# =============================================================================
# PREUVES : présence runtime, graphe, validation
# =============================================================================

def verify_in_runtime(compiled: dict, obj: dict, cfg: dict) -> dict[str, Any]:
    """Vérifie la présence RÉELLE de l'entité dans la sortie compilée."""
    oid = obj.get("id")
    runtime = compiled["runtime"]
    if cfg["kind"] == "catalog":
        # Collection résolue PAR ENTITÉ (lots mixtes : recette + objet, etc.).
        prefix = str(oid).split("_", 1)[0]
        if prefix == "placement":
            # Les règles de placement compilent dans le manifest de placement,
            # pas dans les collections d'entités ni les nœuds du graphe monde.
            entries = runtime.get("placement_manifest", [])
            return {"id": oid,
                    "in_runtime": any(isinstance(e, dict) and e.get("id") == oid
                                      for e in entries),
                    "in_nodes": True}
        coll_name = TYPE_TO_COLLECTION.get(prefix, cfg["collection"])
        coll = runtime["entities"].get(coll_name, [])
        in_entities = any(isinstance(e, dict) and e.get("id") == oid for e in coll)
        in_nodes = any(n.get("id") == oid for n in runtime.get("nodes", []))
        need_nodes = cfg.get("node_type") is not None
        return {"id": oid, "in_runtime": in_entities,
                "in_nodes": in_nodes or not need_nodes}
    if cfg["kind"] == "manifest":
        entries = runtime.get(cfg["runtime_key"], [])
        return {"id": oid, "in_runtime":
                any(isinstance(e, dict) and e.get("id") == oid for e in entries),
                "in_nodes": True}
    # sauvegardes : l'artefact compilé est le schéma de sauvegarde.
    return {"id": oid, "in_runtime": bool(compiled["save_schema"].get("schema")),
            "in_nodes": True}


def _all_ids(state: dict) -> set[str]:
    ids = {n["id"] for n in state["graph"].get("nodes", [])}
    for coll in state["catalogs"].values():
        for e in coll:
            if isinstance(e, dict) and "id" in e:
                ids.add(e["id"])
    return ids


def graph_evidence(cfg: dict, state: dict, objects: list[dict]) -> dict[str, Any]:
    """Preuve de connexion au graphe (ou de résolution des références)."""
    ids = _all_ids(state)
    conn = state.get("connectivity", {})
    fid = {o.get("id") for o in objects}
    ev: dict[str, Any] = {"ids": sorted(fid)}
    if cfg["kind"] == "save":
        sv = objects[0]
        pl = sv.get("player", {})
        checks = {
            "location": pl.get("location") in ids,
            "inventory": all(k in ids for k in (pl.get("inventory") or {})),
            "relationships": all(k in ids for k in (pl.get("relationships") or {})),
            "quests": all(q in ids for q in
                          (sv.get("world", {}).get("active_quests") or [])
                          + (sv.get("world", {}).get("completed_quests") or [])),
            "facts": all(f in ids for f in (pl.get("known_facts") or [])),
        }
        ev.update(checks)
        ev["ok"] = all(checks.values())
        return ev
    if cfg["kind"] == "manifest":
        if cfg["collection"] == "assets":
            ev["entity_refs"] = all(o.get("entity_id") in ids
                                    or str(o.get("entity_id", "")).startswith(("map_", "asset_"))
                                    for o in objects)
            ev["ok"] = ev["entity_refs"]
        elif cfg["collection"] == "animations":
            asset_ids = {a["id"] for a in state["manifests"].get("assets", [])}
            ev["entity_refs"] = all(o.get("entity_id") in ids for o in objects)
            ev["asset_refs"] = all(ra in asset_ids for o in objects
                                   for ra in o.get("required_assets", []) or [])
            ev["ok"] = ev["entity_refs"] and ev["asset_refs"]
        else:  # placement
            coll_ok = []
            for o in objects:
                coll = TYPE_TO_COLLECTION.get(o.get("places", ""))
                coll_ok.append(bool(coll) and len(state["catalogs"].get(coll, [])) > 0)
            ev["places_resolvable"] = coll_ok
            ev["ok"] = all(coll_ok) if coll_ok else False
        return ev
    # Catalogues.
    if cfg.get("node_type") is None:  # dialogues : références au graphe
        ok = True
        for o in objects:
            ok = ok and o.get("speaker_id") in ids
            for c in o.get("conditions", []) or []:
                lid = (c.get("params") or {}).get("lieu_id")
                if lid:
                    ok = ok and lid in ids
        ev["refs_resolved"] = ok
        ev["ok"] = ok
        return ev
    nodes = {n["id"] for n in state["graph"].get("nodes", [])}
    deg = {n: 0 for n in nodes}
    for e in state["graph"].get("edges", []):
        if e["source"] in deg:
            deg[e["source"]] += 1
        if e["target"] in deg:
            deg[e["target"]] += 1
    primaries = [o for o in objects
                 if str(o.get("id", "")).startswith(cfg["prefix"] + "_")
                 and not (cfg.get("marker") and o.get(cfg["marker"][0]) != cfg["marker"][1])]
    if cfg.get("marker"):
        primaries = [o for o in objects if o.get(cfg["marker"][0]) == cfg["marker"][1]]
    ev["in_nodes"] = all(o["id"] in nodes for o in primaries)
    ev["connected"] = all(deg.get(o["id"], 0) >= 1 for o in primaries)
    ev["no_orphan"] = not (fid & set(conn.get("orphans", [])))
    ev["no_unreachable"] = not (fid & set(conn.get("unreachable", [])))
    ev["no_dangling"] = not any(o["id"] in str(d) for d in conn.get("dangling_references", [])
                                for o in objects)
    ev["ok"] = all([ev["in_nodes"], ev["connected"], ev["no_orphan"],
                    ev["no_unreachable"], ev["no_dangling"]])
    return ev


# =============================================================================
# TESTS RUNTIME PAR DOMAINE (le simulateur exécute la donnée COMPILÉE)
# =============================================================================

def runtime_probe(domain: str, compiled: dict, fixture: dict) -> dict[str, Any]:
    """Test d'intégration runtime réel du domaine, sur données compilées."""
    cats = simulator_mod.from_runtime(compiled["runtime"])
    w = simulator_mod.initial_state(cats)
    sim = simulator_mod
    primary = fixture["entities"][0]
    pid = primary["id"]
    byid = lambda coll: {e["id"]: e for e in cats.get(coll, [])}  # noqa: E731
    det: dict[str, Any] = {"domain": domain, "entity": pid}

    if domain == "objets":
        added = sim.apply_effect(w, {"type": "add_item", "params": {"item_id": pid, "qty": 1}})
        money0 = w["player"]["money"]
        sold = sim.action_sell(w, pid, int(primary.get("base_value") or 1), 1)
        det.update(inventory=w["player"]["inventory"].get(pid, 0) + (1 if sold else 0),
                   money_gain=w["player"]["money"] - money0)
        det["ok"] = added and sold and w["player"]["money"] > money0

    elif domain == "ressources":
        rec = next((r for r in cats.get("recipes", [])
                    if any(i["item_id"] == pid for i in r.get("inputs", []))), None)
        det["real_consumer"] = rec["id"] if rec else None
        if rec:
            for ing in rec["inputs"]:
                sim.apply_effect(w, {"type": "add_item",
                                     "params": {"item_id": ing["item_id"],
                                                "qty": ing.get("qty", 1)}})
            crafted = sim.action_craft(w, rec)
            outs = all(w["player"]["inventory"].get(o["item_id"], 0) >= o.get("qty", 1)
                       for o in rec["outputs"])
            det["ok"] = crafted and outs
        else:
            det["ok"] = False

    elif domain == "cultures":
        crop = byid("crops")[pid]
        seed = crop["seed_id"]
        sim.apply_effect(w, {"type": "add_item", "params": {"item_id": seed, "qty": 1}})
        planted = sim.action_plant(w, seed, crop)
        sim.action_water(w, pid)
        days = 0
        inst = w["world"]["crops"].get(pid)
        while inst and inst["stage"] < inst["max_stage"] and days < 60:
            sim.advance_day(w, cats)
            inst = w["world"]["crops"].get(pid)
            days += 1
        harvested = sim.action_harvest(w, pid)
        det.update(planted=planted, days_to_mature=days, harvested=harvested,
                   yield_qty=w["player"]["inventory"].get(crop["yield_id"], 0))
        det["ok"] = planted and harvested and det["yield_qty"] >= 1

    elif domain == "recettes":
        rec = byid("recipes")[pid]
        for ing in rec["inputs"]:
            sim.apply_effect(w, {"type": "add_item",
                                 "params": {"item_id": ing["item_id"], "qty": ing.get("qty", 1)}})
        crafted = sim.action_craft(w, rec)
        outs = all(w["player"]["inventory"].get(o["item_id"], 0) >= o.get("qty", 1)
                   for o in rec["outputs"])
        station_ok = (not rec.get("station_id")) or rec["station_id"] in byid("machines")
        det.update(crafted=crafted, outputs=outs, station_ok=station_ok)
        det["ok"] = crafted and outs and station_ok

    elif domain == "machines":
        mach = byid("machines")[pid]
        rec = next((r for r in cats.get("recipes", []) if r.get("station_id") == pid), None)
        det["station_of"] = rec["id"] if rec else None
        placement_ok = (not mach.get("placement_id")) or any(
            p.get("id") == mach["placement_id"]
            for p in compiled["runtime"].get("placement_manifest", []))
        crafted = False
        if rec:
            for ing in rec["inputs"]:
                sim.apply_effect(w, {"type": "add_item",
                                     "params": {"item_id": ing["item_id"],
                                                "qty": ing.get("qty", 1)}})
            crafted = sim.action_craft(w, rec)
        det.update(placement_ok=placement_ok, crafted=crafted)
        det["ok"] = bool(rec) and placement_ok and crafted

    elif domain == "pnj":
        npc = byid("npcs")[pid]
        sim.apply_effect(w, {"type": "add_item",
                             "params": {"item_id": "objet_navet", "qty": 1}})
        talked = sim.action_talk(w, pid)
        r0 = w["player"]["relationships"].get(pid, 0)
        gifted = sim.action_gift(w, pid, "objet_navet", 12)
        lieux = {l["id"] for l in cats.get("locations", [])}
        places_ok = all(p in lieux for p in
                        ([npc.get("home")] if npc.get("home") else [])
                        + (npc.get("frequented_places") or []))
        det.update(talked=talked, gift_raised=w["player"]["relationships"].get(pid, 0) > r0,
                   places_ok=places_ok)
        det["ok"] = talked and gifted and det["gift_raised"] and places_ok

    elif domain == "dialogues":
        dlg = next((d for d in compiled["dialogs"] if d["id"] == pid), None)
        det["compiled"] = bool(dlg)
        if dlg:
            _apply_dialog_context(w, dlg)
            chosen = sim.evaluate_dialogs(compiled["dialogs"], w, dlg["speaker_id"])
            det["chosen"] = chosen["id"] if chosen else None
            reveals = [rv for line in dlg.get("lines", [])
                       for rv in line.get("reveals", []) or []]
            det["reveals_applied"] = all(rv in w["player"]["known_facts"] for rv in reveals)
            # Contexte négatif : ailleurs, le dialogue conditionnel ne se déclenche pas.
            w2 = sim.initial_state(cats)
            w2["player"]["location"] = "lieu_lac_muet"
            none_elsewhere = sim.evaluate_dialogs(compiled["dialogs"], w2,
                                                  dlg["speaker_id"]) is None
            det["context_sensitive"] = none_elsewhere
            det["ok"] = (det["chosen"] == pid and det["reveals_applied"]
                         and none_elsewhere)
        else:
            det["ok"] = False

    elif domain == "quetes":
        q = byid("quests")[pid]
        applied = all(sim.apply_effect(w, eff) for eff in q.get("effects", []))
        completed = pid in w["world"]["completed_quests"]
        active = pid in w["world"]["active_quests"]
        sim.process_quests(w, cats)  # ne doit pas lever
        det.update(effects_applied=applied, completed=completed, active=active,
                   consequences=bool(q.get("consequences")))
        det["ok"] = applied and (completed or active) and det["consequences"]

    elif domain == "evenements":
        ev = byid("events")[pid]
        trig = ev.get("trigger", {})
        params = trig.get("params", {})
        if "season_id" in params:
            w["time"]["season"] = params["season_id"]
        if "lieu_id" in params:
            w["player"]["location"] = params["lieu_id"]
        matches = sim._trigger_matches(w, trig)
        applied = all(sim.apply_effect(w, eff) for eff in ev.get("effects", []))
        det.update(trigger_matches=matches, effects_applied=applied)
        det["ok"] = matches and applied

    elif domain == "creatures":
        c = byid("creatures")[pid]
        lieux = {l["id"] for l in cats.get("locations", [])}
        habitat_ok = all(h in lieux for h in c.get("habitat", []))
        yields_ok = all(sim.apply_effect(w, {"type": "add_item",
                                             "params": {"item_id": y, "qty": 1}})
                        for y in c.get("yields", []))
        explored = sim.action_explore(w, c["habitat"][0]) if c.get("habitat") else False
        det.update(habitat_ok=habitat_ok, yields_ok=yields_ok, explored=explored)
        det["ok"] = habitat_ok and yields_ok and bool(c.get("habitat"))

    elif domain == "boss":
        b = byid("creatures").get(pid)
        det["kind"] = (b or {}).get("kind")
        spawned = sim.apply_effect(w, {"type": "spawn_entity",
                                       "params": {"entity_id": pid}})
        in_spawned = pid in w["world"].get("spawned", [])
        yields_ok = all(sim.apply_effect(w, {"type": "add_item",
                                             "params": {"item_id": y, "qty": 1}})
                        for y in (b or {}).get("yields", []))
        det.update(spawned=spawned and in_spawned, yields_ok=yields_ok,
                   content_note=("combat = décision ouverte (INPUT/open_decisions.md) ; "
                                 "canon : pas de magie de combat traditionnelle -> "
                                 "aucune mécanique de combat simulée, boss traité "
                                 "comme rencontre/épreuve"))
        det["ok"] = (b or {}).get("kind") == "boss" and det["spawned"] and yields_ok

    elif domain == "maps":
        mp = byid("maps")[pid]
        pm = sim.probe_maps(compiled["runtime"])
        sim.apply_effect(w, {"type": "unlock_location",
                             "params": {"lieu_id": mp.get("location_id", "")}})
        explored = sim.action_explore(w, mp.get("location_id", ""))
        det.update(probe=pm, explored=explored,
                   seed_stable=isinstance(mp.get("seed"), int))
        det["ok"] = pm["ok"] and explored and det["seed_stable"]

    elif domain == "placement":
        rules = {r["id"]: r for r in compiled["runtime"].get("placement_manifest", [])}
        rule = rules.get(pid)
        det["rule_found"] = bool(rule)
        if rule:
            allowed = set(rule.get("allowed_terrain") or [])
            map_terrains = next((m["terrains"] for m in cats.get("maps", [])
                                 if allowed & set(m.get("terrains", []))), None)
            det["terrain_source"] = bool(map_terrains)
            res = sim.simulate_placement(rule, map_terrains or sorted(allowed),
                                         seed=derive_seed("placement", pid), count=8)
            coll = TYPE_TO_COLLECTION.get(rule.get("places", ""))
            places_ok = bool(coll) and len(cats.get(coll, [])) > 0
            det.update(simulation=res, places_ok=places_ok)
            det["ok"] = res["ok"] and places_ok
        else:
            det["ok"] = False

    elif domain == "assets":
        pa = sim.probe_assets(compiled["runtime"])
        found = next((a for a in compiled["runtime"].get("assets_manifest", [])
                      if a["id"] == pid), None)
        det.update(probe=pa, found=bool(found),
                   fingerprint_unique=pa["unique_fingerprints"])
        det["ok"] = pa["ok"] and bool(found)

    elif domain == "animations":
        an = next((a for a in compiled["runtime"].get("animations_manifest", [])
                   if a["id"] == pid), None)
        pa = sim.probe_animations(compiled["runtime"], compiled["rules"], w)
        det.update(probe_ok=pa["ok"], found=bool(an))
        if an:
            eff = sim.animation_effect(an.get("logic_effect"))
            applied = bool(eff) and sim.apply_effect(w, eff)
            flag = (eff or {}).get("params", {}).get("flag_id")
            det.update(effect_applied=applied,
                       flag_set=(flag in w["player"]["flags"]) if flag else applied,
                       impact_in_frames=(not isinstance(an.get("impact_event"), int)
                                         or 0 <= an["impact_event"] < an.get("frames", 0)))
            det["ok"] = pa["ok"] and applied and det["impact_in_frames"]
        else:
            det["ok"] = False

    elif domain == "sauvegardes":
        st = {"time": primary["time"], "player": primary["player"],
              "world": primary["world"], "log": []}
        schema = compiled["save_schema"]
        blob = sim.save_game(st, schema)
        loaded = sim.load_game(blob, schema)
        roundtrip = (loaded["time"] == st["time"] and loaded["player"] == st["player"]
                     and loaded["world"] == st["world"])
        # Migration : version 0.0.0 -> courante (empreinte recalculée par le moteur).
        data = json.loads(blob)
        data["save_version"] = "0.0.0"
        data["checksum"] = fingerprint(data["world"])
        migrated = sim.load_game(json.dumps(data, sort_keys=True), schema, cats) is not None
        # Trucature : altération d'un champ protégé -> rejet.
        data2 = json.loads(blob)
        data2["world"]["player"]["money"] += 9999
        try:
            sim.load_game(json.dumps(data2, sort_keys=True), schema)
            tamper_rejected = False
        except ValueError:
            tamper_rejected = True
        # Reproductibilité : deux sauvegardes du même état = mêmes octets.
        repro = blob == sim.save_game(st, schema)
        det.update(roundtrip=roundtrip, migration=migrated,
                   tamper_rejected=tamper_rejected, byte_stable=repro)
        det["ok"] = roundtrip and migrated and tamper_rejected and repro

    else:
        det["ok"] = False
    det.setdefault("ok", False)
    return det


def _apply_dialog_context(w: dict, dlg: dict) -> None:
    """Place l'état du monde dans un contexte qui satisfait les conditions."""
    for c in dlg.get("conditions", []):
        t, p = c.get("type"), c.get("params", {}) or {}
        if t == "location" and p.get("lieu_id"):
            w["player"]["location"] = p["lieu_id"]
        elif t == "time_of_day":
            h, op = int(p.get("hour", 12)), p.get("op", ">=")
            w["time"]["hour"] = {"<": max(0, h - 1), "<=": h, ">": h + 1,
                                 ">=": h, "==": h, "!=": (h + 2) % 24}.get(op, h)
        elif t == "season" and p.get("season_id"):
            w["time"]["season"] = p["season_id"]
        elif t == "weather" and p.get("weather_id"):
            w["time"]["weather"] = p["weather_id"]
        elif t == "flag" and p.get("flag_id"):
            w["player"]["flags"][p["flag_id"]] = p.get("expected", True)


# =============================================================================
# PARCOURS COMPLETS (nominal, rejet, orphelin, volume, reproductibilité)
# =============================================================================

def load_fixture(domain: str) -> dict:
    path = FIXTURE_DIR / f"{domain}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@contextlib.contextmanager
def temp_results():
    """Isole les dossiers RESULTS de l'importateur (aucune écriture réelle)."""
    old = (importer_mod.ACCEPTED, importer_mod.REJECTED, importer_mod.INCOMING)
    with tempfile.TemporaryDirectory() as tmp:
        importer_mod.ACCEPTED = Path(tmp) / "accepted"
        importer_mod.REJECTED = Path(tmp) / "rejected"
        importer_mod.INCOMING = Path(tmp) / "incoming"
        try:
            yield tmp
        finally:
            importer_mod.ACCEPTED, importer_mod.REJECTED, importer_mod.INCOMING = old


def import_objects(objects: list[dict], state: dict) -> list[dict]:
    """Importation réelle (schéma + canon + références) via l'importateur.

    Séquentielle : chaque objet accepté est intégré immédiatement à l'état de
    contrôle, pour que les objets suivants du même lot résolvent leurs
    références (ex. une recette qui référence une machine du même lot)."""
    results: list[dict] = []
    working = state
    with temp_results():
        for o in objects:
            rec = importer_mod.import_one(json.dumps(o, ensure_ascii=False),
                                          filename=f"{o.get('id', 'x')}.json",
                                          state=working)
            results.append(rec)
            if rec["status"] == "ACCEPTED" and rec.get("object"):
                working, _ = integrate(working, [rec["object"]])
    return results


def run_journey(fixture: dict, state: dict | None = None) -> dict[str, Any]:
    """Parcours nominal complet : entrée -> … -> test runtime -> maturité."""
    domain = fixture["domain"]
    cfg = DOMAINS[domain]
    st0 = copy.deepcopy(state) if state is not None else base_state()
    rec: dict[str, Any] = {"domain": domain, "steps": {}}

    # 1. SPECIFIED : fixture réaliste et justifiée.
    ents = fixture.get("entities", [])
    rec["steps"]["specified"] = bool(ents) and all(
        e.get("justification") or e.get("derivation") or domain == "sauvegardes"
        for e in ents)

    # 2. IMPORTED / SCHEMA_VALIDATED : importation réelle.
    results = import_objects(ents, st0)
    accepted = all(r["status"] == "ACCEPTED" for r in results)
    rec["steps"]["import"] = {"statuses": [r["status"] for r in results],
                              "accepted": accepted,
                              "issues": [i for r in results for i in r.get("issues", [])]}
    if not accepted:
        rec["maturity"] = Maturity.SPECIFIED
        rec["evidence"] = {Maturity.SPECIFIED: rec["steps"]["specified"],
                           Maturity.SCHEMA_VALIDATED: False}
        return rec

    # 3. CATALOGED : intégration catalogue/manifest.
    st1, routing = integrate(st0, ents)
    rec["steps"]["catalog"] = {"routing": routing,
                               "routed": all(r["routed"] for r in routing)}

    # 4. GRAPH_CONNECTED + VALIDATION : reconstruction + validateurs.
    st2 = rebuild(st1)
    rep = validator_mod.run_all(st2)
    fids = {e["id"] for e in ents}
    entity_errors = [i for i in rep["issues"]
                     if i["severity"] == "ERROR" and i.get("entity") in fids]
    gev = graph_evidence(cfg, st2, ents)
    rec["steps"]["graph"] = gev
    rec["steps"]["validation"] = {"passed": rep["passed"],
                                  "error_count": rep["error_count"],
                                  "entity_errors": entity_errors}

    # 5. COMPILED : compilation + présence dans la sortie runtime.
    compiled = compile_all(st2)
    verifs = [verify_in_runtime(compiled, e, cfg) for e in ents]
    rec["steps"]["compile"] = {"verifications": verifs,
                               "all_present": all(v["in_runtime"] and v["in_nodes"]
                                                  for v in verifs)}

    # 6. RUNTIME_TESTED : le simulateur exécute la donnée compilée.
    probe = runtime_probe(domain, compiled, fixture)
    rec["steps"]["runtime"] = probe

    # 7. MATURITÉ depuis les preuves (jamais déclarative).
    clean = rep["passed"] and not entity_errors
    evidence = {
        Maturity.SPECIFIED: bool(rec["steps"]["specified"]),
        Maturity.SCHEMA_VALIDATED: accepted,
        Maturity.IMPORTED: accepted,
        Maturity.CATALOGED: rec["steps"]["catalog"]["routed"],
        Maturity.GRAPH_CONNECTED: bool(gev.get("ok")),
        Maturity.COMPILED: rec["steps"]["compile"]["all_present"],
        Maturity.RUNTIME_TESTED: bool(probe.get("ok")) and clean,
        Maturity.PRODUCTION_READY: bool(probe.get("ok")) and clean
        and rec["steps"]["compile"]["all_present"] and bool(gev.get("ok")),
    }
    rec["evidence"] = evidence
    rec["maturity"] = Maturity.from_evidence(evidence)
    rec["compiled_fingerprint"] = compiled["runtime"]["fingerprint"]
    return rec


def run_rejection(fixture: dict, state: dict | None = None) -> dict[str, Any]:
    """Test de REJET : la variante invalide doit être refusée (import ou
    validation) — jamais intégrée silencieusement."""
    st0 = copy.deepcopy(state) if state is not None else base_state()
    bad = fixture["invalid_variant"]
    results = import_objects([bad], st0)
    if results[0]["status"] != "ACCEPTED":
        return {"detected": True, "at": "import",
                "issues": [i["code"] for i in results[0].get("issues", [])]}
    # Accepté à l'import : la validation globale doit le rattraper.
    cfg = DOMAINS[fixture["domain"]]
    st1, _ = integrate(st0, [bad])
    st2 = rebuild(st1)
    rep = validator_mod.run_all(st2)
    conn = st2["connectivity"]
    caught = [i for i in rep["issues"] if i["severity"] == "ERROR"
              and (i.get("entity") == bad.get("id")
                   or bad.get("id") in str(i.get("message", "")))]
    in_conn = any(bad.get("id") in conn.get(k, []) for k in
                  ("orphans", "unreachable", "objects_no_usage", "recipes_no_input",
                   "recipes_no_output", "quests_no_giver", "quests_no_consequence",
                   "resources_no_producer", "resources_no_consumer",
                   "secrets_no_discovery", "events_unreachable"))
    dangling = any(bad.get("id") in str(d) for d in conn.get("dangling_references", []))
    return {"detected": bool(caught) or in_conn or dangling or not rep["passed"],
            "at": "validation",
            "issues": [i["code"] for i in caught],
            "connectivity_flagged": in_conn or dangling}


def run_orphan(fixture: dict, state: dict | None = None) -> dict[str, Any]:
    """Test de DONNÉE ORPHELINE : la variante orpheline doit être détectée
    (rejet à l'import, erreur de validation ou détection de connectivité)."""
    st0 = copy.deepcopy(state) if state is not None else base_state()
    orph = fixture["orphan_variant"]
    results = import_objects([orph], st0)
    if results[0]["status"] != "ACCEPTED":
        return {"detected": True, "at": "import",
                "issues": [i["code"] for i in results[0].get("issues", [])]}
    st1, _ = integrate(st0, [orph])
    st2 = rebuild(st1)
    cfg = DOMAINS[fixture["domain"]]
    if cfg["kind"] == "save":
        # Sauvegardes : pas de catalogue ni de validateur dédié — une
        # sauvegarde orpheline référence des entités HORS graphe ; détectée
        # par les preuves de graphe (location/inventaire/relations/quêtes/faits).
        ev = graph_evidence(cfg, st2, [orph])
        return {"detected": not ev.get("ok"), "at": "graphe (références)",
                "issues": sorted(k for k, v in ev.items()
                                 if k not in ("ok", "ids") and v is False),
                "connectivity_flagged": False}
    rep = validator_mod.run_all(st2)
    conn = st2["connectivity"]
    oid = orph.get("id")
    caught = [i for i in rep["issues"] if i["severity"] in ("ERROR", "WARNING")
              and i.get("entity") == oid]
    in_conn = any(oid in conn.get(k, []) for k in
                  ("orphans", "unreachable", "weak_usage", "objects_no_usage",
                   "recipes_no_input", "recipes_no_output", "quests_no_giver",
                   "quests_no_consequence", "npcs_no_routine", "npcs_no_interaction",
                   "resources_no_producer", "resources_no_consumer",
                   "secrets_no_discovery", "events_unreachable"))
    dangling = any(oid in str(d) for d in conn.get("dangling_references", []))
    return {"detected": bool(caught) or in_conn or dangling,
            "at": "validation/connectivité",
            "issues": [i["code"] for i in caught],
            "connectivity_flagged": in_conn or dangling}


def clone_set(entities: list[dict], i: int) -> list[dict]:
    """Clone un jeu d'entités en préservant ses références internes
    (ids suffixés, empreintes et graines recalculées)."""
    blob = json.dumps(entities, ensure_ascii=False)
    for e in entities:
        old = e.get("id", "")
        if old:
            blob = blob.replace(f'"{old}"', f'"{old}_vol{i}"')
    clones = json.loads(blob)
    for c in clones:
        if "display_name" in c:
            c["display_name"] = f"{c['display_name']} (vol. {i})"
        if "fingerprint" in c:
            c["fingerprint"] = fingerprint(f"{c['id']}|{c.get('family', '')}")
        if isinstance(c.get("seed"), int):
            c["seed"] = derive_seed("map", c["id"])
    return clones


def run_volume(fixture: dict, n: int = 25, state: dict | None = None) -> dict[str, Any]:
    """Test de VOLUME : n clones cohérents intégrés, validés, compilés et
    présents dans la sortie runtime (aucun placeholder : chaque clone garde
    ses relations et références)."""
    st0 = copy.deepcopy(state) if state is not None else base_state()
    cfg = DOMAINS[fixture["domain"]]
    all_clones: list[dict] = []
    for i in range(n):
        all_clones.extend(clone_set(fixture["entities"], i))
    if fixture["domain"] == "sauvegardes":
        # Volume de sauvegardes : n états distincts, aller-retour complet.
        schema = compiler_mod.compile_save_schema(st0)
        ok = 0
        for i in range(n):
            st = {"time": dict(fixture["entities"][0]["time"], day=i + 1),
                  "player": copy.deepcopy(fixture["entities"][0]["player"]),
                  "world": copy.deepcopy(fixture["entities"][0]["world"]),
                  "log": []}
            blob = simulator_mod.save_game(st, schema)
            back = simulator_mod.load_game(blob, schema)
            ok += int(back["time"]["day"] == i + 1)
        return {"n": n, "integrated": ok, "compiled_present": ok == n,
                "runtime_ok": ok == n, "ok": ok == n}
    st1, _ = integrate(st0, all_clones)
    st2 = rebuild(st1)
    rep = validator_mod.run_all(st2)
    compiled = compile_all(st2)
    present = sum(1 for c in all_clones
                  if verify_in_runtime(compiled, c, cfg)["in_runtime"])
    probe = runtime_probe(fixture["domain"], compiled,
                          {"domain": fixture["domain"], "entities": all_clones[:1]})
    return {"n": n, "entities": len(all_clones), "integrated": present,
            "validation_errors": rep["error_count"],
            "compiled_present": present == len(all_clones),
            "runtime_ok": bool(probe.get("ok")),
            "ok": present == len(all_clones) and rep["error_count"] == 0
            and bool(probe.get("ok"))}


def run_reproducibility(fixture: dict, state: dict | None = None) -> dict[str, Any]:
    """Test de REPRODUCTIBILITÉ : deux parcours identiques produisent des
    sorties compilées stables octet par octet."""
    st0 = copy.deepcopy(state) if state is not None else base_state()
    r1 = run_journey(fixture, st0)
    r2 = run_journey(fixture, st0)
    if "compiled_fingerprint" not in r1 or "compiled_fingerprint" not in r2:
        return {"stable": False, "reason": "parcours nominal en échec"}
    # Stabilité octet par octet du bundle compilé (hors entités intégrées,
    # comparé sur la même entrée) :
    st_a, _ = integrate(copy.deepcopy(st0), fixture["entities"])
    st_b, _ = integrate(copy.deepcopy(st0), fixture["entities"])
    ca = compile_all(rebuild(st_a))
    cb = compile_all(rebuild(st_b))
    bytes_a = json.dumps(ca["runtime"], ensure_ascii=False, sort_keys=True)
    bytes_b = json.dumps(cb["runtime"], ensure_ascii=False, sort_keys=True)
    save_a = simulator_mod.save_game(
        {"time": {"day": 1}, "player": {}, "world": {}}, ca["save_schema"])
    save_b = simulator_mod.save_game(
        {"time": {"day": 1}, "player": {}, "world": {}}, cb["save_schema"])
    return {"stable": (r1["compiled_fingerprint"] == r2["compiled_fingerprint"]
                       and bytes_a == bytes_b and save_a == save_b),
            "fingerprint": r1["compiled_fingerprint"],
            "byte_identical_runtime": bytes_a == bytes_b,
            "byte_identical_save": save_a == save_b,
            "maturity_identique": r1["maturity"] == r2["maturity"]}
