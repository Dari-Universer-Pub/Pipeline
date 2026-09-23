"""Tests E2E V2 — les 6 tests obligatoires x 16 domaines de contenu.

Contrat V2 : chaque domaine (objets, ressources, cultures, recettes, machines,
PNJ, dialogues, quêtes, événements, créatures, boss, maps, placement, assets,
animations, sauvegardes) doit passer :
1. nominal            — parcours complet entrée -> runtime -> PRODUCTION_READY ;
2. rejet              — variante invalide détectée (import ou validation) ;
3. volume             — 25 clones cohérents intégrés, compilés, exécutés ;
4. orphelin           — variante orpheline détectée (jamais intégrée) ;
5. reproductibilité   — sorties stables octet par octet ;
6. intégration runtime — le simulateur exécute la donnée compilée (sans LLM)
   et produit une sortie vérifiable spécifique au domaine.

Les fixtures réalistes vivent dans tests/fixtures/e2e/*.json. Les résultats
sont calculés UNE fois (setUpClass) puis assertés par test — aucune écriture
dans les vrais dossiers RESULTS/ (import redirigé vers un dossier temporaire).
"""
from __future__ import annotations

import unittest

import helpers  # noqa: F401  (prépare sys.path vers tools/)

from lib import integration as ig  # noqa: E402

VOLUME_N = 25


class TestE2EDomains(unittest.TestCase):
    """96 tests : 6 épreuves obligatoires pour chacun des 16 domaines V2."""

    @classmethod
    def setUpClass(cls):
        cls.base = ig.base_state()
        cls.fx = {d: ig.load_fixture(d) for d in ig.DOMAINS}
        cls.res: dict[str, dict] = {}
        for dom in ig.DOMAINS:
            fx = cls.fx[dom]
            cls.res[dom] = {
                "journey": ig.run_journey(fx, cls.base),
                "rejection": ig.run_rejection(fx, cls.base),
                "orphan": ig.run_orphan(fx, cls.base),
                "volume": ig.run_volume(fx, VOLUME_N, cls.base),
                "repro": ig.run_reproducibility(fx, cls.base),
            }


def _make_tests(domain: str) -> None:
    """Génère les 6 méthodes de test d'un domaine (noms stables et lisibles)."""

    def test_01_nominal(self: TestE2EDomains) -> None:
        rec = self.res[domain]
        j = rec["journey"]
        self.assertEqual(j["maturity"], "PRODUCTION_READY",
                         f"{domain} : le parcours nominal doit atteindre "
                         f"PRODUCTION_READY (preuves réelles, jamais déclaratif)")
        self.assertTrue(all(s == "ACCEPTED"
                            for s in j["steps"]["import"]["statuses"]),
                        f"{domain} : toutes les entités de la fixture doivent "
                        f"être ACCEPTÉES par l'importateur réel")
        self.assertTrue(j["steps"]["validation"]["passed"],
                        f"{domain} : la validation globale doit passer")
        self.assertEqual(j["steps"]["validation"]["entity_errors"], [],
                         f"{domain} : aucune erreur de validation sur la fixture")
        self.assertTrue(j["steps"]["graph"]["ok"],
                        f"{domain} : le graphe doit connecter la fixture")
        self.assertTrue(j["steps"]["compile"]["all_present"],
                        f"{domain} : toutes les entités doivent être présentes "
                        f"dans la sortie compilée")

    def test_02_rejet(self: TestE2EDomains) -> None:
        rej = self.res[domain]["rejection"]
        self.assertTrue(rej["detected"],
                        f"{domain} : la variante invalide doit être détectée "
                        f"(rejet à l'import ou erreur de validation) — jamais "
                        f"intégrée silencieusement")

    def test_03_volume(self: TestE2EDomains) -> None:
        vol = self.res[domain]["volume"]
        self.assertTrue(vol["ok"], f"{domain} : le test de volume doit passer")
        self.assertEqual(vol["n"], VOLUME_N)
        self.assertTrue(vol["compiled_present"],
                        f"{domain} : les {VOLUME_N} clones doivent tous être "
                        f"présents dans la sortie compilée")
        self.assertTrue(vol["runtime_ok"],
                        f"{domain} : le runtime doit exécuter les clones")

    def test_04_orphelin(self: TestE2EDomains) -> None:
        orp = self.res[domain]["orphan"]
        self.assertTrue(orp["detected"],
                        f"{domain} : la variante orpheline doit être détectée "
                        f"(rejet, erreur de validation ou connectivité)")

    def test_05_reproductibilite(self: TestE2EDomains) -> None:
        rep = self.res[domain]["repro"]
        self.assertTrue(rep["stable"],
                        f"{domain} : deux parcours identiques doivent produire "
                        f"la même empreinte compilée")
        self.assertTrue(rep["byte_identical_runtime"],
                        f"{domain} : le bundle runtime doit être stable octet "
                        f"par octet")
        self.assertTrue(rep["maturity_identique"],
                        f"{domain} : la maturité doit être identique")

    def test_06_integration_runtime(self: TestE2EDomains) -> None:
        j = self.res[domain]["journey"]
        rt = j["steps"]["runtime"]
        self.assertTrue(rt.get("ok"),
                        f"{domain} : l'épreuve runtime (donnée compilée "
                        f"exécutée par le simulateur, sans LLM) doit réussir")
        outputs = {k: v for k, v in rt.items()
                   if k not in ("domain", "entity", "ok", "probe")}
        self.assertTrue(outputs,
                        f"{domain} : le runtime doit produire une sortie "
                        f"vérifiable (pas seulement un booléen)")
        # Assertions spécifiques au domaine (sortie runtime RÉELLE).
        if domain == "objets":
            self.assertEqual(rt["inventory"], 1)
            self.assertGreater(rt["money_gain"], 0)
        elif domain == "ressources":
            self.assertTrue(rt["real_consumer"])
        elif domain == "cultures":
            self.assertTrue(rt["planted"] and rt["harvested"])
        elif domain in ("recettes", "machines"):
            self.assertTrue(rt["crafted"] and rt["station_ok"]
                            if domain == "recettes" else rt["crafted"])
        elif domain == "pnj":
            self.assertTrue(rt["talked"] and rt["gift_raised"])
        elif domain == "dialogues":
            self.assertTrue(rt["compiled"] and rt["context_sensitive"]
                            and rt["reveals_applied"])
            self.assertEqual(rt["chosen"], "dialogue_pnj_alba_apresmidi")
        elif domain == "quetes":
            self.assertTrue(rt["completed"] and rt["effects_applied"]
                            and rt["consequences"])
        elif domain == "evenements":
            self.assertTrue(rt["trigger_matches"] and rt["effects_applied"])
        elif domain == "creatures":
            self.assertTrue(rt["habitat_ok"] and rt["yields_ok"])
        elif domain == "boss":
            self.assertEqual(rt["kind"], "boss")
            self.assertTrue(rt["spawned"] and rt["yields_ok"])
            self.assertIn("décision ouverte", rt["content_note"],
                          "le boss doit documenter la décision ouverte "
                          "« système de combat » dans sa sortie runtime")
        elif domain == "maps":
            self.assertTrue(rt["explored"] and rt["seed_stable"])
        elif domain == "placement":
            self.assertTrue(rt["rule_found"] and rt["places_ok"])
            self.assertTrue(rt["simulation"]["ok"])
        elif domain == "assets":
            self.assertTrue(rt["found"] and rt["fingerprint_unique"])
        elif domain == "animations":
            self.assertTrue(rt["found"] and rt["impact_in_frames"]
                            and rt["flag_set"] and rt["effect_applied"])
        elif domain == "sauvegardes":
            self.assertTrue(rt["roundtrip"] and rt["migration"]
                            and rt["tamper_rejected"] and rt["byte_stable"])

    for fn in (test_01_nominal, test_02_rejet, test_03_volume,
               test_04_orphelin, test_05_reproductibilite,
               test_06_integration_runtime):
        safe = domain.replace(" ", "_")
        fn.__name__ = f"test_{safe}_{fn.__name__[5:]}"
        fn.__qualname__ = f"TestE2EDomains_{safe}.{fn.__name__}"
        fn.__doc__ = f"Domaine « {domain} » — épreuve {fn.__name__[5:]}."
        setattr(TestE2EDomains, fn.__name__, fn)


for _dom in ig.DOMAINS:
    _make_tests(_dom)


class TestFixturesIsolation(unittest.TestCase):
    """Les fixtures E2E ne doivent jamais polluer l'usine réelle."""

    FIXTURE_IDS = None

    @classmethod
    def setUpClass(cls):
        cls.fixture_ids = set()
        for dom in ig.DOMAINS:
            fx = ig.load_fixture(dom)
            for key in ("entities", "invalid_variant", "orphan_variant"):
                v = fx.get(key)
                items = v if isinstance(v, list) else ([v] if isinstance(v, dict) else [])
                for e in items:
                    if e.get("id"):
                        cls.fixture_ids.add(e["id"])

    def test_no_fixture_leak_into_results(self):
        """Aucun fichier de fixture dans RESULTS/ (import redirigé en tmp)."""
        import json
        from pathlib import Path
        results = Path(__file__).resolve().parents[1] / "RESULTS"
        if not results.exists():
            self.skipTest("RESULTS/ absent")
        leaked = []
        for f in results.rglob("*.json"):
            try:
                name = f.name
                data = f.read_text(encoding="utf-8")
            except OSError:
                continue
            if any(fid in name or f'"{fid}"' in data for fid in self.fixture_ids):
                leaked.append(str(f))
        self.assertEqual(leaked, [],
                         "les fixtures E2E ne doivent jamais être écrites "
                         f"dans RESULTS/ : {leaked}")

    def test_no_fixture_leak_into_catalogs(self):
        """Les catalogues/manifests sur disque restent le canon de l'usine."""
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        on_disk = set()
        for d in ("GAME/catalogs", "GAME/manifests"):
            for f in (root / d).glob("*.json"):
                payload = json.loads(f.read_text(encoding="utf-8")).get("payload", [])
                if isinstance(payload, list):
                    on_disk |= {e.get("id") for e in payload if isinstance(e, dict)}
        self.assertEqual(on_disk & self.fixture_ids, set(),
                         "aucune entité de fixture ne doit apparaître dans "
                         "les catalogues/manifests persistés")


if __name__ == "__main__":
    unittest.main(verbosity=2)
