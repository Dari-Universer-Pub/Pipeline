#!/usr/bin/env python3
"""Orchestrateur de la Pipeline V5 Graph-Driven — Les Jardins de l'Écho.

Point d'entrée unique. Exécute le flux obligatoire du contrat d'architecture :

    INPUT (brief, canon, contraintes, décisions) + CONTRACT
        -> Analyse des entrées
        -> Canon central verrouillé + rapports de décisions/contradictions
        -> Ontologie + Schémas
        -> Systèmes de gameplay
        -> Catalogue fonctionnel + catalogues (quantités dérivées)
        -> Graphe du monde + relations + connectivité
        -> Manifests (objets, maps, assets, animations, placement, transitions, effets)
        -> Prompts spécialisés contextualisés
        -> Validation
        -> Rapports (maturité, manquants, isolés, décisions ouvertes)
        -> Simulation (profils + chaînes de production)
        -> Compilation pour le moteur (Godot 4, sans LLM runtime)
        -> Traçabilité V2 (matrice 16 domaines x 6 tests, preuves réelles)

L'importation des résultats d'une autre IA et la régénération ciblée sont
gérées par `tools/import_results.py`.

Usage :
    python3 tools/pipeline.py            # pipeline complet
    python3 tools/pipeline.py --stage canon
    python3 tools/pipeline.py --validate # validation seule
    python3 tools/pipeline.py --check    # vérifie l'état écrit et retourne un code
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permet l'exécution depuis la racine du dépôt (`python3 tools/pipeline.py`).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (  # noqa: E402
    canon as canon_mod, ontology as ontology_mod, systems as systems_mod,
    catalog as catalog_mod, graph as graph_mod, manifest as manifest_mod,
    prompt as prompt_mod, validator as validator_mod, report as report_mod,
    simulator as simulator_mod, compiler as compiler_mod,
)
from lib.common import PIPELINE_VERSION, now_iso  # noqa: E402

STAGES = ["canon", "ontology", "systems", "catalog", "graph", "manifest",
          "prompt", "validate", "report", "simulate", "compile",
          "traceability"]


def run_full(verbose: bool = True) -> dict:
    """Exécute la pipeline complète et retourne un résumé par étape."""
    summary: dict = {"pipeline_version": PIPELINE_VERSION, "started": now_iso(),
                     "stages": {}}

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    # 1. Canon central verrouillé + rapports.
    log("• Étape 1 — Canon : extraction, verrouillage, décisions, contradictions")
    ca = canon_mod.run_stage(write=True)
    summary["stages"]["canon"] = {
        "locations": len(ca["canon"]["locations"]), "npcs": len(ca["canon"]["npcs"]),
        "objects": len(ca["canon"]["objects"]),
        "contradictions": len(ca["contradictions"]),
        "open_decisions": len(ca["open_decisions"]),
    }

    # 2. Ontologie + schémas.
    log("• Étape 2 — Ontologie + schémas JSON")
    onto = ontology_mod.run_stage(write=True)
    summary["stages"]["ontology"] = {
        "entity_types": len(onto["ontology"]["entity_types"]),
        "relation_types": len(onto["ontology"]["relation_types"]),
        "schemas": len(onto["schemas"]),
    }

    # 3. Systèmes de gameplay.
    log("• Étape 3 — Systèmes de gameplay")
    sy = systems_mod.run_stage(write=True)
    summary["stages"]["systems"] = {"count": sy["count"]}
    systems = sy["systems"]

    # 4. Catalogues + catalogue fonctionnel (quantités dérivées).
    log("• Étape 4 — Catalogues + catalogue fonctionnel (quantités dérivées)")
    cats = catalog_mod.run_stage(ca, systems, write=True)
    summary["stages"]["catalog"] = {
        k: len(cats[k]) for k in ("seasons", "locations", "crops", "resources",
                                  "machines", "recipes", "objects", "npcs",
                                  "creatures", "quests", "events", "secrets", "maps")
    }
    summary["stages"]["catalog"]["functional_entries"] = cats["functional_catalog"]["count"]

    # 5. Graphe du monde + connectivité.
    log("• Étape 5 — Graphe du monde + connectivité")
    gr = graph_mod.run_stage(cats, systems, ca["canon"], write=True)
    summary["stages"]["graph"] = {
        "nodes": gr["connectivity"]["node_count"],
        "edges": gr["connectivity"]["edge_count"],
        "reachable": gr["connectivity"]["reachable_count"],
        "orphans": len(gr["connectivity"]["orphans"]),
        "dangling": len(gr["connectivity"]["dangling_references"]),
    }

    # 6. Manifests.
    log("• Étape 6 — Manifests (objets, maps, assets, animations, placement, etc.)")
    mf = manifest_mod.run_stage(cats, write=True)
    summary["stages"]["manifest"] = mf["counts"]

    # 7. Prompts spécialisés contextualisés (exemples).
    log("• Étape 7 — Prompts spécialisés contextualisés (exemples)")
    pr = prompt_mod.run_stage(write=True)
    summary["stages"]["prompt"] = pr["summary"]

    # 8. Validation.
    log("• Étape 8 — Validation (structurelle, schémas, références, logique, ...)")
    st = validator_mod.load_state()
    rep = validator_mod.run_all(st)
    validator_mod.write_report(rep)
    summary["stages"]["validate"] = {
        "passed": rep["passed"], "errors": rep["error_count"],
        "warnings": rep["warning_count"],
    }

    # 9. Rapports.
    log("• Étape 9 — Rapports (maturité, manquants, isolés, décisions ouvertes)")
    st["connectivity"] = gr["connectivity"]
    st["graph"] = gr["graph"]
    rp = report_mod.run_stage(st, write=True)
    summary["stages"]["report"] = {
        "average_maturity": rp["maturity"]["average_maturity"],
        "isolated_total": sum(len(v) for v in rp["isolated"].values()),
        "open_decisions": rp["open_decisions"]["total"],
    }

    # 10. Simulation (profils + chaînes de production).
    log("• Étape 10 — Simulation (profils de joueurs + chaînes de production)")
    sim = simulator_mod.run_stage(cats, write=True)
    chains_ok = sum(1 for c in sim["production_chains"].values() if c["ok"])
    summary["stages"]["simulate"] = {
        "profiles": len(sim["profiles"]),
        "production_chains_ok": f"{chains_ok}/{len(sim['production_chains'])}",
    }

    # 11. Compilation moteur.
    log("• Étape 11 — Compilation pour le moteur (Godot 4, sans LLM runtime)")
    comp = compiler_mod.run_stage(st, write=True)
    summary["stages"]["compile"] = comp

    # 12. Traçabilité V2 — matrice des 16 domaines sur preuves réelles
    # (fixtures E2E : import -> validation -> graphe -> compilation -> runtime).
    log("• Étape 12 — Traçabilité V2 (16 domaines x 6 tests obligatoires)")
    from lib import traceability as traceability_mod
    tm = traceability_mod.run_stage(write=True)
    summary["stages"]["traceability"] = {
        "domains_total": tm["summary"]["domains_total"],
        "production_ready": len(tm["summary"]["production_ready"]),
        "incomplete": tm["summary"]["incomplete"],
        "tests": f"{tm['summary']['tests_passed']}/{tm['summary']['tests_total']}",
        "all_green": tm["summary"]["all_green"],
    }

    summary["finished"] = now_iso()
    summary["validation_passed"] = rep["passed"]

    from lib.common import DIRS, write_json, versioned_envelope
    write_json(DIRS["output"] / "PIPELINE_RUN.json",
               versioned_envelope(summary, kind="pipeline_run"))

    log("")
    log("=" * 64)
    log(f"PIPELINE V5 terminée — validation : "
        f"{'SUCCÈS ✓' if rep['passed'] else 'ÉCHEC ✗'} "
        f"({rep['error_count']} erreur(s), {rep['warning_count']} avertissement(s))")
    log("=" * 64)
    return summary


def run_stage_only(stage: str, verbose: bool = True) -> dict:
    """Exécute une seule étape (et ses prérequis en lecture)."""
    if stage not in STAGES:
        raise SystemExit(f"étape inconnue: {stage} (choix: {', '.join(STAGES)})")
    # Pour simplifier, on rejoue le full jusqu'à l'étape demandée.
    idx = STAGES.index(stage)
    summary = run_full(verbose=verbose)
    return {"ran_until": stage, "stage_index": idx, "summary": summary}


def validate_only(verbose: bool = True) -> dict:
    st = validator_mod.load_state()
    rep = validator_mod.run_all(st)
    validator_mod.write_report(rep)
    if verbose:
        print(f"Validation : {'SUCCÈS ✓' if rep['passed'] else 'ÉCHEC ✗'} — "
              f"{rep['error_count']} erreur(s), {rep['warning_count']} avertissement(s)")
        for k, v in rep["by_validator"].items():
            if v:
                print(f"  {k}: {v}")
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pipeline V5 Graph-Driven")
    ap.add_argument("--stage", help="exécuter jusqu'à une étape précise")
    ap.add_argument("--validate", action="store_true", help="validation seule")
    ap.add_argument("--check", action="store_true",
                    help="valide et retourne un code de sortie (0=succès)")
    ap.add_argument("--quiet", action="store_true", help="moins de sorties")
    args = ap.parse_args(argv)
    verbose = not args.quiet

    if args.validate:
        rep = validate_only(verbose)
        return 0 if rep["passed"] else 1
    if args.check:
        rep = validate_only(verbose=False)
        print("CHECK:", "PASS" if rep["passed"] else "FAIL",
              f"({rep['error_count']} erreurs)")
        return 0 if rep["passed"] else 1
    if args.stage:
        run_stage_only(args.stage, verbose)
        return 0
    run_full(verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
