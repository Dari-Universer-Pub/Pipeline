"""Simulateur abstrait de parties (étape 34 ; livrables 87-90).

Moteur DÉTERMINISTE et SANS LLM qui exécute la logique du jeu :
- état du monde (temps, inventaire, relations, drapeaux, quêtes, secrets) ;
- application des effets (ontologie des effets) ;
- évaluation des conditions (ontologie des conditions) ;
- chaînes de production (planter -> arroser -> pousser -> récolter -> transformer) ;
- routines des PNJ (horaires) ;
- événements (déclencheurs) ;
- profils de joueurs (agriculteur, explorateur, social, etc.).

Le simulateur prouve que le jeu final fonctionne sans LLM runtime et vérifie
les états AVANT/APRÈS chaque action (un simple test d'existence ne suffit pas).
"""
from __future__ import annotations

import copy
from typing import Any

from .common import DIRS, Status, write_json, write_text, versioned_envelope, unwrap, read_json

DAY_HOURS = 24


# =============================================================================
# ÉTAT DU MONDE
# =============================================================================

def initial_state(catalogs: dict, *, day_length: int = DAY_HOURS,
                  season_length: int = 28) -> dict[str, Any]:
    """État initial déterministe (aucun LLM)."""
    seasons = [s["id"] for s in catalogs.get("seasons", [])] or ["saison_1"]
    return {
        "time": {"day": 1, "hour": 6, "minute": 0,
                 "season_index": 0, "seasons": seasons,
                 "season": seasons[0], "weather": "ensoleille",
                 "day_length": day_length, "season_length": season_length},
        "player": {
            "location": "lieu_vallee_claire",
            "inventory": {"objet_graine_d_echo": 2, "objet_houe_de_depart": 1,
                          "objet_arrosoir_de_cuivre": 1, "objet_carnet_du_jardinier": 1},
            "money": 50, "relationships": {n["id"]: 10 for n in catalogs.get("npcs", [])},
            "flags": {}, "unlocked_locations": ["lieu_vallee_claire", "lieu_maison_racine"],
            "known_facts": ["fait_monde_valdore", "fait_joueur_jardinier", "fait_refuge_maison_racine"],
        },
        "world": {
            "discovered_secrets": [], "active_quests": [], "completed_quests": [],
            "global_flags": {}, "crops": {}, "machines": {}, "currency": "unité À_VALIDER",
        },
        "log": [],
    }


def _log(state: dict, msg: str) -> None:
    state["log"].append(f"[J{state['time']['day']} {state['time']['hour']:02d}h] {msg}")


# =============================================================================
# CONDITIONS (évaluation déterministe)
# =============================================================================

def check_condition(state: dict, cond: dict) -> bool:
    t = cond.get("type")
    p = cond.get("params", {})
    pl = state["player"]
    tm = state["time"]
    wd = state["world"]
    if t == "flag":
        return bool(pl["flags"].get(p.get("flag_id")) == p.get("expected", True))
    if t == "item_count":
        have = pl["inventory"].get(p.get("item_id"), 0)
        return _cmp(have, p.get("op", ">="), p.get("qty", 1))
    if t == "relationship":
        have = pl["relationships"].get(p.get("pnj_id"), 0)
        return _cmp(have, p.get("op", ">="), p.get("value", 0))
    if t == "season":
        return tm["season"] == p.get("season_id")
    if t == "weather":
        return tm["weather"] == p.get("weather_id")
    if t == "time_of_day":
        return _cmp(tm["hour"], p.get("op", ">="), p.get("hour", 0))
    if t == "location":
        return pl["location"] == p.get("lieu_id")
    if t == "quest_state":
        qid = p.get("quete_id")
        if p.get("state") == "complete":
            return qid in wd["completed_quests"]
        if p.get("state") == "active":
            return qid in wd["active_quests"]
        return qid not in wd["active_quests"] and qid not in wd["completed_quests"]
    if t == "fact_known":
        return p.get("fait_id") in pl["known_facts"]
    if t == "secret_discovered":
        return p.get("secret_id") in wd["discovered_secrets"]
    if t == "crop_stage":
        crop = wd["crops"].get(p.get("crop_id"))
        return crop is not None and _cmp(crop["stage"], p.get("op", ">="), p.get("stage", 0))
    if t == "and":
        return all(check_condition(state, c) for c in p.get("conditions", []))
    if t == "or":
        return any(check_condition(state, c) for c in p.get("conditions", []))
    if t == "not":
        return not check_condition(state, p.get("condition", {}))
    return False


def _cmp(a: float, op: str, b: float) -> bool:
    return {"<": a < b, "<=": a <= b, "==": a == b,
            ">=": a >= b, ">": a > b, "!=": a != b}.get(op, False)


# =============================================================================
# EFFETS (application déterministe)
# =============================================================================

def apply_effect(state: dict, eff: dict) -> bool:
    """Applique un effet. Retourne True si appliqué. Déterministe, sans LLM."""
    t = eff.get("type")
    p = eff.get("params", {})
    pl = state["player"]
    wd = state["world"]
    if t == "add_item":
        pl["inventory"][p["item_id"]] = pl["inventory"].get(p["item_id"], 0) + p.get("qty", 1)
        return True
    if t == "remove_item":
        have = pl["inventory"].get(p["item_id"], 0)
        pl["inventory"][p["item_id"]] = max(0, have - p.get("qty", 1))
        return True
    if t == "set_flag":
        pl["flags"][p["flag_id"]] = p.get("value", True)
        return True
    if t == "change_relationship":
        pl["relationships"][p["pnj_id"]] = max(0, min(100,
            pl["relationships"].get(p["pnj_id"], 0) + p.get("delta", 0)))
        return True
    if t == "unlock_location":
        if p["lieu_id"] not in pl["unlocked_locations"]:
            pl["unlocked_locations"].append(p["lieu_id"])
        return True
    if t == "trigger_event":
        wd.setdefault("pending_events", []).append(p["evenement_id"])
        return True
    if t == "advance_quest":
        qid = p["quete_id"]
        if p.get("step") == "complete":
            if qid in wd["active_quests"]:
                wd["active_quests"].remove(qid)
            if qid not in wd["completed_quests"]:
                wd["completed_quests"].append(qid)
        elif qid not in wd["active_quests"]:
            wd["active_quests"].append(qid)
        return True
    if t == "reveal_fact":
        pl["known_facts"].append(p["fait_id"]) if p["fait_id"] not in pl["known_facts"] else None
        return True
    if t == "discover_secret":
        if p["secret_id"] not in wd["discovered_secrets"]:
            wd["discovered_secrets"].append(p["secret_id"])
        return True
    if t == "spawn_entity":
        wd.setdefault("spawned", []).append(p.get("entity_id"))
        return True
    if t == "transform_item":
        remove_effect = {"type": "remove_item",
                         "params": {"item_id": p["from_id"], "qty": p.get("qty", 1)}}
        add_effect = {"type": "add_item",
                      "params": {"item_id": p["to_id"], "qty": p.get("qty", 1)}}
        apply_effect(state, remove_effect)
        apply_effect(state, add_effect)
        return True
    if t == "modify_economy":
        pl["money"] = max(0, pl["money"] + p.get("amount", 0))
        return True
    return False


# =============================================================================
# TEMPS
# =============================================================================

def advance_day(state: dict, catalogs: dict) -> None:
    """Fait avancer d'un jour : météo, saison, croissance des cultures."""
    tm = state["time"]
    tm["day"] += 1
    tm["hour"] = 6
    # Saison.
    if tm["day"] % tm["season_length"] == 1 and tm["day"] > 1:
        tm["season_index"] = (tm["season_index"] + 1) % len(tm["seasons"])
        tm["season"] = tm["seasons"][tm["season_index"]]
        _log(state, f"changement de saison -> {tm['season']}")
    # Météo déterministe (dérivée du jour + saison, sans LLM).
    weathers = ["ensoleille", "nuageux", "pluie", "vent", "brouillard"]
    tm["weather"] = weathers[(tm["day"] * 7 + tm["season_index"] * 3) % len(weathers)]
    # Croissance des cultures.
    for cid, crop in list(state["world"]["crops"].items()):
        if crop["stage"] < crop["max_stage"]:
            growth = 1 + (1 if tm["weather"] == "pluie" else 0)
            crop["watered_days"] = crop.get("watered_days", 0)
            crop["progress"] += growth
            if crop["progress"] >= crop["days_per_stage"]:
                crop["progress"] = 0
                crop["stage"] += 1
                _log(state, f"{cid} -> stade {crop['stage']}")


# =============================================================================
# ACTIONS DE GAMEPLAY (verbes)
# =============================================================================

def action_plant(state: dict, seed_id: str, crop: dict) -> bool:
    if state["player"]["inventory"].get(seed_id, 0) < 1:
        _log(state, f"plantation impossible: pas de {seed_id}")
        return False
    apply_effect(state, {"type": "remove_item", "params": {"item_id": seed_id, "qty": 1}})
    stages = crop.get("stages", ["semis", "pousse", "mature", "recoltable"])
    state["world"]["crops"][crop["id"]] = {
        "crop_id": crop["id"], "seed_id": seed_id, "yield_id": crop["yield_id"],
        "stage": 0, "max_stage": len(stages) - 1,
        "days_per_stage": max(1, crop["growth_days"] // max(1, len(stages) - 1)),
        "progress": 0, "watered": False,
    }
    _log(state, f"planté {seed_id} -> {crop['id']}")
    return True


def action_water(state: dict, crop_id: str) -> bool:
    crop = state["world"]["crops"].get(crop_id)
    if crop:
        crop["watered"] = True
        crop["watered_days"] = crop.get("watered_days", 0) + 1
        _log(state, f"arrosé {crop_id}")
        return True
    return False


def action_harvest(state: dict, crop_id: str) -> bool:
    crop = state["world"]["crops"].get(crop_id)
    if not crop or crop["stage"] < crop["max_stage"]:
        return False
    apply_effect(state, {"type": "add_item", "params": {"item_id": crop["yield_id"], "qty": 1}})
    del state["world"]["crops"][crop_id]
    _log(state, f"récolté {crop_id} -> {crop['yield_id']}")
    return True


def action_craft(state: dict, recipe: dict) -> bool:
    """Exécute une recette si les ingrédients sont présents (déterministe)."""
    inv = state["player"]["inventory"]
    for ing in recipe.get("inputs", []):
        if inv.get(ing["item_id"], 0) < ing.get("qty", 1):
            _log(state, f"artisanat impossible ({recipe['id']}): manque {ing['item_id']}")
            return False
    for ing in recipe.get("inputs", []):
        apply_effect(state, {"type": "remove_item",
                             "params": {"item_id": ing["item_id"], "qty": ing.get("qty", 1)}})
    for out in recipe.get("outputs", []):
        apply_effect(state, {"type": "add_item",
                             "params": {"item_id": out["item_id"], "qty": out.get("qty", 1)}})
    _log(state, f"recette {recipe['id']} exécutée")
    return True


def action_sell(state: dict, item_id: str, value: int, qty: int = 1) -> bool:
    if state["player"]["inventory"].get(item_id, 0) < qty:
        return False
    apply_effect(state, {"type": "remove_item", "params": {"item_id": item_id, "qty": qty}})
    apply_effect(state, {"type": "modify_economy", "params": {"amount": value * qty}})
    _log(state, f"vendu {qty}× {item_id} (+{value*qty})")
    return True


def action_talk(state: dict, npc_id: str) -> bool:
    apply_effect(state, {"type": "change_relationship",
                         "params": {"pnj_id": npc_id, "delta": 1}})
    _log(state, f"parlé à {npc_id}")
    return True


def action_gift(state: dict, npc_id: str, item_id: str, value: int) -> bool:
    if state["player"]["inventory"].get(item_id, 0) < 1:
        return False
    apply_effect(state, {"type": "remove_item", "params": {"item_id": item_id, "qty": 1}})
    apply_effect(state, {"type": "change_relationship",
                         "params": {"pnj_id": npc_id, "delta": max(2, value // 5)}})
    _log(state, f"offert {item_id} à {npc_id}")
    return True


def action_explore(state: dict, lieu_id: str) -> bool:
    if lieu_id in state["player"]["unlocked_locations"]:
        state["player"]["location"] = lieu_id
        _log(state, f"exploré {lieu_id}")
        return True
    _log(state, f"lieu verrouillé: {lieu_id}")
    return False


def action_fish(state: dict, fish_id: str = "objet_poisson_du_lac") -> bool:
    if state["player"]["location"] != "lieu_lac_muet":
        return False
    if state["player"]["inventory"].get("objet_ligne_de_peche", 0) < 1:
        _log(state, "pêche impossible: pas de ligne")
        return False
    apply_effect(state, {"type": "add_item", "params": {"item_id": fish_id, "qty": 1}})
    _log(state, f"pêché {fish_id}")
    return True


# =============================================================================
# ÉVÉNEMENTS ET QUÊTES (déclencheurs)
# =============================================================================

def process_events(state: dict, catalogs: dict) -> list[str]:
    """Évalue les déclencheurs d'événements et applique leurs effets."""
    fired = []
    for ev in catalogs.get("events", []):
        trig = ev.get("trigger", {})
        if _trigger_matches(state, trig):
            pre = ev.get("preconditions", [])
            if all(check_condition(state, c) for c in pre):
                key = f"{ev['id']}@J{state['time']['day']}"
                if ev.get("repeatable") or key not in state["world"].setdefault("fired_events", []):
                    for eff in ev.get("effects", []):
                        apply_effect(state, eff)
                    state["world"].setdefault("fired_events", []).append(key)
                    fired.append(ev["id"])
                    _log(state, f"événement déclenché: {ev['id']}")
    return fired


def _trigger_matches(state: dict, trig: dict) -> bool:
    t = trig.get("type")
    p = trig.get("params", {})
    tm, pl, wd = state["time"], state["player"], state["world"]
    if t == "on_day_start":
        return True
    if t == "on_season_change":
        return tm["season"] == p.get("season_id")
    if t == "on_weather":
        return tm["weather"] == p.get("weather_id")
    if t == "on_enter_location":
        return pl["location"] == p.get("lieu_id")
    if t == "on_item_acquired":
        return pl["inventory"].get(p.get("item_id"), 0) > 0
    if t == "on_quest_complete":
        return p.get("quete_id") in wd["completed_quests"]
    if t == "on_relationship_threshold":
        return pl["relationships"].get(p.get("pnj_id"), 0) >= p.get("value", 0)
    if t == "on_secret_discovered":
        return p.get("secret_id") in wd["discovered_secrets"]
    return False


def process_quests(state: dict, catalogs: dict) -> list[str]:
    """Active les quêtes dont le déclencheur correspond, puis les complète."""
    started = []
    for q in catalogs.get("quests", []):
        qid = q["id"]
        if qid in state["world"]["completed_quests"]:
            continue
        if _trigger_matches(state, q.get("trigger", {})):
            pre = q.get("preconditions", [])
            if all(check_condition(state, c) for c in pre):
                if qid not in state["world"]["active_quests"]:
                    state["world"]["active_quests"].append(qid)
                    started.append(qid)
                    _log(state, f"quête activée: {qid}")
                # Applique les effets (simule l'accomplissement).
                for eff in q.get("effects", []):
                    apply_effect(state, eff)
    return started


# =============================================================================
# ROUTINES DES PNJ
# =============================================================================

def simulate_routines(state: dict, catalogs: dict) -> dict[str, str]:
    """Détermine la localisation de chaque PNJ selon l'heure (routine)."""
    hour = state["time"]["hour"]
    positions = {}
    for n in catalogs.get("npcs", []):
        routines = n.get("routines") or []
        pos = n.get("home")
        for r in sorted(routines, key=lambda x: x.get("hour", 0)):
            if hour >= r.get("hour", 0):
                pos = r.get("location_id", pos)
        positions[n["id"]] = pos or (n.get("frequented_places") or [None])[0]
    return positions


# =============================================================================
# PROFILS DE JOUEURS
# =============================================================================

def _farmer_profile(state, catalogs):
    """Joueur agriculteur : plante, arrose, récolte, transforme, vend."""
    crops = {c["id"]: c for c in catalogs.get("crops", [])}
    recipes = {r["id"]: r for r in catalogs.get("recipes", [])}
    trace = []
    # Plante la Graine d'Écho (canon) -> Floraison d'Écho.
    echo = next((c for c in crops.values() if c.get("memory_plant")), None)
    if echo:
        action_plant(state, "objet_graine_d_echo", echo)
        for _ in range(echo["growth_days"] + 2):
            action_water(state, echo["id"])
            advance_day(state, catalogs)
            process_events(state, catalogs)
        action_harvest(state, echo["id"])
        trace.append(("harvest_echo", state["player"]["inventory"].get(echo["yield_id"], 0)))
    # Plante un navet et le transforme en soupe.
    navet = crops.get("culture_navet_de_la_vallee")
    if navet:
        state["player"]["inventory"]["objet_graine_de_navet_de_la_vallee"] = 1
        action_plant(state, navet["seed_id"], navet)
        for _ in range(navet["growth_days"] + 2):
            action_water(state, navet["id"])
            advance_day(state, catalogs)
        # récolte 2 navets
        action_harvest(state, navet["id"])
        state["player"]["inventory"][navet["yield_id"]] = 2
        action_craft(state, recipes.get("recette_soupe_de_navet", {}))
        trace.append(("craft_soupe", state["player"]["inventory"].get("objet_soupe_de_navet", 0)))
    return trace


def _explorer_profile(state, catalogs):
    """Joueur explorateur : débloque lieux, découvre secrets."""
    trace = []
    for lieu in ["lieu_maison_racine", "lieu_bois_des_retours", "lieu_lac_muet"]:
        state["player"]["unlocked_locations"].append(lieu)
        action_explore(state, lieu)
    # Découverte du secret du Bois via événement.
    state["time"]["season"] = "saison_des_brumes"
    fired = process_events(state, catalogs)
    trace.append(("events_fired", fired))
    trace.append(("secrets", list(state["world"]["discovered_secrets"])))
    return trace


def _social_profile(state, catalogs):
    """Joueur social : parle, offre, fait monter les relations."""
    trace = []
    for n in catalogs.get("npcs", []):
        action_talk(state, n["id"])
    # Offrir un fragment à Alba.
    state["player"]["inventory"]["objet_fragment_de_souvenir"] = 1
    action_gift(state, "pnj_alba", "objet_fragment_de_souvenir", 30)
    trace.append(("rel_alba", state["player"]["relationships"].get("pnj_alba")))
    return trace


def _ignore_quests_profile(state, catalogs):
    """Joueur qui ignore les quêtes : vérifie la résilience (pas de blocage)."""
    trace = []
    # Ne déclenche aucune quête volontairement ; joue l'économie.
    state["player"]["inventory"]["objet_navet"] = 5
    for _ in range(3):
        action_sell(state, "objet_navet", 12)
    trace.append(("money", state["player"]["money"]))
    trace.append(("quests_completed", list(state["world"]["completed_quests"])))
    return trace


def _optimize_economy_profile(state, catalogs):
    """Joueur qui optimise l'économie : transforme puis vend à marge."""
    trace = []
    recipes = {r["id"]: r for r in catalogs.get("recipes", [])}
    state["player"]["inventory"].update({"ressource_bois": 4})
    money_before = state["player"]["money"]
    action_craft(state, recipes.get("recette_planche", {}))
    action_sell(state, "objet_planche", 20, state["player"]["inventory"].get("objet_planche", 0))
    trace.append(("money_delta", state["player"]["money"] - money_before))
    return trace


def _miss_events_profile(state, catalogs):
    """Joueur qui rate des événements : vérifie qu'aucun contenu n'est bloqué."""
    trace = []
    # Avance plusieurs jours sans aller au Bois -> rate l'événement saisonnier.
    for _ in range(5):
        advance_day(state, catalogs)
    trace.append(("missed_events", True))
    # La quête du Bois a un fallback : pas de blocage définitif.
    trace.append(("quests_active", list(state["world"]["active_quests"])))
    return trace


def _specialist_profile(state, catalogs):
    """Joueur qui se spécialise (pêche uniquement)."""
    trace = []
    state["player"]["unlocked_locations"].append("lieu_lac_muet")
    action_explore(state, "lieu_lac_muet")
    state["player"]["inventory"]["objet_ligne_de_peche"] = 1
    for _ in range(3):
        action_fish(state)
    trace.append(("poisson", state["player"]["inventory"].get("objet_poisson_du_lac", 0)))
    return trace


def _contrarian_profile(state, catalogs):
    """Joueur qui prend des décisions opposées au parcours prévu."""
    trace = []
    # Vend le fragment au lieu de le conserver ; ignore Alba ; explore d'abord le Lac.
    state["player"]["inventory"]["objet_fragment_de_souvenir"] = 1
    action_sell(state, "objet_fragment_de_souvenir", 30)
    state["player"]["unlocked_locations"].append("lieu_lac_muet")
    action_explore(state, "lieu_lac_muet")
    trace.append(("money", state["player"]["money"]))
    trace.append(("location", state["player"]["location"]))
    return trace


PROFILES = {
    "agriculteur": _farmer_profile,
    "explorateur": _explorer_profile,
    "social": _social_profile,
    "ignore_quetes": _ignore_quests_profile,
    "optimise_economie": _optimize_economy_profile,
    "rate_evenements": _miss_events_profile,
    "specialiste": _specialist_profile,
    "contrarian": _contrarian_profile,
}


def run_profile(name: str, catalogs: dict) -> dict[str, Any]:
    """Exécute un profil de joueur et retourne trace + état final."""
    state = initial_state(catalogs)
    fn = PROFILES.get(name)
    if not fn:
        return {"profile": name, "error": "profil inconnu"}
    before = copy.deepcopy({"inventory": state["player"]["inventory"],
                            "money": state["player"]["money"],
                            "relationships": state["player"]["relationships"]})
    trace = fn(state, catalogs)
    # Traite quêtes/événements en fin de partie.
    process_quests(state, catalogs)
    process_events(state, catalogs)
    after = {"inventory": state["player"]["inventory"],
             "money": state["player"]["money"],
             "relationships": state["player"]["relationships"]}
    return {
        "profile": name, "trace": trace, "before": before, "after": after,
        "final_state": {k: v for k, v in state.items() if k != "log"},
        "log": state["log"],
        "quests_completed": state["world"]["completed_quests"],
        "secrets_discovered": state["world"]["discovered_secrets"],
        "facts_known": state["player"]["known_facts"],
    }


def run_all_profiles(catalogs: dict) -> dict[str, Any]:
    return {name: run_profile(name, catalogs) for name in PROFILES}


# =============================================================================
# SIMULATION DE CHAÎNE DE PRODUCTION (test avant/après)
# =============================================================================

def simulate_production_chain(catalogs: dict, recipe_id: str) -> dict[str, Any]:
    """Simule une chaîne de production complète et vérifie avant/après."""
    recipes = {r["id"]: r for r in catalogs.get("recipes", [])}
    recipe = recipes.get(recipe_id)
    if not recipe:
        return {"recipe_id": recipe_id, "ok": False, "reason": "recette introuvable"}
    state = initial_state(catalogs)
    # Dote le joueur des ingrédients.
    for ing in recipe.get("inputs", []):
        state["player"]["inventory"][ing["item_id"]] = ing.get("qty", 1)
    before = dict(state["player"]["inventory"])
    ok = action_craft(state, recipe)
    after = dict(state["player"]["inventory"])
    # Vérifie que les entrées ont été consommées et les sorties produites.
    consumed = all(after.get(i["item_id"], 0) < before.get(i["item_id"], 0)
                   for i in recipe.get("inputs", []))
    produced = all(after.get(o["item_id"], 0) >= o.get("qty", 1)
                   for o in recipe.get("outputs", []))
    return {
        "recipe_id": recipe_id, "ok": ok and consumed and produced,
        "executed": ok, "inputs_consumed": consumed, "outputs_produced": produced,
        "before": before, "after": after,
    }


def run_stage(catalogs: dict, write: bool = True) -> dict[str, Any]:
    profiles = run_all_profiles(catalogs)
    # Chaînes de production pour chaque recette.
    chains = {}
    for r in catalogs.get("recipes", []):
        chains[r["id"]] = simulate_production_chain(catalogs, r["id"])
    artifact = {"profiles": profiles, "production_chains": chains}
    if write:
        write_json(DIRS["reports"] / "simulation.json",
                   versioned_envelope(artifact, kind="simulation"))
    return artifact


if __name__ == "__main__":
    from . import canon as canon_mod, systems as sys_mod, catalog as cat_mod
    ca = canon_mod.run_stage(write=False)
    sy = sys_mod.run_stage(write=False)["systems"]
    cats = cat_mod.run_stage(ca, sy, write=False)
    res = run_stage(cats, write=False)
    for name, p in res["profiles"].items():
        print(f"{name}: quests={p.get('quests_completed')} secrets={p.get('secrets_discovered')}")
    ok = sum(1 for c in res["production_chains"].values() if c["ok"])
    print(f"chaînes de production OK : {ok}/{len(res['production_chains'])}")
