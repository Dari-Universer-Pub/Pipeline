# Rapport d'audit V2 — contrat d'architecture v2

*Généré le 2026-09-23. Contrat audité : `CONTRACT/architecture_contract.md`
(v2, officielle). Version précédente archivée : `CONTRACT/architecture_contract_v1.md`
— changement signalé, rien n'a été remplacé silencieusement.*

---

## 0. Principe de l'audit

Le contrat V2 impose : **« un fichier qui existe n'est pas une fonctionnalité
terminée »**. Chaque affirmation de ce rapport repose sur une **preuve vivante** :
parcours réels exécutés (importateur, validateurs, graphe, compilateur,
simulateur) sur des fixtures réalistes, jamais sur la simple présence d'un
fichier, d'un schéma ou d'un validateur isolé.

---

## 1. Fichiers modifiés / ajoutés pour l'intégration V2

### Modifiés (16)

| Fichier | Changement |
| --- | --- |
| `CONTRACT/architecture_contract.md` | Contrat V2 adopté comme officiel (zip V2 des entrées) |
| `tools/bootstrap_pipeline.py` | Spécification V2 : échelle de maturité, 16 domaines, gabarit de matrice (`OUTPUT/TRACEABILITY_MATRIX_TEMPLATE.md`) |
| `tools/lib/common.py` | Statuts EN (`Status.to_v2()` : CANONICAL/DERIVED/PROPOSED/TO_VALIDATE) mappés sur les statuts FR existants + classe `Maturity` (échelle 8 barreaux, `from_evidence`, `promote` anti-saut) |
| `tools/lib/ontology.py` | Schéma `placement_rule` (22e schéma) ; `animation.impact_event` : `integer`/`string`/`null` (aligné sur la pratique compilée) |
| `tools/lib/importer.py` | Routage `placement` → `placement_rule`, `sauvegarde` → `world_state` |
| `tools/lib/simulator.py` | Section runtime V2 : `from_runtime` (état initial depuis données compilées), `evaluate_dialogs` (conditions contextuelles), `save_game`/`load_game` (checksum, migration, rejet de trucature), `probe_maps`, `simulate_placement`, `probe_assets`, `probe_animations` |
| `tools/pipeline.py` | Étape 12 « traçabilité » (matrice sur preuves réelles) |
| `ONTOLOGY/ontology.json`, `SCHEMAS/animation.schema.json` | Régénérés (22 schémas) |
| `README.md`, `DOC/ARCHITECTURE.md`, `DOC/SCRIPTS.md`, `DOC/TREE.md`, `DOC/EXECUTION_PROCEDURE.md` | Documentation V2 (audit, étape 12, 234 tests, procédure de preuve) |
| `OUTPUT/BOOTSTRAP_SPEC.md`, `OUTPUT/PIPELINE_RUN.json` | Régénérés (étape 12 incluse) |

### Ajoutés (11 + 16 fixtures)

| Fichier | Rôle |
| --- | --- |
| `CONTRACT/architecture_contract_v1.md` | Archive V1 (traçabilité du changement de contrat) |
| `tools/lib/integration.py` | Couche d'intégration V2 : `base_state`, `integrate`, `rebuild`, `compile_all`, `verify_in_runtime`, `graph_evidence`, `runtime_probe` (16 domaines), parcours E2E (`run_journey`, `run_rejection`, `run_orphan`, `run_volume`, `run_reproducibility`), import redirigé en temporaire (`temp_results`) |
| `tools/lib/traceability.py` | Matrice de traçabilité sur preuves vivantes (`build_matrix`, `render_markdown`, `run_stage`) |
| `tools/traceability.py` | CLI étape 12 (`--volume-n`, `--no-write`) |
| `SCHEMAS/placement_rule.schema.json` | 22e schéma (domaine placement) |
| `tests/fixtures/e2e/*.json` | **16 fixtures réalistes** (entités + variante invalide + variante orpheline par domaine) |
| `tests/test_e2e_domains.py` | 98 tests : 16 domaines × 6 épreuves + isolation des fixtures |
| `tests/test_maturity_traceability.py` | 16 tests : échelle de maturité, matrice, stabilité octet, protection du canon |
| `REPORTS/traceability.json` | Preuves complètes (stables octet par octet) |
| `OUTPUT/TRACEABILITY_MATRIX.md` | Matrice générée (gabarit officiel 8 colonnes + détail V2) |
| `REPORTS/V2_AUDIT_REPORT.md` | Ce rapport |

**Aucun remplacement silencieux** : la pipeline V1→V5 existante (11 étapes,
120 tests) est conservée et étendue ; les statuts FR restent la référence
interne, les statuts EN V2 sont un mapping.

---

## 2. Tests ajoutés

- **`tests/test_e2e_domains.py` (98 tests)** — pour chacun des 16 domaines :
  1. *nominal* : parcours complet entrée → import → schéma → canon → graphe →
     catalogues → validation → compilation → sortie runtime vérifiée →
     maturité PRODUCTION_READY ;
  2. *rejet* : variante invalide détectée (rejet à l'import **ou** erreur de
     validation — jamais intégrée silencieusement) ;
  3. *volume* : 25 clones cohérents intégrés, validés (0 erreur), compilés,
     exécutés par le runtime (25 états de sauvegarde distincts pour le domaine
     sauvegardes) ;
  4. *orphelin* : variante orpheline détectée (rejet, validation ou
     connectivité ; références hors graphe pour les sauvegardes) ;
  5. *reproductibilité* : deux parcours identiques → même empreinte, bundle
     runtime et sauvegarde stables **octet par octet** ;
  6. *intégration runtime* : le simulateur exécute la donnée compilée (sans
     LLM) et produit une sortie vérifiable **spécifique** au domaine
     (ex. dialogues : dialogue choisi selon le contexte, révélations
     appliquées ; sauvegardes : aller-retour + migration + rejet de
     trucature ; placement : 8 placements conformes distance/terrain).
  Plus 2 tests d'isolation : aucune fixture ne fuit dans `RESULTS/` ni dans
  les catalogues/manifests persistés.
- **`tests/test_maturity_traceability.py` (16 tests)** — échelle de maturité
  (8 barreaux, monotonie, PRODUCTION_READY **interdit** sans RUNTIME_TESTED),
  matrice complète (16 domaines, 96/96, chaîne de présence, sorties runtime
  réelles, validateurs réels, stabilité octet par octet, conformité au
  gabarit), protection du canon (aucun boss dans les catalogues persistés,
  note de décision ouverte), étape 12 présente dans la pipeline.

## 3. Tests exécutés — résultats

```text
Suite complète : python3 tools/run_tests.py
Ran 234 tests — OK : 234 | ÉCHECS : 0 | ERREURS : 0
  dont 120 tests préexistants (V5) — inchangés, tous verts
  dont 114 tests ajoutés (audit V2) : 98 E2E domaines + 16 maturité/traçabilité
Pipeline : python3 tools/pipeline.py → 12 étapes, validation SUCCÈS (0 erreur, 0 avertissement)
Reproductibilité globale : double exécution complète → 117/117 artefacts
  identiques octet par octet (hors OUTPUT/PIPELINE_RUN.json, horodaté par conception)
```

---

## 4. Matrice de traçabilité

Matrice complète : **`OUTPUT/TRACEABILITY_MATRIX.md`** (gabarit officiel) ;
preuves détaillées : **`REPORTS/traceability.json`**.

| Domaine | Schéma | Importateur | Validation | Catalogue | Graphe | Compilateur | Sortie runtime | 6 tests | Maturité |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| objets | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ inventaire+vente | 6/6 | PRODUCTION_READY |
| ressources | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ consommateur réel | 6/6 | PRODUCTION_READY |
| cultures | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ semis→récolte | 6/6 | PRODUCTION_READY |
| recettes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ fabrication+station | 6/6 | PRODUCTION_READY |
| machines | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ station+placement+craft | 6/6 | PRODUCTION_READY |
| pnj | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ parler+cadeau (relation ↑) | 6/6 | PRODUCTION_READY |
| dialogues | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ choix contextuel+révélations | 6/6 | PRODUCTION_READY |
| quetes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ effets+conséquences | 6/6 | PRODUCTION_READY |
| evenements | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ déclencheur+effets | 6/6 | PRODUCTION_READY |
| creatures | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ habitat+récoltes | 6/6 | PRODUCTION_READY |
| boss | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ spawn+récoltes (rencontre) | 6/6 | PRODUCTION_READY (infrastructure) |
| maps | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ exploration+graine stable | 6/6 | PRODUCTION_READY |
| placement | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ 8 placements conformes | 6/6 | PRODUCTION_READY |
| assets | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ empreintes uniques | 6/6 | PRODUCTION_READY |
| animations | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ frame d'impact+drapeau posé | 6/6 | PRODUCTION_READY |
| sauvegardes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ aller-retour+migration+anti-trucature | 6/6 | PRODUCTION_READY |

**Total : 96/96 tests obligatoires réussis.**

## 5. Domaines PRODUCTION_READY

**16/16** : objets, ressources, cultures, recettes, machines, pnj, dialogues,
quetes, evenements, creatures, boss, maps, placement, assets, animations,
sauvegardes.

Cas particulier **boss** : l'**infrastructure** est PRODUCTION_READY (schéma
`creature` + kind `boss`, import, graphe, compilation, runtime — rencontre/
épreuve sans combat, conformément au canon « pas de magie de combat
traditionnelle »). Le **contenu** boss reste `A_VALIDER` : décision ouverte
« présence ou non d'un système de combat » (`INPUT/open_decisions.md`). Aucun
boss n'est ajouté aux catalogues canoniques (vérifié par test).

## 6. Domaines incomplets

**Aucun** au sens du contrat (chaque domaine prouve la chaîne complète jusqu'à
la sortie runtime vérifiée). Réserves honnêtes :

- Le domaine boss prouve une infrastructure, pas un système de combat (décision
  ouverte — voir §5).
- Les preuves s'appuient sur **une fixture réaliste par domaine** (+ 25 clones
  au test de volume), pas sur la totalité du contenu futur : c'est exactement
  l'exigence V2 (épreuve d'intégration), pas une génération massive (interdite
  avant la fin de l'audit).

## 7. Limites restantes

1. **Validateur de schéma maison** : sous-ensemble de JSON Schema draft-07
   (type/enum/required/minimum/items/ref_fields), stdlib uniquement — pas de
   dépendance `jsonschema`. Suffisant pour les 22 schémas, mais les mots-clés
   avancés (oneOf, $ref internes, formats) ne sont pas supportés.
2. **Routines des PNJ canoniques vides** : les 3 PNJ du canon n'ont pas de
   routines horaires (donnée d'entrée) ; le simulateur utilise
   `frequented_places`/`home`. Un avertissement `conn.npc_no_routine` existe et
   un test de détection le couvre.
3. **Dialogues compilés dans `ENGINE_OUT/`** : 3 dialogues essentiels issus du
   repli canonique. Le compilateur accepte **l'ensemble futur** (prouvé par le
   test de volume : 25 dialogues importés → compilés → évalués par le moteur
   de dialogue), mais le contenu massif n'est pas généré (interdit avant fin
   d'audit).
4. **Migrations de sauvegarde** : seule la migration `0.0.0 → 1.0.0` est
   implémentée (fusion sur état initial + recalcul du checksum). Ajouter une
   migration par version future.
5. **`OUTPUT/PIPELINE_RUN.json` horodaté** : non stable octet par octet par
   conception (journal de run). Les 117 autres artefacts sont stables
   (vérifié par double exécution).
6. **Maturité par domaine vs par entité** : la matrice V2 mesure les domaines
   (exigence du contrat) ; la maturité moyenne des **entités canoniques**
   reste 71/100 (`REPORTS/maturity_report.md`) — les entités individuelles
   progresseront à l'import des contenus générés.
7. **Volume n = 25** : échantillon représentatif par domaine (cohérent, validé,
   compilé, exécuté) ; l'usine accepte plus (l'import est unitaire et rejoue
   les mêmes épreuves), mais la génération massive reste exclue avant décision.
8. **Prompts** : l'injecteur de contexte couvre canon/ontologie/graphe/
   manifests/fonction/relations/dimensions/variantes/animations/placement/
   validations, avec `BLOCKED` si information manquante (testé). Les nouvelles
   règles de placement issues des fixtures E2E ne sont pas encore injectées
   dans les prompts de génération de maps (les manifests de placement existants
   le sont).

## 8. Procédure d'utilisation (pour une autre IA)

1. **Lire** `README.md`, `CONTRACT/architecture_contract.md` (V2),
   `DOC/EXECUTION_PROCEDURE.md`, `DOC/SCRIPTS.md`.
2. **Reconstruire l'état** : `python3 tools/pipeline.py` (12 étapes, ~6 s).
   Attendu : `validation SUCCÈS ✓ (0 erreur)`.
3. **Vérifier** : `python3 tools/pipeline.py --check` (exit 0).
4. **Produire du contenu** : choisir un élément dans `GAME/manifests/`,
   générer le prompt contextualisé (`python3 tools/prompt_gen.py --id <id>
   --task <type>`), l'exécuter avec un LLM **hors ligne**, déposer la réponse
   JSON dans `RESULTS/incoming/`.
5. **Importer** : `python3 tools/import_results.py` — schéma + canon +
   références vérifiés ; accepted / rejected / BLOCKED. Si rejet :
   `python3 tools/regenerate.py` (correction ciblée), jamais d'entité
   fabriquée.
6. **Prouver l'intégration** : `python3 tools/run_tests.py` (234 tests, OK
   attendu) puis `python3 tools/traceability.py` (16 domaines × 6 tests,
   96/96 attendu ; `OUTPUT/TRACEABILITY_MATRIX.md` sans ✗).
7. **Règles dures** : ne jamais convertir une décision ouverte en canon ;
   ne jamais déclarer PRODUCTION_READY sans test d'intégration runtime réel ;
   pas de LLM au runtime du jeu ; pas de placeholder ni de noms numérotés ;
   outputs reproductibles (graines + tri + `sort_keys`).

---

*Preuves : `REPORTS/traceability.json` (parcours complets par domaine),
`OUTPUT/TRACEABILITY_MATRIX.md` (matrice), `REPORTS/validation.json`
(0 erreur), suite de tests 234/234.*
