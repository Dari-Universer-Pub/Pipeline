"""Tests V2 — échelle de maturité et matrice de traçabilité.

Contrat V2 :
- échelle SPECIFIED -> SCHEMA_VALIDATED -> IMPORTED -> CATALOGED ->
  GRAPH_CONNECTED -> COMPILED -> RUNTIME_TESTED -> PRODUCTION_READY ;
- PRODUCTION_READY INTERDIT sans test d'intégration runtime réel ;
- matrice de traçabilité par domaine : schéma présent, importateur présent,
  validation présente, catalogue/graphe/compilateur alimentés, sortie runtime
  produite, 6 tests obligatoires, statut final ;
- la matrice est construite sur PREUVES VIVANTES (parcours réels), stable
  octet par octet, et n'ajoute rien au canon.
"""
from __future__ import annotations

import json
import unittest

import helpers  # noqa: F401  (prépare sys.path vers tools/)

from lib import traceability as tr  # noqa: E402
from lib.common import Maturity  # noqa: E402
from lib import integration as ig  # noqa: E402

DOMAINS_V2 = {"objets", "ressources", "cultures", "recettes", "machines",
              "pnj", "dialogues", "quetes", "evenements", "creatures",
              "boss", "maps", "placement", "assets", "animations",
              "sauvegardes"}


class TestMaturityLadder(unittest.TestCase):
    """L'échelle de maturité est calculée depuis les preuves, jamais déclarée."""

    def test_ladder_has_8_rungs(self):
        self.assertEqual(tr.MATURITY_LADDER, [
            "SPECIFIED", "SCHEMA_VALIDATED", "IMPORTED", "CATALOGED",
            "GRAPH_CONNECTED", "COMPILED", "RUNTIME_TESTED",
            "PRODUCTION_READY"])

    def test_production_ready_requires_full_chain(self):
        ev = {rung: True for rung in tr.MATURITY_LADDER}
        self.assertEqual(Maturity.from_evidence(ev), "PRODUCTION_READY")

    def test_no_runtime_test_means_not_production_ready(self):
        """PRODUCTION_READY est INTERDIT sans intégration runtime réelle."""
        ev = {rung: True for rung in tr.MATURITY_LADDER}
        ev["RUNTIME_TESTED"] = False
        self.assertNotEqual(Maturity.from_evidence(ev), "PRODUCTION_READY")
        self.assertEqual(Maturity.from_evidence(ev), "COMPILED")

    def test_ladder_is_monotonic(self):
        """Une preuve manquante fait retomber au barreau précédent."""
        for i in range(1, len(tr.MATURITY_LADDER)):
            ev = {rung: (j < i) for j, rung in enumerate(tr.MATURITY_LADDER)}
            self.assertEqual(Maturity.from_evidence(ev), tr.MATURITY_LADDER[i - 1])


class TestTraceabilityMatrix(unittest.TestCase):
    """La matrice est construite sur preuves vivantes (parcours réels)."""

    @classmethod
    def setUpClass(cls):
        cls.base = ig.base_state()
        cls.matrix = tr.build_matrix(state=cls.base, volume_n=25)

    def test_16_domains_audited(self):
        self.assertEqual(set(self.matrix["domains"]), DOMAINS_V2)

    def test_all_domains_production_ready(self):
        not_ready = {n: d["maturity"] for n, d in self.matrix["domains"].items()
                     if d["maturity"] != "PRODUCTION_READY"}
        self.assertEqual(not_ready, {},
                         "tous les domaines doivent être PRODUCTION_READY "
                         f"(échec : {not_ready})")

    def test_96_mandatory_tests_passed(self):
        s = self.matrix["summary"]
        self.assertEqual(s["tests_total"], 96)
        self.assertEqual(s["tests_passed"], 96)
        self.assertTrue(s["all_green"])

    def test_presence_chain_per_domain(self):
        """Schéma, importateur, validation présents ; catalogue/graphe/
        compilateur alimentés ; sortie runtime produite."""
        for n, d in self.matrix["domains"].items():
            with self.subTest(domaine=n):
                self.assertTrue(d["schema_present"], f"{n} : schéma absent")
                self.assertTrue(d["importer_present"], f"{n} : importateur absent")
                self.assertTrue(d["validation_present"], f"{n} : validation absente")
                self.assertTrue(d["catalog_fed"], f"{n} : catalogue non alimenté")
                self.assertTrue(d["graph_fed"], f"{n} : graphe non alimenté")
                self.assertTrue(d["validation_passed"], f"{n} : validation en échec")
                self.assertTrue(d["compiler_fed"], f"{n} : compilateur non alimenté")
                self.assertTrue(d["runtime_output_produced"],
                                f"{n} : aucune sortie runtime produite")

    def test_runtime_outputs_are_real(self):
        """La sortie runtime n'est pas un booléen décoratif : chaque domaine
        produit des données vérifiables spécifiques."""
        for n, d in self.matrix["domains"].items():
            with self.subTest(domaine=n):
                self.assertTrue(d["runtime_outputs"],
                                f"{n} : sortie runtime vide")

    def test_validators_are_real_functions(self):
        from lib import validator as v
        for n, names in tr.DOMAIN_VALIDATORS.items():
            with self.subTest(domaine=n):
                for fn in names:
                    self.assertTrue(callable(getattr(v, fn, None)),
                                    f"{n} : validateur {fn} introuvable")

    def test_matrix_is_byte_stable(self):
        """Deux constructions donnent des artefacts strictement identiques."""
        m2 = tr.build_matrix(state=self.base, volume_n=25)
        self.assertEqual(json.dumps(self.matrix, sort_keys=True, ensure_ascii=False),
                         json.dumps(m2, sort_keys=True, ensure_ascii=False))
        self.assertEqual(tr.render_markdown(self.matrix), tr.render_markdown(m2))

    def test_markdown_follows_template(self):
        md = tr.render_markdown(self.matrix)
        header = ("| Type | Specified | Schema | Imported | Cataloged | Graph "
                  "| Compiled | Runtime tested | Status |")
        self.assertIn(header, md, "la matrice doit suivre le gabarit officiel")
        for n in DOMAINS_V2:
            self.assertIn(f"| {n} |", md)
        self.assertNotIn("✗", md.split("## Détail")[0],
                         "aucune case en échec dans la matrice de maturité")
        self.assertIn("96", md)


class TestCanonProtection(unittest.TestCase):
    """La traçabilité prouve l'intégration SANS jamais modifier le canon."""

    def test_boss_content_never_in_catalogs(self):
        """Le boss est une infrastructure À_VALIDER (décision ouverte
        « système de combat ») — jamais ajouté aux catalogues persistés."""
        from pathlib import Path
        p = Path(__file__).resolve().parents[1] / "GAME/catalogs/creatures.json"
        payload = json.loads(p.read_text(encoding="utf-8"))["payload"]
        ids = {c["id"] for c in payload}
        self.assertNotIn("creature_gardien_du_puits", ids)
        self.assertTrue(all(c.get("kind") != "boss" for c in payload),
                        "aucun boss dans le canon tant que la décision "
                        "'système de combat' est ouverte")

    def test_boss_status_note_documents_open_decision(self):
        note = tr.STATUS_NOTES.get("boss", "")
        self.assertIn("À_VALIDER", note)
        self.assertIn("décision ouverte", note)

    def test_fixture_schemas_are_pipeline_schemas(self):
        """Les fixtures s'appuient sur les schémas RÉELS de l'usine
        (22 schémas, dont placement_rule et world_state ajoutés pour la V2)."""
        base = ig.base_state()
        schemas = base.get("schemas", {})
        self.assertIn("placement_rule", schemas,
                      "le schéma placement_rule doit exister (domaine V2)")
        self.assertIn("world_state", schemas,
                      "le schéma world_state porte les sauvegardes (domaine V2)")
        self.assertGreaterEqual(len(schemas), 22)
        for n, cfg in ig.DOMAINS.items():
            with self.subTest(domaine=n):
                self.assertIn(cfg["schema"], schemas,
                              f"{n} : schéma {cfg['schema']} absent de l'ontologie")


class TestPipelineStage12(unittest.TestCase):
    def test_traceability_is_stage_12(self):
        import pipeline
        self.assertEqual(pipeline.STAGES[-1], "traceability")
        self.assertEqual(len(pipeline.STAGES), 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
