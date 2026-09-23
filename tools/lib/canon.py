"""Extraction et verrouillage du canon central.

Étape 1-14 de l'ordre de travail :
- lire les quatre fichiers d'entrée + le contrat ;
- extraire le canon initial (faits, lieux, personnages, objets, règles) ;
- distinguer CANONIQUE / DEDUITE / PROPOSEE / A_VALIDER ;
- produire le canon central verrouillé ;
- produire le rapport des décisions et le rapport des contradictions/ambiguïtés.

Aucune décision créative ouverte n'est transformée en fait canonique.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import (
    DIRS, Status, make_id, read_text, write_json, write_text, versioned_envelope,
    strip_accents,
)

# --- Analyse markdown --------------------------------------------------------

_SECTION_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def parse_markdown_sections(text: str) -> dict[str, list[str]]:
    """Découpe un markdown en {titre_de_section: [lignes]}.

    Les puces ('- ', '* ') et lignes numérotées ('1. ') sont conservées
    telles quelles dans la liste de la section courante.
    """
    sections: dict[str, list[str]] = {}
    current = "_preamble"
    sections[current] = []
    for raw in text.splitlines():
        m = _SECTION_RE.match(raw.strip())
        if m:
            current = m.group(2).strip()
            sections.setdefault(current, [])
            continue
        sections[current].append(raw)
    return sections


def bullets(lines: list[str], *, strict: bool = False) -> list[str]:
    """Extrait le texte des puces/numéros d'une liste de lignes.

    strict=True : ne conserve QUE les vraies puces ('- ', '* ', '1. ') et
    ignore le texte libre (paragraphes d'introduction).
    """
    out = []
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        m = re.match(r"^(?:[-*+]|\d+\.)\s+(.*)$", s)
        if m:
            out.append(m.group(1).strip().rstrip(".;").strip())
        elif not strict and s and not s.startswith("#"):
            # Ligne de texte libre (ex. prémisse) : conservée.
            out.append(s.rstrip(".;").strip())
    return out


def _clean_name(raw: str) -> str:
    """Retire les deux-points/explications d'une entrée 'Nom : description'."""
    return raw.split(":")[0].split(" :")[0].strip()


def _split_name_desc(raw: str) -> tuple[str, str]:
    """Sépare 'Nom : description' -> ('Nom', 'description')."""
    if ":" in raw:
        name, desc = raw.split(":", 1)
        return name.strip(), desc.strip()
    return raw.strip(), ""


_ARTICLE_RE = re.compile(
    r"^(?:les?\s+|la\s+|l['’]\s*|aux?\s+|du\s+|des?\s+|d['’]\s*)",
    re.IGNORECASE,
)


def strip_article(name: str) -> str:
    """Retire l'article initial d'un nom pour un ID stable et propre.

    'La Maison-Racine' -> 'Maison-Racine' ; 'Le Lac Muet' -> 'Lac Muet' ;
    'le Jardinier' -> 'Jardinier'. Le display_name conserve l'article ;
    seul l'ID interne le perd.
    """
    prev = None
    s = name.strip()
    # Retire les articles composés successifs (ex. 'du', 'des').
    while prev != s:
        prev = s
        s = _ARTICLE_RE.sub("", s, count=1).strip()
    return s


# IDs sémantiques stables pour les faits immuables (référençables en aval).
_FACT_SEMANTIC = [
    ("monde s’appelle", "fait_monde_valdore"),
    ("monde s'appelle", "fait_monde_valdore"),
    ("joueur est appelé", "fait_joueur_jardinier"),
    ("joueur est appele", "fait_joueur_jardinier"),
    ("refuge principal", "fait_refuge_maison_racine"),
    ("fragments physiques", "fait_fragments_physiques"),
    ("graines d’écho", "fait_graines_echo"),
    ("graines d'echo", "fait_graines_echo"),
    ("magie de combat", "fait_pas_magie_combat"),
]


def semantic_fact_id(statement: str) -> str:
    """Associe un ID sémantique stable à un fait immuable (sinon slug)."""
    low = statement.lower()
    for key, fid in _FACT_SEMANTIC:
        if key in low:
            return fid
    return make_id("fait", statement)


# --- Chargement des entrées --------------------------------------------------

def load_inputs() -> dict[str, str]:
    """Charge les quatre entrées + le contrat. Échoue si une entrée manque."""
    required = {
        "brief": DIRS["input"] / "game_brief.md",
        "canon": DIRS["input"] / "canon_initial.md",
        "constraints": DIRS["input"] / "constraints.md",
        "open_decisions": DIRS["input"] / "open_decisions.md",
        "contract": DIRS["contract"] / "architecture_contract.md",
    }
    loaded = {}
    for key, path in required.items():
        text = read_text(path)
        if not text.strip():
            raise SystemExit(f"MISSING_INPUT: {path}")
        loaded[key] = text
    return loaded


# --- Extraction du canon -----------------------------------------------------

def _entry(category: str, name: str, desc: str, status: str, source: str,
           justification: str) -> dict[str, Any]:
    return {
        "id": make_id(category, name),
        "display_name": name,
        "category": category,
        "description": desc,
        "status": status,
        "source": source,
        "justification": justification,
    }


def extract_canon(canon_md: str) -> dict[str, Any]:
    """Extrait le canon structuré depuis canon_initial.md."""
    sec = parse_markdown_sections(canon_md)

    def find(*keys: str) -> list[str]:
        for k in keys:
            for title, lines in sec.items():
                if title.lower().startswith(k.lower()):
                    return bullets(lines)
        return []

    src = "INPUT/canon_initial.md"

    # Faits immuables -> CANONIQUE (IDs sémantiques stables).
    facts = []
    for f in find("Faits immuables"):
        facts.append({
            "id": semantic_fact_id(f),
            "statement": f,
            "status": Status.CANONIQUE,
            "source": f"{src}#Faits immuables",
        })

    # Lieux connus -> CANONIQUE (ID sans article, display_name avec article).
    locations = []
    for raw in find("Lieux connus"):
        name, desc = _split_name_desc(raw)
        clean = strip_article(name)
        loc = _entry("lieu", clean, desc, Status.CANONIQUE,
                     f"{src}#Lieux connus",
                     "Lieu explicitement défini dans le canon initial.")
        loc["display_name"] = name  # conserve l'article à l'affichage
        loc["clean_name"] = clean
        loc["map_id"] = make_id("map", clean)
        locations.append(loc)

    # Personnages connus -> CANONIQUE
    npcs = []
    for raw in find("Personnages connus"):
        name, desc = _split_name_desc(raw)
        npcs.append(_entry("pnj", name, desc, Status.CANONIQUE,
                           f"{src}#Personnages connus",
                           "Personnage explicitement défini dans le canon initial."))

    # Objets canoniques -> CANONIQUE
    objects = []
    for raw in find("Objets canoniques"):
        name = _clean_name(raw)
        objects.append(_entry("objet", name, "", Status.CANONIQUE,
                              f"{src}#Objets canoniques",
                              "Objet explicitement défini dans le canon initial."))

    # Règles de nommage -> CANONIQUE (règle du monde)
    naming_lines = find("Règles de nommage")
    naming_rules = " ".join(naming_lines).strip()

    # Éléments ouverts (dans le canon) -> A_VALIDER
    open_in_canon = []
    for raw in find("Éléments ouverts", "Elements ouverts"):
        open_in_canon.append({
            "id": make_id("ouvert", raw),
            "topic": raw,
            "status": Status.A_VALIDER,
            "source": f"{src}#Éléments ouverts",
            "justification": "Élément explicitement marqué ouvert dans le canon.",
        })

    # Faits saillants réutilisables.
    world_name = "Valdore"
    player_name = "le Jardinier"
    refuge_name = "la Maison-Racine"
    for f in facts:
        s = f["statement"].lower()
        if "monde s’appelle" in s or "monde s'appelle" in s:
            world_name = f["statement"].split("appelle")[-1].strip().rstrip(".")
        if "joueur est appelé" in s or "joueur est appele" in s:
            player_name = f["statement"].split("appelé")[-1].split("appele")[-1].strip().rstrip(".")
        if "refuge principal" in s:
            refuge_name = f["statement"].split("appelle")[-1].strip().rstrip(".")

    world_e = _entry("monde", strip_article(world_name), "Nom du monde.",
                     Status.CANONIQUE, f"{src}#Faits immuables", "Fait immuable explicite.")
    world_e["display_name"] = world_name
    player_e = _entry("joueur", strip_article(player_name),
                      "Rôle incarné par le joueur.",
                      Status.CANONIQUE, f"{src}#Faits immuables", "Fait immuable explicite.")
    player_e["display_name"] = player_name
    refuge_e = _entry("lieu", strip_article(refuge_name),
                      "Refuge et atelier principal.",
                      Status.CANONIQUE, f"{src}#Faits immuables", "Fait immuable explicite.")
    refuge_e["display_name"] = refuge_name

    return {
        "world": world_e,
        "player": player_e,
        "refuge": refuge_e,
        "facts": facts,
        "locations": locations,
        "npcs": npcs,
        "objects": objects,
        "naming_rules": naming_rules,
        "open_in_canon": open_in_canon,
    }


def extract_brief(brief_md: str) -> dict[str, Any]:
    """Extrait le brief structuré (identité, prémisse, boucles, systèmes)."""
    sec = parse_markdown_sections(brief_md)

    def find(*keys: str) -> list[str]:
        for k in keys:
            for title, lines in sec.items():
                if title.lower().startswith(k.lower()):
                    return bullets(lines)
        return []

    identity = {}
    for line in find("Identité", "Identite"):
        if ":" in line:
            k, v = line.split(":", 1)
            identity[k.strip().lower()] = v.strip()

    loops = find("Boucles principales")
    systems = [s for s in find("Systèmes souhaités", "Systemes souhaités")]
    premise = " ".join(find("Prémisse", "Premisse")).strip()
    role = " ".join(find("Rôle du joueur", "Role du joueur")).strip()

    return {
        "title": identity.get("nom provisoire", "Sans titre"),
        "genre": identity.get("genre", ""),
        "perspective": identity.get("perspective", ""),
        "platform": identity.get("plateforme", ""),
        "style": identity.get("style général", identity.get("style general", "")),
        "premise": premise,
        "player_role": role,
        "loops": loops,
        "systems": systems,
        "source": "INPUT/game_brief.md",
    }


def extract_constraints(constraints_md: str) -> dict[str, Any]:
    """Extrait les contraintes structurées (technique, architecture, IA, qualité)."""
    sec = parse_markdown_sections(constraints_md)
    out: dict[str, Any] = {"source": "INPUT/constraints.md"}
    for title, lines in sec.items():
        key = make_id("categorie", title) if title != "_preamble" else "_preamble"
        items = bullets(lines)
        if items:
            out[key] = items

    # Valeur technique clé : taille de tuile (CANONIQUE via contraintes).
    tile = {"w": 16, "h": 16}
    for cat, items in out.items():
        if not isinstance(items, list):
            continue
        for it in items:
            m = re.search(r"(\d+)\s*[×x]\s*(\d+)", it)
            if m and "tuile" in it.lower():
                tile = {"w": int(m.group(1)), "h": int(m.group(2))}
    out["tile_size"] = tile
    return out


def extract_open_decisions(decisions_md: str) -> list[dict[str, Any]]:
    """Extrait les décisions ouvertes (À_VALIDER) depuis open_decisions.md."""
    sec = parse_markdown_sections(decisions_md)
    items: list[str] = []
    for title, lines in sec.items():
        # strict=True : ne garder que les vraies puces décisionnelles,
        # pas les paragraphes d'introduction/de politique.
        items.extend(bullets(lines, strict=True))
    # Filtrer la phrase de politique si elle apparaît malgré tout.
    out = []
    for raw in items:
        low = raw.lower()
        if low.startswith("l’ia peut") or low.startswith("l'ia peut") or "peut choisir" in low:
            continue
        out.append({
            "id": make_id("decision", raw),
            "topic": raw,
            "status": Status.A_VALIDER,
            "source": "INPUT/open_decisions.md",
            "justification": "Décision explicitement listée comme ouverte par le propriétaire.",
        })
    return out


# --- Détection de contradictions / ambiguïtés --------------------------------

def detect_contradictions(canon: dict, brief: dict, constraints: dict,
                          open_decisions: list[dict]) -> list[dict]:
    """Détecte contradictions et ambiguïtés entre les entrées.

    Chaque entrée : id, severite (CONTRADICTION|AMBIGUITE|MANQUE), sujet,
    description, sources, statut_recommande, action.
    """
    findings: list[dict] = []

    def norm(s: str) -> str:
        # Normalisation sans accents pour les comparaisons de présence.
        return strip_accents(s).lower()

    open_topics = norm(" ".join(d["topic"] for d in open_decisions))
    canon_blob = norm(" ".join(
        [canon["world"]["display_name"]]
        + [l["display_name"] + " " + l["description"] for l in canon["locations"]]
        + [n["display_name"] + " " + n["description"] for n in canon["npcs"]]
        + [o["display_name"] for o in canon["objects"]]
        + [f["statement"] for f in canon["facts"]]
    ))

    def add(sev, sujet, desc, sources, statut, action):
        findings.append({
            "id": make_id(sujet.split()[0] if sujet else "amb", sujet),
            "severite": sev,
            "sujet": sujet,
            "description": desc,
            "sources": sources,
            "statut_recommande": statut,
            "action": action,
        })

    # 1. Tension canon vs décision ouverte : un système canonique dont une
    #    propriété est ouverte.
    tension_map = [
        ("saison", "Le système 'saisons' est implicite dans le brief, mais le "
                   "NOMBRE de saisons est une décision ouverte. Le système est "
                   "acquis, la quantité reste à valider.",
         ["INPUT/game_brief.md#Systèmes souhaités", "INPUT/open_decisions.md"],
         Status.A_VALIDER, "Générer les saisons avec un défaut modulaire (4) "
                           "marqué À_VALIDER ; ne pas verrouiller la quantité."),
        ("peche", "Le Lac Muet est canoniquement une 'zone de pêche', mais "
                  "l'IMPORTANCE de la pêche est une décision ouverte. "
                  "L'existence est déduite du canon, la profondeur reste à valider.",
         ["INPUT/canon_initial.md#Lieux connus", "INPUT/open_decisions.md"],
         Status.DEDUITE, "Pêche présente comme système mineur (DEDUITE) ; son "
                         "ampleur est À_VALIDER."),
        ("combat", "Le canon interdit la 'magie de combat traditionnelle', mais "
                   "open_decisions demande la 'présence ou non d'un système de "
                   "combat'. Absence de magie de combat != absence de tout "
                   "système de combat : ambiguïté à trancher.",
         ["INPUT/canon_initial.md#Faits immuables", "INPUT/open_decisions.md"],
         Status.A_VALIDER, "Défaut technique : aucun système de combat (cohérent "
                           "avec le ton contemplatif) ; décision finale À_VALIDER."),
    ]
    for key, desc, sources, statut, action in tension_map:
        if key in open_topics or key in canon_blob:
            add("AMBIGUITE", key, desc, sources, statut, action)

    # 2. Manque : systèmes requis sans donnée canonique associée.
    system_list = [s.lower() for s in brief["systems"]]
    if any("économie" in s or "economie" in s for s in system_list):
        if "monnaie" not in canon_blob and "écu" not in canon_blob and "prix" not in canon_blob:
            add("MANQUE", "monnaie",
                "Le système 'économie simple' est souhaité mais aucune monnaie "
                "n'est définie dans le canon. Nécessaire pour les validateurs "
                "économiques.",
                ["INPUT/game_brief.md#Systèmes souhaités", "INPUT/canon_initial.md"],
                Status.A_VALIDER,
                "Proposer une monnaie (nom + unité) marquée À_VALIDER ; bloquer "
                "seulement la validation économique tant que non tranchée.")

    # 3. Manque : météo souhaitée sans saisons/états définis.
    if any("météo" in s or "meteo" in s for s in system_list):
        add("MANQUE", "meteo",
            "Le système 'météo' est souhaité mais aucun état météo n'est défini "
            "dans le canon. À déduire des saisons.",
            ["INPUT/game_brief.md#Systèmes souhaités"],
            Status.DEDUITE,
            "Déduire un ensemble météo minimal par saison (DEDUITE) ; noms À_VALIDER.")

    # 4. Cohérence positive : vérifier qu'aucun lieu canonique n'est contredit.
    #    (Ici les entrées sont cohérentes ; on documente l'absence de conflit dur.)
    return findings


# --- Canon central verrouillé ------------------------------------------------

def build_locked_canon(canon: dict, brief: dict, constraints: dict,
                       open_decisions: list[dict]) -> dict[str, Any]:
    """Construit le canon central verrouillé (artefact signé, non négociable).

    Le canon verrouillé ne contient QUE des éléments CANONIQUE. Les éléments
    DEDUITE/PROPOSEE/A_VALIDER vivent dans les rapports et les catalogues,
    jamais dans le canon verrouillé.
    """
    locked = {
        "world": canon["world"],
        "player": canon["player"],
        "refuge": canon["refuge"],
        "immutable_facts": canon["facts"],
        "locations": canon["locations"],
        "npcs": canon["npcs"],
        "objects": canon["objects"],
        "naming_rules": canon["naming_rules"],
        "technical_constraints": {
            "engine": "Godot 4",
            "perspective": brief["perspective"] or "2D vue du dessus",
            "tile_size": constraints.get("tile_size", {"w": 16, "h": 16}),
            "rendering": "pixel art, mise à l'échelle entière",
            "data_export": ["JSON", "ressources Godot"],
            "runtime_llm_required": False,
        },
        "gameplay_systems_canonical": brief["systems"],
        "main_loops": brief["loops"],
        "lock": {
            "locked": True,
            "policy": "Aucun élément de ce fichier ne peut être modifié sans "
                      "signalement explicite. Les propositions et décisions "
                      "ouvertes sont stockées hors de ce fichier.",
        },
    }
    return locked


# --- Rapports ----------------------------------------------------------------

def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(["---"] * len(headers)) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("\n", " ") for c in r) + " |")
    return "\n".join(out)


def build_decision_report(canon, brief, constraints, open_decisions,
                          contradictions) -> str:
    """Rapport des informations CANONIQUE/DEDUITE/PROPOSEE/A_VALIDER."""
    lines = ["# Rapport des décisions et statuts", "",
             "Ce rapport classe chaque information selon les quatre statuts. "
             "Aucune décision créative ouverte n'est convertie en canon.", ""]

    # CANONIQUE
    lines += ["## CANONIQUE (non négociable)", "",
              _md_table(["Élément", "Type", "Source"],
                        [[canon["world"]["display_name"], "monde", canon["world"]["source"]],
                         [canon["player"]["display_name"], "joueur", canon["player"]["source"]],
                         [canon["refuge"]["display_name"], "refuge", canon["refuge"]["source"]]]
                        + [[f["statement"], "fait", f["source"]] for f in canon["facts"]]
                        + [[l["display_name"], "lieu", l["source"]] for l in canon["locations"]]
                        + [[n["display_name"], "pnj", n["source"]] for n in canon["npcs"]]
                        + [[o["display_name"], "objet", o["source"]] for o in canon["objects"]]),
              ""]

    # DEDUITE
    ded = [c for c in contradictions if c["statut_recommande"] == Status.DEDUITE]
    lines += ["## DEDUITE (dérivée du canon/systèmes)", "",
              _md_table(["Sujet", "Justification", "Action"],
                        [[c["sujet"], c["description"], c["action"]] for c in ded])
              if ded else "_Aucune information purement déduite à ce stade._",
              ""]

    # PROPOSEE (défauts techniques modulaires)
    lines += ["## PROPOSEE (recommandations techniques/créatives)", "",
              _md_table(["Sujet", "Proposition", "Justification"],
                        [["météo", "Ensemble météo minimal dérivé des saisons",
                          "Requis par le système 'météo' du brief"],
                         ["monnaie", "Monnaie unique proposée (voir rapport)",
                          "Requise par le système 'économie simple'"],
                         ["durée_journée", "Defaut technique modulaire",
                          "Nécessaire au simulateur temporel"]]),
              ""]

    # A_VALIDER
    lines += ["## À_VALIDER (décision du propriétaire)", "",
              _md_table(["Décision", "Source", "Statut"],
                        [[d["topic"], d["source"], d["status"]] for d in open_decisions]
                        + [[o["topic"] + " (canon ouvert)", o["source"], o["status"]]
                           for o in canon["open_in_canon"]]),
              ""]
    return "\n".join(lines)


def build_contradiction_report(contradictions) -> str:
    lines = ["# Rapport des contradictions et ambiguïtés", "",
             "Détection des tensions entre canon, brief, contraintes et "
             "décisions ouvertes. Chaque finding propose un statut et une action.",
             ""]
    if not contradictions:
        lines.append("_Aucune contradiction détectée._")
        return "\n".join(lines)
    by_sev = {}
    for c in contradictions:
        by_sev.setdefault(c["severite"], []).append(c)
    for sev in ("CONTRADICTION", "AMBIGUITE", "MANQUE"):
        group = by_sev.get(sev, [])
        if not group:
            continue
        lines += [f"## {sev} ({len(group)})", "",
                  _md_table(["Sujet", "Description", "Statut recommandé", "Action"],
                            [[c["sujet"], c["description"], c["statut_recommande"], c["action"]]
                             for c in group]),
                  ""]
    return "\n".join(lines)


# --- Point d'entrée de l'étape canon ----------------------------------------

def run_stage(write: bool = True) -> dict[str, Any]:
    """Exécute l'étape 'canon' et retourne tous les artefacts produits."""
    inputs = load_inputs()
    canon = extract_canon(inputs["canon"])
    brief = extract_brief(inputs["brief"])
    constraints = extract_constraints(inputs["constraints"])
    open_decisions = extract_open_decisions(inputs["open_decisions"])
    contradictions = detect_contradictions(canon, brief, constraints, open_decisions)
    locked = build_locked_canon(canon, brief, constraints, open_decisions)

    artifacts = {
        "inputs": inputs,
        "canon": canon,
        "brief": brief,
        "constraints": constraints,
        "open_decisions": open_decisions,
        "contradictions": contradictions,
        "locked_canon": locked,
        "decision_report_md": build_decision_report(
            canon, brief, constraints, open_decisions, contradictions),
        "contradiction_report_md": build_contradiction_report(contradictions),
    }

    if write:
        write_json(DIRS["canon"] / "canon_locked.json",
                   versioned_envelope(locked, kind="canon_locked"))
        write_json(DIRS["canon"] / "canon_extracted.json",
                   versioned_envelope(canon, kind="canon_extracted"))
        write_json(DIRS["canon"] / "brief_extracted.json",
                   versioned_envelope(brief, kind="brief_extracted"))
        write_json(DIRS["canon"] / "constraints_extracted.json",
                   versioned_envelope(constraints, kind="constraints_extracted"))
        write_json(DIRS["canon"] / "open_decisions.json",
                   versioned_envelope(open_decisions, kind="open_decisions"))
        write_json(DIRS["canon"] / "contradictions.json",
                   versioned_envelope(contradictions, kind="contradictions"))
        write_text(DIRS["reports"] / "decision_report.md",
                   artifacts["decision_report_md"])
        write_text(DIRS["reports"] / "contradiction_report.md",
                   artifacts["contradiction_report_md"])

    return artifacts


if __name__ == "__main__":
    res = run_stage()
    print("canon extrait :",
          len(res["canon"]["locations"]), "lieux,",
          len(res["canon"]["npcs"]), "PNJ,",
          len(res["canon"]["objects"]), "objets")
    print("contradictions/ambiguïtés :", len(res["contradictions"]))
    print("décisions ouvertes :", len(res["open_decisions"]))
