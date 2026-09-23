# Entrées / sorties de chaque étape & format d'échange

*Livrables 50 (entrées/sorties de chaque étape), 51 (format d'échange),
99 (documentation des entrées et sorties).*

Ce document décrit précisément ce que consomme et ce que produit chaque étape de
la pipeline, et le format d'échange entre les étapes.

---

## Format d'échange général

- **Entre modules Python** : dictionaries Python (passés en mémoire) via les
  fonctions `run_stage(...)`.
- **Sur disque (persistance)** : JSON UTF-8 sous **enveloppe versionnée**
  (`pipeline_version`, `schema_version`, `kind`, `seed?`, `payload`).
- **Rapports** : markdown (lisibles) + JSON (exploitables).
- **Prompts** : markdown.
- **Réponses de l'autre IA** : JSON dans un bloc ```json (ou `BLOCKED: raison`).

Règle d'échange : chaque étape **lit** les artefacts des étapes précédentes
(depuis le disque via `lib/common.read_json` + `unwrap`) et **écrit** ses propres
artefacts. Aucune étape ne dépend d'un état non persisté.

---

## Étape 0 — Bootstrapper (optionnel)

| | |
| --- | --- |
| **Script** | `tools/bootstrap_pipeline.py` |
| **Entrées** | `INPUT/*.md`, `CONTRACT/architecture_contract.md` |
| **Sorties** | `OUTPUT/BOOTSTRAP_SPEC.md` |
| **Échange** | markdown (spécification initiale concaténée) |

---

## Étape 1 — Canon & décisions

| | |
| --- | --- |
| **Module** | `lib/canon.py` (`run_stage`) |
| **Entrées** | `INPUT/game_brief.md`, `canon_initial.md`, `constraints.md`, `open_decisions.md`, `CONTRACT/architecture_contract.md` |
| **Sorties** | `CANON/canon_locked.json`, `canon_extracted.json`, `brief_extracted.json`, `constraints_extracted.json`, `open_decisions.json`, `contradictions.json` ; `REPORTS/decision_report.md`, `contradiction_report.md` |
| **In-memory** | `{inputs, canon, brief, constraints, open_decisions, contradictions, locked_canon}` |

**canon_locked.json** (payload) : `world`, `player`, `refuge`,
`immutable_facts[]`, `locations[]`, `npcs[]`, `objects[]`, `naming_rules`,
`technical_constraints{engine, tile_size, runtime_llm_required}`,
`gameplay_systems_canonical[]`, `main_loops[]`, `lock{locked, policy}`.
Ne contient QUE des éléments `CANONIQUE`.

---

## Étape 2 — Ontologie & schémas

| | |
| --- | --- |
| **Module** | `lib/ontology.py` (`run_stage`) |
| **Entrées** | (aucune — définitions internes) |
| **Sorties** | `ONTOLOGY/ontology.json` ; `SCHEMAS/*.schema.json` (21) |
| **In-memory** | `{ontology, schemas}` |

**ontology.json** : `entity_types` (17), `relation_types` (18),
`world_state_schema`, `condition_types`, `effect_types`,
`event_trigger_types`, `weather_types`, `naming_policy`.

---

## Étape 3 — Systèmes de gameplay

| | |
| --- | --- |
| **Module** | `lib/systems.py` (`run_stage`) |
| **Entrées** | brief (systèmes souhaités), canon (prémisse) |
| **Sorties** | `GAME/systems/systems.json` |
| **In-memory** | `{systems[], requirements{}, count}` |

Chaque système : `id`, `display_name`, `status`, `depends_on[]`, `verbs[]`,
`entity_types[]`, `requires[{entity_type, role, min}]`, `produces[]`,
`consumes[]`. Le champ `requires` pilote la dérivation des quantités.

---

## Étape 4 — Catalogues (quantités dérivées)

| | |
| --- | --- |
| **Module** | `lib/catalog.py` (`run_stage`) |
| **Entrées** | canon (étape 1), systèmes (étape 3) |
| **Sorties** | `GAME/catalogs/{seasons,locations,crops,resources,machines,recipes,objects,npcs,creatures,quests,events,secrets,maps,quantity_plan}.json` ; `GAME/functional_catalog/functional_catalog.json` |
| **In-memory** | dict des catalogues + `quantity_plan` + `functional_catalog` |

**quantity_plan.json** : par type, `{canonical, derived, proposed_total,
system_floor, quantity_status, justification}`.

---

## Étape 5 — Graphe du monde

| | |
| --- | --- |
| **Module** | `lib/graph.py` (`run_stage`) |
| **Entrées** | catalogues (étape 4), systèmes (3), canon (1) |
| **Sorties** | `GAME/graph/world_graph.json`, `connectivity.json` |
| **In-memory** | `{graph{nodes,edges}, connectivity, fingerprint}` |

**world_graph.json** : `{node_count, edge_count, nodes[{id,type,display_name,
status}], edges[{id,type,source,target,status,implies_usage}]}`.

**connectivity.json** : `{node_count, edge_count, reachable_count,
dangling_references[], orphans[], unreachable[], weak_usage[],
objects_no_usage[], recipes_no_input[], recipes_no_output[], quests_no_giver[],
quests_no_consequence[], npcs_no_routine[], npcs_no_interaction[],
resources_no_producer[], resources_no_consumer[], secrets_no_discovery[],
events_unreachable[], systems_isolated[], causal_depth{}}`.

---

## Étape 6 — Manifests

| | |
| --- | --- |
| **Module** | `lib/manifest.py` (`run_stage`) |
| **Entrées** | catalogues (4) |
| **Sorties** | `GAME/manifests/manifest_{objects,resources,crops,machines,recipes,quests,npcs,creatures,maps,placement,navigation,assets,animations,transitions,effects}.json` |
| **In-memory** | `{manifests{}, counts{}}` |

Chaque manifest est une **spécification de production** (décrit ce qui doit être
produit, ne produit rien). Assets dérivés par familles ; animations par
(action, direction) ; maps avec placement/navigation/transitions/spawn.

---

## Étape 7 — Prompts spécialisés

| | |
| --- | --- |
| **Module** | `lib/prompt.py` (`run_stage`) + CLI `tools/prompt_gen.py` |
| **Entrées** | canon (1), ontologie (2), graphe (5), manifests (6) |
| **Sorties** | `PROMPTS/examples/*.md`, `PROMPTS/generated/*.md`, `PROMPTS/generated/index.json` |
| **In-memory** | `{examples{}, summary{}}` |

L'injecteur de contexte assemble canon + ontologie + entité + relations +
contraintes visuelles + dépendances + validations. Modes : par identifiant, par
famille, par séquence animée. Manque d'information → `BLOCKED`.

---

## Étape 8 — Génération externe (autre IA)

| | |
| --- | --- |
| **Acteur** | Une autre IA (avec LLM), hors de cette pipeline |
| **Entrées** | prompts de `PROMPTS/` |
| **Sorties** | réponses JSON déposées dans `RESULTS/incoming/` |
| **Échange** | markdown (prompt) → JSON (réponse) ou `BLOCKED: raison` |

---

## Étape 9 — Importation

| | |
| --- | --- |
| **Module** | `lib/importer.py` + CLI `tools/import_results.py` |
| **Entrées** | `RESULTS/incoming/*.{json,md,txt}`, état courant (schémas, graphe) |
| **Sorties** | `RESULTS/accepted/*.json`, `RESULTS/rejected/*.{raw.txt,errors.json}`, `REPORTS/generation_errors.{md,json}` |
| **In-memory** | `{total, accepted, rejected, blocked, results[]}` |

Chaque réponse est validée (schéma + références + logique + canon). Valide →
acceptée ; invalide → rejetée avec erreurs ; `BLOCKED` → non importée.

---

## Étape 10 — Validation

| | |
| --- | --- |
| **Module** | `lib/validator.py` (`run_all`) |
| **Entrées** | état complet (catalogues, manifests, graphe, canon, ontologie, schémas, connectivité) |
| **Sorties** | `REPORTS/validation.json`, `validation_report.md` |
| **In-memory** | `{passed, error_count, warning_count, by_validator{}, issues[]}` |

16 familles de validateurs. `passed=true` si 0 erreur.

---

## Étape 10b — Régénération ciblée (si rejet)

| | |
| --- | --- |
| **Script** | `tools/regenerate.py` |
| **Entrées** | `RESULTS/rejected/*`, état courant |
| **Sorties** | `PROMPTS/generated/regeneration/regen_<id>.md` |
| **Échange** | markdown (prompt de correction avec feedback d'erreurs) |

---

## Étape 11 — Rapports

| | |
| --- | --- |
| **Module** | `lib/report.py` (`run_stage`) |
| **Entrées** | état complet + connectivité + graphe |
| **Sorties** | `REPORTS/{maturity_report.md, missing_report.md, isolated_report.md, open_decisions_report.md, reports.json}` |
| **In-memory** | `{maturity, missing, isolated, open_decisions}` |

---

## Étape 12 — Simulation

| | |
| --- | --- |
| **Module** | `lib/simulator.py` (`run_stage`) |
| **Entrées** | catalogues (4) |
| **Sorties** | `REPORTS/simulation.json` |
| **In-memory** | `{profiles{}, production_chains{}}` |

8 profils de joueurs + chaînes de production (vérification avant/après).

---

## Étape 13 — Compilation moteur

| | |
| --- | --- |
| **Module** | `lib/compiler.py` (`run_stage`) |
| **Entrées** | état validé (10) |
| **Sorties** | `ENGINE_OUT/{runtime_data.json, dialogs_compiled.json, rules_compiled.json, save_schema.json, godot/}` |
| **In-memory** | `{runtime_entities, relations, dialogs, assets, animations, llm_required_at_runtime:false}` |

Bundle runtime **déterministe, sans LLM**. Dialogues essentiels compilés en
données conditionnelles. Amorces Godot 4 (chargement de données uniquement).

---

## Journal de run

| | |
| --- | --- |
| **Script** | `tools/pipeline.py` |
| **Sortie** | `OUTPUT/PIPELINE_RUN.json` (résumé par étape + validation_passed) |

Résumé horodaté de l'exécution complète, avec le compte d'artefacts par étape et
le statut de validation final.
