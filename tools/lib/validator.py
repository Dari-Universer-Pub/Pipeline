"""Validateurs (étape 29 ; livrables 57-72).

Un validateur retourne une liste d'`Issue` :
{severity: ERROR|WARNING|INFO, code, entity, message, fix}.

Familles de validation (exigées par le brief) :
structurelle, schémas, références, logique, narrative, canonique, économique,
temporelle, progression, maps, navigation, collisions, assets, animations,
placement, connectivité.

Tous les validateurs sont déterministes et sans LLM.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .common import DIRS, Status, is_valid_id, make_id, read_json, unwrap
from . import graph as graph_mod

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"


def issue(severity: str, code: str, entity: str, message: str, fix: str = "") -> dict:
    return {"severity": severity, "code": code, "entity": entity,
            "message": message, "fix": fix}


# =============================================================================
# VALIDATION DE SCHÉMA (sous-ensemble JSON Schema draft-07, stdlib)
# =============================================================================

def validate_schema_subset(instance: Any, schema: dict, path: str = "$") -> list[dict]:
    """Valide une instance contre un sous-ensemble de JSON Schema draft-07."""
    errs: list[dict] = []
    if not isinstance(schema, dict):
        return errs

    # type
    if "type" in schema:
        t = schema["type"]
        types = t if isinstance(t, list) else [t]
        if not _type_ok(instance, types):
            # 'null' autorisé si présent dans types.
            errs.append(issue(ERROR, "schema.type", path,
                              f"type attendu {types}, obtenu {type(instance).__name__}"))
            return errs  # inutile de continuer si le type est faux

    # enum
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(issue(ERROR, "schema.enum", path,
                          f"valeur '{instance}' hors enum {schema['enum']}"))

    # string constraints
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append(issue(ERROR, "schema.minLength", path,
                              f"longueur {len(instance)} < {schema['minLength']}"))
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errs.append(issue(ERROR, "schema.pattern", path,
                              f"'{instance}' ne respecte pas le motif {schema['pattern']}"))

    # numeric constraints
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append(issue(ERROR, "schema.minimum", path,
                              f"{instance} < minimum {schema['minimum']}"))

    # object
    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errs.append(issue(ERROR, "schema.required", f"{path}.{req}",
                                  f"champ obligatoire '{req}' manquant"))
        props = schema.get("properties", {})
        for k, v in instance.items():
            if k in props:
                errs.extend(validate_schema_subset(v, props[k], f"{path}.{k}"))
        # additionalProperties=False -> rejet des champs inconnus
        if schema.get("additionalProperties") is False:
            for k in instance:
                if k not in props:
                    errs.append(issue(ERROR, "schema.additionalProperties",
                                      f"{path}.{k}", f"champ non autorisé '{k}'"))

    # array
    if isinstance(instance, list) and "items" in schema:
        item_schema = schema["items"]
        for i, it in enumerate(instance):
            errs.extend(validate_schema_subset(it, item_schema, f"{path}[{i}]"))

    return errs


def _type_ok(value: Any, types: list[str]) -> bool:
    for t in types:
        if t == "object" and isinstance(value, dict):
            return True
        if t == "array" and isinstance(value, list):
            return True
        if t == "string" and isinstance(value, str):
            return True
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if t == "boolean" and isinstance(value, bool):
            return True
        if t == "null" and value is None:
            return True
    return False


# =============================================================================
# CHARGEMENT DE L'ÉTAT
# =============================================================================

def load_state() -> dict[str, Any]:
    """Charge l'état complet de la pipeline pour validation."""
    catalogs = {}
    for name in ("objects", "resources", "crops", "machines", "recipes", "quests",
                 "npcs", "creatures", "locations", "seasons", "events", "secrets",
                 "maps", "dialogues"):
        catalogs[name] = unwrap(read_json(DIRS["catalogs"] / f"{name}.json", []))
    manifests = {}
    for name in ("objects", "resources", "crops", "machines", "recipes", "quests",
                 "npcs", "creatures", "maps", "placement", "navigation", "assets",
                 "animations", "transitions", "effects"):
        manifests[name] = unwrap(read_json(DIRS["manifests"] / f"manifest_{name}.json", []))
    schemas = {}
    for p in (DIRS["schemas"]).glob("*.schema.json"):
        schemas[p.name.replace(".schema.json", "")] = read_json(p)
    graph = unwrap(read_json(DIRS["graph"] / "world_graph.json", {"nodes": [], "edges": []}))
    canon = unwrap(read_json(DIRS["canon"] / "canon_locked.json", {}))
    ontology = unwrap(read_json(DIRS["ontology"] / "ontology.json", {}))
    connectivity = unwrap(read_json(DIRS["graph"] / "connectivity.json", {}))
    return {"catalogs": catalogs, "manifests": manifests, "schemas": schemas,
            "graph": graph, "canon": canon, "ontology": ontology,
            "connectivity": connectivity}


def all_entity_ids(state: dict) -> set[str]:
    ids = set()
    for coll in state["catalogs"].values():
        for e in coll:
            if isinstance(e, dict) and "id" in e:
                ids.add(e["id"])
    for n in state["graph"].get("nodes", []):
        ids.add(n["id"])
    for coll in state["manifests"].values():
        for e in coll:
            if isinstance(e, dict) and "id" in e:
                ids.add(e["id"])
    return ids


# =============================================================================
# 1. VALIDATION STRUCTURELLE
# =============================================================================

FORBIDDEN_TERMS = [
    "épée", "epee", "dragon", "magie", "magique", "galaxie", "cosmique", "laser",
    "robot", "ordinateur", "plasma", "elfe", "orc", "nain", "sort", "sortilège",
    "sortilege", "mana", "donjon", "cyber", "nucléaire", "nucleaire", "pistolet",
    "fusil", "grenade", "missile", "espace", "interstellaire", "android",
]


def validate_structural(state: dict) -> list[dict]:
    """Champs obligatoires, types, identifiants, formats, UTF-8."""
    errs: list[dict] = []
    for coll_name, coll in state["catalogs"].items():
        if not isinstance(coll, list):
            continue  # ignore quantity_plan / functional_catalog (non-listes)
        for e in coll:
            if not isinstance(e, dict):
                errs.append(issue(ERROR, "struct.not_object", coll_name, "entrée non-objet"))
                continue
            eid = e.get("id", "?")
            # ID présent et valide.
            if "id" not in e:
                errs.append(issue(ERROR, "struct.no_id", coll_name, "id manquant"))
                continue
            if not is_valid_id(eid):
                errs.append(issue(ERROR, "struct.bad_id", eid,
                                  "ID interne invalide (minuscules, [a-z0-9_], sans accent)"))
            # Statut présent et valide.
            if e.get("status") not in Status.ALL:
                errs.append(issue(WARNING, "struct.bad_status", eid,
                                  f"statut '{e.get('status')}' hors {Status.ALL}"))
            # Nom affiché présent.
            if not e.get("display_name"):
                errs.append(issue(WARNING, "struct.no_name", eid, "display_name manquant"))
    return errs


def validate_schemas(state: dict) -> list[dict]:
    """Valide chaque entité contre son schéma JSON (sous-ensemble)."""
    errs: list[dict] = []
    # Map catalogue -> nom de schéma.
    coll_schema = {
        "objects": "objet", "resources": "ressource", "crops": "culture",
        "machines": "machine", "recipes": "recette", "quests": "quete",
        "npcs": "pnj", "creatures": "creature", "locations": "lieu",
        "seasons": "saison", "events": "evenement", "maps": "map",
    }
    for coll_name, schema_name in coll_schema.items():
        schema = state["schemas"].get(schema_name)
        if not schema:
            errs.append(issue(ERROR, "schema.missing", schema_name,
                              "schéma introuvable"))
            continue
        for e in state["catalogs"].get(coll_name, []):
            sub = validate_schema_subset(e, schema, e.get("id", coll_name))
            errs.extend(sub)
    return errs


def validate_encoding(state: dict) -> list[dict]:
    """Vérifie l'encodage UTF-8 de tous les artefacts JSON et l'ASCII des IDs."""
    errs: list[dict] = []
    for p in DIRS.values():
        p = Path(p)
        if not p.exists():
            continue
        for f in p.rglob("*.json"):
            try:
                f.read_bytes().decode("utf-8")
            except UnicodeDecodeError:
                errs.append(issue(ERROR, "enc.utf8", str(f), "fichier non-UTF-8"))
            try:
                json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as ex:
                errs.append(issue(ERROR, "enc.json", str(f), f"JSON invalide: {ex}"))
    # IDs ASCII.
    for coll in state["catalogs"].values():
        for e in coll:
            if isinstance(e, dict) and "id" in e and not e["id"].isascii():
                errs.append(issue(ERROR, "enc.id_ascii", e["id"], "ID non-ASCII"))
    return errs


# =============================================================================
# 2. VALIDATION DE RÉFÉRENCES
# =============================================================================

def validate_references(state: dict) -> list[dict]:
    """Toute référence doit résoudre vers une entité existante."""
    errs: list[dict] = []
    ids = all_entity_ids(state)

    # Références pendantes du graphe.
    for d in state["connectivity"].get("dangling_references", []):
        errs.append(issue(ERROR, "ref.dangling", d,
                          "le graphe référence un ID inexistant",
                          "créer l'entité ou retirer la référence"))

    # Références dans les champs des entités.
    ref_fields = {
        "crops": ["seed_id", "yield_id"],
        "machines": ["built_by"],
        "recipes": ["station_id"],
        "quests": ["giver_id", "location_id"],
        "events": ["location_id"],
        "creatures": [],
        "npcs": ["home"],
        "secrets": ["location_id"],
        "maps": ["location_id"],
        "locations": ["map_id", "parent_id"],
    }
    for coll_name, fields in ref_fields.items():
        for e in state["catalogs"].get(coll_name, []):
            for f in fields:
                v = e.get(f)
                if v and v not in ids:
                    errs.append(issue(ERROR, "ref.unresolved", e["id"],
                                      f"champ '{f}' -> '{v}' inexistant"))
            # Listes de références.
            for f in ("seasons", "linked_maps", "recipe_ids", "frequented_places",
                      "habitat", "yields", "inputs", "outputs", "discovery_path",
                      "knowledge", "forbidden_knowledge"):
                v = e.get(f)
                if isinstance(v, list):
                    for x in v:
                        ref = x.get("item_id") if isinstance(x, dict) else x
                        if isinstance(ref, str) and ref and ref not in ids:
                            # Les IDs de saison/carte/terrain peuvent être hors catalogue.
                            if not (f in ("seasons",) and ref.startswith("saison_")) \
                               and not (f == "linked_maps" and ref.startswith("map_")) \
                               and not ref.startswith(("terrain_", "flag_", "weather_")):
                                errs.append(issue(WARNING, "ref.list_unresolved",
                                                  e["id"], f"'{f}' -> '{ref}' inexistant"))
    return errs


# =============================================================================
# 3. VALIDATION CANONIQUE
# =============================================================================

def validate_canonical(state: dict) -> list[dict]:
    """Noms respectés, éléments interdits absents, canon vs proposition."""
    errs: list[dict] = []
    canon = state["canon"]

    # Noms canoniques présents et inchangés.
    canon_names = {}
    for l in canon.get("locations", []):
        canon_names[l["id"]] = l["display_name"]
    for n in canon.get("npcs", []):
        canon_names[n["id"]] = n["display_name"]
    for o in canon.get("objects", []):
        canon_names[o["id"]] = o["display_name"]

    for coll in state["catalogs"].values():
        for e in coll:
            if not isinstance(e, dict):
                continue
            eid = e.get("id")
            # Un élément CANONIQUE doit conserver son nom canonique.
            if e.get("status") == Status.CANONIQUE and eid in canon_names:
                if e.get("display_name") != canon_names[eid]:
                    errs.append(issue(ERROR, "canon.name_changed", eid,
                                      f"nom canonique altéré: '{e.get('display_name')}' "
                                      f"!= '{canon_names[eid]}'"))
            # Termes interdits dans les noms affichés.
            dn = (e.get("display_name") or "").lower()
            for term in FORBIDDEN_TERMS:
                if term in dn:
                    errs.append(issue(ERROR, "canon.forbidden_term", eid,
                                      f"terme interdit '{term}' dans '{e.get('display_name')}'"))
            # Un élément CANONIQUE doit avoir une source canonique.
            if e.get("status") == Status.CANONIQUE and "canon_initial" not in (e.get("source") or ""):
                errs.append(issue(WARNING, "canon.source", eid,
                                  "statut CANONIQUE sans source dans canon_initial.md"))
    return errs


# =============================================================================
# 4. VALIDATION LOGIQUE
# =============================================================================

def validate_logical(state: dict) -> list[dict]:
    """Conditions atteignables, effets valides, dépendances, boucles impossibles."""
    errs: list[dict] = []
    onto = state["ontology"]
    effect_types = set(onto.get("effect_types", {}).keys())
    condition_types = set(onto.get("condition_types", {}).keys())

    def check_effects(owner: str, effects: Iterable[dict]):
        for eff in effects or []:
            if eff.get("type") not in effect_types:
                errs.append(issue(ERROR, "logic.bad_effect", owner,
                                  f"effet '{eff.get('type')}' hors ontologie"))

    def check_conditions(owner: str, conds: Iterable[dict]):
        for c in conds or []:
            if c.get("type") not in condition_types:
                errs.append(issue(ERROR, "logic.bad_condition", owner,
                                  f"condition '{c.get('type')}' hors ontologie"))

    for q in state["catalogs"].get("quests", []):
        check_effects(q["id"], q.get("effects"))
        check_conditions(q["id"], q.get("preconditions"))
        check_conditions(q["id"], q.get("failure_conditions"))
    for ev in state["catalogs"].get("events", []):
        check_effects(ev["id"], ev.get("effects"))
        check_conditions(ev["id"], ev.get("preconditions"))

    # Recettes : entrées ET sorties non vides (pas de boucle impossible).
    for r in state["catalogs"].get("recipes", []):
        if not r.get("inputs"):
            errs.append(issue(ERROR, "logic.recipe_no_input", r["id"], "recette sans ingrédient"))
        if not r.get("outputs"):
            errs.append(issue(ERROR, "logic.recipe_no_output", r["id"], "recette sans résultat"))
        # Détection de boucle de transformation triviale (A->A).
        ins = {i["item_id"] for i in r.get("inputs", [])}
        outs = {o["item_id"] for o in r.get("outputs", [])}
        if ins and ins == outs:
            errs.append(issue(ERROR, "logic.recipe_self_loop", r["id"],
                              "entrée == sortie (transformation nulle)"))
    return errs


# =============================================================================
# 5. VALIDATION NARRATIVE
# =============================================================================

def validate_narrative(state: dict) -> list[dict]:
    """Motivations, voix distinctes, mémoire respectée, secrets progressifs."""
    errs: list[dict] = []
    ids = all_entity_ids(state)
    npcs = {n["id"]: n for n in state["catalogs"].get("npcs", [])}

    # Voix distinctes.
    voices = {}
    for nid, n in npcs.items():
        v = n.get("voice", "")
        if not v:
            errs.append(issue(WARNING, "narr.no_voice", nid, "PNJ sans signature de voix"))
        elif v in voices:
            errs.append(issue(WARNING, "narr.voice_duplicate", nid,
                              f"voix identique à {voices[v]}"))
        else:
            voices[v] = nid
        # Connaissances : chaque fait/entité connu doit exister.
        for k in n.get("knowledge", []):
            if k not in ids:
                errs.append(issue(WARNING, "narr.knowledge_unresolved", nid,
                                  f"connaissance '{k}' inexistante"))
        # Aucun chevauchement knowledge / forbidden_knowledge.
        overlap = set(n.get("knowledge", [])) & set(n.get("forbidden_knowledge", []))
        if overlap:
            errs.append(issue(ERROR, "narr.memory_contradiction", nid,
                              f"connaît ET ignore : {sorted(overlap)}"))

    # Dialogues : reveals ⊆ knowledge du locuteur.
    for d in state["manifests"].get("dialogues", []) + state["catalogs"].get("dialogues", []):
        spk = npcs.get(d.get("speaker_id"))
        if not spk:
            continue
        known = set(spk.get("knowledge", []))
        forbidden = set(spk.get("forbidden_knowledge", []))
        for line in d.get("lines", []):
            for rv in line.get("reveals", []):
                if rv in forbidden:
                    errs.append(issue(ERROR, "narr.secret_leak", d["id"],
                                      f"révèle un fait interdit '{rv}'"))
                elif rv not in known:
                    errs.append(issue(WARNING, "narr.reveal_unknown", d["id"],
                                      f"révèle '{rv}' hors connaissances du PNJ"))
    return errs


# =============================================================================
# 6. VALIDATION ÉCONOMIQUE
# =============================================================================

def validate_economic(state: dict) -> list[dict]:
    """Prix, récompenses, ressources, boucles d'argent, transformations."""
    errs: list[dict] = []
    objs = {o["id"]: o for o in state["catalogs"].get("objects", [])}
    res = {r["id"]: r for r in state["catalogs"].get("resources", [])}
    values = {}
    for o in objs.values():
        values[o["id"]] = o.get("base_value")
    for r in res.values():
        values[r["id"]] = r.get("base_value")

    for rec in state["catalogs"].get("recipes", []):
        in_val = sum((values.get(i["item_id"]) or 0) * i.get("qty", 1)
                     for i in rec.get("inputs", []))
        out_val = sum((values.get(o["item_id"]) or 0) * o.get("qty", 1)
                      for o in rec.get("outputs", []))
        # Transformation sans perte injustifiée (sortie >= entrée attendue).
        if in_val and out_val and out_val < in_val:
            errs.append(issue(WARNING, "eco.value_loss", rec["id"],
                              f"sortie ({out_val}) < entrée ({in_val}) : perte de valeur"))
        if not rec.get("inputs"):
            errs.append(issue(ERROR, "eco.recipe_free", rec["id"],
                              "recette sans entrée = création de valeur ex nihilo"))

    # Boucle d'argent : au moins un producteur ET un consommateur de monnaie.
    has_merchant = any("merchant" in (n.get("roles") or [])
                       for n in state["catalogs"].get("npcs", []))
    if not has_merchant:
        errs.append(issue(WARNING, "eco.no_merchant", "economie",
                          "aucun marchand : boucle d'argent incomplète"))
    return errs


# =============================================================================
# 7. VALIDATION TEMPORELLE
# =============================================================================

def validate_temporal(state: dict) -> list[dict]:
    """Saisons, horaires, durée, événements, disponibilité des ressources."""
    errs: list[dict] = []
    seasons = {s["id"]: s for s in state["catalogs"].get("seasons", [])}

    # Cultures : au moins une saison valide ; growth_days >= 1.
    for c in state["catalogs"].get("crops", []):
        if not c.get("seasons"):
            errs.append(issue(ERROR, "temp.crop_no_season", c["id"],
                              "culture sans saison de croissance"))
        for s in c.get("seasons", []):
            if s not in seasons:
                errs.append(issue(ERROR, "temp.crop_bad_season", c["id"],
                                  f"saison '{s}' inexistante"))
        if c.get("growth_days", 0) < 1:
            errs.append(issue(ERROR, "temp.crop_growth", c["id"], "growth_days < 1"))

    # Événements saisonniers : la saison référencée doit exister.
    for ev in state["catalogs"].get("events", []):
        trig = ev.get("trigger", {})
        sid = trig.get("params", {}).get("season_id")
        if sid and sid not in seasons:
            errs.append(issue(ERROR, "temp.event_bad_season", ev["id"],
                              f"saison '{sid}' inexistante"))

    # Routines PNJ : horaires valides (0-23).
    for n in state["catalogs"].get("npcs", []):
        for r in n.get("routines", []) or []:
            h = r.get("hour")
            if h is not None and not (0 <= h <= 23):
                errs.append(issue(ERROR, "temp.routine_hour", n["id"],
                                  f"heure de routine invalide: {h}"))
    return errs


# =============================================================================
# 8. VALIDATION DE PROGRESSION
# =============================================================================

def validate_progression(state: dict) -> list[dict]:
    """Quêtes atteignables, déblocages, conséquences."""
    errs: list[dict] = []
    conn = state["connectivity"]
    for q in conn.get("quests_no_giver", []):
        errs.append(issue(ERROR, "prog.quest_no_giver", q, "quête sans donneur"))
    for q in conn.get("quests_no_consequence", []):
        errs.append(issue(ERROR, "prog.quest_no_consequence", q,
                          "quête sans conséquence (aucun effet durable)"))
    for s in conn.get("secrets_no_discovery", []):
        errs.append(issue(ERROR, "prog.secret_no_discovery", s,
                          "secret sans chemin de découverte"))
    # Chaque quête a un fallback (aucun blocage définitif).
    for q in state["catalogs"].get("quests", []):
        if not q.get("fallback"):
            errs.append(issue(WARNING, "prog.quest_no_fallback", q["id"],
                              "quête sans solution de repli"))
    return errs


# =============================================================================
# 9. VALIDATION DES MAPS / NAVIGATION / COLLISIONS / PLACEMENT
# =============================================================================

def validate_maps(state: dict) -> list[dict]:
    errs: list[dict] = []
    maps = {m["id"]: m for m in state["manifests"].get("maps", [])}

    for mid, m in maps.items():
        # Taille présente.
        if not m.get("size"):
            errs.append(issue(ERROR, "map.no_size", mid, "taille absente"))
        # Terrains + règles de placement + navigation présentes.
        if not m.get("terrains"):
            errs.append(issue(ERROR, "map.no_terrain", mid, "aucun terrain"))
        if not m.get("placement_rules") and not state["manifests"].get("placement"):
            errs.append(issue(ERROR, "map.no_placement", mid, "aucune règle de placement"))
        # Entrées/sorties réciproques avec les cartes liées.
        for linked in m.get("linked_maps", []):
            lm = maps.get(linked)
            if lm and mid not in lm.get("linked_maps", []):
                errs.append(issue(WARNING, "map.link_asymetric", mid,
                                  f"liaison non réciproque avec {linked}"))
        # Zones secrètes découvrables.
        for sz in m.get("secret_zones", []):
            if not sz.get("discovery"):
                errs.append(issue(ERROR, "map.secret_no_discovery", mid,
                                  "zone secrète sans méthode de découverte"))

    # Navigation globale présente.
    if not state["manifests"].get("navigation"):
        errs.append(issue(ERROR, "nav.missing", "navigation",
                          "aucune règle de navigation globale"))
    return errs


def validate_collisions(state: dict) -> list[dict]:
    errs: list[dict] = []
    for m in state["manifests"].get("maps", []):
        coll = m.get("collisions", [])
        if not coll:
            errs.append(issue(WARNING, "coll.none", m["id"],
                              "aucune règle de collision définie"))
        # Au moins un terrain marchable (sinon carte entièrement bloquée).
        if coll and not any(not c.get("solid", True) for c in coll):
            errs.append(issue(ERROR, "coll.all_solid", m["id"],
                              "tous les terrains solides : carte infranchissable"))
    return errs


def validate_placement(state: dict) -> list[dict]:
    errs: list[dict] = []
    for p in state["manifests"].get("placement", []):
        if not p.get("allowed_terrain"):
            errs.append(issue(ERROR, "place.no_allowed", p["id"],
                              "règle de placement sans terrain autorisé"))
        if p.get("density") is None:
            errs.append(issue(WARNING, "place.no_density", p["id"], "densité non précisée"))
        # Terrain autorisé et interdit ne doivent pas se chevaucher.
        overlap = set(p.get("allowed_terrain", [])) & set(p.get("forbidden_terrain", []))
        if overlap:
            errs.append(issue(ERROR, "place.terrain_conflict", p["id"],
                              f"terrain à la fois autorisé et interdit : {sorted(overlap)}"))
    return errs


# =============================================================================
# 10. VALIDATION DES ASSETS / ANIMATIONS
# =============================================================================

def validate_assets(state: dict) -> list[dict]:
    errs: list[dict] = []
    ids = all_entity_ids(state)
    assets = state["manifests"].get("assets", [])
    fingerprints = {}

    for a in assets:
        aid = a["id"]
        # Asset rattaché à une entité (jamais isolé).
        ent = a.get("entity_id")
        if not ent or (ent not in ids and not ent.startswith(("map_", "asset_"))):
            errs.append(issue(ERROR, "asset.orphan", aid,
                              f"asset sans entité propriétaire valide ('{ent}')"))
        # Dimensions.
        if not a.get("width") or not a.get("height"):
            errs.append(issue(ERROR, "asset.no_dimensions", aid, "dimensions absentes"))
        # Empreinte unique (pas de doublon).
        fp = a.get("fingerprint")
        if fp:
            if fp in fingerprints:
                errs.append(issue(ERROR, "asset.duplicate_fingerprint", aid,
                                  f"empreinte identique à {fingerprints[fp]}"))
            fingerprints[fp] = aid
        # Famille + palette.
        if not a.get("family"):
            errs.append(issue(WARNING, "asset.no_family", aid, "asset sans famille"))
        if not a.get("palette"):
            errs.append(issue(WARNING, "asset.no_palette", aid, "asset sans palette"))

    # Assets inutilisés : un asset doit être référencé par une entité/animation/
    # carte/transition.
    referenced = set()
    for an in state["manifests"].get("animations", []):
        referenced.update(an.get("required_assets", []))
    for coll in state["manifests"].values():
        for e in coll:
            if isinstance(e, dict):
                for f in ("asset_id", "spritesheet_asset", "portrait_asset"):
                    if e.get(f):
                        referenced.add(e[f])
                for x in e.get("required_assets", []) or []:
                    referenced.add(x)
    # Tilesets de terrain : référencés par les terrains des cartes.
    for m in state["manifests"].get("maps", []):
        for t in m.get("terrains", []):
            tname = t if isinstance(t, str) else t.get("id", "")
            if tname:
                referenced.add(make_id("asset", f"tileset_{tname}"))
    # Transitions : référencées par leurs règles d'adjacence.
    for tr in state["manifests"].get("transitions", []):
        if tr.get("asset_id"):
            referenced.add(tr["asset_id"])
    # Les assets d'entités (icônes/sprites) sont référencés par leur entité.
    for a in assets:
        if a["id"] not in referenced:
            # Toléré si l'asset appartient à une entité existante (icône/sprite).
            if a.get("entity_id") not in ids:
                errs.append(issue(WARNING, "asset.unused", a["id"],
                                  "asset non référencé par une animation/entité"))
    return errs


def validate_animations(state: dict) -> list[dict]:
    errs: list[dict] = []
    ids = all_entity_ids(state)
    asset_ids = {a["id"] for a in state["manifests"].get("assets", [])}

    for an in state["manifests"].get("animations", []):
        aid = an["id"]
        # Animation rattachée à une entité + action/état.
        if not an.get("entity_id") or an["entity_id"] not in ids:
            errs.append(issue(ERROR, "anim.orphan", aid,
                              f"animation sans entité valide ('{an.get('entity_id')}')"))
        if not an.get("state_or_action"):
            errs.append(issue(ERROR, "anim.no_action", aid, "animation sans action/état"))
        # frames/fps.
        if not an.get("frames") or not an.get("fps"):
            errs.append(issue(ERROR, "anim.no_frames", aid, "frames/fps absents"))
        # Assets requis existent.
        for ra in an.get("required_assets", []):
            if ra not in asset_ids:
                errs.append(issue(ERROR, "anim.asset_missing", aid,
                                  f"asset requis '{ra}' absent du manifest"))
        # Synchronisation : impact_event implique logic_effect.
        if an.get("impact_event") and not an.get("logic_effect"):
            errs.append(issue(WARNING, "anim.impact_no_effect", aid,
                              "frame d'impact sans effet logique (non synchronisé)"))

    # Actions sans animation : chaque verbe de gameplay outillé doit avoir une anim.
    player_anims = {a["state_or_action"] for a in state["manifests"].get("animations", [])
                    if a.get("entity_id") == "joueur_jardinier"}
    required_player_actions = {"idle", "marche", "labourer", "arroser", "planter",
                               "recolter", "pecher", "fabriquer", "cuisiner", "parler", "offrir"}
    for act in required_player_actions - player_anims:
        errs.append(issue(ERROR, "anim.action_missing", "joueur_jardinier",
                          f"action '{act}' sans animation"))
    return errs


# =============================================================================
# 11. VALIDATION DE CONNECTIVITÉ (graphe)
# =============================================================================

def validate_connectivity(state: dict) -> list[dict]:
    errs: list[dict] = []
    conn = state["connectivity"]
    mapping = {
        "orphans": ("conn.orphan", ERROR, "entité orpheline (aucune relation)"),
        "unreachable": ("conn.unreachable", ERROR, "entité inatteignable depuis le départ"),
        "objects_no_usage": ("conn.object_no_usage", ERROR, "objet sans usage réel"),
        "recipes_no_input": ("conn.recipe_no_input", ERROR, "recette sans ingrédient"),
        "recipes_no_output": ("conn.recipe_no_output", ERROR, "recette sans résultat"),
        "npcs_no_routine": ("conn.npc_no_routine", WARNING, "PNJ sans routine"),
        "npcs_no_interaction": ("conn.npc_no_interaction", WARNING, "PNJ sans interaction"),
        "resources_no_producer": ("conn.resource_no_producer", ERROR, "ressource sans producteur"),
        "resources_no_consumer": ("conn.resource_no_consumer", ERROR, "ressource sans consommateur"),
        "secrets_no_discovery": ("conn.secret_no_discovery", ERROR, "secret sans découverte"),
        "events_unreachable": ("conn.event_unreachable", ERROR, "événement inatteignable"),
        "systems_isolated": ("conn.system_isolated", WARNING, "système isolé"),
        "weak_usage": ("conn.weak_usage", WARNING, "entité sans relation d'usage forte"),
    }
    for key, (code, sev, msg) in mapping.items():
        for ent in conn.get(key, []):
            errs.append(issue(sev, code, ent, msg))
    return errs


# =============================================================================
# EXÉCUTION DE TOUS LES VALIDATEURS
# =============================================================================

VALIDATORS = [
    ("structurelle", validate_structural),
    ("schemas", validate_schemas),
    ("encodage", validate_encoding),
    ("references", validate_references),
    ("canonique", validate_canonical),
    ("logique", validate_logical),
    ("narrative", validate_narrative),
    ("economique", validate_economic),
    ("temporelle", validate_temporal),
    ("progression", validate_progression),
    ("maps", validate_maps),
    ("collisions", validate_collisions),
    ("placement", validate_placement),
    ("assets", validate_assets),
    ("animations", validate_animations),
    ("connectivite", validate_connectivity),
]


def run_all(state: dict | None = None) -> dict[str, Any]:
    state = state or load_state()
    results = {}
    all_issues: list[dict] = []
    for name, fn in VALIDATORS:
        issues = fn(state)
        results[name] = issues
        all_issues.extend(issues)
    errors = [i for i in all_issues if i["severity"] == ERROR]
    warnings = [i for i in all_issues if i["severity"] == WARNING]
    return {
        "passed": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "info_count": len([i for i in all_issues if i["severity"] == INFO]),
        "by_validator": {k: len(v) for k, v in results.items()},
        "issues": all_issues,
        "results": results,
    }


def write_report(report: dict) -> Path:
    from .common import write_text, versioned_envelope, write_json
    write_json(DIRS["reports"] / "validation.json",
               versioned_envelope(report, kind="validation_report"))
    lines = ["# Rapport de validation", "",
             f"- Statut global : **{'SUCCÈS' if report['passed'] else 'ÉCHEC'}**",
             f"- Erreurs : {report['error_count']}",
             f"- Avertissements : {report['warning_count']}", "",
             "## Par validateur", ""]
    for k, v in report["by_validator"].items():
        lines.append(f"- {k} : {v} problème(s)")
    if report["issues"]:
        lines += ["", "## Détail des problèmes", "",
                  "| Sévérité | Code | Entité | Message |",
                  "| --- | --- | --- | --- |"]
        for i in report["issues"][:500]:
            lines.append(f"| {i['severity']} | {i['code']} | {i['entity']} | "
                         f"{i['message'].replace(chr(10),' ')} |")
    return write_text(DIRS["reports"] / "validation_report.md", "\n".join(lines))


if __name__ == "__main__":
    rep = run_all()
    write_report(rep)
    print("passed:", rep["passed"], "errors:", rep["error_count"],
          "warnings:", rep["warning_count"])
    for k, v in rep["by_validator"].items():
        if v:
            print(f"  {k}: {v}")
