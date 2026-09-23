#!/usr/bin/env python3
"""CLI Traçabilité V2 — matrice par domaine sur preuves vivantes.

Usage :
    python3 tools/traceability.py [--volume-n 25] [--no-write]

Écrit (sauf --no-write) :
- REPORTS/traceability.json
- OUTPUT/TRACEABILITY_MATRIX.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import traceability  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Matrice de traçabilité V2")
    ap.add_argument("--volume-n", type=int, default=25,
                    help="nombre de clones pour le test de volume (défaut 25)")
    ap.add_argument("--no-write", action="store_true",
                    help="ne pas écrire les artefacts (sortie stdout)")
    args = ap.parse_args()

    matrix = traceability.run_stage(volume_n=args.volume_n,
                                    write=not args.no_write)
    s = matrix["summary"]
    print(f"Domaines audités        : {s['domains_total']}")
    print(f"PRODUCTION_READY        : {len(s['production_ready'])}")
    if s["incomplete"]:
        print(f"Incomplets              : {', '.join(s['incomplete'])}")
    print(f"Tests obligatoires      : {s['tests_passed']}/{s['tests_total']}")
    if not args.no_write:
        print("Artefacts               : REPORTS/traceability.json, "
              "OUTPUT/TRACEABILITY_MATRIX.md")
    for name, d in matrix["domains"].items():
        print(f"  {name:13} maturité={d['maturity']:16} "
              f"tests={d['tests_passed']}/6")
    return 0 if s["tests_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
