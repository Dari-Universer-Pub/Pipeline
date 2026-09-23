# Architecture complète de la Pipeline V5 Graph-Driven

*Livrable 1 — Architecture complète de la pipeline.*

Ce document décrit l'architecture de la fabrique de production du jeu
*Les Jardins de l'Écho*. La pipeline est **graph-driven** : le graphe du monde
est la structure centrale dont dérivent catalogues, manifests, assets,
animations, prompts, validations et simulation.

---

## 1. Principes architecturaux

1. **Le canon est la source de vérité.** Aucune information canonique n'est
   altérée ; aucune décision ouverte n'est convertie en canon silencieusement.
2. **Tout est dérivé, rien n'est arbitraire.** Les quantités (objets, cultures,
   machines, recettes, PNJ, quêtes, assets, animations, maps) sont **calculées**
   depuis les systèmes, la boucle principale, les chaînes de production, la
   progression, le canon, les lieux et les saisons.
3. **Le graphe relie tout.** Chaque entité est un nœud ; chaque dépendance est
   une arête typée. Une entité sans usage réel est rejetée.
4. **Séparation conception / exécution.** Le LLM conçoit et génère **hors ligne**.
   Le jeu final s'exécute **sans LLM** : règles et effets sont des données
   déterministes.
5. **Validation avant import.** Toute sortie externe est validée (structure,
   schéma, références, logique, canon, économie, temps, maps, assets,
   animations, connectivité) avant acceptation.
6. **Déterminisme et reproductibilité.** À entrées et graines fixées, la
   pipeline produit exactement les mêmes sorties.
7. **Correction ciblée.** Un élément invalide est régénéré seul, avec feedback
   d'erreurs — jamais une campagne massive.

---

## 2. Vue d'ensemble des couches

```text
┌───────────────────────────────────────────────────────────────────────────┐
│ COUCHE 0 — ENTRÉES (source de vérité, lues intégralement)                    │
│   INPUT/game_brief.md · canon_initial.md · constraints.md · open_decisions.md │
│   CONTRACT/architecture_contract.md                                          │
└───────────────────────────────────────────────────────────────────────────┘
                                   │  extraction + verrouillage
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ COUCHE 1 — CANON & DÉCISIONS                                                 │
│   CANON/canon_locked.json (CANONIQUE uniquement)                            │
│   CANON/canon_extracted · brief_extracted · constraints · open_decisions    │
│   REPORTS/decision_report.md · contradiction_report.md                       │
└───────────────────────────────────────────────────────────────────────────┘
                                   │  vocabulaire du monde
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ COUCHE 2 — ONTOLOGIE & SCHÉMAS                                               │
│   ONTOLOGY/ontology.json (17 entités, 18 relations, états, conditions,      │
│   effets, déclencheurs)                                                      │
│   SCHEMAS/*.schema.json (22 schémas JSON draft-07, dérivés de l'ontologie)   │
└───────────────────────────────────────────────────────────────────────────┘
                                   │  besoins de gameplay
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ COUCHE 3 — SYSTÈMES & CATALOGUES (quantités dérivées)                        │
│   GAME/systems/systems.json (15 systèmes + exigences 'requires')            │
│   GAME/catalogs/*.json (objets, cultures, machines, recettes, PNJ, ...)     │
│   GAME/catalogs/quantity_plan.json (quantités calculées + justifiées)       │
│   GAME/functional_catalog/functional_catalog.json                           │
└───────────────────────────────────────────────────────────────────────────┘
                                   │  mise en relation
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ COUCHE 4 — GRAPHE DU MONDE (structure centrale)                              │
│   GAME/graph/world_graph.json (nœuds + arêtes typées)                       │
│   GAME/graph/connectivity.json (orphelins, atteignabilité, profondeur,      │
│   systèmes affectés, détections)                                            │
└───────────────────────────────────────────────────────────────────────────┘
                                   │  spécifications de production
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ COUCHE 5 — MANIFESTS (ce qui doit être produit, sans le produire)            │
│   manifest_objects · resources · crops · machines · recipes · quests · npcs  │
│   creatures · maps · placement · navigation · assets · animations ·          │
│   transitions · effects                                                      │
└───────────────────────────────────────────────────────────────────────────┘
                                   │  contextualisation
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ COUCHE 6 — PROMPTS SPÉCIALISÉS CONTEXTUALISÉS                                │
│   PROMPTS/templates/ (gabarits) · injecteur de contexte (lib/prompt.py)     │
│   PROMPTS/examples/ · PROMPTS/generated/ (par id / famille / séquence)      │
└───────────────────────────────────────────────────────────────────────────┘
                                   │  GÉNÉRATION EXTERNE (autre IA + LLM)
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ COUCHE 7 — IMPORT / VALIDATION / RÉGÉNÉRATION                                │
│   RESULTS/incoming → accepted / rejected (lib/importer.py)                  │
│   16 familles de validateurs (lib/validator.py)                            │
│   PROMPTS/generated/regeneration/ (correction ciblée, tools/regenerate.py)  │
└───────────────────────────────────────────────────────────────────────────┘
                                   │  compilation déterministe
                                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ COUCHE 8 — SORTIES MOTEUR (Godot 4, SANS LLM runtime)                        │
│   ENGINE_OUT/runtime_data.json · dialogs_compiled.json · rules_compiled.json │
│   save_schema.json · godot/ (amorces de chargement)                         │
└───────────────────────────────────────────────────────────────────────────┘
```

Couches transverses : **simulation** (`lib/simulator.py`), **rapports**
(`lib/report.py`) et **tests** (`tests/`) interrogent toutes les couches.

---

## 3. Modules (tools/lib/)

| Module | Rôle | Entrées | Sorties |
| --- | --- | --- | --- |
| `common.py` | IDs stables, statuts, versionnement, graines, I/O JSON | — | — |
| `canon.py` | Extraction/verrouillage du canon, décisions, contradictions | INPUT/, CONTRACT/ | CANON/, REPORTS/decision+contradiction |
| `ontology.py` | Ontologie + schémas JSON dérivés | — | ONTOLOGY/, SCHEMAS/ |
| `systems.py` | Catalogue des systèmes de gameplay + exigences | brief | GAME/systems/ |
| `catalog.py` | Dérivation des quantités + catalogues + plan | canon, systems | GAME/catalogs/, functional_catalog/ |
| `graph.py` | Graphe du monde + analyse de connectivité | catalogues, systems, canon | GAME/graph/ |
| `manifest.py` | Manifests (assets, animations, maps, placement, ...) | catalogues | GAME/manifests/ |
| `prompt.py` | Injecteur de contexte + générateurs de prompts | canon, ontology, graph, manifests | PROMPTS/examples, generated |
| `importer.py` | Import/validation des résultats externes | RESULTS/incoming | RESULTS/accepted+rejected, REPORTS/generation_errors |
| `validator.py` | 16 familles de validateurs | tout l'état | REPORTS/validation |
| `simulator.py` | Simulateur déterministe (profils, chaînes, routines) | catalogues | REPORTS/simulation |
| `report.py` | Rapports maturité/manquants/isolés/décisions | état complet | REPORTS/ |
| `compiler.py` | Compilation moteur (runtime sans LLM + Godot) | état validé | ENGINE_OUT/ |

---

## 4. Le modèle de données graph-driven

### 4.1 Nœuds (entités)

17 types d'entités définis dans l'ontologie : `monde`, `lieu`, `pnj`,
`creature`, `objet`, `ressource`, `culture`, `machine`, `recette`, `quete`,
`evenement`, `dialogue`, `asset`, `animation`, `map`, `system`, `saison`.

Chaque nœud porte : `id` (interne stable), `display_name` (affiché), `status`
(CANONIQUE/DEDUITE/PROPOSEE/A_VALIDER), `source`, `justification`, et un bloc
`derivation` (why, system, obtention, consumers, consequences, assets,
animations, tests).

### 4.2 Arêtes (relations)

18 types de relations : `contient`, `produit`, `consomme`, `transforme`,
`requiert`, `declenche`, `habite`, `frequente`, `donne`, `affecte`,
`adjacent_a`, `utilise`, `obtenu_par`, `evolue_vers`, `releve_de`, `connecte_a`,
`decrit`, `pousse_dans`.

Chaque relation précise si elle **implique un usage réel** (`implies_usage`).
Une relation purement technique ne suffit pas à rendre une entité « utile ».

### 4.3 Dérivation des arêtes

Les arêtes sont dérivées des **champs référentiels** des entités :
`seed_id`/`yield_id` (cultures), `inputs`/`outputs`/`station_id` (recettes),
`built_by`/`recipe_ids` (machines), `giver_id`/`effects` (quêtes),
`trigger`/`effects` (événements), `home`/`frequented_places`/`knowledge` (PNJ),
`habitat`/`yields` (créatures), `map_id`/`parent_id`/`linked_maps` (lieux/maps),
`location_id`/`discovery_path` (secrets), `depends_on` (systèmes), et l'ancrage
canonique (monde/joueur/faits).

---

## 5. Dérivation des quantités (cœur graph-driven)

La quantité de chaque type d'entité n'est **jamais arbitraire**. Elle est
calculée dans `catalog.build_quantity_plan` à partir de :

- **le plancher système** : somme des `min` exigés par les systèmes
  (`systems.compute_system_requirements`) pour chaque (type, rôle) ;
- **le canon** : entités canoniques obligatoires (5 objets, 4 lieux, 3 PNJ) ;
- **la boucle principale** : chaque étape (explorer → planter → transformer →
  offrir → débloquer) exige ses entités ;
- **les chaînes de production** : une culture exige graine + produit ; une
  recette exige station + entrées + sorties ;
- **les lieux et saisons** : 1 carte par lieu canonique ; couverture des saisons ;
- **la progression** : 1 quête par PNJ + quêtes de secrets ;
- **les relations** : rôles économiques (marchand) couverts par les PNJ canon.

Chaque quantité reçoit un **statut** : `À_VALIDER` si elle correspond à une
décision ouverte (nombre de cultures, quêtes, recettes, PNJ, biomes, saisons),
`DEDUITE` si elle découle du canon, `PROPOSEE` si c'est un défaut technique.

Avant de valider une quantité, la pipeline **explique** (bloc `derivation`) :
pourquoi l'élément existe, quel système l'utilise, comment il est obtenu, qui le
consomme, quelles conséquences il produit, quels assets/animations il nécessite,
quels tests le couvrent.

---

## 6. Dérivation des assets et animations

- **Assets** = entités × états × directions × variantes, regroupés par
  **familles cohérentes** : `famille_objets`, `famille_outils`,
  `famille_cultures`, `famille_machines`, `famille_personnages`,
  `famille_creatures`, `famille_terrains`, `famille_transitions`,
  `famille_effets`. Un asset n'est **jamais isolé** : il est rattaché à une
  entité, une famille, des dimensions, une palette, des variantes et des règles
  d'utilisation.
- **Animations** = actions/états × directions. Chaque animation précise entité,
  action, direction, frames, fps, boucle, **frame d'impact**, **effet logique
  déclenché**, transitions, assets requis et tests. Une animation est
  **synchronisée** avec la logique de gameplay (pas seulement visuelle).

---

## 7. Validation et connectivité

16 familles de validateurs (`validator.py`) : structurelle, schémas, encodage,
références, canonique, logique, narrative, économique, temporelle, progression,
maps, collisions, placement, assets, animations, connectivité.

La connectivité détecte : entités orphelines, objets sans usage, recettes sans
entrée/sortie, quêtes sans donneur/conséquence, PNJ sans routine/interaction,
ressources sans producteur/consommateur, secrets sans découverte, événements
inatteignables, systèmes isolés, références pendantes.

---

## 8. Simulation et exécution sans LLM

Le `simulator.py` est un moteur **déterministe** qui :
- maintient l'état du monde (temps, inventaire, relations, drapeaux, quêtes) ;
- applique les effets et évalue les conditions (mêmes tables que le runtime) ;
- simule 8 profils de joueurs (agriculteur, explorateur, social, ignore-quêtes,
  optimise-économie, rate-événements, spécialiste, contrarien) ;
- teste les chaînes de production avec vérification **avant/après**.

Le `compiler.py` produit `ENGINE_OUT/` : un bundle runtime **sans LLM**, des
dialogues essentiels **compilés en données conditionnelles**, des tables de
règles/effets déterministes, et un schéma de sauvegarde avec migrations. Un LLM
éventuel en runtime ne peut **jamais** modifier canon, progression, règles,
statistiques, sauvegardes, objets, quêtes majeures ou secrets non débloqués.

---

## 9. Versionnement et reproductibilité

- Chaque artefact JSON est enveloppé (`versioned_envelope`) avec
  `pipeline_version`, `schema_version`, `kind`, et `seed` le cas échéant.
- Les graines procédurales sont dérivées de façon stable (`derive_seed`) →
  reproductibilité des maps.
- Le schéma de sauvegarde (`ENGINE_OUT/save_schema.json`) versionne les données
  et fournit une table de migration.
- Les empreintes (`fingerprint`) garantissent l'unicité des assets (anti-doublon)
  et permettent de détecter toute dérive entre deux runs.

---

## 10. Ce que la pipeline NE fait PAS

- Elle ne développe **pas** le jeu dans Godot (seules des amorces de chargement
  de données sont fournies).
- Elle ne construit **pas** la Vertical Slice comme produit final.
- Elle ne génère **pas** massivement assets, maps, sprites, animations ou scènes.
- Elle ne remplace **pas** les quatre entrées par des inventions.
- Elle ne modifie **pas** le contrat d'architecture universel.
- Elle ne crée **pas** de placeholders présentés comme du contenu final, ni de
  noms numérotés/génériques pour atteindre une cible.

Les assets, animations, maps et contenus sont **uniquement décrits** dans des
manifests et spécifications de production, à l'exception de quelques exemples
minimaux destinés à tester la pipeline (fixtures, prompts d'exemple).
