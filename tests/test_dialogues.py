"""Tests : cycle de vie des DIALOGUES (dérivation, import, validation, compilation).

Prouve que :
  * les 3 dialogues compilés par défaut sont un REPLI déterministe dérivé des
    PNJ canoniques (salutations), PAS du contenu canonique ni la totalité des
    dialogues du jeu ;
  * le compilateur accepte et compile n'importe quel dialogue importé présent
    dans le catalogue `dialogues` (conditions -> lignes -> choix -> effets),
    y compris en volume, dès lors qu'il respecte schémas et relations du graphe ;
  * les conditions / choix / effets / révélations sont validés ;
  * un dialogue incohérent (fuite de secret, locuteur hors graphe) est rejeté.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import helpers
from lib import canon as canon_mod
from lib import catalog as catalog_mod
from lib import compiler as compiler_mod
from lib import importer
from lib import validator as val
from lib.common import make_id


def _redirect_results(tmp: str) -> None:
    """Redirige les dossiers RESULTS de l'importateur vers un tmp (isolation)."""
    importer.ACCEPTED = Path(tmp) / "accepted"
    importer.REJECTED = Path(tmp) / "rejected"
    importer.INCOMING = Path(tmp) / "incoming"


def _valid_dialogue(nid: str = "pnj_alba", suffix: str = "accueil_test",
                    reveals=None) -> dict:
    """Dialogue conforme à dialogue.schema.json, ancré dans le graphe."""
    return {
        "id": make_id("dialogue", f"{nid}_{suffix}"),
        "display_name": "Dialogue de test",
        "status": "PROPOSEE",
        "speaker_id": nid,
        "conditions": [
            {"type": "location", "params": {"lieu_id": "lieu_maison_racine"}},
            {"type": "time_of_day", "params": {"op": "<", "hour": 12}},
        ],
        "lines": [
            {
                "text": "Bonjour, Jardinier.",
                "reveals": reveals if reveals is not None else ["fait_monde_valdore"],
                "choices": [
                    {"text": "Que dois-je faire ?",
                     "effect": {"type": "advance_quest",
                                "params": {"quete_id": "quete_le_premier_echo",
                                           "step": "step_1"}}}
                ],
            }
        ],
        "priority": 5,
    }


class TestEssentialDialogsAreDerivedFallback(unittest.TestCase):
    """Les dialogues compilés par défaut = repli dérivé des PNJ, pas du canon."""

    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()
        # Aucun dialogue importé dans le catalogue -> le compilateur replie.
        cls.state["catalogs"].pop("dialogues", None)
        cls.dialogs = compiler_mod.compile_dialogs(cls.state)
        cls.npcs = cls.state["catalogs"]["npcs"]

    def test_one_greeting_per_canonical_npc(self):
        self.assertEqual(len(self.dialogs), len(self.npcs),
                         "le repli produit exactement 1 salutation par PNJ")

    def test_ids_are_derived_from_npc_ids(self):
        expected = {make_id("dialogue", f"{n['id']}_salutation") for n in self.npcs}
        self.assertEqual({d["id"] for d in self.dialogs}, expected,
                         "les IDs sont DÉRIVÉS des PNJ (…_salutation), pas du contenu libre")

    def test_speakers_are_the_canonical_npcs(self):
        self.assertEqual({d["speaker_id"] for d in self.dialogs},
                         {n["id"] for n in self.npcs})

    def test_each_has_conditions_lines_and_knowledge_boundary(self):
        for d in self.dialogs:
            self.assertIn("conditions", d)
            self.assertIn("lines", d)
            self.assertIn("knowledge_boundary", d)

    def test_knowledge_boundary_matches_speaker(self):
        by_id = {n["id"]: n for n in self.npcs}
        for d in self.dialogs:
            n = by_id[d["speaker_id"]]
            self.assertEqual(d["knowledge_boundary"]["allowed"], n.get("knowledge", []))
            self.assertEqual(d["knowledge_boundary"]["forbidden"],
                             n.get("forbidden_knowledge", []))

    def test_not_present_in_locked_canon(self):
        canon = canon_mod.run_stage(write=False)["locked_canon"]
        blob = json.dumps(canon, ensure_ascii=False)
        self.assertNotIn("dialogues", canon,
                         "le canon verrouillé ne contient AUCUN dialogue")
        for d in self.dialogs:
            self.assertNotIn(d["id"], blob,
                             "une salutation dérivée n'est pas un fait canonique")


class TestImportedDialogsAreCompiled(unittest.TestCase):
    """Le compilateur accepte ensuite les dialogues produits par l'IA."""

    def setUp(self):
        self.state = helpers.build_state()

    def test_imported_dialogue_replaces_fallback(self):
        dlg = _valid_dialogue()
        self.state["catalogs"]["dialogues"] = [dlg]
        compiled = compiler_mod.compile_dialogs(self.state)
        ids = {d["id"] for d in compiled}
        self.assertIn(dlg["id"], ids, "le dialogue importé est compilé")
        self.assertFalse(any(i.endswith("_salutation") for i in ids),
                         "le repli disparaît dès qu'un vrai dialogue existe")

    def test_imported_dialogue_preserves_conditions_choices_effects(self):
        dlg = _valid_dialogue()
        self.state["catalogs"]["dialogues"] = [dlg]
        compiled = compiler_mod.compile_dialogs(self.state)[0]
        self.assertEqual(compiled["conditions"], dlg["conditions"])
        self.assertEqual(compiled["lines"], dlg["lines"])
        # effets/choix conservés tels quels (exécutables sans LLM)
        self.assertEqual(compiled["lines"][0]["choices"][0]["effect"]["type"],
                         "advance_quest")

    def test_imported_dialogue_gets_speaker_knowledge_boundary(self):
        dlg = _valid_dialogue(nid="pnj_nox", suffix="test_nox")
        self.state["catalogs"]["dialogues"] = [dlg]
        compiled = compiler_mod.compile_dialogs(self.state)[0]
        nox = next(n for n in self.state["catalogs"]["npcs"] if n["id"] == "pnj_nox")
        self.assertEqual(compiled["knowledge_boundary"]["forbidden"],
                         nox.get("forbidden_knowledge", []))

    def test_compiles_a_large_volume(self):
        npcs = [n["id"] for n in self.state["catalogs"]["npcs"]]
        dialogues = [_valid_dialogue(nid=npcs[i % len(npcs)], suffix=f"vol_{i}")
                     for i in range(50)]
        self.state["catalogs"]["dialogues"] = dialogues
        compiled = compiler_mod.compile_dialogs(self.state)
        self.assertEqual(len(compiled), 50,
                         "le compilateur traite un volume important sans repli")
        self.assertEqual({d["id"] for d in compiled}, {d["id"] for d in dialogues})


class TestDialogueValidation(unittest.TestCase):
    """Conditions / choix / effets / révélations sont validés."""

    def setUp(self):
        self.state = helpers.build_state()

    def test_valid_dialogue_matches_schema(self):
        schema = self.state["schemas"]["dialogue"]
        errs = val.validate_schema_subset(_valid_dialogue(), schema)
        self.assertEqual([e for e in errs if e["severity"] == "ERROR"], [])

    def test_secret_leak_is_an_error(self):
        # pnj_alba a 'secret_passe_nox' en connaissance INTERDITE.
        bad = _valid_dialogue(nid="pnj_alba", suffix="fuite",
                              reveals=["secret_passe_nox"])
        self.state["catalogs"]["dialogues"] = [bad]
        errs = val.validate_narrative(self.state)
        self.assertTrue(any(e["code"] == "narr.secret_leak"
                            and e["severity"] == "ERROR" for e in errs),
                        "révéler un fait interdit doit être une ERREUR")

    def test_reveal_outside_knowledge_warns(self):
        warn = _valid_dialogue(nid="pnj_alba", suffix="inconnu",
                               reveals=["fait_totalement_inconnu"])
        self.state["catalogs"]["dialogues"] = [warn]
        errs = val.validate_narrative(self.state)
        self.assertTrue(any(e["code"] == "narr.reveal_unknown"
                            and e["severity"] == "WARNING" for e in errs))

    def test_importer_accepts_valid_dialogue(self):
        content = json.dumps(_valid_dialogue(), ensure_ascii=False)
        with tempfile.TemporaryDirectory() as tmp:
            _redirect_results(tmp)
            r = importer.import_one(content, filename="dialogue.json", state=self.state)
        self.assertEqual(r["status"], "ACCEPTED", r.get("issues"))

    def test_importer_rejects_unknown_speaker(self):
        # Locuteur absent du graphe -> relation invalide -> REJETÉ.
        bad = _valid_dialogue(nid="pnj_alba", suffix="mauvais_locuteur")
        bad["speaker_id"] = "pnj_inexistant"
        content = json.dumps(bad, ensure_ascii=False)
        with tempfile.TemporaryDirectory() as tmp:
            _redirect_results(tmp)
            r = importer.import_one(content, filename="dialogue.json", state=self.state)
        self.assertEqual(r["status"], "REJECTED")
        self.assertTrue(any(i["code"] == "import.unresolved_ref" for i in r["issues"]))


class TestDialoguesCatalogIntegration(unittest.TestCase):
    """Le catalogue `dialogues` est le point d'intégration (vide par défaut)."""

    def test_catalog_run_stage_exposes_dialogues(self):
        ca = canon_mod.run_stage(write=False)
        sy = catalog_mod.systems_mod.run_stage(write=False)["systems"]
        cats = catalog_mod.run_stage(ca, sy, write=False)
        self.assertIn("dialogues", cats,
                      "le catalogue expose une collection 'dialogues'")
        self.assertIsInstance(cats["dialogues"], list)

    def test_load_state_includes_dialogues_collection(self):
        # Après un run, GAME/catalogs/dialogues.json existe (vide par défaut)
        # et load_state l'expose pour validation/compilation.
        state = val.load_state()
        self.assertIn("dialogues", state["catalogs"])
        self.assertIsInstance(state["catalogs"]["dialogues"], list)


if __name__ == "__main__":
    unittest.main()
