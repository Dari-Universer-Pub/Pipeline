"""Rapports de pipeline (étapes 44-46 ; livrables 91-96).

Produit :
- rapport de maturité des éléments (91) ;
- rapport des éléments manquants (92) ;
- rapport des éléments isolés (93) ;
- rapport des contradictions (94, déjà produit par canon.py, consolidé ici) ;
- rapport des décisions encore ouvertes (95) ;
- rapport des erreurs de génération (96, produit par importer.py).

La maturité d'un élément combine : statut, connectivité, systèmes affectés,
présence d'assets/animations, validation et couverture de tests.
"""
from __future__ import annotations

from typing import Any

from .common import DIRS, Status, write_text, write_json, versioned_envelope, unwrap, read_json

# Poids de maturité par statut (plus le statut est sûr, plus l'élément est mûr).
STATUS_WEIGHT = {Status.CANONIQUE: 40, Status.DEDUITE: 30, Status.PROPOSEE: 20,
                 Status.A_VALIDER: 10}


def compute_maturity(state: dict) -> dict[str, Any]:
    """Calcule un score de maturité (0-100) par entité."""
    conn = state.get("connectivity", {})
    depth = conn.get("causal_depth", {})
    graph = state.get("graph", {})
    edges = graph.get("edges", [])

    # Index des relations par entité.
    rel_count: dict[str, int] = {}
    usage_count: dict[str, int] = {}
    systems: dict[str, set] = {}
    node_type = {n["id"]: n["type"] for n in graph.get("nodes", [])}
    for e in edges:
        for nid in (e["source"], e["target"]):
            rel_count[nid] = rel_count.get(nid, 0) + 1
            if e.get("implies_usage"):
                usage_count[nid] = usage_count.get(nid, 0) + 1
        other_map = {e["source"]: e["target"], e["target"]: e["source"]}
        for a, b in other_map.items():
            if node_type.get(b) == "system":
                systems.setdefault(a, set()).add(b)

    # Assets/animations présents par entité.
    assets_by_entity: dict[str, int] = {}
    for a in state.get("manifests", {}).get("assets", []):
        assets_by_entity[a.get("entity_id")] = assets_by_entity.get(a.get("entity_id"), 0) + 1
    anims_by_entity: dict[str, int] = {}
    for an in state.get("manifests", {}).get("animations", []):
        anims_by_entity[an.get("entity_id")] = anims_by_entity.get(an.get("entity_id"), 0) + 1

    entries = []
    for coll_name, coll in state.get("catalogs", {}).items():
        for e in coll:
            if not isinstance(e, dict) or "id" not in e:
                continue
            eid = e["id"]
            score = 0
            score += STATUS_WEIGHT.get(e.get("status"), 0)
            # Connectivité (max 20).
            score += min(20, rel_count.get(eid, 0) * 3)
            # Usage réel (max 15).
            score += min(15, usage_count.get(eid, 0) * 5)
            # Systèmes affectés (max 10).
            score += min(10, len(systems.get(eid, set())) * 3)
            # Assets/animations (max 10).
            has_asset = assets_by_entity.get(eid, 0) > 0
            has_anim = anims_by_entity.get(eid, 0) > 0
            # Entités devant posséder un visuel propre (sprite/icône).
            needs_visual = coll_name in ("objects", "crops", "machines", "npcs",
                                         "creatures")
            if coll_name == "maps":
                # Une carte est mûre si elle a terrains + règles de placement/navigation.
                has_rules = bool(e.get("placement_rules") or e.get("terrains"))
                score += 10 if has_rules else 0
            else:
                if not needs_visual or has_asset:
                    score += 5
                if not needs_visual or has_anim or coll_name not in ("npcs", "creatures", "crops", "machines"):
                    score += 5
            # Test couvert (max 5) : présence d'un bloc derivation.tests.
            if e.get("derivation", {}).get("tests"):
                score += 5
            entries.append({
                "id": eid, "type": coll_name, "display_name": e.get("display_name"),
                "status": e.get("status"), "maturity": min(100, score),
                "relations": rel_count.get(eid, 0),
                "usage_relations": usage_count.get(eid, 0),
                "systems_affected": len(systems.get(eid, set())),
                "has_asset": has_asset, "has_animation": has_anim,
                "causal_depth": depth.get(eid, 0),
            })

    entries.sort(key=lambda x: x["maturity"])
    by_status = {}
    for e in entries:
        by_status.setdefault(e["status"], []).append(e)
    avg = round(sum(e["maturity"] for e in entries) / max(1, len(entries)), 1)
    return {
        "count": len(entries), "average_maturity": avg,
        "by_status": {k: len(v) for k, v in by_status.items()},
        "mature": len([e for e in entries if e["maturity"] >= 80]),
        "partial": len([e for e in entries if 50 <= e["maturity"] < 80]),
        "immature": len([e for e in entries if e["maturity"] < 50]),
        "entries": entries,
    }


def compute_missing(state: dict) -> dict[str, Any]:
    """Éléments manquants : à produire, références pendantes, exigences non couvertes."""
    conn = state.get("connectivity", {})
    quantity_plan = unwrap(read_json(DIRS["catalogs"] / "quantity_plan.json", {}))
    missing = {
        "dangling_references": conn.get("dangling_references", []),
        "to_produce": [], "open_quantity_decisions": [],
        "unmet_system_requirements": [],
    }
    # Éléments à produire (proposé > canonique+déduit) : contenu manquant.
    for kind, q in quantity_plan.items():
        produced = q.get("canonical", 0) + q.get("derived", 0)
        target = q.get("proposed_total", 0)
        if q.get("quantity_status") == Status.A_VALIDER:
            missing["open_quantity_decisions"].append(
                {"kind": kind, "proposed": target, "justification": q.get("justification")})
        if target > produced:
            missing["to_produce"].append(
                {"kind": kind, "have": produced, "target": target, "gap": target - produced})
    # Assets/animations référencés mais absents.
    asset_ids = {a["id"] for a in state.get("manifests", {}).get("assets", [])}
    for an in state.get("manifests", {}).get("animations", []):
        for ra in an.get("required_assets", []):
            if ra not in asset_ids:
                missing.setdefault("missing_assets", []).append(
                    {"animation": an["id"], "asset": ra})
    return missing


def compute_isolated(state: dict) -> dict[str, Any]:
    """Éléments isolés / orphelins / sans usage (depuis la connectivité)."""
    conn = state.get("connectivity", {})
    return {
        "orphans": conn.get("orphans", []),
        "unreachable": conn.get("unreachable", []),
        "weak_usage": conn.get("weak_usage", []),
        "objects_no_usage": conn.get("objects_no_usage", []),
        "resources_no_consumer": conn.get("resources_no_consumer", []),
        "secrets_no_discovery": conn.get("secrets_no_discovery", []),
        "systems_isolated": conn.get("systems_isolated", []),
    }


def compute_open_decisions(state: dict) -> dict[str, Any]:
    """Décisions encore ouvertes (propriétaire) + éléments ouverts du canon."""
    open_dec = unwrap(read_json(DIRS["canon"] / "open_decisions.json", []))
    canon_extracted = unwrap(read_json(DIRS["canon"] / "canon_extracted.json", {}))
    quantity_plan = unwrap(read_json(DIRS["catalogs"] / "quantity_plan.json", {}))
    a_valider = [
        {"topic": d["topic"], "source": d["source"], "status": d["status"]}
        for d in open_dec
    ]
    canon_open = canon_extracted.get("open_in_canon", [])
    quantity_open = [
        {"topic": f"Quantité de {k}", "proposed": v.get("proposed_total"),
         "justification": v.get("justification"), "status": Status.A_VALIDER}
        for k, v in quantity_plan.items() if v.get("quantity_status") == Status.A_VALIDER
    ]
    return {
        "owner_decisions": a_valider,
        "canon_open_elements": canon_open,
        "quantity_decisions": quantity_open,
        "total": len(a_valider) + len(canon_open) + len(quantity_open),
    }


# --- Rendus markdown ---------------------------------------------------------

def _table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join(["---"] * len(headers)) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("\n", " ") for c in r) + " |")
    return "\n".join(out)


def render_maturity(m: dict) -> str:
    lines = ["# Rapport de maturité des éléments", "",
             f"- Éléments évalués : **{m['count']}**",
             f"- Maturité moyenne : **{m['average_maturity']} / 100**",
             f"- Mûrs (≥80) : {m['mature']}  |  Partiels (50-79) : {m['partial']}  |  "
             f"Imatures (<50) : {m['immature']}",
             f"- Par statut : {m['by_status']}", "",
             "La maturité combine statut, connectivité, usage réel, systèmes "
             "affectés, assets/animations et couverture de tests.", "",
             "## Éléments les moins mûrs (à travailler en priorité)", ""]
    lines.append(_table(["ID", "Type", "Statut", "Maturité", "Relations", "Usage",
                         "Systèmes", "Asset", "Anim"],
                        [[e["id"], e["type"], e["status"], e["maturity"], e["relations"],
                          e["usage_relations"], e["systems_affected"],
                          "oui" if e["has_asset"] else "non",
                          "oui" if e["has_animation"] else "non"]
                         for e in m["entries"][:25]]))
    return "\n".join(lines)


def render_missing(mi: dict) -> str:
    lines = ["# Rapport des éléments manquants", "",
             "Éléments à produire, références pendantes et décisions de quantité "
             "ouvertes. La pipeline ne génère pas massivement : elle signale ce "
             "qui reste à produire.", ""]
    lines += ["## Références pendantes", "",
              (_table(["Référence"], [[d] for d in mi["dangling_references"]])
               if mi["dangling_references"] else "_Aucune ✓_"), ""]
    lines += ["## Contenu à produire (écart proposé vs canon+dérivé)", "",
              (_table(["Type", "Possédé", "Cible", "Écart"],
                      [[t["kind"], t["have"], t["target"], t["gap"]]
                       for t in mi["to_produce"]]) if mi["to_produce"]
               else "_Aucun écart : le blueprint minimal est complet ✓_"), ""]
    lines += ["## Décisions de quantité ouvertes (À_VALIDER)", "",
              _table(["Type", "Proposé", "Justification"],
                     [[q["kind"], q["proposed"], q["justification"]]
                      for q in mi["open_quantity_decisions"]]), ""]
    if mi.get("missing_assets"):
        lines += ["## Assets manquants (référencés par des animations)", "",
                  _table(["Animation", "Asset manquant"],
                         [[a["animation"], a["asset"]] for a in mi["missing_assets"]]), ""]
    return "\n".join(lines)


def render_isolated(iso: dict) -> str:
    lines = ["# Rapport des éléments isolés", "",
             "Détection des entités orphelines, inatteignables ou sans usage réel. "
             "Une simple relation technique ne suffit pas : l'usage est vérifié.", ""]
    labels = {
        "orphans": "Entités orphelines (aucune relation)",
        "unreachable": "Entités inatteignables depuis le départ",
        "weak_usage": "Entités sans relation d'usage forte",
        "objects_no_usage": "Objets sans usage réel",
        "resources_no_consumer": "Ressources sans consommateur réel",
        "secrets_no_discovery": "Secrets sans chemin de découverte",
        "systems_isolated": "Systèmes isolés",
    }
    any_problem = False
    for key, label in labels.items():
        items = iso.get(key, [])
        if items:
            any_problem = True
        lines += [f"## {label}", "",
                  (_table(["ID"], [[i] for i in items]) if items else "_Aucun ✓_"), ""]
    if not any_problem:
        lines.insert(2, "**Aucun élément isolé détecté : le graphe est pleinement "
                        "connecté et utile. ✓**\n")
    return "\n".join(lines)


def render_open_decisions(od: dict) -> str:
    lines = ["# Rapport des décisions encore ouvertes", "",
             f"- Total : **{od['total']}** décisions ouvertes (propriétaire).", "",
             "Ces décisions ne sont JAMAIS converties en canon. La pipeline "
             "propose des valeurs par défaut modulaires et documentées, mais le "
             "choix final appartient au propriétaire du projet.", "",
             "## Décisions du propriétaire (open_decisions.md)", "",
             _table(["Décision", "Source", "Statut"],
                    [[d["topic"], d["source"], d["status"]] for d in od["owner_decisions"]]),
             "", "## Éléments ouverts du canon", "",
             _table(["Élément", "Source", "Statut"],
                    [[o["topic"], o["source"], o["status"]] for o in od["canon_open_elements"]]),
             "", "## Décisions de quantité (propositions À_VALIDER)", "",
             _table(["Type", "Proposé", "Justification"],
                    [[q["topic"], q["proposed"], q["justification"]]
                     for q in od["quantity_decisions"]]), ""]
    return "\n".join(lines)


def run_stage(state: dict, write: bool = True) -> dict[str, Any]:
    maturity = compute_maturity(state)
    missing = compute_missing(state)
    isolated = compute_isolated(state)
    open_dec = compute_open_decisions(state)
    reports = {
        "maturity": maturity, "missing": missing,
        "isolated": isolated, "open_decisions": open_dec,
    }
    if write:
        write_text(DIRS["reports"] / "maturity_report.md", render_maturity(maturity))
        write_text(DIRS["reports"] / "missing_report.md", render_missing(missing))
        write_text(DIRS["reports"] / "isolated_report.md", render_isolated(isolated))
        write_text(DIRS["reports"] / "open_decisions_report.md", render_open_decisions(open_dec))
        write_json(DIRS["reports"] / "reports.json",
                   versioned_envelope(reports, kind="reports"))
    return reports


if __name__ == "__main__":
    from . import validator
    st = validator.load_state()
    rep = run_stage(st)
    print("maturité moyenne :", rep["maturity"]["average_maturity"])
    print("par statut :", rep["maturity"]["by_status"])
    print("isolés :", {k: len(v) for k, v in rep["isolated"].items() if v})
    print("décisions ouvertes :", rep["open_decisions"]["total"])
