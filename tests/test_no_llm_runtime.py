"""Tests : le jeu final fonctionne SANS LLM runtime (livrable 54 de l'ordre,
condition de fin, et constraints#IA).

Vérifie que les sorties compilées sont déterministes, que les dialogues
essentiels sont compilés en données conditionnelles, que les règles/effets
sont exécutables par un moteur déterministe, et qu'aucune dépendance LLM
n'existe dans le bundle runtime.
"""
from __future__ import annotations

import unittest

import helpers
from lib import compiler as compiler_mod, simulator


class TestNoLLMRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()
        cls.runtime = compiler_mod.compile_runtime_data(cls.state)
        cls.rules = compiler_mod.compile_rules(cls.state)
        cls.dialogs = compiler_mod.compile_dialogs(cls.state)
        cls.save = compiler_mod.compile_save_schema(cls.state)

    def test_runtime_declares_no_llm(self):
        self.assertFalse(self.runtime["meta"]["llm_required_at_runtime"],
                         "le bundle runtime ne doit pas requérir de LLM")
        self.assertFalse(self.rules["llm_required_at_runtime"])

    def test_runtime_is_deterministic_flag(self):
        self.assertTrue(self.runtime["meta"]["deterministic"])
        self.assertTrue(self.rules["deterministic"])

    def test_dialogs_compiled_to_conditional_data(self):
        # Les dialogues essentiels doivent être des données conditionnelles.
        self.assertTrue(self.dialogs, "aucun dialogue essentiel compilé")
        for d in self.dialogs:
            self.assertIn("conditions", d, "dialogue sans conditions (non déterministe)")
            self.assertIn("lines", d)
            self.assertIn("knowledge_boundary", d,
                          "dialogue sans frontière de connaissance")

    def test_rules_have_condition_and_effect_tables(self):
        self.assertTrue(self.rules["condition_types"], "table de conditions vide")
        self.assertTrue(self.rules["effect_types"], "table d'effets vide")

    def test_no_llm_mutation_of_protected_data(self):
        protected = self.save["llm_mutation_forbidden"]
        for p in ["canon", "progression", "rules", "stats", "saves",
                  "objects", "major_quests", "unlocked_secrets"]:
            self.assertIn(p, protected, f"{p} non protégé contre la mutation LLM")

    def test_engine_can_evaluate_without_llm(self):
        # Le moteur (simulateur) évalue conditions/effets sans aucun appel LLM.
        state = simulator.initial_state(self.state["catalogs"])
        # Toutes les opérations sont des fonctions déterministes pures.
        simulator.apply_effect(state, {"type": "add_item",
                                       "params": {"item_id": "objet_navet", "qty": 1}})
        ok = simulator.check_condition(state, {"type": "item_count",
                                               "params": {"item_id": "objet_navet",
                                                          "op": ">=", "qty": 1}})
        self.assertTrue(ok, "l'évaluation déterministe doit fonctionner sans LLM")

    def test_runtime_bundle_self_contained(self):
        # Le bundle contient tout le nécessaire (entités, relations, manifests).
        self.assertIn("entities", self.runtime)
        self.assertIn("relations", self.runtime)
        self.assertIn("assets_manifest", self.runtime)
        self.assertIn("animations_manifest", self.runtime)
        self.assertIn("maps_manifest", self.runtime)
        self.assertIn("canon_locked", self.runtime)

    def test_no_network_or_llm_imports_in_lib(self):
        # Aucun module de la bibliothèque ne doit importer de client LLM/réseau.
        import pathlib
        lib_dir = pathlib.Path(helpers.__file__).resolve().parents[1] / "tools" / "lib"
        banned = ["openai", "anthropic", "requests", "urllib.request", "httpx",
                  "socket", "langchain", "google.generativeai"]
        for py in lib_dir.glob("*.py"):
            text = py.read_text("utf-8")
            for b in banned:
                self.assertNotIn(f"import {b}", text,
                                 f"{py.name} importe '{b}' (dépendance runtime interdite)")


if __name__ == "__main__":
    unittest.main()
