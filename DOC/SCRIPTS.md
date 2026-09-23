# Liste et rôle des scripts

*Livrables 48 (liste des scripts) et 49 (rôle de chaque script).*

Tous les scripts sont en Python 3.8+ (stdlib uniquement, aucun `pip install`).
Ils se lancent depuis la racine du projet.

---

## Scripts exécutables (tools/)

### `tools/pipeline.py` — Orchestrateur principal
Exécute la chaîne complète de la pipeline : canon → ontologie → schémas →
systèmes → catalogues → graphe → manifests → prompts → validation → rapports →
simulation → compilation moteur.

```bash
python3 tools/pipeline.py              # run complet + validation
python3 tools/pipeline.py --check      # exit 0 si validation passe, sinon 1
python3 tools/pipeline.py --stage N    # exécute uniquement l'étape N (1..11)
python3 tools/pipeline.py --validate   # validation seulement
python3 tools/pipeline.py --quiet      # sans affichage
```
Écrit `OUTPUT/PIPELINE_RUN.json`.

### `tools/bootstrap_pipeline.py` — Bootstrapper (optionnel)
Lit les quatre entrées + le contrat et produit `OUTPUT/BOOTSTRAP_SPEC.md`, une
spécification initiale consolidée. Ne lance pas la génération de contenu.

### `tools/run_tests.py` — Lanceur de tests
Découvre et exécute toute la suite de tests (`tests/`).

```bash
python3 tools/run_tests.py             # tous les tests
python3 tools/run_tests.py -v          # verbeux
```
Equivalent : `python3 -m unittest discover -s tests -p "test_*.py"`.

### `tools/import_results.py` — Importateur de résultats
Valide et importe les réponses d'une autre IA depuis `RESULTS/incoming/`.

```bash
python3 tools/import_results.py                 # importe RESULTS/incoming/
python3 tools/import_results.py --dir AUTRE/    # répertoire alternatif
python3 tools/import_results.py --file X.json   # fichier unique
python3 tools/import_results.py --revalidate    # réimporte RESULTS/rejected/
```
Valide → `RESULTS/accepted/` ; invalide → `RESULTS/rejected/` (+ erreurs) ;
`BLOCKED` → non importé. Met à jour `REPORTS/generation_errors.{md,json}`.

### `tools/regenerate.py` — Régénération ciblée
Construit des prompts de correction ciblés pour les résultats rejetés
(feedback d'erreurs injecté). Une entité fabriquée (non présente dans le canon/
graphes) est **bloquée**, pas corrigée.

```bash
python3 tools/regenerate.py                     # tous les rejets
python3 tools/regenerate.py --entity objet_x    # entité spécifique
python3 tools/regenerate.py --all               # rejoue aussi les BLOCKED
```
Écrit dans `PROMPTS/generated/regeneration/`.

### `tools/prompt_gen.py` — Générateur de prompts contextualisés (CLI)
Génère un prompt spécialisé pour une entité, une famille ou une séquence animée.
L'information de contexte est auto-injectée depuis canon + ontologie + graphe +
manifests. Manque d'information → `BLOCKED`.

```bash
python3 tools/prompt_gen.py --id objet_fragment_de_souvenir --task objet
python3 tools/prompt_gen.py --family famille_cultures
python3 tools/prompt_gen.py --seq joueur_jardinier --action recolter
python3 tools/prompt_gen.py --id objet_x --print     # stdout seulement
python3 tools/prompt_gen.py --id objet_x --outdir P  # répertoire de sortie
```

---

## Modules de bibliothèque (tools/lib/)

Ces modules ne sont pas destinés à être lancés directement (sauf en
démonstration) ; ils sont importés par `pipeline.py` et les tests. Chacun expose
une fonction `run_stage(...)` retournant un dict et écrivant ses artefacts.

| Module | Rôle | Fonction clé |
| --- | --- | --- |
| `common.py` | IDs stables, statuts, versionnement, graines, I/O JSON, constantes | `make_id`, `slugify`, `derive_seed`, `versioned_envelope`, `read_json`, `write_json` |
| `canon.py` | Extraction/verrouillage du canon, décisions, contradictions | `run_stage`, `build_locked_canon`, `find_contradictions` |
| `ontology.py` | Ontologie (17 entités, 18 relations, états) + schémas JSON | `build_ontology`, `build_schemas`, `run_stage` |
| `systems.py` | Catalogue des 15 systèmes de gameplay + exigences | `build_systems`, `compute_system_requirements`, `run_stage` |
| `catalog.py` | Dérivation des quantités + catalogues + plan | `build_quantity_plan`, `build_all`, `run_stage` |
| `graph.py` | Graphe du monde + analyse de connectivité | `build_graph`, `analyze_connectivity`, `run_stage` |
| `manifest.py` | Manifests de production (assets, animations, maps, ...) | `build_all_manifests`, `build_asset_manifest`, `build_animation_manifest`, `run_stage` |
| `prompt.py` | Injecteur de contexte + générateurs de prompts | `build_context`, `generate_by_id`, `generate_by_family`, `generate_by_animation_sequence`, `run_stage` |
| `importer.py` | Import/validation des résultats externes | `import_dir`, `validate_result`, `_write_generation_errors` |
| `validator.py` | 16 familles de validateurs | `run_all`, `validate_*`, `load_state` |
| `simulator.py` | Simulateur déterministe (profils, chaînes, routines) | `simulate_profiles`, `simulate_production_chain`, `run_stage` |
| `report.py` | Rapports maturité/manquants/isolés/décisions | `maturity_report`, `missing_report`, `isolated_report`, `run_stage` |
| `compiler.py` | Compilation moteur (runtime sans LLM + amorces Godot) | `compile_runtime_data`, `compile_dialogs`, `compile_rules`, `compile_save_schema`, `run_stage` |

---

## Modules de test (tests/)

| Module | Couvre |
| --- | --- |
| `helpers.py` | Construit l'état complet en mémoire pour les tests |
| `test_connectivity.py` | Graphe : arêtes, orphelins, référence pendante, systèmes isolés |
| `test_production.py` | Chaînes de production : culture→récolte→recette→objet, économie |
| `test_simulation.py` | Simulateur : 8 profils, effets, conditions, déterminisme |
| `test_validation_import.py` | Validateurs (positifs/négatifs) + importation (fixtures) |
| `test_reproducibility.py` | IDs stables, empreintes, reproductibilité, versionnement |
| `test_naming_canon.py` | Nommage, unicité des IDs, canon verrouillé, pureté canonique |
| `test_no_llm_runtime.py` | Exécution sans LLM, déterminisme, protection des sauvegardes |
| `test_end_to_end.py` | Chaîne bout-en-bout (mémoire + artefacts disque) |

---

## Ordre d'exécution typique

```bash
python3 tools/pipeline.py            # 1. construire tout l'état
python3 tools/prompt_gen.py --id X --task objet   # 2. prompts à la demande
# 3. (autre IA génère, dépose dans RESULTS/incoming/)
python3 tools/import_results.py      # 4. importer/valider les réponses
python3 tools/regenerate.py          # 5. corriger les rejets
python3 tools/pipeline.py --check    # 6. revalider l'état complet
python3 tools/run_tests.py           # 7. vérifier l'intégrité de la pipeline
```
