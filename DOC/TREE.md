# Arborescence finale du projet

*Livrable 47 — Arborescence finale.*

Arborescence complète produite par la pipeline (les caches `__pycache__` sont
exclus et ignorés par Git).

```text
Pipeline/
├── README.md                       # Documentation principale (comment utiliser la pipeline)
├── .gitignore
├── INPUT/                          # ENTRÉES (source de vérité, ne pas modifier)
│   ├── game_brief.md               #   brief du jeu
│   ├── canon_initial.md            #   canon initial
│   ├── constraints.md              #   contraintes techniques/créatives
│   └── open_decisions.md           #   décisions ouvertes
├── CONTRACT/                       # CONTRAT D'ARCHITECTURE
│   └── architecture_contract.md    #   contrat universel (non modifié)
├── CANON/                          # CANON VERROUILLÉ + EXTRAITS
│   ├── canon_locked.json           #   faits CANONIQUE uniquement
│   ├── canon_extracted.json        #   canon extrait (avec statuts)
│   ├── brief_extracted.json        #   éléments structurés du brief
│   ├── constraints_extracted.json  #   contraintes structurées
│   ├── open_decisions.json         #   décisions ouvertes structurées
│   └── contradictions.json         #   ambiguïtés/manques détectés
├── ONTOLOGY/
│   └── ontology.json               # 17 entités, 18 relations, états, conditions, effets
├── SCHEMAS/                        # 22 schémas JSON (draft-07, dérivés de l'ontologie)
│   ├── objet.schema.json
│   ├── culture.schema.json
│   ├── recette.schema.json
│   ├── machine.schema.json
│   ├── ressource.schema.json
│   ├── creature.schema.json
│   ├── quete.schema.json
│   ├── evenement.schema.json
│   ├── dialogue.schema.json
│   ├── animation.schema.json
│   ├── asset.schema.json
│   ├── placement_rule.schema.json
│   ├── world_state.schema.json
│   ├── map.schema.json
│   ├── transition.schema.json
│   ├── placement_rule.schema.json
│   ├── navigation_rule.schema.json
│   ├── collision_rule.schema.json
│   ├── spawn_rule.schema.json
│   ├── condition.schema.json
│   ├── effect.schema.json
│   ├── relation.schema.json
│   └── world_state.schema.json
├── GAME/
│   ├── systems/
│   │   └── systems.json            # 15 systèmes de gameplay + exigences 'requires'
│   ├── catalogs/                   # catalogues (quantités dérivées)
│   │   ├── seasons.json            #   4 saisons
│   │   ├── locations.json          #   11 lieux (4 canoniques + dérivés)
│   │   ├── crops.json              #   6 cultures
│   │   ├── resources.json          #   3 ressources
│   │   ├── machines.json           #   4 machines
│   │   ├── recipes.json            #   8 recettes
│   │   ├── objects.json            #   25 objets (5 canoniques + dérivés)
│   │   ├── npcs.json               #   3 PNJ
│   │   ├── creatures.json          #   2 créatures
│   │   ├── quests.json             #   4 quêtes
│   │   ├── events.json             #   4 événements
│   │   ├── secrets.json            #   2 secrets
│   │   ├── maps.json               #   4 cartes (1 par lieu canonique)
│   │   ├── dialogues.json          #   dialogues importés+validés (vide par défaut ;
│   │   │                           #     vide → le compilateur replie sur les
│   │   │                           #     salutations essentielles dérivées des PNJ)
│   │   └── quantity_plan.json      #   plan des quantités + justifications + statuts
│   ├── functional_catalog/
│   │   └── functional_catalog.json # vue unifiée de toutes les entités fonctionnelles
│   ├── graph/
│   │   ├── world_graph.json        #   nœuds + arêtes typées (103/279)
│   │   └── connectivity.json       #   analyse d'orphelins/atteignabilité/profondeur
│   └── manifests/                  # 15 manifests de production
│       ├── manifest_objects.json
│       ├── manifest_resources.json
│       ├── manifest_crops.json
│       ├── manifest_machines.json
│       ├── manifest_recipes.json
│       ├── manifest_quests.json
│       ├── manifest_npcs.json
│       ├── manifest_creatures.json
│       ├── manifest_maps.json
│       ├── manifest_placement.json
│       ├── manifest_navigation.json
│       ├── manifest_assets.json    #   102 assets (9 familles)
│       ├── manifest_animations.json#   107 animations
│       ├── manifest_transitions.json #  14 transitions
│       └── manifest_effects.json   #   10 effets
├── PROMPTS/
│   ├── templates/                  # gabarits
│   │   ├── prompt_objet.md
│   │   ├── prompt_culture.md
│   │   ├── prompt_recette.md
│   │   ├── prompt_machine.md
│   │   ├── asset.md
│   │   ├── animation.md
│   │   ├── map.md
│   │   ├── _context_header.md      #   injecteur de contexte commun
│   │   ├── _task_footer.md         #   pied commun (correction + BLOCKED)
│   │   └── ... (autres gabarits)
│   ├── examples/                   # exemples générés (9 OK + 1 BLOCKED)
│   ├── generated/                  # prompts à la demande (par id/famille/séquence)
│   │   └── regeneration/           #   prompts de correction ciblée
│   └── ...
├── RESULTS/
│   ├── incoming/                   # zone de dépôt des réponses d'une autre IA
│   ├── accepted/                   #   réponses validées
│   └── rejected/                   #   réponses rejetées (+ .raw.txt, .errors.json)
├── REPORTS/                        # rapports markdown + JSON
│   ├── decision_report.md
│   ├── contradiction_report.md
│   ├── maturity_report.md          #   71/100 en moyenne
│   ├── missing_report.md           #   manques de contenu
│   ├── isolated_report.md          #   entités isolées
│   ├── open_decisions_report.md    #   21 décisions ouvertes
│   ├── validation_report.md        #   0 erreur
│   ├── validation.json
│   ├── generation_errors.md        #   erreurs de génération (feedback)
│   ├── generation_errors.json
│   ├── simulation.json
│   ├── reports.json
│   ├── traceability.json           #   V2 : 16 domaines x 6 tests (preuves complètes)
│   └── V2_AUDIT_REPORT.md          #   V2 : rapport d'audit (modifications, limites, usage)
├── ENGINE_OUT/                     # SORTIES MOTEUR (Godot 4, SANS LLM runtime)
│   ├── runtime_data.json           #   bundle runtime (80 entités, 280 relations)
│   ├── dialogs_compiled.json       #   dialogues essentiels compilés en données
│   ├── rules_compiled.json         #   tables de règles/effets déterministes
│   ├── save_schema.json            #   schéma de sauvegarde versionné + migrations
│   └── godot/                      #   amorces de chargement de données (autoload)
├── OUTPUT/
│   ├── PIPELINE_RUN.json           #   journal du run complet
│   ├── BOOTSTRAP_SPEC.md           #   spécification du bootstrapper
│   ├── TRACEABILITY_MATRIX_TEMPLATE.md  # gabarit officiel de la matrice
│   └── TRACEABILITY_MATRIX.md      #   matrice V2 générée (preuves vivantes)
├── tools/
│   ├── pipeline.py                 # orchestrateur
│   ├── bootstrap_pipeline.py       # bootstrapper (optionnel)
│   ├── run_tests.py                # lanceur de tests
│   ├── import_results.py           # importateur de résultats
│   ├── regenerate.py               # régénération ciblée
│   ├── prompt_gen.py               # générateur de prompts (CLI)
│   ├── traceability.py             # matrice de traçabilité V2 (CLI, étape 12)
│   └── lib/                        # 15 modules de bibliothèque (voir SCRIPTS.md)
│       ├── common.py · canon.py · ontology.py · systems.py · catalog.py
│       ├── graph.py · manifest.py · prompt.py · importer.py · validator.py
│       ├── simulator.py · report.py · compiler.py
│       ├── integration.py          #   V2 : parcours E2E réels + 6 épreuves par domaine
│       └── traceability.py         #   V2 : matrice sur preuves vivantes
├── tests/                          # suite de tests (234 tests)
│   ├── helpers.py
│   ├── test_connectivity.py
│   ├── test_production.py
│   ├── test_simulation.py
│   ├── test_validation_import.py
│   ├── test_reproducibility.py
│   ├── test_naming_canon.py
│   ├── test_no_llm_runtime.py
│   ├── test_dialogues.py           # cycle de vie des dialogues (repli/import/volume/rejet)
│   ├── test_end_to_end.py
│   ├── test_e2e_domains.py         # V2 : 16 domaines x 6 tests obligatoires (96 tests)
│   ├── test_maturity_traceability.py  # V2 : maturité + matrice + protection du canon
│   └── fixtures/                   # exemples valides/invalides pour tester l'import
│       ├── valid/
│       ├── invalid/
│       └── e2e/                    #   V2 : 16 fixtures d'intégration de bout en bout
└── DOC/                            # documentation détaillée
    ├── ARCHITECTURE.md             #   architecture complète
    ├── FORMATS.md                  #   formats de données
    ├── IO.md                       #   entrées/sorties par étape + échange
    ├── SCRIPTS.md                  #   liste et rôle des scripts
    ├── TREE.md                     #   cette arborescence
    └── EXECUTION_PROCEDURE.md      #   procédure pas à pas pour une autre IA
```

---

## Compte d'artefacts

| Dossier | Fichiers |
| --- | --- |
| CANON | 6 |
| ONTOLOGY | 1 |
| SCHEMAS | 21 |
| GAME/systems | 1 |
| GAME/catalogs | 15 |
| GAME/functional_catalog | 1 |
| GAME/graph | 2 |
| GAME/manifests | 15 |
| PROMPTS/templates | 11 |
| PROMPTS/examples | 10 |
| REPORTS | 12 |
| ENGINE_OUT | 4 (+ autoload) |
| tools | 6 (+ 13 dans lib/) |
| tests | 10 (+ fixtures) |

Total projet : ~160 fichiers (hors `.git`, `__pycache__`, `RESULTS/incoming`).
