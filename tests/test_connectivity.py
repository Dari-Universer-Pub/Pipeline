"""Tests de connectivité du graphe (livrables 72, 75, 76, 77, 78, 79).

Vérifie : entités orphelines, atteignabilité, couverture, assets/animations
inutilisés, ET la DÉTECTION de ces problèmes sur un état volontairement cassé.
"""
from __future__ import annotations

import unittest

import helpers


class TestConnectivityClean(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = helpers.build_state()
        cls.conn = cls.state["connectivity"]

    def test_no_orphans(self):
        self.assertEqual(self.conn["orphans"], [],
                         "le graphe canonique ne doit avoir aucun orphelin")

    def test_all_reachable(self):
        self.assertEqual(self.conn["reachable_count"], self.conn["node_count"],
                         "tous les nœuds doivent être atteignables depuis le départ")

    def test_no_dangling_references(self):
        self.assertEqual(self.conn["dangling_references"], [],
                         "aucune référence pendante tolérée")

    def test_no_unused_objects(self):
        self.assertEqual(self.conn["objects_no_usage"], [],
                         "aucun objet sans usage réel")

    def test_no_resource_without_consumer(self):
        self.assertEqual(self.conn["resources_no_consumer"], [],
                         "chaque ressource a un consommateur réel (recette/machine)")

    def test_no_quest_without_consequence(self):
        self.assertEqual(self.conn["quests_no_consequence"], [],
                         "chaque quête a une conséquence")

    def test_no_secret_without_discovery(self):
        self.assertEqual(self.conn["secrets_no_discovery"], [],
                         "chaque secret a un chemin de découverte")

    def test_coverage_all_systems_connected(self):
        # Un système est isolé s'il n'a AUCUNE arête. system_temps communique
        # avec météo/agriculture/etc. qui en dépendent -> non isolé.
        edges = self.state["graph"]["edges"]
        systems = {n["id"] for n in self.state["graph"]["nodes"] if n["type"] == "system"}
        connected = set()
        for e in edges:
            if e["source"] in systems:
                connected.add(e["source"])
            if e["target"] in systems:
                connected.add(e["target"])
        self.assertEqual(systems - connected, set(),
                         "aucun système ne doit être isolé (sans aucune relation)")
        # De plus, le détecteur intégré ne signale aucun système isolé.
        self.assertEqual(self.conn["systems_isolated"], [])

    def test_coverage_all_catalog_entities_in_graph(self):
        node_ids = {n["id"] for n in self.state["graph"]["nodes"]}
        for coll in ("objects", "crops", "machines", "recipes", "npcs",
                     "creatures", "quests", "events", "locations"):
            for e in self.state["catalogs"][coll]:
                self.assertIn(e["id"], node_ids,
                              f"{e['id']} absent du graphe")


class TestConnectivityDetection(unittest.TestCase):
    """Vérifie que la pipeline DÉTECTE les problèmes injectés."""

    def setUp(self):
        self.state = helpers.build_state()

    def test_detect_orphan_entity(self):
        # Injecte un objet orphelin (aucune relation).
        self.state["graph"]["nodes"].append(
            {"id": "objet_orphelin_test", "type": "objet", "display_name": "Orphelin",
             "status": "PROPOSEE"})
        conn = helpers.rebuild_connectivity(self.state)
        self.assertIn("objet_orphelin_test", conn["orphans"],
                      "un objet sans relation doit être détecté comme orphelin")

    def test_detect_unused_asset(self):
        # Injecte un asset sans entité propriétaire valide.
        from lib import validator as val
        self.state["manifests"]["assets"].append({
            "id": "asset_fantome_test", "display_name": "Asset fantôme",
            "status": "PROPOSEE", "entity_id": "entite_inexistante_xyz",
            "family": "famille_objets", "kind": "icone", "width": 16, "height": 16,
            "fingerprint": "unique_fantome_123", "palette": ["#000000"],
        })
        issues = val.validate_assets(self.state)
        codes = {(i["code"], i["entity"]) for i in issues}
        self.assertTrue(any(c == "asset.orphan" and e == "asset_fantome_test"
                            for c, e in codes),
                        "un asset sans entité valide doit être détecté")

    def test_detect_animation_without_action(self):
        from lib import validator as val
        self.state["manifests"]["animations"].append({
            "id": "anim_sans_action_test", "entity_id": "pnj_alba",
            "state_or_action": "", "frames": 4, "fps": 6, "loop": False,
            "required_assets": [],
        })
        issues = val.validate_animations(self.state)
        codes = {i["code"] for i in issues}
        self.assertIn("anim.no_action", codes,
                      "une animation sans action/état doit être détectée")

    def test_detect_unreachable_entity(self):
        # Injecte un nœud connecté à rien d'atteignable.
        self.state["graph"]["nodes"].append(
            {"id": "lieu_isole_test", "type": "lieu", "display_name": "Isolé",
             "status": "PROPOSEE"})
        self.state["graph"]["edges"].append(
            {"id": "x", "type": "contient", "source": "lieu_isole_test",
             "target": "objet_isole_test", "implies_usage": False})
        self.state["graph"]["nodes"].append(
            {"id": "objet_isole_test", "type": "objet", "display_name": "Obj",
             "status": "PROPOSEE"})
        conn = helpers.rebuild_connectivity(self.state)
        self.assertIn("lieu_isole_test", conn["unreachable"],
                      "une entité non atteignable depuis le départ doit être détectée")

    def test_detect_resource_without_real_consumer(self):
        from lib import validator as val
        # Une ressource sans recette/machine qui la consomme.
        self.state["catalogs"]["resources"].append({
            "id": "ressource_test_sans_conso", "display_name": "Bidule",
            "status": "PROPOSEE", "category": "matériau",
            "producers": ["system_exploration"], "consumers": ["system_artisanat"],
        })
        # Pas d'arête recette/machine -> pas de consommateur réel.
        conn = helpers.rebuild_connectivity(self.state)
        # La ressource n'est pas dans le graphe, donc on vérifie via validate_connectivity
        # après l'y avoir ajoutée.
        self.state["graph"]["nodes"].append(
            {"id": "ressource_test_sans_conso", "type": "ressource",
             "display_name": "Bidule", "status": "PROPOSEE"})
        conn = helpers.rebuild_connectivity(self.state)
        self.assertIn("ressource_test_sans_conso", conn["resources_no_consumer"],
                      "une ressource sans consommateur réel doit être détectée")


if __name__ == "__main__":
    unittest.main()
