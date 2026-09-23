#!/usr/bin/env python3
"""Générateur de prompts spécialisés contextualisés (CLI).

Permet à une autre IA de générer UN prompt à la demande, avec tout le contexte
canonique injecté automatiquement (livrables 50-55).

Trois modes :
- par identifiant : `--id <entity_id> --task <type>`
- par famille (éléments visuellement interdépendants) : `--family <nom>`
- par séquence animée (action × directions) : `--seq <entity_id> --action <action>`

Le prompt est écrit dans PROMPTS/generated/ (et affiché sur stdout avec --print).
Si une information nécessaire manque, la sortie est `BLOCKED: <raison>`.

Exemples :
    python3 tools/prompt_gen.py --id objet_graine_d_echo --task objet --print
    python3 tools/prompt_gen.py --id asset_tileset_herbe --task asset
    python3 tools/prompt_gen.py --family famille_terrains
    python3 tools/prompt_gen.py --seq joueur_jardinier --action marche
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import prompt as prompt_mod  # noqa: E402
from lib.common import DIRS, write_text  # noqa: E402


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in name).strip("_")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Générateur de prompts contextualisés")
    ap.add_argument("--id", help="identifiant de l'entité")
    ap.add_argument("--task", default="objet",
                    help="type de tâche (objet, asset, animation, map, pnj, "
                         "dialogue, quete, recette, ...)")
    ap.add_argument("--family", help="nom de famille visuelle (mode famille)")
    ap.add_argument("--seq", help="entité d'une séquence animée (mode séquence)")
    ap.add_argument("--action", help="action de la séquence animée")
    ap.add_argument("--print", dest="do_print", action="store_true",
                    help="afficher le prompt sur stdout")
    ap.add_argument("--outdir", help="dossier de sortie (défaut PROMPTS/generated)")
    args = ap.parse_args(argv)

    state = prompt_mod.load_state()
    outdir = Path(args.outdir) if args.outdir else DIRS["prompt_generated"]
    outdir.mkdir(parents=True, exist_ok=True)

    if args.family:
        res = prompt_mod.generate_by_family(state, args.family)
        name = f"family_{_slug(args.family)}"
    elif args.seq:
        if not args.action:
            raise SystemExit("--action requis avec --seq")
        res = prompt_mod.generate_by_animation_sequence(state, args.seq, args.action)
        name = f"seq_{_slug(args.seq)}_{_slug(args.action)}"
    elif args.id:
        res = prompt_mod.generate_by_id(state, args.id, args.task)
        name = f"{args.task}_{_slug(args.id)}"
    else:
        raise SystemExit("fournissez --id, --family ou --seq")

    path = outdir / f"{name}.md"
    header = (f"<!-- statut: {res['status']} -->\n"
              f"<!-- généré par prompt_gen.py (injecteur de contexte) -->\n\n")
    write_text(path, header + res["content"])

    if args.do_print:
        print(res["content"])
    print(f"[{res['status']}] {name} -> {path}", file=sys.stderr)
    if res["status"] == "BLOCKED":
        print(f"BLOCKED: {res.get('reason')}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
