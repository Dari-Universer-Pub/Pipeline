"""Catalogue fonctionnel et dérivation des quantités (étapes 18, 22-32).

Ce module est le cœur « graph-driven » : il calcule les quantités d'entités
depuis les systèmes, le canon, la boucle principale, les chaînes de
production, la progression, les lieux et les saisons — jamais arbitrairement.

Chaque entité produite embarque un bloc `derivation` qui explique :
- pourquoi l'élément existe (why) ;
- quel système l'utilise (system) ;
- comment il est obtenu (obtention) ;
- quelles entités le consomment (consumers) ;
- quelles conséquences il produit (consequences) ;
- quels assets sont nécessaires (assets) ;
- quelles animations sont nécessaires (animations) ;
- quels tests le couvrent (tests).

Statuts : les entités issues du canon sont CANONIQUE ; celles logiquement
dérivées sont DEDUITE ; les recommandations créatives/techniques sont
PROPOSEE ; les quantités correspondant à une décision ouverte sont notees
A_VALIDER dans le plan de quantités (jamais verrouillées en canon).
"""
from __future__ import annotations

from typing import Any

from .common import DIRS, Status, make_id, write_json, versioned_envelope, derive_seed
from . import systems as systems_mod

SRC_CANON = "INPUT/canon_initial.md"
SRC_BRIEF = "INPUT/game_brief.md"


# --- Bloc de dérivation (justification obligatoire) -------------------------

def _derivation(*, why: str, system: str, obtention: str, consumers: str,
                consequences: str, assets: str, animations: str,
                tests: str) -> dict[str, str]:
    return {
        "why": why, "system": system, "obtention": obtention,
        "consumers": consumers, "consequences": consequences,
        "assets": assets, "animations": animations, "tests": tests,
    }


# =============================================================================
# SAISONS (quantité À_VALIDER ; défaut technique = 4 ; noms PROPOSÉS)
# =============================================================================

SEASON_TEMPLATES = [
    ("Saison des Premières Pousses", "Renouveau ; terres cultivables ouvertes.",
     ["ensoleille", "nuageux", "pluie", "vent"]),
    ("Saison des Épis", "Croissance et récoltes abondantes.",
     ["ensoleille", "orage", "vent", "nuageux"]),
    ("Saison des Brumes", "Brouillard et souvenirs ; événements du Bois.",
     ["brouillard", "pluie", "nuageux", "vent"]),
    ("Saison du Repos", "Repos ; pêche et artisanat.",
     ["neige", "brouillard", "nuageux", "ensoleille"]),
]


def build_seasons() -> list[dict]:
    out = []
    for i, (name, desc, weather) in enumerate(SEASON_TEMPLATES, start=1):
        # ID propre : évite le préfixe dupliqué 'saison_saison_...'.
        clean = name[len("Saison "):] if name.lower().startswith("saison ") else name
        out.append({
            "id": make_id("saison", clean),
            "display_name": name,
            "status": Status.PROPOSEE,
            "source": "INPUT/open_decisions.md (nombre) + brief (système saisons)",
            "justification": "Le système 'saisons' est requis par le brief ; le "
                             "NOMBRE exact est une décision ouverte (À_VALIDER). "
                             "Défaut technique modulaire = 4, noms PROPOSÉS selon "
                             "les règles de nommage du canon.",
            "description": desc,
            "order": i,
            "length_days": 28,
            "weather_pool": weather,
            "growable": [],  # rempli par build_crops
            "quantity_status": Status.A_VALIDER,
            "derivation": _derivation(
                why="Le cycle saisonnier pilote la croissance, la météo, les "
                    "événements et la disponibilité des ressources.",
                system="system_temps, system_meteo",
                obtention="N/A (cadre temporel).",
                consumers="agriculture, météo, événements, exploration.",
                consequences="Détermine quelles cultures poussent et quels "
                             "événements se déclenchent.",
                assets="1 tileset de sol par saison (famille terrains).",
                animations="Transitions de saison (fondu) + météo animée.",
                tests="test_saisons, test_temporel, test_reproductibilite."),
        })
    return out


# =============================================================================
# LIEUX / ZONES / POI (canon + dérivés des descriptions et des systèmes)
# =============================================================================

def build_locations(canon: dict) -> list[dict]:
    """Lieux canoniques + zones/POI déduits de leurs descriptions et des systèmes."""
    locs: list[dict] = []

    # Lieux canoniques (CANONIQUE). L'ID/map_id viennent du canon (sans article).
    for l in canon["locations"]:
        locs.append({
            "id": l["id"], "display_name": l["display_name"],
            "status": Status.CANONIQUE, "source": l["source"],
            "justification": l["justification"], "description": l["description"],
            "kind": "carte", "map_id": l.get("map_id", make_id("map", l["display_name"])),
            "clean_name": l.get("clean_name", l["display_name"]),
            "function": _canon_location_function(l["display_name"]),
            "terrain": [], "walkable": True,
        })

    # Zones/POI DEDUITES des descriptions canoniques + exigences des systèmes.
    derived = [
        # Vallée Claire -> terres cultivables (agriculture: lieu:farmland)
        ("lieu", "Champ de la Vallée Claire", "Vallée Claire",
         "zone", "agriculture", "Terres cultivables déduites de 'zone de départ "
         "et terres cultivables' (canon).", "system_agriculture",
         ["sol_meuble", "herbe"], True),
        # Vallée Claire -> puits de mémoire (prémisse)
        ("lieu", "Puits de Mémoire", "Vallée Claire",
         "interet", "memoire", "Puits ancien de la prémisse : 'jardin construit "
         "autour d'un ancien puits de mémoire'.", "system_memoire",
         ["pierre", "eau"], True),
        # Maison-Racine -> atelier (artisanat: Marin)
        ("lieu", "Atelier de la Maison-Racine", "Maison-Racine",
         "zone", "artisanat", "Atelier principal (canon) ; Marin y fabrique les "
         "machines agricoles.", "system_artisanat", ["plancher", "bois"], True),
        # Maison-Racine -> cuisine (cuisine)
        ("lieu", "Cuisine de la Maison-Racine", "Maison-Racine",
         "zone", "cuisine", "Cuisine du refuge (canon) ; système 'cuisine'.",
         "system_cuisine", ["plancher", "pierre"], True),
        # Bois des Retours -> zone secrète (secrets: lieu:secret)
        ("lieu", "Clairière qui se répète", "Bois des Retours",
         "secret", "secrets", "Zone secrète déduite de 'forêt où certains "
         "événements se répètent' (canon) ; système 'secrets'.",
         "system_secrets", ["herbe", "feuillage"], True),
        # Bois des Retours -> sentier (exploration: lieu:poi)
        ("lieu", "Sentier des Retours", "Bois des Retours",
         "interet", "exploration", "Sentier d'exploration ; système 'exploration'.",
         "system_exploration", ["terre", "feuillage"], True),
        # Lac Muet -> poste de pêche (peche: lieu:fishing_spot)
        ("lieu", "Poste de pêche du Lac Muet", "Lac Muet",
         "interet", "peche", "Poste de pêche déduit de 'zone d'exploration et de "
         "pêche' (canon) ; Nox y pêche.", "system_peche",
         ["eau", "pont"], True),
    ]
    for cat, name, parent, kind, func, just, sysid, terrain, walk in derived:
        locs.append({
            "id": make_id(cat, name), "display_name": name,
            "status": Status.DEDUITE,
            "source": f"{SRC_CANON}#Lieux connus (dérivé) + brief#Systèmes",
            "justification": just, "description": just,
            "kind": kind, "map_id": make_id("map", parent),
            "parent_id": make_id("lieu", parent),
            "function": func, "terrain": terrain, "walkable": walk,
            "system": sysid,
        })
    return locs


def _canon_location_function(name: str) -> str:
    n = name.lower()
    if "maison-racine" in n:
        return "refuge"
    if "vallée claire" in n or "vallee claire" in n:
        return "farmland"
    if "bois des retours" in n:
        return "secret"
    if "lac muet" in n:
        return "fishing_spot"
    return "poi"


# =============================================================================
# CULTURES (quantité À_VALIDER ; noms PROPOSÉS ; plante mémorielle DEDUITE)
# =============================================================================

# name, seasons(order), growth_days, memory_plant, seed_source, yield_name,
# yield_category, used_by, regrows, water
CROP_TEMPLATES = [
    ("Floraison d'Écho", [3], 6, True, "objet_graine_d_echo", "Écho Cristallin",
     "fragment", "system_memoire", False, True),
    ("Navet de la Vallée", [1], 4, False, None, "Navet", "produit",
     "system_cuisine", False, True),
    ("Blé des Épis", [2], 5, False, None, "Grain de blé", "produit",
     "system_cuisine", False, True),
    ("Courge des Brumes", [3], 6, False, None, "Courge", "produit",
     "system_cuisine", False, True),
    ("Lin du Repos", [4], 5, False, None, "Fibre de lin", "ressource",
     "system_artisanat", False, True),
    ("Souci de la Vallée", [1, 2], 3, False, None, "Fleur de souci", "produit",
     "system_relations", True, True),
]


def build_crops(seasons: list[dict]) -> tuple[list[dict], list[dict]]:
    """Construit les cultures + les objets graine/produit associés.

    Retourne (crops, objets_deduits). Les graines non-canoniques sont créées ;
    la Graine d'Écho (canon) est référencée sans être recréée.
    """
    crops = []
    objets = []
    season_by_order = {s["order"]: s for s in seasons}

    for (name, orders, days, memory, seed_src, yield_name, yield_cat,
         used_by, regrows, water) in CROP_TEMPLATES:
        cid = make_id("culture", name)
        # Graine.
        if seed_src:
            seed_id = seed_src  # canon (Graine d'Écho)
            seed_status = Status.CANONIQUE
        else:
            seed_id = make_id("objet", "Graine de " + name)
            seed_status = Status.DEDUITE
            objets.append(_seed_object(name, seed_id, cid, used_by))
        # Produit récolté.
        yield_id = make_id("objet", yield_name)
        objets.append(_yield_object(yield_name, yield_id, cid, yield_cat, used_by, memory))

        status = Status.DEDUITE if memory else Status.PROPOSEE
        crops.append({
            "id": cid, "display_name": name, "status": status,
            "source": (f"{SRC_CANON}#Faits immuables (dérivé)" if memory
                       else "brief#Systèmes souhaités (agriculture)"),
            "justification": ("Plante mémorielle déduite du canon : 'les graines "
                              "d'écho peuvent faire pousser des plantes mémorielles'."
                              if memory else
                              "Culture proposée pour couvrir une saison et un "
                              "système (cuisine/artisanat/relations). Nom PROPOSÉ "
                              "selon les règles de nommage du canon."),
            "seed_id": seed_id, "yield_id": yield_id,
            "seasons": [season_by_order[o]["id"] for o in orders if o in season_by_order],
            "growth_days": days, "stages": ["semis", "pousse", "mature", "recoltable"],
            "water_needed": water, "memory_plant": memory, "regrows": regrows,
            "used_by": used_by,
            "quantity_status": Status.A_VALIDER,
            "derivation": _derivation(
                why=("Fait remonter un fragment du passé (cœur de la prémisse)."
                     if memory else
                     f"Alimente la boucle de production pour {used_by}."),
                system=f"system_agriculture, {used_by}",
                obtention=f"Planter {seed_id} puis arroser {days} jour(s).",
                consumers=f"{used_by} ; recettes associées.",
                consequences=("Récolte -> Écho Cristallin -> fragment de souvenir."
                              if memory else
                              "Récolte -> produit transformé (cuisine/artisanat)."),
                assets="1 sprite par stade de croissance (4) + icône graine/produit.",
                animations="animation de croissance par stade + geste récolte.",
                tests="test_chaine_production, test_culture, test_temporel."),
        })
        # Enregistrer la culture comme poussant dans ses saisons.
        for o in orders:
            if o in season_by_order:
                season_by_order[o]["growable"].append(cid)
    return crops, objets


def _seed_object(crop_name: str, seed_id: str, crop_id: str, used_by: str) -> dict:
    return {
        "id": seed_id, "display_name": "Graine de " + crop_name,
        "status": Status.DEDUITE, "category": "graine",
        "source": "brief#Boucles (explorer et trouver des graines)",
        "justification": f"Graine nécessaire pour planter {crop_id} (système agriculture).",
        "function": f"Semence de {crop_name}.", "gameplay_verb": "planter",
        # Obtention : exploration (forage) ; la culture la reproduit si regrows.
        "obtention": ["lieu:exploration"],
        "loop_stage": 1,
        # La culture consomme la graine (plantée) -> usage réel.
        "users": [crop_id],
        "transforms_into": [crop_id], "stackable": True,
        "base_value": 5, "decorative_only": False,
        "derivation": _derivation(
            why=f"Permet de démarrer la culture {crop_id}.",
            system="system_agriculture, system_exploration",
            obtention="Forage/exploration ; reproduction par récolte (si regrows).",
            consumers=f"culture {crop_id} (plantée).",
            consequences="Plantée -> croissance -> récolte.",
            assets="1 icône d'inventaire.", animations="geste 'planter'.",
            tests="test_chaine_production, test_objet_utile."),
    }


def _yield_object(name: str, yield_id: str, crop_id: str, category: str,
                  used_by: str, memory: bool) -> dict:
    cat = "fragment" if memory else category
    return {
        "id": yield_id, "display_name": name,
        "status": Status.DEDUITE if memory else Status.PROPOSEE,
        "category": cat,
        "source": (f"{SRC_CANON}#Faits immuables" if memory
                   else f"brief#Systèmes ({used_by})"),
        "justification": (f"Produit de la plante mémorielle {crop_id}."
                          if memory else f"Produit récolté de {crop_id}."),
        "function": name, "gameplay_verb": "recolter",
        "obtention": [f"culture:{crop_id}"], "loop_stage": 2,
        "users": [used_by], "transforms_into": [], "stackable": True,
        "base_value": 12 if not memory else 30, "decorative_only": False,
        "derivation": _derivation(
            why=("Fragment du passé remonté par la culture (prémisse)." if memory
                 else f"Récolte consommée/transformée par {used_by}."),
            system=f"system_agriculture, {used_by}",
            obtention=f"Récolte de {crop_id} à maturité.",
            consumers=f"{used_by} ; recettes de transformation.",
            consequences=("Alimente le système mémoire/narration." if memory
                          else "Alimente cuisine/artisanat/économie."),
            assets="1 icône d'inventaire + sprite de récolte.",
            animations="geste 'récolter' + effet de ramassage.",
            tests="test_chaine_production, test_objet_utile, test_economique."),
    }


# =============================================================================
# RESSOURCES (matériaux bruts pour artisanat)
# =============================================================================

RESOURCE_TEMPLATES = [
    ("Bois", "matériau", "exploration", "artisanat",
     "Bûches ramassées dans le Bois des Retours.", ["system_artisanat"]),
    ("Pierre", "matériau", "exploration", "artisanat",
     "Pierres ramassées près du Puits de Mémoire.", ["system_artisanat"]),
    ("Argile", "matériau", "exploration", "artisanat",
     "Argile au bord du Lac Muet.", ["system_artisanat"]),
]


def build_resources() -> list[dict]:
    out = []
    for name, cat, producer, consumer, desc, systems in RESOURCE_TEMPLATES:
        rid = make_id("ressource", name)
        out.append({
            "id": rid, "display_name": name, "status": Status.PROPOSEE,
            "category": cat, "source": "brief#Systèmes (artisanat/exploration)",
            "justification": f"Matériau requis par l'artisanat ; obtenu par {producer}.",
            "description": desc,
            "producers": [make_id("system", producer)],
            "consumers": [make_id("system", consumer)],
            "seasonal": False, "base_value": 8,
            "derivation": _derivation(
                why=f"Matériau de base des chaînes d'artisanat ({consumer}).",
                system=", ".join(systems) + ", system_exploration",
                obtention=f"Forage/exploration ({producer}).",
                consumers=f"Recettes d'artisanat via {consumer}.",
                consequences="Transformé en objets/machines améliorées.",
                assets="1 icône + sprite de gisement sur la carte.",
                animations="geste 'extraire' + effet de récolte.",
                tests="test_chaine_production, test_ressource, test_economique."),
        })
    return out


# =============================================================================
# MACHINES (stations de transformation)
# =============================================================================

MACHINE_TEMPLATES = [
    ("Établi de Marin", "artisanat", "pnj_marin",
     "Station d'artisanat ; Marin (canon) fabrique les machines agricoles.",
     ["ressource_bois", "ressource_pierre"], ["objet_planche"], "system_artisanat"),
    ("Foyer de la Maison-Racine", "cuisine", None,
     "Foyer de cuisine du refuge (canon Maison-Racine) ; bâti d'argile et de "
     "pierre ; système cuisine.",
     ["ressource_argile", "ressource_pierre"], [], "system_cuisine"),
    ("Métier à tisser", "artisanat", "pnj_marin",
     "Transforme la fibre de lin en fil puis en toile ; système artisanat.",
     ["objet_fibre_de_lin"], ["objet_fil_de_lin"], "system_artisanat"),
    ("Puits de Mémoire", "memoire", None,
     "Station mémorielle de la prémisse ; transforme les échos en fragments "
     "et révèle des souvenirs. Système mémoire.",
     ["objet_echo_cristallin"], ["objet_fragment_de_souvenir"], "system_memoire"),
]


def build_machines() -> list[dict]:
    out = []
    for name, func, built_by, desc, inputs, outputs, sysid in MACHINE_TEMPLATES:
        mid = make_id("machine", name)
        status = Status.DEDUITE if (built_by or "canon" in desc.lower()
                                    or "Mémoire" in name) else Status.PROPOSEE
        out.append({
            "id": mid, "display_name": name, "status": status,
            "function": func, "source": f"{SRC_CANON}/brief#Systèmes ({sysid})",
            "justification": desc, "description": desc,
            "built_by": built_by, "inputs": inputs, "outputs": outputs,
            "recipe_ids": [], "placement_id": make_id("placement", name),
            "animation_ids": [make_id("anim", name + " actif")],
            "system": sysid,
            "derivation": _derivation(
                why=f"Station de transformation pour {sysid}.",
                system=sysid,
                obtention=("Fabriquée par " + built_by if built_by
                           else "Présente dans le refuge/lieu canonique."),
                consumers="Recettes de transformation.",
                consequences="Convertit entrées -> sorties (chaîne de production).",
                assets="1 sprite de machine (état inactif/actif) dans sa famille.",
                animations="animation 'actif' bouclée + événement d'impact.",
                tests="test_chaine_production, test_machine, test_placement."),
        })
    return out


# =============================================================================
# RECETTES (transformations : cuisine + artisanat + mémoire)
# =============================================================================

# name, station, inputs[(id,qty)], outputs[(id,qty)], unlocked_by
RECIPE_TEMPLATES = [
    ("Soupe de navet", "machine_foyer_de_la_maison_racine",
     [("objet_navet", 2)], [("objet_soupe_de_navet", 1)], None, "cuisine"),
    ("Pain de blé", "machine_foyer_de_la_maison_racine",
     [("objet_grain_de_ble", 3)], [("objet_pain_de_ble", 1)], None, "cuisine"),
    ("Courge rôtie", "machine_foyer_de_la_maison_racine",
     [("objet_courge", 1)], [("objet_courge_rotie", 1)], None, "cuisine"),
    ("Tisane de souci", "machine_foyer_de_la_maison_racine",
     [("objet_fleur_de_souci", 2)], [("objet_tisane_de_souci", 1)], None, "cuisine"),
    ("Planche", "machine_etabli_de_marin",
     [("ressource_bois", 2)], [("objet_planche", 1)], None, "artisanat"),
    ("Fil de lin", "machine_metier_a_tisser",
     [("objet_fibre_de_lin", 2)], [("objet_fil_de_lin", 1)], None, "artisanat"),
    ("Toile", "machine_metier_a_tisser",
     [("objet_fil_de_lin", 3)], [("objet_toile", 1)], None, "artisanat"),
    ("Fragment ravivé", "machine_puits_de_memoire",
     [("objet_echo_cristallin", 1)], [("objet_fragment_de_souvenir", 1)],
     "quete_le_premier_echo", "memoire"),
]


def build_recipes() -> tuple[list[dict], list[dict]]:
    """Construit les recettes + les objets produits manquants (plats, artisanaux)."""
    recipes = []
    objets = []
    created_ids = set()
    for name, station, inputs, outputs, unlocked_by, kind in RECIPE_TEMPLATES:
        rid = make_id("recette", name)
        # Objets produits (consommables/artisanat) -> créer s'ils n'existent pas.
        for out_id, qty in outputs:
            if out_id not in created_ids:
                objets.append(_crafted_object(out_id, kind, name))
                created_ids.add(out_id)
        recipes.append({
            "id": rid, "display_name": name, "status": Status.PROPOSEE,
            "source": f"brief#Systèmes ({kind}) — recette exacte À_VALIDER (canon ouvert)",
            "justification": f"Recette de {kind} reliant une station à ses "
                             f"entrées/sorties. Les recettes exactes sont un "
                             f"élément ouvert du canon (À_VALIDER).",
            "station_id": station,
            "inputs": [{"item_id": i, "qty": q} for i, q in inputs],
            "outputs": [{"item_id": o, "qty": q} for o, q in outputs],
            "duration": 2.0, "unlocked_by": unlocked_by, "kind": kind,
            "quantity_status": Status.A_VALIDER,
            "derivation": _derivation(
                why=f"Étape de transformation de la chaîne {kind}.",
                system=f"system_{kind}",
                obtention=f"Utiliser {station} avec les ingrédients requis.",
                consumers="Joueur, PNJ (dons), quêtes, économie.",
                consequences="Produit un objet de valeur supérieure / fait avancer "
                             "une quête.",
                assets="icônes des entrées/sorties + sprite station active.",
                animations="animation de la station + geste d'interaction.",
                tests="test_recette_complete, test_chaine_production, test_economique."),
        })
    return recipes, objets


def _crafted_object(obj_id: str, kind: str, recipe_name: str) -> dict:
    # Nom affiché déduit de l'ID.
    name = obj_id.split("_", 1)[1].replace("_", " ").capitalize()
    cat = "consommable" if kind == "cuisine" else "artisanat"
    return {
        "id": obj_id, "display_name": name, "status": Status.PROPOSEE,
        "category": cat, "source": f"brief#Systèmes ({kind})",
        "justification": f"Produit de la recette '{recipe_name}' ({kind}).",
        "function": name, "gameplay_verb": "utiliser" if kind == "cuisine" else "fabriquer",
        "obtention": [f"recette:{make_id('recette', recipe_name)}"], "loop_stage": 3,
        "users": ["system_economie", "system_relations"] if kind == "cuisine" else ["system_artisanat"],
        "transforms_into": [], "stackable": True,
        "base_value": 25 if kind == "cuisine" else 20, "decorative_only": False,
        "derivation": _derivation(
            why=f"Sortie de la chaîne de transformation {kind}.",
            system=f"system_{kind}, system_economie",
            obtention=f"Recette '{recipe_name}'.",
            consumers="Joueur (usage), PNJ (dons), économie (vente).",
            consequences="Valeur économique supérieure ; effets sur relations.",
            assets="1 icône d'inventaire.", animations="geste d'usage/offrande.",
            tests="test_recette_complete, test_objet_utile, test_economique."),
    }


# =============================================================================
# OBJETS OUTILS (canon + dérivés des systèmes)
# =============================================================================

def build_tool_objects(canon: dict) -> list[dict]:
    """Objets canoniques + outils déduits des systèmes (pêche, etc.)."""
    objets = []
    # Objets canoniques (CANONIQUE).
    canon_meta = {
        "objet_graine_d_echo": ("graine", "planter", 1,
                               "Graine mémorielle canonique ; fait pousser la "
                               "Floraison d'Écho.", "system_memoire, system_agriculture"),
        "objet_houe_de_depart": ("outil", "labourer", 1,
                                 "Outil de départ canonique ; prépare le sol.",
                                 "system_agriculture"),
        "objet_arrosoir_de_cuivre": ("outil", "arroser", 1,
                                     "Arrosoir canonique ; arrose les cultures.",
                                     "system_agriculture"),
        "objet_fragment_de_souvenir": ("fragment", "commemorer", 4,
                                       "Fragment de souvenir canonique ; unité "
                                       "narrative du système mémoire.",
                                       "system_memoire, system_relations"),
        "objet_carnet_du_jardinier": ("cle", "consigner", 0,
                                      "Carnet canonique ; journal de progression "
                                      "et des souvenirs.", "system_progression"),
    }
    for o in canon["objects"]:
        cat, verb, stage, just, sysid = canon_meta.get(
            o["id"], ("quotidien", "utiliser", 0, o["justification"], "system_agriculture"))
        objets.append({
            "id": o["id"], "display_name": o["display_name"],
            "status": Status.CANONIQUE, "category": cat, "source": o["source"],
            "justification": just, "function": just, "gameplay_verb": verb,
            "obtention": ["canon"], "loop_stage": stage,
            "users": [s.strip() for s in sysid.split(",")],
            "transforms_into": [], "stackable": cat in ("graine", "fragment"),
            "base_value": None, "decorative_only": False,
            "derivation": _derivation(
                why="Objet canonique non négociable.",
                system=sysid, obtention="Défini par le canon.",
                consumers="Systèmes canoniques associés.",
                consequences="Ancre la boucle principale / la narration.",
                assets="1 icône + sprite monde si applicable.",
                animations="geste d'usage propre à l'outil.",
                tests="test_canon, test_objet_utile."),
        })

    # Outil de pêche (DEDUIT : système peche + Lac Muet canon).
    objets.append({
        "id": make_id("objet", "Ligne de pêche"),
        "display_name": "Ligne de pêche", "status": Status.DEDUITE,
        "category": "outil", "source": f"{SRC_CANON}#Lieux (Lac Muet) + brief#Systèmes",
        "justification": "Outil requis par le système pêche (Lac Muet canonique).",
        "function": "Pêcher au Lac Muet.", "gameplay_verb": "pecher",
        "obtention": ["pnj:pnj_nox"], "loop_stage": 1,
        "users": ["system_peche"], "transforms_into": [], "stackable": False,
        "base_value": 40, "decorative_only": False,
        "derivation": _derivation(
            why="Permet la pêche au Lac Muet (système peche).",
            system="system_peche", obtention="Don/achat auprès de Nox ou artisanat.",
            consumers="system_peche.", consequences="Produit du poisson (ressource).",
            assets="1 icône + sprite de canne.", animations="geste 'pêcher' 4 directions.",
            tests="test_chaine_production, test_objet_utile, test_peche."),
    })
    return objets


# =============================================================================
# PNJ (canon ; rôles économiques/socials DEDUITS)
# =============================================================================

NPC_EXTRA = {
    "pnj_alba": {
        "function": "soigneuse_des_plantes",
        "goals": ["soigner les plantes", "guider le Jardinier"],
        "needs": ["plantes médicinales", "souci"],
        "beliefs": ["les souvenirs doivent être soignés, pas effacés"],
        "knowledge": ["fait_monde_valdore", "fait_joueur_jardinier", "lieu_maison_racine",
                      "lieu_vallee_claire", "culture_souci_de_la_vallee"],
        "forbidden_knowledge": ["secret_clairiere_repetition", "secret_passe_nox"],
        "emotions": ["chaleureuse", "inquiete"],
        "voice": "douce, pédagogue, phrases courtes, métaphores végétales",
        "home": "lieu_maison_racine",
        "frequented": ["lieu_maison_racine", "lieu_champ_de_la_vallee_claire"],
        "role": ["guide", "soins"],
    },
    "pnj_marin": {
        "function": "artisan_machines",
        "goals": ["fabriquer des machines", "améliorer le refuge"],
        "needs": ["bois", "pierre", "argile"],
        "beliefs": ["le travail bien fait répare la mémoire"],
        "knowledge": ["fait_monde_valdore", "machine_etabli_de_marin", "machine_metier_a_tisser",
                      "ressource_bois", "ressource_pierre"],
        "forbidden_knowledge": ["secret_passe_nox"],
        "emotions": ["bourru", "fier"],
        "voice": "directe, technique, peu de mots, jargon d'atelier",
        "home": "lieu_atelier_de_la_maison_racine",
        "frequented": ["lieu_atelier_de_la_maison_racine"],
        "role": ["merchant", "artisan"],  # économie: merchant (DEDUIT)
    },
    "pnj_nox": {
        "function": "pecheur",
        "goals": ["pêcher", "éviter son passé"],
        "needs": ["poisson", "solitude"],
        "beliefs": ["certains souvenirs doivent rester au fond de l'eau"],
        "knowledge": ["lieu_lac_muet", "creature_poisson_du_lac", "fait_monde_valdore"],
        "forbidden_knowledge": ["secret_passe_nox", "secret_clairiere_repetition"],
        "emotions": ["silencieux", "melancolique"],
        "voice": "laconique, silences, non-dits, phrases inachevées",
        "home": "lieu_poste_de_peche_du_lac_muet",
        "frequented": ["lieu_poste_de_peche_du_lac_muet", "lieu_lac_muet"],
        "role": ["merchant", "peche"],  # économie: merchant (DEDUIT)
    },
}


def build_npcs(canon: dict) -> list[dict]:
    out = []
    for n in canon["npcs"]:
        extra = NPC_EXTRA.get(n["id"], {})
        out.append({
            "id": n["id"], "display_name": n["display_name"],
            "status": Status.CANONIQUE, "source": n["source"],
            "justification": n["justification"], "description": n["description"],
            "function": extra.get("function", "habitant"),
            "goals": extra.get("goals", []), "needs": extra.get("needs", []),
            "beliefs": extra.get("beliefs", []),
            "knowledge": extra.get("knowledge", []),
            "forbidden_knowledge": extra.get("forbidden_knowledge", []),
            "emotions": extra.get("emotions", []),
            "routines": [],  # construites par le simulateur/manifest
            "frequented_places": extra.get("frequented", []),
            "voice": extra.get("voice", ""), "home": extra.get("home"),
            "roles": extra.get("role", []),
            "derivation": _derivation(
                why="Personnage canonique ; porte un rôle social/économique.",
                system="system_relations, system_economie",
                obtention="Présent dans le monde (canon).",
                consumers="Dialogues, quêtes, dons, économie.",
                consequences="Modifie relations, débloque lieux/quêtes.",
                assets="1 sprite de personnage (famille) + portrait.",
                animations="idle + marche 4 directions + geste d'interaction.",
                tests="test_pnj_routine, test_dialogue, test_narratif, test_relations."),
        })
    return out


# =============================================================================
# CRÉATURES (poisson pour pêche + faune du Bois)
# =============================================================================

CREATURE_TEMPLATES = [
    ("Poisson du Lac", "animal", ["lieu_lac_muet"], ["objet_poisson_du_lac"],
     "Poisson pêché au Lac Muet (système peche).", False, "system_peche"),
    ("Écho du Bois", "creature", ["lieu_bois_des_retours"], ["objet_fragment_de_souvenir"],
     "Manifestation qui répète des événements dans le Bois des Retours (canon).",
     False, "system_secrets"),
]


def build_creatures() -> tuple[list[dict], list[dict]]:
    creatures = []
    objets = []
    for name, kind, habitat, yields, desc, hostile, sysid in CREATURE_TEMPLATES:
        cid = make_id("creature", name)
        creatures.append({
            "id": cid, "display_name": name, "status": Status.PROPOSEE,
            "kind": kind, "source": f"{SRC_CANON}/brief#Systèmes ({sysid})",
            "justification": desc, "description": desc,
            "behavior": "passif" if not hostile else "fuyant",
            "habitat": habitat, "yields": yields, "hostile": hostile,
            "system": sysid,
            "derivation": _derivation(
                why=f"Faune liée à {sysid} et à un lieu canonique.",
                system=sysid, obtention="Pêche/observation dans son habitat.",
                consumers="system_peche, system_secrets, économie.",
                consequences="Produit une ressource/fragment ; événement narratif.",
                assets="1 sprite (famille créatures) + variantes.",
                animations="idle/nage + réaction.",
                tests="test_creature, test_chaine_production, test_placement."),
        })
        for y in yields:
            if y not in {o["id"] for o in objets}:
                nm = y.split("_", 1)[1].replace("_", " ").capitalize()
                objets.append({
                    "id": y, "display_name": nm, "status": Status.DEDUITE,
                    "category": "ressource", "source": f"brief#Systèmes ({sysid})",
                    "justification": f"Produit par {cid}.", "function": nm,
                    "gameplay_verb": "pecher" if "poisson" in y else "collecter",
                    "obtention": [f"creature:{cid}"], "loop_stage": 1,
                    "users": [sysid, "system_economie"], "transforms_into": [],
                    "stackable": True, "base_value": 15, "decorative_only": False,
                    "derivation": _derivation(
                        why=f"Ressource produite par {cid}.", system=sysid,
                        obtention=f"Récolte sur {cid}.", consumers="cuisine/économie.",
                        consequences="Alimente économie/recettes.",
                        assets="1 icône.", animations="geste de collecte.",
                        tests="test_chaine_production, test_ressource."),
                })
    return creatures, objets


# =============================================================================
# QUÊTES (donneurs canoniques ; triggers + conséquences obligatoires)
# =============================================================================

QUEST_TEMPLATES = [
    ("Le premier écho", "pnj_alba", "lieu_champ_de_la_vallee_claire",
     "Alba guide le Jardinier pour planter la première Graine d'Écho.",
     {"type": "on_day_start"}, ["system_memoire", "system_progression"],
     False),
    ("L'outil de Marin", "pnj_marin", "lieu_atelier_de_la_maison_racine",
     "Marin demande des matériaux pour construire une machine.",
     {"type": "on_relationship_threshold", "params": {"pnj_id": "pnj_marin", "value": 20}},
     ["system_artisanat", "system_economie"], False),
    ("Le silence de Nox", "pnj_nox", "lieu_poste_de_peche_du_lac_muet",
     "Nox refuse de parler ; le Jardinier doit gagner sa confiance.",
     {"type": "on_enter_location", "params": {"lieu_id": "lieu_lac_muet"}},
     ["system_relations", "system_peche"], True),
    ("Ce qui se répète", "pnj_alba", "lieu_bois_des_retours",
     "Enquêter sur les événements qui se répètent dans le Bois des Retours.",
     {"type": "on_secret_discovered", "params": {"secret_id": "secret_clairiere_repetition"}},
     ["system_secrets", "system_memoire"], True),
]


def build_quests(canon: dict) -> list[dict]:
    out = []
    for name, giver, loc, desc, trigger, systems, missable in QUEST_TEMPLATES:
        qid = make_id("quete", name)
        out.append({
            "id": qid, "display_name": name, "status": Status.PROPOSEE,
            "source": f"{SRC_CANON}#Personnages + brief#Boucles",
            "justification": f"Quête reliant un donneur canonique à un système ; "
                             f"le nombre exact de quêtes est À_VALIDER.",
            "description": desc, "giver_id": giver, "trigger": trigger,
            "preconditions": [], "participants": [giver], "location_id": loc,
            "steps": [{"id": "step_1", "objective": desc}],
            "choices": [], "effects": _quest_effects(qid, systems),
            "consequences": _quest_consequences(name),
            "fallback": "Si le donneur est indisponible, la quête est reportée au "
                        "prochain jour (aucun blocage définitif).",
            "failure_conditions": [], "missable": missable,
            "discovery": f"Parler à {giver} ou déclencheur contextuel.",
            "systems": systems, "quantity_status": Status.A_VALIDER,
            "derivation": _derivation(
                why="Donne une conséquence durable et relie les systèmes entre eux.",
                system=", ".join(systems),
                obtention=f"Donneur {giver} + déclencheur.",
                consumers="system_progression, system_relations.",
                consequences="Débloque lieux/recettes/faits ; modifie relations.",
                assets="icônes de quête + marqueur de donneur.",
                animations="geste de dialogue/don.",
                tests="test_quete_atteignable, test_quete_consequence, test_progression."),
        })
    return out


def _quest_effects(qid: str, systems: list[str]) -> list[dict]:
    eff = [{"type": "advance_quest", "params": {"quete_id": qid, "step": "complete"}}]
    if "system_memoire" in systems:
        eff.append({"type": "reveal_fact", "params": {"fait_id": "fait_valdore", "to": "joueur"}})
        eff.append({"type": "add_item", "params": {"item_id": "objet_fragment_de_souvenir", "qty": 1}})
    if "system_artisanat" in systems:
        eff.append({"type": "add_item", "params": {"item_id": "machine_etabli_de_marin", "qty": 1}})
    if "system_relations" in systems:
        eff.append({"type": "change_relationship", "params": {"pnj_id": "pnj_nox", "delta": 15}})
    if "system_secrets" in systems:
        eff.append({"type": "discover_secret", "params": {"secret_id": "secret_clairiere_repetition"}})
    if "system_peche" in systems:
        eff.append({"type": "add_item", "params": {"item_id": "objet_ligne_de_peche", "qty": 1}})
    return eff


def _quest_consequences(name: str) -> list[str]:
    return {
        "Le premier écho": ["Débloque la recette 'Fragment ravivé' au Puits de Mémoire.",
                            "Le Jardinier apprend que les cultures font remonter le passé."],
        "L'outil de Marin": ["Marin fabrique l'Établi ; accès à l'artisanat avancé.",
                             "Relation Marin augmentée."],
        "Le silence de Nox": ["Nox partage un fragment de son passé (narration).",
                              "Accès à la pêche profonde au Lac Muet."],
        "Ce qui se répète": ["Révèle un secret du Bois des Retours.",
                             "Débloque un événement mémoriel répété."],
    }.get(name, ["Conséquence narrative durable."])


# =============================================================================
# ÉVÉNEMENTS (contextuels, saisonniers, secrets)
# =============================================================================

EVENT_TEMPLATES = [
    ("Retour du Bois", "lieu_bois_des_retours", {"type": "on_season_change",
     "params": {"season_id": "saison_des_brumes"}}, True,
     "Un événement se répète dans le Bois des Retours (canon).",
     ["system_secrets", "system_evenements"]),
    ("Pluie sur la Vallée", "lieu_champ_de_la_vallee_claire",
     {"type": "on_weather", "params": {"weather_id": "pluie"}}, False,
     "La pluie arrose naturellement les cultures.", ["system_meteo", "system_agriculture"]),
    ("Le Puits chante", "lieu_puits_de_memoire",
     {"type": "on_item_acquired", "params": {"item_id": "objet_echo_cristallin"}}, True,
     "Le Puits de Mémoire réagit à un Écho Cristallin.", ["system_memoire"]),
    ("Marché de la Vallée", "lieu_champ_de_la_vallee_claire",
     {"type": "on_day_start"}, False,
     "Les habitants échangent leurs productions.", ["system_economie", "system_relations"]),
]


def build_events() -> list[dict]:
    out = []
    for name, loc, trigger, repeatable, desc, systems in EVENT_TEMPLATES:
        eid = make_id("evenement", name)
        out.append({
            "id": eid, "display_name": name, "status": Status.PROPOSEE,
            "source": f"{SRC_CANON}/brief#Systèmes ({', '.join(systems)})",
            "justification": desc, "description": desc,
            "trigger": trigger, "preconditions": [], "participants": [],
            "location_id": loc, "timing": {"seasonal": "on_season_change" in str(trigger)},
            "effects": _event_effects(eid, systems), "missable": repeatable,
            "repeatable": repeatable, "systems": systems,
            "derivation": _derivation(
                why="Événement contextuel reliant temps/lieu/météo aux systèmes.",
                system=", ".join(systems),
                obtention=f"Déclencheur {trigger['type']} à {loc}.",
                consumers="system_evenements, system_progression.",
                consequences="Applique des effets (narration/économie/cultures).",
                assets="effet visuel/particules de l'événement.",
                animations="animation contextuelle de l'événement.",
                tests="test_evenement_atteignable, test_evenement, test_temporel."),
        })
    return out


def _event_effects(eid: str, systems: list[str]) -> list[dict]:
    eff = []
    if "system_memoire" in systems:
        eff.append({"type": "reveal_fact", "params": {"fait_id": "fait_valdore", "to": "joueur"}})
    if "system_agriculture" in systems:
        eff.append({"type": "set_flag", "params": {"flag_id": "sol_arrose", "value": True}})
    if "system_economie" in systems:
        eff.append({"type": "modify_economy", "params": {"amount": 10}})
    if "system_secrets" in systems:
        eff.append({"type": "discover_secret", "params": {"secret_id": "secret_clairiere_repetition"}})
    if not eff:
        eff.append({"type": "set_flag", "params": {"flag_id": f"evt_{eid}", "value": True}})
    return eff


# =============================================================================
# SECRETS (existence DEDUITE du canon ; contenu À_VALIDER ; chemin de découverte)
# =============================================================================

SECRET_TEMPLATES = [
    ("secret_clairiere_repetition", "Ce qui se répète dans le Bois",
     "lieu_clairiere_qui_se_repete",
     ["quete_ce_qui_se_repete", "evenement_retour_du_bois"],
     "DEDUITE de 'forêt où certains événements se répètent' (canon) ; le contenu "
     "exact des secrets du Bois est un élément ouvert du canon (À_VALIDER).",
     "system_secrets, system_memoire"),
    ("secret_passe_nox", "Le passé tu de Nox",
     "lieu_poste_de_peche_du_lac_muet",
     ["quete_le_silence_de_nox"],
     "DEDUITE de 'Nox : pêcheur qui refuse de parler de son passé' (canon).",
     "system_relations, system_memoire"),
]


def build_secrets() -> list[dict]:
    out = []
    for sid, name, loc, discovery, just, sysid in SECRET_TEMPLATES:
        out.append({
            "id": sid, "display_name": name, "status": Status.DEDUITE,
            "source": f"{SRC_CANON}#Lieux/Personnages (dérivé)",
            "justification": just, "description": name,
            "kind": "secret", "location_id": loc,
            "discovery_path": discovery, "system": sysid,
            "content_status": Status.A_VALIDER,
            "derivation": _derivation(
                why="Secret rattaché à un lieu canonique ; donne une conséquence "
                    "narrative durable et un objectif d'exploration.",
                system=sysid,
                obtention="Découverte via quête/événement (chemin explicite).",
                consumers="system_secrets, system_progression, dialogues.",
                consequences="Révèle un fait ; débloque narration/quête.",
                assets="indice visuel discret sur la carte (famille secrets).",
                animations="animation de découverte/révélation.",
                tests="test_secret_decouvrable, test_evenement_atteignable, test_narratif."),
        })
    return out


# =============================================================================
# MAPS (1 par lieu canonique ; navigation + terrains ; détails au manifest)
# =============================================================================

MAP_TEMPLATES = [
    # clean_name, size(tuiles), terrains, linked (clean_names), desc
    ("Maison-Racine", (40, 30), ["plancher", "bois", "pierre"],
     ["Vallée Claire"], "Refuge et atelier principal (canon)."),
    ("Vallée Claire", (80, 60), ["herbe", "sol_meuble", "eau", "terre"],
     ["Maison-Racine", "Bois des Retours", "Lac Muet"],
     "Zone de départ et terres cultivables (canon)."),
    ("Bois des Retours", (70, 70), ["feuillage", "terre", "herbe"],
     ["Vallée Claire", "Lac Muet"], "Forêt où certains événements se répètent (canon)."),
    ("Lac Muet", (60, 50), ["eau", "pont", "herbe"],
     ["Vallée Claire", "Bois des Retours"], "Zone d'exploration et de pêche (canon)."),
]


def build_maps(canon: dict) -> list[dict]:
    out = []
    for clean, size, terrains, linked, desc in MAP_TEMPLATES:
        mid = make_id("map", clean)
        out.append({
            "id": mid, "display_name": clean, "status": Status.DEDUITE,
            "source": f"{SRC_CANON}#Lieux connus (dérivé)",
            "justification": f"Carte du lieu canonique '{clean}' ; le nombre de "
                             f"biomes est une décision ouverte (À_VALIDER).",
            "description": desc,
            "location_id": make_id("lieu", clean),
            "size": {"w": size[0], "h": size[1]},
            "tile_size": {"w": 16, "h": 16},
            "terrains": terrains,
            "linked_maps": [make_id("map", l) for l in linked],
            "seed": derive_seed("map", clean),
            "regions": [], "zones": [], "paths": [], "entrances": [], "exits": [],
            "collisions": [], "height_levels": [0],
            "points_of_interest": [], "buildings": [], "secret_zones": [],
            "resources": [], "placement_rules": [], "navigation_rules": [],
            "spawn_rules": [], "seasonal_conditions": [], "transitions": [],
            "quantity_status": Status.A_VALIDER,
            "derivation": _derivation(
                why="Chaque lieu canonique a besoin d'une carte navigable.",
                system="system_exploration, system_navigation",
                obtention="Déduite du lieu canonique.",
                consumers="navigation, placement, spawn, exploration.",
                consequences="Permet le déplacement, le placement et les transitions.",
                assets="1 tileset par famille de terrain + transitions.",
                animations="animations météo/saisonnières de la carte.",
                tests="test_map, test_navigation, test_placement, test_atteignabilite."),
        })
    return out


# =============================================================================
# PLAN DE QUANTITÉS (calculé + justifié)
# =============================================================================

def build_quantity_plan(canon, systems, seasons, crops, objects, machines,
                        recipes, npcs, creatures, quests, events,
                        locations) -> dict[str, Any]:
    """Calcule et JUSTIFIE chaque quantité (jamais arbitraire).

    Pour chaque type : valeur plancher (systèmes), valeur canonique, valeur
    proposée, statut (À_VALIDER si décision ouverte), et justification.
    """
    reqs = systems_mod.compute_system_requirements(systems)

    def floor_for(entity_type: str) -> int:
        return sum(v for k, v in reqs.items() if k.startswith(entity_type + ":"))

    plan = {}

    def add(kind, canon_n, derived_n, proposed_n, status, why):
        plan[kind] = {
            "canonical": canon_n, "derived": derived_n, "proposed_total": proposed_n,
            "system_floor": floor_for(kind), "quantity_status": status,
            "justification": why,
        }

    add("saison", 0, 0, len(seasons), Status.A_VALIDER,
        "Nombre de saisons = décision ouverte ; défaut technique 4 (1 par cycle).")
    add("lieu", len(canon["locations"]),
        len([l for l in locations if l["status"] == Status.DEDUITE]),
        len(locations), Status.DEDUITE,
        "4 lieux canoniques + zones/POI déduites des descriptions et des systèmes.")
    add("culture", 0, len([c for c in crops if c["status"] == Status.DEDUITE]),
        len(crops), Status.A_VALIDER,
        "Nombre exact de cultures = décision ouverte ; proposé = 1 plante mémorielle "
        "(canon) + couverture des 4 saisons + besoins cuisine/artisanat/relations.")
    add("objet", len(canon["objects"]),
        len([o for o in objects if o["status"] == Status.DEDUITE]),
        len(objects), Status.DEDUITE,
        "5 objets canoniques + graines/produits/outils déduits des cultures, "
        "recettes et systèmes. Aucun objet sans utilité.")
    add("ressource", 0, len([r for r in objects if r.get("category") == "ressource"]),
        len([r for r in objects if r.get("category") == "ressource"]) + 3,
        Status.PROPOSEE,
        "Matériaux d'artisanat (bois/pierre/argile) + ressources de récolte/pêche.")
    add("machine", 0, len([m for m in machines if m["status"] == Status.DEDUITE]),
        len(machines), Status.PROPOSEE,
        "1 station par système de transformation (artisanat, cuisine, mémoire) + "
        "métier à tisser pour la chaîne lin->fil->toile.")
    add("recette", 0, 0, len(recipes), Status.A_VALIDER,
        "Recettes exactes = élément ouvert du canon ; proposé = couverture des "
        "chaînes cuisine/artisanat/mémoire (1 recette par station minimum).")
    add("pnj", len(canon["npcs"]), 0, len(npcs), Status.A_VALIDER,
        "3 PNJ canoniques ; nombre exact = décision ouverte. Rôles merchant "
        "couverts par Marin/Nox (DEDUIT), donc pas de PNJ inventé requis.")
    add("creature", 0, len([c for c in creatures if c["status"] == Status.DEDUITE]),
        len(creatures), Status.PROPOSEE,
        "1 poisson (pêche, Lac Muet canon) + 1 écho du Bois (secrets, canon).")
    add("quete", 0, 0, len(quests), Status.A_VALIDER,
        "Nombre exact de quêtes = décision ouverte ; proposé = 1 quête par PNJ "
        "canonique + 1 quête de secret (Bois des Retours).")
    add("evenement", 0, 0, len(events), Status.PROPOSEE,
        "1 événement par contexte déclencheur (saison, météo, objet, jour) pour "
        "couvrir le système 'événements contextuels'.")
    add("map", 0, len(canon["locations"]), len(canon["locations"]), Status.A_VALIDER,
        "1 carte par lieu canonique (4). Nombre de biomes = décision ouverte.")
    return plan


# =============================================================================
# ASSEMBLAGE
# =============================================================================

def _propagate_values(objets: list[dict], resources: list[dict],
                      recipes: list[dict], margin: float = 1.4) -> None:
    """Calcule la valeur des produits transformés depuis leurs intrants.

    Garantit une chaîne économique sans perte : valeur(sortie) >=
    somme(valeur(entrées)) * margin. Itère pour propager le long des chaînes
    (lin -> fil -> toile). Déterministe.
    """
    value: dict[str, float] = {}
    for o in objets:
        if o.get("base_value") is not None:
            value[o["id"]] = o["base_value"]
    for r in resources:
        if r.get("base_value") is not None:
            value[r["id"]] = r["base_value"]

    obj_by_id = {o["id"]: o for o in objets}
    # Plusieurs passes pour propager les chaînes multi-étapes.
    for _ in range(6):
        changed = False
        for rec in recipes:
            in_val = sum(value.get(i["item_id"], 0) * i.get("qty", 1)
                         for i in rec.get("inputs", []))
            if in_val <= 0:
                continue
            for outp in rec.get("outputs", []):
                oid = outp["item_id"]
                qty = outp.get("qty", 1) or 1
                new_val = round((in_val * margin) / qty)
                # Ne jamais diminuer une valeur canonique fixée.
                target = obj_by_id.get(oid)
                if target is None:
                    continue
                cur = value.get(oid)
                if cur is None or new_val > cur:
                    if target.get("status") == Status.CANONIQUE and target.get("base_value") is not None:
                        continue  # valeur canonique non négociable
                    value[oid] = new_val
                    target["base_value"] = new_val
                    changed = True
        if not changed:
            break


def _dedupe(objets: list[dict]) -> list[dict]:
    """Déduplique les objets par ID en préservant le statut le plus fort."""
    by_id: dict[str, dict] = {}
    rank = {Status.CANONIQUE: 0, Status.DEDUITE: 1, Status.PROPOSEE: 2, Status.A_VALIDER: 3}
    for o in objets:
        prev = by_id.get(o["id"])
        if prev is None or rank.get(o["status"], 9) < rank.get(prev["status"], 9):
            by_id[o["id"]] = o
    return list(by_id.values())


def build_all(canon_artifacts: dict, systems: list[dict]) -> dict[str, Any]:
    """Construit tous les catalogues depuis le canon et les systèmes."""
    canon = canon_artifacts["canon"]
    seasons = build_seasons()
    locations = build_locations(canon)
    crops, crop_objets = build_crops(seasons)
    resources = build_resources()
    machines = build_machines()
    recipes, recipe_objets = build_recipes()
    tool_objets = build_tool_objects(canon)
    npcs = build_npcs(canon)
    creatures, creature_objets = build_creatures()
    quests = build_quests(canon)
    events = build_events()
    secrets = build_secrets()
    maps = build_maps(canon)

    # Assembler les objets : canon + graines + produits + plats + outils + créatures.
    all_objets = _dedupe(
        tool_objets + crop_objets + recipe_objets + creature_objets
    )

    # Lier les recettes aux machines.
    machine_by_id = {m["id"]: m for m in machines}
    for r in recipes:
        m = machine_by_id.get(r["station_id"])
        if m and r["id"] not in m["recipe_ids"]:
            m["recipe_ids"].append(r["id"])

    # Propagation économique : la valeur d'un produit transformé doit être
    # supérieure à la somme de ses intrants (marge), sinon perte de valeur.
    _propagate_values(all_objets, resources, recipes)

    quantity_plan = build_quantity_plan(
        canon, systems, seasons, crops, all_objets, machines, recipes,
        npcs, creatures, quests, events, locations)
    quantity_plan["secret"] = {
        "canonical": 0, "derived": len(secrets), "proposed_total": len(secrets),
        "system_floor": 1, "quantity_status": Status.A_VALIDER,
        "justification": "Secrets du Bois des Retours = élément ouvert du canon ; "
                         "existence DEDUITE (Bois qui se répète, passé de Nox), "
                         "contenu exact À_VALIDER. Chaque secret a un chemin de découverte.",
    }

    return {
        "seasons": seasons, "locations": locations, "crops": crops,
        "resources": resources, "machines": machines, "recipes": recipes,
        "objects": all_objets, "npcs": npcs, "creatures": creatures,
        "quests": quests, "events": events, "secrets": secrets, "maps": maps,
        "quantity_plan": quantity_plan,
    }


def build_functional_catalog(catalogs: dict, systems: list[dict]) -> dict[str, Any]:
    """Catalogue fonctionnel : vue unifiée entité -> systèmes -> verbes -> tests."""
    entries = []

    def add(entity_type: str, ent: dict):
        entries.append({
            "entity_type": entity_type, "id": ent["id"],
            "display_name": ent.get("display_name"),
            "status": ent.get("status"),
            "system": ent.get("system") or ent.get("used_by")
            or (ent.get("systems") if isinstance(ent.get("systems"), str) else None),
            "systems": ent.get("systems") or [],
            "justification": ent.get("justification"),
            "derivation": ent.get("derivation"),
        })

    for etype, key in [("saison", "seasons"), ("lieu", "locations"),
                       ("culture", "crops"), ("ressource", "resources"),
                       ("machine", "machines"), ("recette", "recipes"),
                       ("objet", "objects"), ("pnj", "npcs"),
                       ("creature", "creatures"), ("quete", "quests"),
                       ("evenement", "events"), ("secret", "secrets"),
                       ("map", "maps")]:
        for ent in catalogs.get(key, []):
            add(etype, ent)

    return {
        "count": len(entries),
        "by_type": {t: len([e for e in entries if e["entity_type"] == t])
                    for t in {e["entity_type"] for e in entries}},
        "entries": entries,
    }


def run_stage(canon_artifacts: dict, systems: list[dict], write: bool = True) -> dict[str, Any]:
    catalogs = build_all(canon_artifacts, systems)
    functional = build_functional_catalog(catalogs, systems)

    if write:
        # Catalogues individuels.
        mapping = {
            "seasons": "seasons", "locations": "locations", "crops": "crops",
            "resources": "resources", "machines": "machines", "recipes": "recipes",
            "objects": "objects", "npcs": "npcs", "creatures": "creatures",
            "quests": "quests", "events": "events", "secrets": "secrets",
            "maps": "maps",
        }
        for key, fname in mapping.items():
            write_json(DIRS["catalogs"] / f"{fname}.json",
                       versioned_envelope(catalogs[key], kind=fname))
        write_json(DIRS["catalogs"] / "quantity_plan.json",
                   versioned_envelope(catalogs["quantity_plan"], kind="quantity_plan"))
        write_json(DIRS["functional_catalog"] / "functional_catalog.json",
                   versioned_envelope(functional, kind="functional_catalog"))
    catalogs["functional_catalog"] = functional
    return catalogs


if __name__ == "__main__":
    from . import canon as canon_mod
    ca = canon_mod.run_stage(write=False)
    sy = systems_mod.run_stage(write=False)["systems"]
    res = run_stage(ca, sy)
    for k in ("seasons", "locations", "crops", "resources", "machines",
              "recipes", "objects", "npcs", "creatures", "quests", "events"):
        print(f"{k}: {len(res[k])}")
    print("functional_catalog:", res["functional_catalog"]["count"], "entrées")
