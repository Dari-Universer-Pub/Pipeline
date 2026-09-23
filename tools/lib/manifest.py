"""Génération des manifests (étapes 21-25, 36-49).

Un manifest est une SPÉCIFICATION DE PRODUCTION : il décrit ce qui doit être
produit (assets, animations, maps, placement, etc.) sans le produire. Aucun
asset n'est généré ici ; seuls des manifests et exemples minimaux le sont.

Dérivations clés :
- assets  = entités × états × directions × variantes, regroupés par FAMILLE ;
- animations = actions/états × directions, synchronisées avec la logique ;
- maps = terrain + placement + navigation + transitions + spawn ;
- placement/nav/transitions = règles déduites des terrains et des systèmes.

Chaque entrée de manifest embarque sa justification, ses dépendances, ses
critères de validation et les tests qui la couvrent.
"""
from __future__ import annotations

from typing import Any

from .common import (
    DIRS, Status, make_id, write_json, versioned_envelope, derive_seed, fingerprint,
)

# --- Style visuel global (déduit du brief : contemplatif, mystérieux, chaud) --

STYLE = "pixel art 16×16, contours souples, mise à l'échelle entière, ambiance contemplative et chaleureuse"
PALETTE = ["#2e2a24", "#6b5d4f", "#a89279", "#d9c7a3",
           "#7fae6b", "#c9a86a", "#5b7d8c", "#e8dcc0"]
RESOLUTION = "16px/tuile, échelle entière x2..x4"

# Directions du jeu (2D vue du dessus).
DIRS4 = ["down", "up", "left", "right"]


# =============================================================================
# ANIMATIONS : dérivées des états/actions × directions
# =============================================================================

# (action, directions, frames, fps, loop, impact_frame, logic_effect)
PLAYER_ACTIONS = [
    ("idle", DIRS4, 3, 6, True, None, None),
    ("marche", DIRS4, 4, 8, True, None, None),
    ("labourer", DIRS4, 4, 6, False, 3, "effet:sol_laboure"),
    ("arroser", DIRS4, 4, 6, False, 3, "effet:sol_arrose"),
    ("planter", DIRS4, 3, 6, False, 2, "effet:graine_plantee"),
    ("recolter", DIRS4, 4, 6, False, 3, "effet:recolte"),
    ("pecher", DIRS4, 6, 4, False, 5, "effet:prise_poisson"),
    ("fabriquer", [None], 4, 6, False, 3, "effet:artisanat"),
    ("cuisiner", [None], 4, 6, False, 3, "effet:cuisine"),
    ("parler", [None], 2, 4, False, None, None),
    ("offrir", [None], 3, 6, False, 2, "effet:don_relation"),
]

NPC_ACTIONS = [
    ("idle", DIRS4, 3, 6, True, None, None),
    ("marche", DIRS4, 4, 8, True, None, None),
    ("interaction", [None], 3, 6, False, None, None),
]

CREATURE_ACTIONS = {
    "animal": [("nage", DIRS4, 4, 6, True, None, None),
               ("reaction", [None], 2, 6, False, None, None)],
    "creature": [("flotte", DIRS4, 4, 4, True, None, None),
                 ("apparition", [None], 5, 6, False, 4, "effet:apparition_echo")],
}

CROP_STAGES = ["semis", "pousse", "mature", "recoltable"]
MACHINE_STATES = ["inactif", "actif"]


def build_animations(catalogs: dict) -> list[dict]:
    """Déduit toutes les animations depuis les entités et leurs actions/états."""
    anims: list[dict] = []

    def add(entity_id, action, direction, frames, fps, loop, impact, effect,
            entity_type, required_assets, transitions=None, status=Status.DEDUITE):
        aid = make_id("anim", f"{entity_id}_{action}" + (f"_{direction}" if direction else ""))
        anims.append({
            "id": aid,
            "display_name": f"{action} ({direction or 'sans direction'}) — {entity_id}",
            "status": status,
            "entity_id": entity_id, "entity_type": entity_type,
            "state_or_action": action, "direction": direction,
            "frames": frames, "fps": fps, "loop": loop,
            "impact_event": impact, "logic_effect": effect,
            "transitions": transitions or [],
            "required_assets": required_assets,
            "source": "dérivé des états/actions (constraints#Architecture)",
            "justification": f"Animation requise par l'action '{action}' de {entity_id}.",
            "derivation": {
                "why": f"Synchronise le visuel de '{action}' avec la logique.",
                "system": entity_type,
                "impact": impact or "aucun",
                "logic_effect": effect or "aucun",
                "tests": "test_animation_action, test_animation_asset, test_sync_impact",
            },
        })

    # Joueur.
    player_id = "joueur_jardinier"
    player_sheet = make_id("asset", "spritesheet_jardinier")
    for action, directions, frames, fps, loop, impact, effect in PLAYER_ACTIONS:
        for d in directions:
            add(player_id, action, d, frames, fps, loop, impact, effect,
                "joueur", [player_sheet],
                transitions=["idle"] if action != "idle" else ["marche"])

    # PNJ.
    for n in catalogs.get("npcs", []):
        sheet = make_id("asset", f"spritesheet_{n['id']}")
        for action, directions, frames, fps, loop, impact, effect in NPC_ACTIONS:
            for d in directions:
                add(n["id"], action, d, frames, fps, loop, impact, effect,
                    "pnj", [sheet])

    # Créatures.
    for c in catalogs.get("creatures", []):
        sheet = make_id("asset", f"spritesheet_{c['id']}")
        for action, directions, frames, fps, loop, impact, effect in CREATURE_ACTIONS.get(c["kind"], []):
            for d in directions:
                add(c["id"], action, d, frames, fps, loop, impact, effect,
                    "creature", [sheet])

    # Cultures : transition entre stades + récolte.
    for cr in catalogs.get("crops", []):
        stage_assets = [make_id("asset", f"{cr['id']}_{s}") for s in CROP_STAGES]
        for i, s in enumerate(CROP_STAGES):
            nxt = CROP_STAGES[i + 1] if i + 1 < len(CROP_STAGES) else None
            add(cr["id"], f"croissance_{s}", None, 2, 2, False, None,
                f"effet:stade_{nxt}" if nxt else None, "culture",
                [stage_assets[i]], transitions=[f"croissance_{nxt}"] if nxt else [])
        add(cr["id"], "recolte", None, 3, 6, False, 2, "effet:recolte",
            "culture", [stage_assets[-1]])

    # Machines : état actif (boucle) + impact.
    for m in catalogs.get("machines", []):
        m_assets = [make_id("asset", f"{m['id']}_{st}") for st in MACHINE_STATES]
        add(m["id"], "inactif", None, 1, 1, False, None, None, "machine", [m_assets[0]])
        add(m["id"], "actif", None, 4, 6, True, 3, f"effet:{m['function']}_fin",
            "machine", [m_assets[1]], transitions=["inactif"])

    return anims


# =============================================================================
# ASSETS : dérivés des entités × états × directions × variantes, par FAMILLE
# =============================================================================

TERRAIN_BY_FUNCTION = {
    "farmland": ["herbe", "sol_meuble", "terre"],
    "refuge": ["plancher", "bois", "pierre"],
    "secret": ["feuillage", "terre", "herbe"],
    "fishing_spot": ["eau", "pont", "herbe"],
    "poi": ["terre", "herbe"],
}


def _asset(aid, name, entity_id, family, kind, w, h, style, palette,
           variants, usage_rules, status, source, justification, validation):
    return {
        "id": aid, "display_name": name, "status": status,
        "entity_id": entity_id, "family": family, "kind": kind,
        "function": family, "width": w, "height": h,
        "resolution": RESOLUTION, "style": style, "palette": palette,
        "variants": variants, "usage_rules": usage_rules,
        "fingerprint": fingerprint({"id": aid, "w": w, "h": h, "family": family,
                                    "variants": sorted(variants)}),
        "source": source, "justification": justification, "validation": validation,
    }


def build_assets(catalogs: dict, animations: list[dict]) -> list[dict]:
    """Déduit les assets par familles cohérentes (jamais d'asset isolé)."""
    assets: list[dict] = []
    icon_val = {"dimensions": "16×16", "transparency": True, "palette": "PALETTE",
                "unique_fingerprint": True}

    # Famille OBJETS : 1 icône par objet.
    for o in catalogs.get("objects", []):
        assets.append(_asset(
            make_id("asset", f"icone_{o['id']}"), f"Icône {o['display_name']}",
            o["id"], "famille_objets", "icone", 16, 16, STYLE, PALETTE,
            ["defaut"], ["inventaire", "sol si droppable"], o["status"],
            "dérivé de l'objet (constraints#Architecture)",
            f"Icône d'inventaire pour {o['display_name']}.", icon_val))

    # Famille OUTILS : sprite monde pour chaque outil.
    for o in catalogs.get("objects", []):
        if o.get("category") == "outil":
            assets.append(_asset(
                make_id("asset", f"sprite_outil_{o['id']}"), f"Sprite outil {o['display_name']}",
                o["id"], "famille_outils", "sprite", 16, 16, STYLE, PALETTE,
                ["main_nue", "en_main"], ["porté par le joueur", "visible en action"],
                o["status"], "dérivé de l'outil (système agriculture/pêche)",
                f"Sprite de l'outil {o['display_name']} tenu par le joueur.", icon_val))

    # Famille CULTURES : 1 sprite par stade + icône graine/récolte.
    for cr in catalogs.get("crops", []):
        for s in CROP_STAGES:
            assets.append(_asset(
                make_id("asset", f"{cr['id']}_{s}"), f"{cr['display_name']} — {s}",
                cr["id"], "famille_cultures", "sprite", 16, 24, STYLE, PALETTE,
                [s], [f"planté sur sol_meuble", f"stade {s}"], cr["status"],
                "dérivé des stades de croissance (agriculture)",
                f"Sprite du stade '{s}' de {cr['display_name']}.", icon_val))

    # Famille MACHINES : 1 sprite par état.
    for m in catalogs.get("machines", []):
        for st in MACHINE_STATES:
            assets.append(_asset(
                make_id("asset", f"{m['id']}_{st}"), f"{m['display_name']} — {st}",
                m["id"], "famille_machines", "sprite", 32, 32, STYLE, PALETTE,
                [st], [f"placée dans atelier/lieu dédié", f"état {st}"], m["status"],
                "dérivé des états de la machine (artisanat/cuisine/mémoire)",
                f"Sprite de la machine {m['display_name']} à l'état '{st}'.", icon_val))

    # Famille PERSONNAGES : spritesheet joueur + PNJ + portrait.
    assets.append(_asset(
        make_id("asset", "spritesheet_jardinier"), "Spritesheet du Jardinier",
        "joueur_jardinier", "famille_personnages", "sprite", 64, 128, STYLE, PALETTE,
        [f"{a}_{d}" for a, ds, *_ in PLAYER_ACTIONS for d in (ds or ["x"])],
        ["4 directions", "actions outillées"], Status.CANONIQUE,
        "joueur canonique (le Jardinier)",
        "Feuille de sprites du personnage joueur (toutes actions/directions).",
        {"dimensions": "64×128 (4×4 frames 16×32)", "transparency": True,
         "unique_fingerprint": True}))
    for n in catalogs.get("npcs", []):
        assets.append(_asset(
            make_id("asset", f"spritesheet_{n['id']}"), f"Spritesheet {n['display_name']}",
            n["id"], "famille_personnages", "sprite", 64, 96, STYLE, PALETTE,
            [f"{a}_{d}" for a, ds, *_ in NPC_ACTIONS for d in (ds or ["x"])],
            ["4 directions", "idle/marche/interaction"], n["status"],
            "dérivé du PNJ (relations)",
            f"Feuille de sprites de {n['display_name']}.",
            {"dimensions": "64×96", "transparency": True, "unique_fingerprint": True}))
        assets.append(_asset(
            make_id("asset", f"portrait_{n['id']}"), f"Portrait {n['display_name']}",
            n["id"], "famille_personnages", "portrait", 64, 64, STYLE, PALETTE,
            ["neutre", "content", "inquiet"], ["dialogue", "carnet"], n["status"],
            "dérivé du PNJ (dialogues)",
            f"Portrait de dialogue pour {n['display_name']}.", icon_val))

    # Famille CRÉATURES.
    for c in catalogs.get("creatures", []):
        assets.append(_asset(
            make_id("asset", f"spritesheet_{c['id']}"), f"Spritesheet {c['display_name']}",
            c["id"], "famille_creatures", "sprite", 32, 32, STYLE, PALETTE,
            ["defaut", "variation_1"], ["dans son habitat"], c["status"],
            "dérivé de la créature (pêche/secrets)",
            f"Feuille de sprites de {c['display_name']}.", icon_val))

    # Famille TERRAINS : 1 tileset par terrain distinct des maps.
    terrains = set()
    for m in catalogs.get("maps", []):
        terrains.update(m.get("terrains", []))
    for t in sorted(terrains):
        assets.append(_asset(
            make_id("asset", f"tileset_{t}"), f"Tileset {t}",
            make_id("map", "terrains"), "famille_terrains", "tileset", 48, 48, STYLE,
            PALETTE, ["sec", "humide", f"par_saison"], ["sol de carte", "9 tuiles (3×3)"],
            Status.DEDUITE, "dérivé des terrains des maps (constraints#Architecture)",
            f"Tileset du terrain '{t}' (variante 3×3 + humide/saison).",
            {"dimensions": "48×48 (3×3 tuiles 16×16)", "transparency": False,
             "unique_fingerprint": True}))

    return assets


def build_transitions(catalogs: dict) -> list[dict]:
    """Manifest des transitions de terrains (règles d'adjacence)."""
    # Paires de terrains adjacents plausibles (déduit des terrains des maps).
    terrains = set()
    for m in catalogs.get("maps", []):
        terrains.update(m.get("terrains", []))
    adjacency = {
        "herbe": ["sol_meuble", "terre", "eau", "feuillage"],
        "sol_meuble": ["herbe", "terre"],
        "terre": ["herbe", "sol_meuble", "feuillage", "pierre"],
        "eau": ["herbe", "pont", "pierre"],
        "pont": ["eau", "herbe", "plancher"],
        "feuillage": ["terre", "herbe"],
        "plancher": ["bois", "pont", "pierre"],
        "bois": ["plancher", "pierre"],
        "pierre": ["terre", "bois", "plancher", "eau"],
    }
    out = []
    seen = set()
    for a, neigh in adjacency.items():
        if a not in terrains:
            continue
        for b in neigh:
            if b not in terrains:
                continue
            pair = tuple(sorted((a, b)))
            if pair in seen:
                continue
            seen.add(pair)
            tid = make_id("transition", f"{pair[0]}_{pair[1]}")
            out.append({
                "id": tid, "display_name": f"Transition {pair[0]} ↔ {pair[1]}",
                "status": Status.DEDUITE, "from_terrain": pair[0], "to_terrain": pair[1],
                "asset_id": make_id("asset", f"transition_{pair[0]}_{pair[1]}"),
                "auto_tile": True, "bitmask": "47-tile ou 16-tile",
                "source": "dérivé de l'adjacence des terrains des maps",
                "justification": f"Les terrains {pair[0]} et {pair[1]} coexistent sur "
                                 f"les maps ; une transition visuelle est requise.",
                "validation": {"auto_tile_complet": True, "sans_couture": True},
            })
    return out


# =============================================================================
# MAPS / PLACEMENT / NAVIGATION
# =============================================================================

def build_map_manifests(catalogs: dict) -> list[dict]:
    """Enrichit les cartes avec régions, zones, chemins, POI, collisions."""
    out = []
    for m in catalogs.get("maps", []):
        mm = dict(m)
        loc_id = m["location_id"]
        func = _location_function(catalogs, loc_id)
        w, h = m["size"]["w"], m["size"]["h"]
        mm["regions"] = [{"id": make_id("region", m["display_name"] + "_principale"),
                          "bounds": {"x": 0, "y": 0, "w": w, "h": h}}]
        mm["zones"] = _zones_for(func, m)
        mm["paths"] = [{"id": make_id("chemin", m["display_name"] + "_central"),
                        "walkable": True, "width": 2}]
        mm["entrances"] = [{"id": make_id("entree", m["display_name"] + "_" + l),
                            "to_map": make_id("map", l), "edge": "bord"}
                           for l in _linked_clean(m)]
        mm["exits"] = [{"id": make_id("sortie", m["display_name"] + "_" + l),
                        "to_map": make_id("map", l)} for l in _linked_clean(m)]
        mm["collisions"] = _collisions_for(func, m)
        mm["points_of_interest"] = _poi_for(catalogs, loc_id)
        mm["buildings"] = ([{"id": make_id("batiment", "Maison-Racine"),
                             "walkable_inside": True}] if func == "refuge" else [])
        mm["secret_zones"] = ([{"id": "secret_clairiere_repetition",
                                 "discovery": "evenement_retour_du_bois"}]
                              if func == "secret" else [])
        mm["resources"] = _resources_for(func)
        mm["spawn_rules"] = _spawn_for(func)
        mm["seasonal_conditions"] = [{"season": s, "effect": "palette/terrain"}
                                     for s in ["saison_des_premieres_pousses",
                                               "saison_des_epis", "saison_des_brumes",
                                               "saison_du_repos"]]
        out.append(mm)
    return out


def _linked_clean(m: dict) -> list[str]:
    return [lm.split("map_", 1)[1].replace("_", " ") for lm in m.get("linked_maps", [])]


def _location_function(catalogs: dict, loc_id: str) -> str:
    for l in catalogs.get("locations", []):
        if l["id"] == loc_id:
            return l.get("function", "poi")
    return "poi"


def _zones_for(func: str, m: dict) -> list[dict]:
    base = {"id": make_id("zone", m["display_name"] + "_explorable"), "walkable": True}
    if func == "farmland":
        return [base, {"id": make_id("zone", "parcelles"), "walkable": True,
                       "cultivable": True, "terrain": "sol_meuble"}]
    if func == "refuge":
        return [base, {"id": make_id("zone", "atelier"), "walkable": True},
                {"id": make_id("zone", "cuisine"), "walkable": True}]
    if func == "secret":
        return [base, {"id": make_id("zone", "clairiere_cachee"), "walkable": True,
                       "hidden": True}]
    if func == "fishing_spot":
        return [base, {"id": make_id("zone", "poste_de_peche"), "walkable": True,
                       "terrain": "pont"}]
    return [base]


def _collisions_for(func: str, m: dict) -> list[dict]:
    solids = {"eau": True, "pierre": True, "bois": True}
    coll = []
    for t in m.get("terrains", []):
        coll.append({"terrain": t, "solid": bool(solids.get(t, False)),
                     "blocks": solids.get(t, False)})
    return coll


def _poi_for(catalogs: dict, loc_id: str) -> list[dict]:
    pois = []
    for l in catalogs.get("locations", []):
        if l.get("parent_id") == loc_id or (l.get("map_id") and l["id"] != loc_id
                                            and l["kind"] in ("interet", "secret", "zone")):
            if l.get("parent_id") == loc_id:
                pois.append({"id": l["id"], "name": l["display_name"],
                             "function": l.get("function")})
    return pois


def _resources_for(func: str) -> list[dict]:
    if func == "secret":
        return [{"resource_id": "ressource_bois", "density": "moyenne"}]
    if func == "fishing_spot":
        return [{"resource_id": "ressource_argile", "density": "faible"}]
    if func == "farmland":
        return [{"resource_id": "ressource_pierre", "density": "faible"}]
    return []


def _spawn_for(func: str) -> list[dict]:
    if func == "fishing_spot":
        return [{"entity_id": "creature_poisson_du_lac", "condition": "zone:eau",
                 "season": "toutes"}]
    if func == "secret":
        return [{"entity_id": "creature_echo_du_bois", "condition": "saison:saison_des_brumes",
                 "season": "saison_des_brumes"}]
    return []


def build_placement_rules(catalogs: dict) -> list[dict]:
    """Règles de placement (terrain autorisé/interdit, densité, saison, etc.)."""
    rules = []

    def rule(rid, what, allowed, forbidden, density, min_dist, cluster, season,
             weather, accessibility, discovery, poi_relation, status, just):
        rules.append({
            "id": make_id("placement", rid), "display_name": f"Placement {what}",
            "status": status, "places": what,
            "allowed_terrain": allowed, "forbidden_terrain": forbidden,
            "density": density, "min_distance": min_dist, "clustering": cluster,
            "season": season, "weather": weather, "accessibility": accessibility,
            "discovery_conditions": discovery, "poi_relation": poi_relation,
            "source": "dérivé des systèmes + contraintes de map",
            "justification": just,
            "validation": {"terrain_respecte": True, "densite_max": True,
                           "distance_min": True, "accessible": True},
        })

    # Cultures -> parcelles (farmland).
    rule("cultures", "culture", ["sol_meuble"], ["eau", "pierre", "plancher", "pont"],
         "haute", 1, "parcelle_contigue", "toutes (selon culture)", "pluie accélère",
         "zone cultivable débloquée", "aucune", "près du Champ de la Vallée Claire",
         Status.DEDUITE, "Les cultures exigent un sol meuble labouré (agriculture).")
    # Machines -> atelier/refuge.
    rule("machines", "machine", ["plancher", "bois"], ["eau", "sol_meuble", "herbe"],
         "faible", 2, "isolé", "toutes", "indépendant", "refuge/atelier",
         "aucune", "dans l'Atelier ou la Cuisine", Status.DEDUITE,
         "Les machines sont placées dans les bâtiments (artisanat/cuisine).")
    # Ressources -> zones d'exploration.
    rule("ressources", "ressource", ["terre", "herbe", "pierre"], ["plancher", "pont"],
         "moyenne", 3, "amas_naturel", "toutes", "indépendant", "carte explorable",
         "peut nécessiter un outil", "hors des sentiers principaux", Status.PROPOSEE,
         "Ressources naturelles réparties dans les zones d'exploration.")
    # Secrets -> Bois des Retours.
    rule("secrets", "secret", ["feuillage", "herbe", "terre"], ["plancher", "pont"],
         "très_faible", 8, "caché", "saison_des_brumes", "brouillard favorise",
         "accessible seulement après découverte", "événement/condition de découverte",
         "lié à la Clairière qui se répète", Status.DEDUITE,
         "Les secrets du Bois sont rares et conditionnels (système secrets).")
    # Créatures -> habitat.
    rule("creatures", "creature", ["eau", "herbe", "feuillage"], ["plancher"],
         "faible", 4, "selon_habitat", "toutes", "indépendant", "habitat naturel",
         "aucune", "dans la zone d'habitat", Status.DEDUITE,
         "Chaque créature n'apparaît que dans son habitat (pêche/Bois).")
    return rules


def build_navigation_rules(catalogs: dict) -> list[dict]:
    """Règles de navigation (terrains marchables, collisions, chemins)."""
    walkable = ["herbe", "sol_meuble", "terre", "plancher", "pont", "feuillage"]
    blocking = ["eau", "pierre", "bois"]
    out = [{
        "id": make_id("navigation", "regles_globales"),
        "display_name": "Règles de navigation globales",
        "status": Status.DEDUITE,
        "walkable_terrain": walkable, "blocking_terrain": blocking,
        "movement": "grille 16×16, 8 directions interdites (4 directions)",
        "collision": "AABB par tuile solide", "pathfinding": "A* sur grille",
        "map_transitions": "les entrées/sorties relient les cartes liées",
        "source": "constraints#Architecture (navigation) + brief (2D vue du dessus)",
        "justification": "Navigation déterministe sur grille, sans LLM runtime.",
        "validation": {"chemin_existe": True, "entrees_sorties": True,
                       "aucune_zone_isolee": True},
    }]
    return out


# =============================================================================
# EFFETS / PARTICULES
# =============================================================================

EFFECT_TEMPLATES = [
    ("sol_laboure", "agriculture", "Particules de terre soulevée.", "labourer"),
    ("sol_arrose", "agriculture", "Gouttelettes d'eau.", "arroser"),
    ("graine_plantee", "agriculture", "Petite pousse qui émerge.", "planter"),
    ("recolte", "agriculture", "Éclats de récolte + icône qui vole.", "recolter"),
    ("prise_poisson", "peche", "Éclaboussures + poisson.", "pecher"),
    ("artisanat", "artisanat", "Étincelles d'atelier.", "fabriquer"),
    ("cuisine", "cuisine", "Vapeur du foyer.", "cuisiner"),
    ("don_relation", "relations", "Cœur/note chaleureuse.", "offrir"),
    ("apparition_echo", "secrets", "Lueur mémorielle qui apparaît.", "evenement"),
    ("revele_fragment", "memoire", "Fragment de souvenir qui brille.", "memoire"),
]


def build_effects(catalogs: dict) -> list[dict]:
    out = []
    for name, sysid, desc, verb in EFFECT_TEMPLATES:
        out.append({
            "id": make_id("effet", name), "display_name": name.replace("_", " ").capitalize(),
            "status": Status.PROPOSEE, "system": f"system_{sysid}",
            "description": desc, "trigger_verb": verb,
            "asset_id": make_id("asset", f"particule_{name}"),
            "duration": 0.8, "loop": False,
            "source": f"dérivé des animations/événements (system_{sysid})",
            "justification": f"Effet visuel synchronisé avec l'action '{verb}'.",
            "validation": {"asset_present": True, "sync_animation": True},
        })
    # Asset particule pour chaque effet.
    return out


def build_effect_assets(effects: list[dict]) -> list[dict]:
    assets = []
    for e in effects:
        assets.append(_asset(
            e["asset_id"], f"Particule {e['display_name']}", e["id"],
            "famille_effets", "particule", 16, 16, STYLE, PALETTE,
            ["defaut"], ["overlay lors de l'action"], Status.PROPOSEE,
            e["source"], e["justification"],
            {"dimensions": "16×16", "transparency": True, "unique_fingerprint": True}))
    return assets


def build_transition_assets(transitions: list[dict]) -> list[dict]:
    """Un asset de transition par paire de terrains adjacents (famille dédiée)."""
    assets = []
    for t in transitions:
        assets.append(_asset(
            t["asset_id"], f"Transition {t['from_terrain']}→{t['to_terrain']}",
            make_id("map", "terrains"), "famille_transitions", "transition",
            16, 16, STYLE, PALETTE,
            [f"{t['from_terrain']}_vers_{t['to_terrain']}", "miroir"],
            ["auto-tile entre deux terrains adjacents"], Status.DEDUITE,
            t["source"], t["justification"],
            {"dimensions": "16×16", "transparency": True, "auto_tile": True,
             "unique_fingerprint": True}))
    return assets


# =============================================================================
# MANIFESTS DE CONTENU (vues production des catalogues)
# =============================================================================

def _content_manifest(catalogs: dict, key: str, extra=None) -> list[dict]:
    """Vue 'production' d'un catalogue : entité + assets/animations requis + validation."""
    anim_by_entity: dict[str, list[str]] = {}
    for a in catalogs.get("_animations", []):
        anim_by_entity.setdefault(a["entity_id"], []).append(a["id"])
    asset_by_entity: dict[str, list[str]] = {}
    for asst in catalogs.get("_assets", []):
        asset_by_entity.setdefault(asst["entity_id"], []).append(asst["id"])

    out = []
    for ent in catalogs.get(key, []):
        m = dict(ent)
        m["required_assets"] = asset_by_entity.get(ent["id"], [])
        m["required_animations"] = anim_by_entity.get(ent["id"], [])
        m["validation"] = {
            "structure": "schéma JSON valide",
            "references": "toutes les références résolues",
            "no_orphan": "au moins une relation d'usage",
        }
        if extra:
            m.update(extra(ent))
        out.append(m)
    return out


# =============================================================================
# ASSEMBLAGE DES MANIFESTS
# =============================================================================

def run_stage(catalogs: dict, write: bool = True) -> dict[str, Any]:
    animations = build_animations(catalogs)
    assets = build_assets(catalogs, animations)
    effects = build_effects(catalogs)
    transitions = build_transitions(catalogs)
    assets = assets + build_effect_assets(effects) + build_transition_assets(transitions)
    maps = build_map_manifests(catalogs)
    placement = build_placement_rules(catalogs)
    navigation = build_navigation_rules(catalogs)

    # Injecter assets/animations dans catalogs pour les manifests de contenu.
    cat2 = dict(catalogs)
    cat2["_animations"] = animations
    cat2["_assets"] = assets

    manifests = {
        "objects": _content_manifest(cat2, "objects"),
        "resources": _content_manifest(cat2, "resources"),
        "crops": _content_manifest(cat2, "crops"),
        "machines": _content_manifest(cat2, "machines"),
        "recipes": _content_manifest(cat2, "recipes"),
        "quests": _content_manifest(cat2, "quests"),
        "npcs": _content_manifest(cat2, "npcs"),
        "creatures": _content_manifest(cat2, "creatures"),
        "maps": maps,
        "placement": placement,
        "navigation": navigation,
        "assets": assets,
        "animations": animations,
        "transitions": transitions,
        "effects": effects,
    }

    if write:
        for name, data in manifests.items():
            write_json(DIRS["manifests"] / f"manifest_{name}.json",
                       versioned_envelope(data, kind=f"manifest_{name}"))

    return {
        "manifests": manifests,
        "counts": {k: len(v) for k, v in manifests.items()},
    }


if __name__ == "__main__":
    from . import canon as canon_mod, systems as sys_mod, catalog as cat_mod
    ca = canon_mod.run_stage(write=False)
    sy = sys_mod.run_stage(write=False)["systems"]
    cats = cat_mod.run_stage(ca, sy, write=False)
    res = run_stage(cats)
    print("counts:", res["counts"])
