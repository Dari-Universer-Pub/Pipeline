"""Tests de reproductibilité, sauvegarde et migration (livrables 84, 85, 86).

Vérifie que la génération est déterministe (mêmes entrées -> mêmes sorties),
que les graines procèdent de façon reproductible, et que le schéma de
sauvegarde supporte le versionnement et les migrations.
"""
from __future__ import annotations

import unittest

import helpers
from lib import (canon as canon_mod, systems as systems_mod, catalog as catalog_mod,
                 graph as graph_mod, manifest as manifest_mod, compiler as compiler_mod,
                 simulator)
from lib.common import fingerprint, derive_seed, DEFAULT_SEED


def _build_fresh():
    ca = canon_mod.run_stage(write=False)
    sy = systems_mod.run_stage(write=False)["systems"]
    cats = catalog_mod.run_stage(ca, sy, write=False)
    gr = graph_mod.run_stage(cats, sy, ca["canon"], write=False)
    mf = manifest_mod.run_stage(cats, write=False)
    return cats, gr, mf


class TestReproducibility(unittest.TestCase):
    def test_catalog_generation_is_deterministic(self):
        c1, g1, m1 = _build_fresh()
        c2, g2, m2 = _build_fresh()
        self.assertEqual(fingerprint(c1["objects"]), fingerprint(c2["objects"]),
                         "la génération des objets doit être reproductible")
        self.assertEqual(g1["fingerprint"], g2["fingerprint"],
                         "le graphe doit être reproductible")
        self.assertEqual(fingerprint(m1["manifests"]["assets"]),
                         fingerprint(m2["manifests"]["assets"]),
                         "les manifests d'assets doivent être reproductibles")

    def test_seed_is_stable(self):
        self.assertEqual(derive_seed("map", "Vallée Claire"),
                         derive_seed("map", "Vallée Claire"),
                         "la graine doit être stable pour les mêmes entrées")
        self.assertNotEqual(derive_seed("map", "Vallée Claire"),
                            derive_seed("map", "Lac Muet"),
                            "des entrées différentes doivent donner des graines différentes")

    def test_map_seeds_reproducible(self):
        cats, _, _ = _build_fresh()
        seeds1 = {m["id"]: m["seed"] for m in cats["maps"]}
        cats2, _, _ = _build_fresh()
        seeds2 = {m["id"]: m["seed"] for m in cats2["maps"]}
        self.assertEqual(seeds1, seeds2, "les graines de maps doivent être reproductibles")

    def test_simulation_deterministic(self):
        cats, _, _ = _build_fresh()
        r1 = simulator.run_profile("agriculteur", cats)
        r2 = simulator.run_profile("agriculteur", cats)
        self.assertEqual(r1["after"], r2["after"],
                         "la simulation doit être déterministe (sans LLM)")


class TestSaveAndMigration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()
        cls.save = compiler_mod.compile_save_schema(cls.state)

    def test_save_schema_has_version(self):
        self.assertIn("save_version", self.save)
        self.assertTrue(self.save["save_version"])

    def test_save_schema_has_migration_table(self):
        self.assertIn("compatibility", self.save)
        self.assertTrue(self.save["compatibility"]["migrations"],
                        "une table de migration doit exister")

    def test_save_state_roundtrip(self):
        # Simule une sauvegarde : sérialiser l'état puis le relire.
        import json
        state = simulator.initial_state(self.state["catalogs"])
        blob = json.dumps(state, ensure_ascii=False, sort_keys=True)
        restored = json.loads(blob)
        self.assertEqual(restored["player"]["inventory"], state["player"]["inventory"],
                         "l'état sauvegardé doit être restauré à l'identique")

    def test_llm_mutation_forbidden_listed(self):
        self.assertIn("canon", self.save["llm_mutation_forbidden"])
        self.assertIn("saves", self.save["llm_mutation_forbidden"])
        self.assertIn("major_quests", self.save["llm_mutation_forbidden"])

    def test_reproducibility_seed_stored(self):
        self.assertTrue(self.save["reproducibility"]["seed_stored"],
                        "la graine doit être stockée pour la reproductibilité")


if __name__ == "__main__":
    unittest.main()
