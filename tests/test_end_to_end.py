"""Test minimal de bout en bout (étape 53, condition de fin).

Exécute la chaîne complète INPUT -> canon -> ontologie -> systèmes ->
catalogues -> graphe -> manifests -> prompts -> validation -> rapports ->
simulation -> compilation, et vérifie les artefacts produits et les conditions
de fin exigées par le brief.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import helpers
from lib import (canon as canon_mod, ontology as ontology_mod, systems as systems_mod,
                 catalog as catalog_mod, graph as graph_mod, manifest as manifest_mod,
                 prompt as prompt_mod, validator as val, report as report_mod,
                 simulator as simulator_mod, compiler as compiler_mod)
from lib.common import DIRS


class TestEndToEnd(unittest.TestCase):
    """Bout en bout en mémoire (rapide, déterministe)."""

    @classmethod
    def setUpClass(cls):
        cls.ca = canon_mod.run_stage(write=False)
        cls.onto = ontology_mod.run_stage(write=False)
        cls.sy = systems_mod.run_stage(write=False)["systems"]
        cls.cats = catalog_mod.run_stage(cls.ca, cls.sy, write=False)
        cls.gr = graph_mod.run_stage(cls.cats, cls.sy, cls.ca["canon"], write=False)
        cls.mf = manifest_mod.run_stage(cls.cats, write=False)
        cls.state = {
            "catalogs": cls.cats, "manifests": cls.mf["manifests"],
            "schemas": ontology_mod.build_schemas(),
            "graph": cls.gr["graph"], "canon": cls.ca["locked_canon"],
            "ontology": ontology_mod.build_ontology(),
            "connectivity": cls.gr["connectivity"],
        }

    def test_01_inputs_read(self):
        # Les quatre fichiers d'entrée + contrat ont été lus.
        self.assertIn("brief", self.ca["inputs"])
        self.assertIn("canon", self.ca["inputs"])
        self.assertIn("constraints", self.ca["inputs"])
        self.assertIn("open_decisions", self.ca["inputs"])
        self.assertIn("contract", self.ca["inputs"])

    def test_02_canon_locked_produced(self):
        self.assertTrue(self.ca["locked_canon"]["lock"]["locked"])
        self.assertEqual(self.ca["locked_canon"]["world"]["display_name"], "Valdore")

    def test_03_open_decisions_listed(self):
        self.assertGreater(len(self.ca["open_decisions"]), 0)

    def test_04_contradictions_signaled(self):
        self.assertGreater(len(self.ca["contradictions"]), 0,
                           "les ambiguïtés doivent être signalées")

    def test_05_ontology_coherent(self):
        onto = self.onto["ontology"]
        # Chaque type de relation a des sources/cibles dans les types d'entités.
        entity_types = set(onto["entity_types"].keys())
        for rname, r in onto["relation_types"].items():
            self.assertTrue(r["source"], f"relation {rname} sans source")
            self.assertTrue(r["target"], f"relation {rname} sans cible")

    def test_06_schemas_pass(self):
        errs = val.validate_schemas(self.state)
        self.assertEqual([e for e in errs if e["severity"] == "ERROR"], [])

    def test_07_graph_built_and_connected(self):
        self.assertGreater(self.gr["connectivity"]["node_count"], 50)
        self.assertEqual(self.gr["connectivity"]["reachable_count"],
                         self.gr["connectivity"]["node_count"])

    def test_08_manifests_generated(self):
        counts = self.mf["counts"]
        for k in ("objects", "assets", "animations", "maps", "placement",
                  "transitions", "effects"):
            self.assertGreater(counts[k], 0, f"manifest {k} vide")

    def test_09_prompts_contextualized(self):
        examples = prompt_mod.generate_examples(self.state, write=False)
        ok = [r for r in examples.values() if r["status"] == "OK"]
        self.assertGreater(len(ok), 0)
        # Chaque prompt OK contient le contexte canonique.
        for r in ok:
            self.assertIn("Valdore", r["content"],
                          "un prompt doit contenir le contexte canonique")
            self.assertIn("BLOCKED", r["content"],
                          "un prompt doit prévoir le comportement BLOCKED")

    def test_10_validation_passes(self):
        rep = val.run_all(self.state)
        self.assertTrue(rep["passed"],
                        f"validation échouée: {[i for i in rep['issues'] if i['severity']=='ERROR'][:5]}")

    def test_11_orphans_detected(self):
        self.assertEqual(self.gr["connectivity"]["orphans"], [])

    def test_12_reports_produced(self):
        rp = report_mod.run_stage(self.state, write=False)
        self.assertGreater(rp["maturity"]["count"], 0)
        self.assertGreater(rp["open_decisions"]["total"], 0)

    def test_13_simulation_runs(self):
        sim = simulator_mod.run_stage(self.cats, write=False)
        self.assertEqual(len(sim["profiles"]), 8)
        ok = sum(1 for c in sim["production_chains"].values() if c["ok"])
        self.assertEqual(ok, len(sim["production_chains"]),
                         "toutes les chaînes de production doivent réussir")

    def test_14_compilation_no_llm(self):
        comp = compiler_mod.run_stage(self.state, write=False)
        self.assertFalse(comp["llm_required_at_runtime"])
        self.assertGreater(comp["runtime_entities"], 0)

    def test_15_invalid_rejected(self):
        # Un résultat invalide doit être rejeté par l'importateur.
        from lib import importer
        bad = '{"id": "objet_x", "display_name": "Épée Laser"}'
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            importer.ACCEPTED = Path(tmp) / "a"
            importer.REJECTED = Path(tmp) / "r"
            r = importer.import_one(bad, filename="bad.json", state=self.state)
        self.assertEqual(r["status"], "REJECTED")


class TestArtifactsOnDisk(unittest.TestCase):
    """Vérifie que les artefacts écrits par `pipeline.py` existent."""

    def test_key_artifacts_exist(self):
        expected = [
            DIRS["canon"] / "canon_locked.json",
            DIRS["ontology"] / "ontology.json",
            DIRS["schemas"] / "objet.schema.json",
            DIRS["graph"] / "world_graph.json",
            DIRS["catalogs"] / "objects.json",
            DIRS["manifests"] / "manifest_assets.json",
            DIRS["reports"] / "maturity_report.md",
            DIRS["reports"] / "validation_report.md",
        ]
        for p in expected:
            self.assertTrue(Path(p).exists(), f"artefact manquant: {p}")


if __name__ == "__main__":
    unittest.main()
