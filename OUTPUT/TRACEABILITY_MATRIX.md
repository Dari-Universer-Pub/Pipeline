# Traceability Matrix

Générée par `tools/traceability.py` — chaque case provient d'un parcours réel (fixture `tests/fixtures/e2e/`, importateur, validateurs, graphe, compilateur, simulateur). Aucune case n'est déclarative.

## Matrice de maturité (gabarit officiel)

| Type | Specified | Schema | Imported | Cataloged | Graph | Compiled | Runtime tested | Status |
|---|---|---|---|---|---|---|---|---|
| objets | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| ressources | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| cultures | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| recettes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| machines | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| pnj | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| dialogues | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| quetes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| evenements | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| creatures | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| boss | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| maps | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| placement | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| assets | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| animations | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| sauvegardes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |

## Détail par domaine (contrat V2 : intégration + 6 tests)

| Domaine | Validation présente | Validation passée | Sortie runtime | Nominal | Rejet | Volume | Orphelin | Repro. | Test runtime | Maturité |
|---|---|---|---|---|---|---|---|---|---|---|
| objets | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| ressources | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| cultures | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| recettes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| machines | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| pnj | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| dialogues | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| quetes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| evenements | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| creatures | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| boss | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| maps | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| placement | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| assets | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| animations | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |
| sauvegardes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PRODUCTION_READY |

## Synthèse

- Domaines audités : **16**
- PRODUCTION_READY : **16** (animations, assets, boss, creatures, cultures, dialogues, evenements, machines, maps, objets, placement, pnj, quetes, recettes, ressources, sauvegardes)
- Incomplets : **0**
- Tests obligatoires : **96/96** réussis (6 par domaine : nominal, rejet, volume, orphelin, reproductibilité, intégration runtime)
- Volume testé : n = 25 clones cohérents par domaine (25 états distincts pour les sauvegardes)

## Notes de statut

- **boss** : Infrastructure PRODUCTION_READY (schéma, import, graphe, compilation, runtime). Le contenu boss reste À_VALIDER : décision ouverte « présence ou non d'un système de combat » (INPUT/open_decisions.md) ; canon : pas de magie de combat traditionnelle. Aucun boss n'est ajouté aux catalogues.

## Légende

- ✓ preuve réelle produite par le parcours ; ✗ preuve absente.
- Échelle de maturité : SPECIFIED → SCHEMA_VALIDATED → IMPORTED → CATALOGED → GRAPH_CONNECTED → COMPILED → RUNTIME_TESTED → PRODUCTION_READY.
- PRODUCTION_READY est interdit sans test d'intégration runtime réel (sortie du simulateur vérifiée, sans LLM).
- Preuves complètes : `REPORTS/traceability.json`.
