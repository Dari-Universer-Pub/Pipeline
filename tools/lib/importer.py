"""Importateur des résultats produits par une autre IA (étape 28, livrable 56).

Flux : l'autre IA exécute les prompts générés et dépose ses réponses dans
`RESULTS/incoming/` (fichiers .json ou .md). L'importateur :
1. détecte le type de tâche et l'entité ;
2. gère les réponses BLOCKED (information manquante -> jamais importé) ;
3. valide structure + schéma + références + logique + canon ;
4. accepte (RESULTS/accepted/) ou rejette (RESULTS/rejected/ + rapport d'erreurs).

Aucun résultat n'est accepté sans validation (constraints#Qualité).
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .common import DIRS, Status, is_valid_id, make_id, read_json, unwrap, write_json, write_text
from . import validator as val

ROOT = DIRS["input"].parent  # racine du dépôt
RESULTS = ROOT / "RESULTS"
INCOMING = RESULTS / "incoming"
ACCEPTED = RESULTS / "accepted"
REJECTED = RESULTS / "rejected"

# Préfixe d'ID -> (type de tâche, nom de schéma).
PREFIX_TO_SCHEMA = {
    "objet": "objet", "ressource": "ressource", "culture": "culture",
    "machine": "machine", "recette": "recette", "quete": "quete",
    "pnj": "pnj", "creature": "creature", "lieu": "lieu", "map": "map",
    "asset": "asset", "anim": "animation", "evenement": "evenement",
    "dialogue": "dialogue", "saison": "saison",
}


def _detect_schema(obj: dict) -> str | None:
    """Déduit le nom de schéma depuis l'ID ou un champ 'kind'/'task_type'."""
    if obj.get("task_type") in PREFIX_TO_SCHEMA:
        return PREFIX_TO_SCHEMA[obj["task_type"]]
    eid = obj.get("id", "")
    for prefix, schema in PREFIX_TO_SCHEMA.items():
        if eid.startswith(prefix + "_"):
            return schema
    # Famille d'assets.
    if obj.get("family"):
        return "asset"
    if obj.get("frames") is not None and obj.get("entity_id"):
        return "animation"
    return None


def _extract_json(text: str) -> Any:
    """Extrait le premier bloc JSON d'une réponse (tolère ```json ... ```)."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    candidate = m.group(1) if m else text
    # Cas sans fence : chercher le premier {...} équilibré.
    if not m:
        start = candidate.find("{")
        if start == -1:
            raise ValueError("aucun objet JSON trouvé")
        depth = 0
        for i in range(start, len(candidate)):
            if candidate[i] == "{":
                depth += 1
            elif candidate[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = candidate[start:i + 1]
                    break
    return json.loads(candidate)


def validate_result(obj: dict, state: dict) -> list[dict]:
    """Valide un résultat externe (schéma + références + logique + canon)."""
    issues: list[dict] = []
    schema_name = _detect_schema(obj)
    if not schema_name:
        issues.append(val.issue(val.ERROR, "import.unknown_type",
                                obj.get("id", "?"),
                                "type de tâche/schéma non détectable"))
        return issues

    schema = state["schemas"].get(schema_name)
    if schema:
        issues.extend(val.validate_schema_subset(obj, schema, obj.get("id", schema_name)))

    eid = obj.get("id")
    if not eid or not is_valid_id(eid):
        issues.append(val.issue(val.ERROR, "import.bad_id", str(eid),
                                "ID interne invalide ou manquant"))

    ids = val.all_entity_ids(state)

    # Références : aucun résultat ne doit inventer de référence hors graphe,
    # sauf s'il crée une entité nouvelle attendue (objet/recette produit).
    ref_fields = ("station_id", "giver_id", "location_id", "speaker_id",
                  "entity_id", "seed_id", "yield_id", "home", "asset_id")
    for f in ref_fields:
        v = obj.get(f)
        if isinstance(v, str) and v and v not in ids:
            issues.append(val.issue(val.ERROR, "import.unresolved_ref", eid,
                                    f"référence '{f}' -> '{v}' inexistante"))

    # Canon : terme interdit dans le nom affiché.
    dn = (obj.get("display_name") or "").lower()
    for term in val.FORBIDDEN_TERMS:
        if term in dn:
            issues.append(val.issue(val.ERROR, "import.forbidden_term", eid,
                                    f"terme interdit '{term}' dans le nom"))

    # Logique recette : entrées/sorties présentes.
    if schema_name == "recette":
        if not obj.get("inputs"):
            issues.append(val.issue(val.ERROR, "import.recipe_no_input", eid,
                                    "recette sans ingrédient"))
        if not obj.get("outputs"):
            issues.append(val.issue(val.ERROR, "import.recipe_no_output", eid,
                                    "recette sans résultat"))

    # Animation : entity + action + assets.
    if schema_name == "animation":
        if not obj.get("state_or_action"):
            issues.append(val.issue(val.ERROR, "import.anim_no_action", eid,
                                    "animation sans action/état"))
        for ra in obj.get("required_assets", []) or []:
            if ra not in {a["id"] for a in state["manifests"].get("assets", [])}:
                issues.append(val.issue(val.ERROR, "import.anim_asset_missing", eid,
                                        f"asset requis '{ra}' absent"))

    return issues


def import_one(content: str, *, filename: str = "result.json",
               state: dict | None = None) -> dict[str, Any]:
    """Importe UN résultat (texte brut d'une réponse d'IA).

    Retourne {status: ACCEPTED|REJECTED|BLOCKED, issues, entity_id, path}.
    """
    state = state or val.load_state()

    # Réponse BLOCKED (information manquante) : jamais importée.
    stripped = content.strip()
    if stripped.startswith("BLOCKED:"):
        reason = stripped[len("BLOCKED:"):].strip()
        rec = {"status": "BLOCKED", "filename": filename, "reason": reason,
               "entity_id": None, "issues": []}
        _write_rejected(filename, content, rec)
        return rec

    # Extraction JSON.
    try:
        obj = _extract_json(content)
    except (ValueError, json.JSONDecodeError) as ex:
        rec = {"status": "REJECTED", "filename": filename, "entity_id": None,
               "issues": [val.issue(val.ERROR, "import.parse", filename,
                                    f"JSON illisible: {ex}")]}
        _write_rejected(filename, content, rec)
        return rec

    if not isinstance(obj, dict):
        rec = {"status": "REJECTED", "filename": filename, "entity_id": None,
               "issues": [val.issue(val.ERROR, "import.not_object", filename,
                                    "la réponse n'est pas un objet JSON")]}
        _write_rejected(filename, content, rec)
        return rec

    issues = validate_result(obj, state)
    eid = obj.get("id", filename)
    errors = [i for i in issues if i["severity"] == val.ERROR]
    if errors:
        rec = {"status": "REJECTED", "filename": filename, "entity_id": eid,
               "issues": issues}
        _write_rejected(filename, content, rec)
        return rec

    rec = {"status": "ACCEPTED", "filename": filename, "entity_id": eid,
           "issues": issues, "object": obj}
    _write_accepted(filename, obj)
    return rec


def _write_accepted(filename: str, obj: dict) -> None:
    ACCEPTED.mkdir(parents=True, exist_ok=True)
    out = ACCEPTED / _as_json_name(filename)
    write_json(out, obj)


def _write_rejected(filename: str, content: str, rec: dict) -> None:
    REJECTED.mkdir(parents=True, exist_ok=True)
    base = Path(filename).stem
    (REJECTED / f"{base}.raw.txt").write_text(content, encoding="utf-8")
    write_json(REJECTED / f"{base}.errors.json",
               {"status": rec["status"], "entity_id": rec.get("entity_id"),
                "reason": rec.get("reason"), "issues": rec["issues"]})


def _as_json_name(filename: str) -> str:
    return Path(filename).stem + ".json"


def import_directory(path: Path | None = None, *, state: dict | None = None) -> dict[str, Any]:
    """Importe tous les fichiers d'un dossier (défaut : RESULTS/incoming)."""
    path = Path(path) if path else INCOMING
    state = state or val.load_state()
    results = []
    if path.exists():
        for f in sorted(path.iterdir()):
            if f.suffix in (".json", ".md", ".txt") and f.is_file():
                content = f.read_text(encoding="utf-8")
                results.append(import_one(content, filename=f.name, state=state))
    accepted = [r for r in results if r["status"] == "ACCEPTED"]
    rejected = [r for r in results if r["status"] == "REJECTED"]
    blocked = [r for r in results if r["status"] == "BLOCKED"]
    summary = {
        "total": len(results), "accepted": len(accepted),
        "rejected": len(rejected), "blocked": len(blocked),
        "results": results,
    }
    # Rapport d'erreurs de génération (livrable 96).
    _write_generation_errors(summary)
    return summary


def _write_generation_errors(summary: dict) -> None:
    lines = ["# Rapport des erreurs de génération (import)", "",
             f"- Total : {summary['total']}",
             f"- Acceptés : {summary['accepted']}",
             f"- Rejetés : {summary['rejected']}",
             f"- Bloqués (BLOCKED) : {summary['blocked']}", ""]
    for r in summary["results"]:
        if r["status"] != "ACCEPTED":
            lines.append(f"## {r['filename']} — {r['status']}")
            if r.get("reason"):
                lines.append(f"- Raison : {r['reason']}")
            fixes = []
            for i in r.get("issues", []):
                lines.append(f"- [{i['severity']}] {i['code']} @ {i['entity']} : {i['message']}")
                if i.get("fix"):
                    fixes.append(i["fix"])
            if fixes:
                lines.append(f"- Correction : {'; '.join(fixes)}")
            lines.append("")
    write_text(DIRS["reports"] / "generation_errors.md", "\n".join(lines))
    write_json(DIRS["reports"] / "generation_errors.json",
               {"summary": {k: v for k, v in summary.items() if k != "results"},
                "results": [{k: v for k, v in r.items() if k != "object"}
                            for r in summary["results"]]})


if __name__ == "__main__":
    s = import_directory()
    print("import :", {k: s[k] for k in ("total", "accepted", "rejected", "blocked")})
