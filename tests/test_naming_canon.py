"""Tests de cohérence des noms et du canon (livrables 82, 83).

Vérifie : IDs internes stables/valides, noms affichés cohérents avec le canon,
distinction canon/proposition, éléments canoniques préservés, aucun terme
interdit, et cohérence des règles de nommage.
"""
from __future__ import annotations

import unittest

import helpers
from lib.common import is_valid_id, slugify, make_id, Status
from lib import canon as canon_mod


class TestInternalIds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()

    def test_all_ids_valid(self):
        for coll in self.state["catalogs"].values():
            for e in coll:
                if isinstance(e, dict) and "id" in e:
                    self.assertTrue(is_valid_id(e["id"]),
                                    f"ID invalide: {e['id']}")

    def test_ids_are_lowercase_no_accents_no_spaces(self):
        for coll in self.state["catalogs"].values():
            for e in coll:
                if isinstance(e, dict) and "id" in e:
                    eid = e["id"]
                    self.assertEqual(eid, eid.lower(), f"ID non minuscule: {eid}")
                    self.assertNotIn(" ", eid, f"ID avec espace: {eid}")
                    self.assertTrue(eid.isascii(), f"ID non-ASCII (accents): {eid}")

    def test_ids_unique(self):
        seen = set()
        for coll_name, coll in self.state["catalogs"].items():
            for e in coll:
                if isinstance(e, dict) and "id" in e:
                    self.assertNotIn(e["id"], seen,
                                     f"ID dupliqué: {e['id']} ({coll_name})")
                    seen.add(e["id"])

    def test_slugify_rules(self):
        self.assertEqual(slugify("Arrosoir de cuivre"), "arrosoir_de_cuivre")
        self.assertEqual(slugify("Graine d'Écho"), "graine_d_echo")
        self.assertEqual(make_id("objet", "Houe de départ"), "objet_houe_de_depart")
        self.assertFalse(is_valid_id("Objet Valide"))  # majuscule
        self.assertFalse(is_valid_id("avec espace"))
        self.assertFalse(is_valid_id("1commence_par_chiffre"))


class TestCanonPreservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()
        cls.ca = canon_mod.run_stage(write=False)

    def test_canon_locations_present(self):
        canon_loc = {l["display_name"] for l in self.ca["canon"]["locations"]}
        cat_loc = {l["display_name"] for l in self.state["catalogs"]["locations"]
                   if l["status"] == Status.CANONIQUE}
        self.assertEqual(canon_loc, cat_loc,
                         "les lieux canoniques doivent être préservés")

    def test_canon_npcs_present(self):
        canon_npc = {n["display_name"] for n in self.ca["canon"]["npcs"]}
        cat_npc = {n["display_name"] for n in self.state["catalogs"]["npcs"]}
        self.assertEqual(canon_npc, cat_npc, "les PNJ canoniques doivent être préservés")

    def test_canon_objects_present(self):
        canon_obj = {o["display_name"] for o in self.ca["canon"]["objects"]}
        cat_obj = {o["display_name"] for o in self.state["catalogs"]["objects"]
                   if o["status"] == Status.CANONIQUE}
        self.assertEqual(canon_obj, cat_obj,
                         "les objets canoniques doivent être préservés")

    def test_world_player_refuge(self):
        self.assertEqual(self.ca["canon"]["world"]["display_name"], "Valdore")
        self.assertEqual(self.ca["canon"]["player"]["display_name"], "le Jardinier")
        self.assertIn("Maison-Racine", self.ca["canon"]["refuge"]["display_name"])

    def test_locked_canon_only_canonique(self):
        # Le canon verrouillé ne doit contenir AUCUN élément À_VALIDER/PROPOSÉ.
        locked = self.ca["locked_canon"]
        for l in locked["locations"]:
            self.assertEqual(l["status"], Status.CANONIQUE)
        for n in locked["npcs"]:
            self.assertEqual(n["status"], Status.CANONIQUE)
        for o in locked["objects"]:
            self.assertEqual(o["status"], Status.CANONIQUE)

    def test_open_decisions_not_in_canon(self):
        # Une décision ouverte ne doit jamais devenir canonique.
        for d in self.ca["open_decisions"]:
            self.assertEqual(d["status"], Status.A_VALIDER,
                             f"décision ouverte '{d['topic']}' convertie en canon!")


class TestNamingConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()

    def test_no_generic_numbered_names(self):
        # Aucun nom générique numéroté pour atteindre une cible.
        import re
        for coll in self.state["catalogs"].values():
            for e in coll:
                if isinstance(e, dict):
                    dn = e.get("display_name", "")
                    self.assertFalse(re.search(r"\b(objet|item|thing)\s*_?\d+\b", dn.lower()),
                                     f"nom générique numéroté: {dn}")

    def test_display_names_present(self):
        for coll_name, coll in self.state["catalogs"].items():
            for e in coll:
                if isinstance(e, dict) and "id" in e:
                    self.assertTrue(e.get("display_name"),
                                    f"{e['id']} sans nom affiché")

    def test_no_modern_tech_terms(self):
        forbidden = ["laser", "robot", "ordinateur", "cyber", "plasma", "nucléaire"]
        for coll in self.state["catalogs"].values():
            for e in coll:
                if isinstance(e, dict):
                    dn = (e.get("display_name") or "").lower()
                    for term in forbidden:
                        self.assertNotIn(term, dn,
                                         f"terme tech moderne '{term}' dans {dn}")


if __name__ == "__main__":
    unittest.main()
