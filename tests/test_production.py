"""Tests des chaînes de production et des dépendances (livrables 73, 74).

Vérifie qu'une recette consomme ses entrées et produit ses sorties (état
AVANT/APRÈS), que les dépendances sont complètes, et que les chaînes
multi-étapes (lin -> fil -> toile) fonctionnent de bout en bout.
"""
from __future__ import annotations

import unittest

import helpers
from lib import simulator, catalog as catalog_mod


class TestProductionChains(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()
        cls.cats = cls.state["catalogs"]

    def test_every_recipe_has_inputs_and_outputs(self):
        for r in self.cats["recipes"]:
            self.assertTrue(r.get("inputs"), f"{r['id']} sans ingrédient")
            self.assertTrue(r.get("outputs"), f"{r['id']} sans résultat")

    def test_recipe_consumes_and_produces(self):
        # État AVANT/APRÈS : la soupe de navet consomme des navets, produit une soupe.
        res = simulator.simulate_production_chain(self.cats, "recette_soupe_de_navet")
        self.assertTrue(res["ok"], "chaîne soupe de navet échouée")
        self.assertTrue(res["inputs_consumed"], "entrées non consommées")
        self.assertTrue(res["outputs_produced"], "sorties non produites")
        self.assertLess(res["after"].get("objet_navet", 0), res["before"]["objet_navet"],
                        "le navet doit être consommé (AVANT > APRÈS)")
        self.assertGreaterEqual(res["after"].get("objet_soupe_de_navet", 0), 1,
                                "la soupe doit être produite")

    def test_all_recipes_simulate_ok(self):
        for r in self.cats["recipes"]:
            res = simulator.simulate_production_chain(self.cats, r["id"])
            self.assertTrue(res["ok"], f"chaîne {r['id']} échouée: {res}")

    def test_multistep_chain_flax_to_cloth(self):
        # lin (culture) -> fibre -> fil -> toile : chaîne multi-étapes.
        state = simulator.initial_state(self.cats)
        recipes = {r["id"]: r for r in self.cats["recipes"]}
        state["player"]["inventory"]["objet_fibre_de_lin"] = 6
        # 3× (2 fibres -> 1 fil) = 3 fils.
        for _ in range(3):
            self.assertTrue(simulator.action_craft(state, recipes["recette_fil_de_lin"]))
        self.assertGreaterEqual(state["player"]["inventory"].get("objet_fil_de_lin", 0), 3)
        # 1× (3 fils -> 1 toile).
        self.assertTrue(simulator.action_craft(state, recipes["recette_toile"]))
        self.assertGreaterEqual(state["player"]["inventory"].get("objet_toile", 0), 1,
                                "la chaîne lin->fil->toile doit aboutir")

    def test_crop_growth_chain(self):
        # Planter -> arroser -> pousser -> récolter (état AVANT/APRÈS).
        state = simulator.initial_state(self.cats)
        crops = {c["id"]: c for c in self.cats["crops"]}
        echo = next(c for c in crops.values() if c.get("memory_plant"))
        seed_before = state["player"]["inventory"]["objet_graine_d_echo"]
        self.assertTrue(simulator.action_plant(state, "objet_graine_d_echo", echo))
        self.assertEqual(state["player"]["inventory"]["objet_graine_d_echo"],
                         seed_before - 1, "planter consomme une graine")
        for _ in range(echo["growth_days"] + 3):
            simulator.action_water(state, echo["id"])
            simulator.advance_day(state, self.cats)
        self.assertTrue(simulator.action_harvest(state, echo["id"]),
                        "la culture mûre doit être récoltable")
        self.assertGreaterEqual(state["player"]["inventory"].get(echo["yield_id"], 0), 1,
                                "récolter produit le rendement")


class TestDependencies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()

    def test_recipe_station_exists(self):
        node_ids = {n["id"] for n in self.state["graph"]["nodes"]}
        for r in self.state["catalogs"]["recipes"]:
            self.assertIn(r["station_id"], node_ids,
                          f"station {r['station_id']} de {r['id']} inexistante")

    def test_recipe_item_ids_exist(self):
        node_ids = {n["id"] for n in self.state["graph"]["nodes"]}
        for r in self.state["catalogs"]["recipes"]:
            for ing in r["inputs"]:
                self.assertIn(ing["item_id"], node_ids,
                              f"ingrédient {ing['item_id']} de {r['id']} inexistant")
            for out in r["outputs"]:
                self.assertIn(out["item_id"], node_ids,
                              f"sortie {out['item_id']} de {r['id']} inexistante")

    def test_crop_seed_and_yield_exist(self):
        node_ids = {n["id"] for n in self.state["graph"]["nodes"]}
        for c in self.state["catalogs"]["crops"]:
            self.assertIn(c["seed_id"], node_ids, f"graine de {c['id']} inexistante")
            self.assertIn(c["yield_id"], node_ids, f"rendement de {c['id']} inexistant")

    def test_system_dependencies_resolved(self):
        from lib import systems as systems_mod
        systems = systems_mod.build_systems()
        ids = {s["id"] for s in systems}
        for s in systems:
            for dep in s["depends_on"]:
                self.assertIn(dep, ids, f"dépendance {dep} de {s['id']} inexistante")

    def test_value_chain_no_loss(self):
        # Après propagation, la valeur d'une sortie >= valeur des entrées.
        objs = {o["id"]: o.get("base_value") for o in self.state["catalogs"]["objects"]}
        ress = {r["id"]: r.get("base_value") for r in self.state["catalogs"]["resources"]}
        vals = {**objs, **ress}
        for r in self.state["catalogs"]["recipes"]:
            in_v = sum((vals.get(i["item_id"]) or 0) * i.get("qty", 1) for i in r["inputs"])
            out_v = sum((vals.get(o["item_id"]) or 0) * o.get("qty", 1) for o in r["outputs"])
            if in_v and out_v:
                self.assertGreaterEqual(out_v, in_v,
                                        f"{r['id']}: perte de valeur ({out_v} < {in_v})")


if __name__ == "__main__":
    unittest.main()
