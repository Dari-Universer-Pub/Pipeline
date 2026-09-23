"""Tests de validation et d'importation (livrables 57-72, et étapes 38-42).

Vérifie : import d'un résultat valide, rejet d'un résultat invalide, gestion
BLOCKED, validateurs de schémas/références/canon, et la détection d'orphelins,
d'assets non référencés et d'animations sans action.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import helpers
from lib import importer, validator as val

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestSchemaValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()

    def test_clean_state_passes_all_validators(self):
        rep = val.run_all(self.state)
        self.assertTrue(rep["passed"],
                        f"l'état canonique doit passer la validation: "
                        f"{[i for i in rep['issues'] if i['severity']=='ERROR'][:5]}")

    def test_schema_subset_types(self):
        schema = {"type": "object", "properties": {"a": {"type": "integer"}},
                  "required": ["a"]}
        self.assertEqual(val.validate_schema_subset({"a": 1}, schema), [])
        errs = val.validate_schema_subset({"a": "x"}, schema)
        self.assertTrue(any(e["code"] == "schema.type" for e in errs))
        errs = val.validate_schema_subset({}, schema)
        self.assertTrue(any(e["code"] == "schema.required" for e in errs))

    def test_schema_subset_enum_and_pattern(self):
        schema = {"type": "string", "enum": ["a", "b"]}
        self.assertEqual(val.validate_schema_subset("a", schema), [])
        self.assertTrue(val.validate_schema_subset("c", schema))
        pat = {"type": "string", "pattern": "^objet_[a-z0-9_]+$"}
        self.assertEqual(val.validate_schema_subset("objet_pioche", pat), [])
        self.assertTrue(val.validate_schema_subset("Objet Pioche", pat))

    def test_all_catalog_entities_match_their_schema(self):
        errs = val.validate_schemas(self.state)
        self.assertEqual([e for e in errs if e["severity"] == "ERROR"], [],
                         "toutes les entités doivent respecter leur schéma")


class TestImportValid(unittest.TestCase):
    def setUp(self):
        self.state = helpers.build_state()

    def test_import_valid_asset_accepted(self):
        content = (FIXTURES / "valid" / "asset_icone_graine_echo.json").read_text("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            _redirect_results(tmp)
            r = importer.import_one(content, filename="asset.json", state=self.state)
        self.assertEqual(r["status"], "ACCEPTED", r.get("issues"))

    def test_import_valid_dialogue_accepted(self):
        content = (FIXTURES / "valid" / "dialogue_alba_matin.json").read_text("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            _redirect_results(tmp)
            r = importer.import_one(content, filename="dialogue.json", state=self.state)
        self.assertEqual(r["status"], "ACCEPTED", r.get("issues"))


class TestImportInvalid(unittest.TestCase):
    def setUp(self):
        self.state = helpers.build_state()

    def _import(self, name):
        content = (FIXTURES / "invalid" / name).read_text("utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            _redirect_results(tmp)
            return importer.import_one(content, filename=name, state=self.state)

    def test_reject_orphan_asset(self):
        r = self._import("asset_orphan.json")
        self.assertEqual(r["status"], "REJECTED")
        self.assertTrue(any(i["code"] == "import.unresolved_ref" for i in r["issues"]))

    def test_reject_recipe_no_output(self):
        r = self._import("recipe_no_output.json")
        self.assertEqual(r["status"], "REJECTED")
        self.assertTrue(any(i["code"] in ("import.recipe_no_output", "schema.required")
                            for i in r["issues"]))

    def test_reject_forbidden_name(self):
        r = self._import("forbidden_name.json")
        self.assertEqual(r["status"], "REJECTED")
        self.assertTrue(any(i["code"] == "import.forbidden_term" for i in r["issues"]))

    def test_reject_broken_json(self):
        r = self._import("broken.json")
        self.assertEqual(r["status"], "REJECTED")
        self.assertTrue(any(i["code"] == "import.parse" for i in r["issues"]))

    def test_blocked_response(self):
        r = self._import("blocked_response.md")
        self.assertEqual(r["status"], "BLOCKED",
                         "une réponse BLOCKED ne doit jamais être importée")


class TestCanonicalValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()

    def test_canon_names_preserved(self):
        errs = val.validate_canonical(self.state)
        self.assertEqual([e for e in errs if e["code"] == "canon.name_changed"], [],
                         "les noms canoniques ne doivent pas être altérés")

    def test_no_forbidden_terms_in_catalog(self):
        errs = val.validate_canonical(self.state)
        self.assertEqual([e for e in errs if e["code"] == "canon.forbidden_term"], [],
                         "aucun terme interdit dans les noms du catalogue")

    def test_detect_forbidden_term_injection(self):
        # État FRAIS (isolation : ne pas polluer l'état partagé de la classe).
        state = helpers.build_state()
        state["catalogs"]["objects"].append({
            "id": "objet_epee_magique_test", "display_name": "Épée Magique",
            "status": "PROPOSEE", "category": "outil", "function": "x",
            "gameplay_verb": "frapper",
        })
        errs = val.validate_canonical(state)
        self.assertTrue(any(e["code"] == "canon.forbidden_term" for e in errs),
                        "un terme interdit injecté doit être détecté")


class TestReferenceValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()

    def test_clean_state_no_unresolved_refs(self):
        errs = val.validate_references(self.state)
        self.assertEqual([e for e in errs if e["severity"] == "ERROR"], [],
                         "aucune référence non résolue dans l'état canonique")

    def test_detect_unresolved_reference(self):
        # État FRAIS (isolation).
        state = helpers.build_state()
        state["catalogs"]["recipes"].append({
            "id": "recette_test_cassee", "display_name": "Cassée",
            "status": "PROPOSEE", "station_id": "machine_inexistante",
            "inputs": [{"item_id": "objet_inexistant", "qty": 1}],
            "outputs": [{"item_id": "objet_inexistant2", "qty": 1}],
        })
        errs = val.validate_references(state)
        self.assertTrue(any(e["code"] == "ref.unresolved" for e in errs),
                        "une référence de recette inexistante doit être détectée")


def _redirect_results(tmp: str) -> None:
    """Redirige les dossiers RESULTS de l'importateur vers un tmp (isolation)."""
    importer.ACCEPTED = Path(tmp) / "accepted"
    importer.REJECTED = Path(tmp) / "rejected"
    importer.INCOMING = Path(tmp) / "incoming"


if __name__ == "__main__":
    unittest.main()
