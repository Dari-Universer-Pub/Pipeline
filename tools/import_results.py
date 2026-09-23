#!/usr/bin/env python3
"""Importe les résultats produits par une autre IA (livrable 56).

L'autre IA exécute les prompts de `PROMPTS/` et dépose ses réponses (JSON ou
markdown avec bloc ```json) dans `RESULTS/incoming/`. Cet outil :
1. valide chaque réponse (schéma, références, logique, canon) ;
2. accepte les réponses valides -> `RESULTS/accepted/` ;
3. rejette les réponses invalides -> `RESULTS/rejected/` + rapport d'erreurs ;
4. gère les réponses `BLOCKED:` (information manquante) sans les importer ;
5. produit `REPORTS/generation_errors.md`.

Après import, relancer la validation : `python3 tools/pipeline.py --validate`.
Pour régénérer un élément rejeté, voir `tools/regenerate.py`.

Usage :
    python3 tools/import_results.py                 # importe RESULTS/incoming/
    python3 tools/import_results.py --dir <dossier> # importe un dossier précis
    python3 tools/import_results.py --file <fichier>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import importer, validator as val  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Import des résultats d'une autre IA")
    ap.add_argument("--dir", help="dossier à importer (défaut RESULTS/incoming)")
    ap.add_argument("--file", help="fichier unique à importer")
    ap.add_argument("--revalidate", action="store_true",
                    help="relance la validation globale après import")
    args = ap.parse_args(argv)

    state = val.load_state()

    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
        res = importer.import_one(content, filename=Path(args.file).name, state=state)
        results = [res]
        summary = {"total": 1,
                   "accepted": sum(1 for r in results if r["status"] == "ACCEPTED"),
                   "rejected": sum(1 for r in results if r["status"] == "REJECTED"),
                   "blocked": sum(1 for r in results if r["status"] == "BLOCKED"),
                   "results": results}
        importer._write_generation_errors(summary)
    else:
        summary = importer.import_directory(Path(args.dir) if args.dir else None,
                                            state=state)

    print(f"Import : total={summary['total']} acceptés={summary['accepted']} "
          f"rejetés={summary['rejected']} bloqués={summary['blocked']}")
    for r in summary["results"]:
        if r["status"] != "ACCEPTED":
            reason = r.get("reason") or "; ".join(i["code"] for i in r.get("issues", []))
            print(f"  [{r['status']}] {r['filename']}: {reason}")

    if args.revalidate:
        print("\n--- Revalidation globale ---")
        rep = val.run_all(val.load_state())
        val.write_report(rep)
        print(f"Validation : {'SUCCÈS' if rep['passed'] else 'ÉCHEC'} "
              f"({rep['error_count']} erreurs, {rep['warning_count']} avertissements)")
        return 0 if rep["passed"] else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
