#!/usr/bin/env python3
"""Régénération ciblée des éléments invalides (étape « Correction ciblée »).

Quand un résultat importé est rejeté (ou qu'un validateur signale une erreur),
cet outil régénère UN prompt contextualisé pour l'élément concerné, en y
injectant le retour d'erreurs précis. L'autre IA peut alors corriger sans
repartir de zéro et sans rien inventer.

Principe : on ne régénère QUE l'élément invalide (correction ciblée), jamais
tout le contenu. Le prompt de régénération contient :
- le contexte canonique complet (identique au prompt initial) ;
- la sortie précédente rejetée ;
- la liste exacte des erreurs à corriger ;
- l'instruction de ne corriger QUE ces points.

Usage :
    python3 tools/regenerate.py                 # depuis RESULTS/rejected + validation
    python3 tools/regenerate.py --entity <id>   # régénère un élément précis
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import importer, prompt as prompt_mod, validator as val  # noqa: E402
from lib.common import DIRS, write_text  # noqa: E402

REGEN_DIR = DIRS["prompt_generated"] / "regeneration"


def _task_type_for(entity_id: str) -> str:
    for prefix, task in prompt_mod.PREFIX_TO_TASK.items() if hasattr(prompt_mod, "PREFIX_TO_TASK") else []:
        if entity_id.startswith(prefix):
            return task
    # Déduction par préfixe d'ID.
    mapping = {
        "objet": "objet", "ressource": "ressource", "culture": "culture",
        "machine": "machine", "recette": "recette", "quete": "quete",
        "pnj": "pnj", "creature": "creature", "lieu": "lieu", "map": "map",
        "asset": "asset", "anim": "animation", "evenement": "evenement",
        "dialogue": "dialogue",
    }
    for prefix, task in mapping.items():
        if entity_id.startswith(prefix + "_"):
            return task
    return "objet"


def _correction_prompt(base_prompt: str, previous: str, errors: list[dict]) -> str:
    err_lines = "\n".join(
        f"- [{e['severity']}] {e['code']} @ {e.get('entity','?')} : {e['message']}"
        + (f"  → correction : {e['fix']}" if e.get("fix") else "")
        for e in errors)
    return (
        "# PROMPT DE RÉGÉNÉRATION CIBLÉE\n\n"
        "> Une version précédente de cet élément a été REJETÉE. Corrige "
        "UNIQUEMENT les erreurs listées, sans modifier le reste, sans changer "
        "l'identifiant interne ni un nom canonique. Si une information manque "
        "toujours, réponds `BLOCKED: <raison>`.\n\n"
        "## Erreurs à corriger\n\n" + err_lines + "\n\n"
        "## Sortie précédente rejetée\n\n```json\n" + previous.strip() + "\n```\n\n"
        "---\n\n" + base_prompt
    )


def regenerate_entity(entity_id: str, previous: str, errors: list[dict],
                      state: dict) -> dict:
    task = _task_type_for(entity_id)
    base = prompt_mod.generate_by_id(state, entity_id, task)
    if base["status"] == "BLOCKED":
        # Le contexte lui-même est incomplet : la régénération reste BLOCKED.
        content = (f"# RÉGÉNÉRATION BLOCKED — {entity_id}\n\n"
                   f"BLOCKED: {base['reason']}\n\n"
                   "Le contexte de la pipeline est incomplet pour cet élément. "
                   "Compléter d'abord le canon/manifest concerné.")
    else:
        content = _correction_prompt(base["content"], previous, errors)
    REGEN_DIR.mkdir(parents=True, exist_ok=True)
    path = REGEN_DIR / f"regen_{entity_id}.md"
    write_text(path, content)
    return {"entity_id": entity_id, "task_type": task, "path": str(path),
            "status": base["status"]}


def regenerate_from_rejected(state: dict) -> list[dict]:
    out = []
    rejected = importer.REJECTED
    if not rejected.exists():
        return out
    for err_file in sorted(rejected.glob("*.errors.json")):
        meta = json.loads(err_file.read_text(encoding="utf-8"))
        base = err_file.name.replace(".errors.json", "")
        raw = rejected / f"{base}.raw.txt"
        previous = raw.read_text(encoding="utf-8") if raw.exists() else ""
        eid = meta.get("entity_id") or base
        issues = meta.get("issues", [])
        if meta.get("status") == "BLOCKED":
            issues = [val.issue("ERROR", "import.blocked", eid, meta.get("reason", ""))]
        out.append(regenerate_entity(eid, previous, issues, state))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Régénération ciblée")
    ap.add_argument("--entity", help="identifiant de l'élément à régénérer")
    args = ap.parse_args(argv)
    state = val.load_state()

    if args.entity:
        res = regenerate_entity(args.entity, "(aucune sortie précédente)", [], state)
        print(f"Régénéré : {res['entity_id']} -> {res['path']} ({res['status']})")
        return 0

    results = regenerate_from_rejected(state)
    if not results:
        print("Aucun élément rejeté à régénérer (RESULTS/rejected vide).")
        return 0
    print(f"{len(results)} prompt(s) de régénération générés dans {REGEN_DIR}:")
    for r in results:
        print(f"  - {r['entity_id']} ({r['task_type']}) [{r['status']}] -> {r['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
