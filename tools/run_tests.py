#!/usr/bin/env python3
"""Runner de tests de la Pipeline V5 (livrables 73-90, étapes 35-43, 53).

Découvre et exécute tous les tests dans `tests/` avec unittest (stdlib).
Retourne un code de sortie non-nul si un test échoue.

Usage :
    python3 tools/run_tests.py            # tous les tests
    python3 tools/run_tests.py -v         # verbeux
    python3 tools/run_tests.py test_production   # un module
"""
from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Tests de la Pipeline V5")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("modules", nargs="*", help="modules de test à exécuter")
    args = ap.parse_args(argv)

    # tests/ doit être importable (helpers.py) ainsi que tools/ (lib).
    sys.path.insert(0, str(TESTS))
    sys.path.insert(0, str(ROOT / "tools"))

    loader = unittest.TestLoader()
    if args.modules:
        suite = unittest.TestSuite()
        for m in args.modules:
            name = m if m.startswith("test_") else f"test_{m}"
            suite.addTests(loader.loadTestsFromName(name))
    else:
        suite = loader.discover(str(TESTS), pattern="test_*.py", top_level_dir=str(TESTS))

    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
