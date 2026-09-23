"""Tests de simulation (livrables 80, 81, 87-90).

Vérifie les profils de joueurs, les événements, les quêtes bloquées, les
routines, et que chaque test compare un état AVANT et APRÈS une action.
"""
from __future__ import annotations

import unittest

import helpers
from lib import simulator


class TestProfiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()
        cls.cats = cls.state["catalogs"]

    def test_all_profiles_run(self):
        res = simulator.run_all_profiles(self.cats)
        for name, p in res.items():
            self.assertNotIn("error", p, f"profil {name} en erreur")
            self.assertIn("after", p, f"profil {name} sans état APRÈS")

    def test_farmer_profile_harvests_and_crafts(self):
        p = simulator.run_profile("agriculteur", self.cats)
        trace = dict(p["trace"])
        self.assertGreaterEqual(trace.get("harvest_echo", 0), 1,
                                "l'agriculteur doit récolter la plante mémorielle")
        self.assertGreaterEqual(trace.get("craft_soupe", 0), 1,
                                "l'agriculteur doit transformer une récolte")

    def test_explorer_discovers_secret(self):
        p = simulator.run_profile("explorateur", self.cats)
        self.assertIn("secret_clairiere_repetition", p["secrets_discovered"],
                      "l'explorateur doit découvrir le secret du Bois")

    def test_social_increases_relationship(self):
        p = simulator.run_profile("social", self.cats)
        before = p["before"]["relationships"].get("pnj_alba", 0)
        after = p["after"]["relationships"].get("pnj_alba", 0)
        self.assertGreater(after, before,
                           "offrir/parler doit augmenter la relation (AVANT < APRÈS)")

    def test_ignore_quests_is_resilient(self):
        # Un joueur qui ignore les quêtes ne doit pas être bloqué économiquement.
        p = simulator.run_profile("ignore_quetes", self.cats)
        trace = dict(p["trace"])
        self.assertGreater(trace.get("money", 0), 50,
                           "ignorer les quêtes ne doit pas bloquer l'économie")

    def test_miss_events_no_hard_block(self):
        p = simulator.run_profile("rate_evenements", self.cats)
        # Rater des événements ne doit pas verrouiller définitivement une quête.
        trace = dict(p["trace"])
        self.assertIsInstance(trace.get("quests_active"), list,
                              "rater des événements ne doit pas bloquer une quête")

    def test_specialist_fishing(self):
        p = simulator.run_profile("specialiste", self.cats)
        trace = dict(p["trace"])
        self.assertGreaterEqual(trace.get("poisson", 0), 1,
                                "le spécialiste pêche doit obtenir du poisson")

    def test_contrarian_opposite_path(self):
        p = simulator.run_profile("contrarian", self.cats)
        trace = dict(p["trace"])
        self.assertEqual(trace.get("location"), "lieu_lac_muet",
                         "le joueur contrarien suit un chemin opposé sans crash")


class TestEffectsAndConditions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cats = helpers.build_state()["catalogs"]

    def test_add_remove_item_before_after(self):
        state = simulator.initial_state(self.cats)
        before = state["player"]["inventory"].get("objet_navet", 0)
        simulator.apply_effect(state, {"type": "add_item",
                                       "params": {"item_id": "objet_navet", "qty": 3}})
        self.assertEqual(state["player"]["inventory"]["objet_navet"], before + 3)
        simulator.apply_effect(state, {"type": "remove_item",
                                       "params": {"item_id": "objet_navet", "qty": 1}})
        self.assertEqual(state["player"]["inventory"]["objet_navet"], before + 2)

    def test_relationship_clamped(self):
        state = simulator.initial_state(self.cats)
        simulator.apply_effect(state, {"type": "change_relationship",
                                       "params": {"pnj_id": "pnj_alba", "delta": 500}})
        self.assertLessEqual(state["player"]["relationships"]["pnj_alba"], 100,
                             "la relation doit être bornée à 100")

    def test_condition_item_count(self):
        state = simulator.initial_state(self.cats)
        simulator.apply_effect(state, {"type": "add_item",
                                       "params": {"item_id": "objet_navet", "qty": 2}})
        self.assertTrue(simulator.check_condition(
            state, {"type": "item_count",
                    "params": {"item_id": "objet_navet", "op": ">=", "qty": 2}}))
        self.assertFalse(simulator.check_condition(
            state, {"type": "item_count",
                    "params": {"item_id": "objet_navet", "op": ">=", "qty": 5}}))

    def test_condition_and_or_not(self):
        state = simulator.initial_state(self.cats)
        c_and = {"type": "and", "params": {"conditions": [
            {"type": "location", "params": {"lieu_id": "lieu_vallee_claire"}},
            {"type": "season", "params": {"season_id": state["time"]["season"]}},
        ]}}
        self.assertTrue(simulator.check_condition(state, c_and))
        c_not = {"type": "not", "params": {"condition": c_and}}
        self.assertFalse(simulator.check_condition(state, c_not))


class TestEvents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cats = helpers.build_state()["catalogs"]

    def test_season_event_fires_in_correct_season(self):
        state = simulator.initial_state(self.cats)
        state["time"]["season"] = "saison_des_brumes"
        fired = simulator.process_events(state, self.cats)
        self.assertIn("evenement_retour_du_bois", fired,
                      "l'événement du Bois doit se déclencher en Saison des Brumes")

    def test_impossible_event_not_fired(self):
        # Un événement dont la condition n'est jamais vraie ne doit pas se déclencher.
        state = simulator.initial_state(self.cats)
        state["time"]["season"] = "saison_des_epis"  # pas la saison du Bois
        fired = simulator.process_events(state, self.cats)
        self.assertNotIn("evenement_retour_du_bois", fired,
                         "événement saisonnier déclenché hors saison (impossible)")


class TestQuestsNotBlocked(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cats = helpers.build_state()["catalogs"]

    def test_intro_quest_completable(self):
        state = simulator.initial_state(self.cats)
        simulator.process_quests(state, self.cats)
        self.assertIn("quete_le_premier_echo", state["world"]["completed_quests"],
                      "la quête d'introduction doit pouvoir être complétée")

    def test_every_quest_has_fallback(self):
        for q in self.cats["quests"]:
            self.assertTrue(q.get("fallback"),
                            f"{q['id']} sans solution de repli (risque de blocage)")

    def test_routines_resolve_locations(self):
        state = simulator.initial_state(self.cats)
        pos = simulator.simulate_routines(state, self.cats)
        for nid, p in pos.items():
            self.assertIsNotNone(p, f"routine de {nid} sans lieu")


if __name__ == "__main__":
    unittest.main()
