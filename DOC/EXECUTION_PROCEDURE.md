# Procédure d'exécution pas à pas (pour une autre IA)

*Livrables 52 (procédure d'exécution pour une autre IA) et 100
(documentation finale + procédure de reprise).*

Cette procédure permet à une autre IA (ou à un humain) de **reprendre** la
pipeline, de l'exécuter, de générer du contenu externe, de l'importer, de le
valider et de compiler le résultat pour le moteur — sans rien réinventer.

> **Règle d'or** : la pipeline **construit la fabrique**, elle ne produit PAS le
> jeu final. Ne lancez jamais de génération massive d'assets/scenes/maps. Le LLM
> n'est utilisé qu'**hors ligne** pour générer du contenu ; le jeu final
> s'exécute **sans LLM**.

---

## Prérequis

- Python 3.8+ (stdlib uniquement — aucun `pip install`).
- Les 5 entrées présentes et **lues intégralement** :
  `INPUT/game_brief.md`, `INPUT/canon_initial.md`, `INPUT/constraints.md`,
  `INPUT/open_decisions.md`, `CONTRACT/architecture_contract.md`.
- Travail depuis la racine du projet.

---

## Phase A — Construire la fabrique (étapes 1 à 13 du flux obligatoire)

### A.0 Lire toutes les entrées AVANT toute décision
Ouvrir et lire les 5 fichiers d'entrée en entier. Ne jamais remplacer une entrée
par une invention. Toute information manquante suit la cascade :
canon → brief → systèmes → défaut technique documenté (PROPOSEE) →
décision créative (A_VALIDER, `DECISION_PROPRIETAIRE`) → blocage ciblé.

### A.1 Exécuter la pipeline complète
```bash
python3 tools/pipeline.py
```
Cela enchaîne, dans l'ordre du contrat :

| # | Étape | Module | Artefacts |
| --- | --- | --- | --- |
| 1 | Canon central verrouillé | `canon.py` | `CANON/canon_locked.json`, décisions, contradictions |
| 2 | Ontologie | `ontology.py` | `ONTOLOGY/ontology.json` |
| 3 | Schémas | `ontology.py` | `SCHEMAS/*.schema.json` (21) |
| 4 | Systèmes de gameplay | `systems.py` | `GAME/systems/systems.json` |
| 5 | Catalogue fonctionnel | `catalog.py` | `GAME/catalogs/*`, `quantity_plan.json`, `functional_catalog/` |
| 6 | Graphe du monde | `graph.py` | `GAME/graph/world_graph.json`, `connectivity.json` |
| 7 | Manifests | `manifest.py` | `GAME/manifests/*` (15) |
| 8 | Prompts contextualisés | `prompt.py` | `PROMPTS/examples/`, `PROMPTS/generated/` |
| 9 | Validation | `validator.py` | `REPORTS/validation.*` |
| 10 | Rapports | `report.py` | `REPORTS/maturity, missing, isolated, open_decisions` |
| 11 | Simulation | `simulator.py` | `REPORTS/simulation.json` |
| 12 | Compilation moteur | `compiler.py` | `ENGINE_OUT/*` |

### A.2 Vérifier la validation
```bash
python3 tools/pipeline.py --check     # exit 0 si 0 erreur
```
Attendu : `PASS — validation passed=True, 0 erreurs`. Si échec, lire
`REPORTS/validation_report.md` et corriger la **source** (canon/catalogue), pas
le symptôme.

### A.3 Relire les rapports de décisions
- `REPORTS/decision_report.md` : statut de chaque décision (aucune décision
  ouverte convertie en canon silencieusement).
- `REPORTS/contradiction_report.md` : ambiguïtés/manques (monnaie, météo, saison,
  pêche, combat) — à faire trancher par le propriétaire, pas à inventer.
- `REPORTS/open_decisions_report.md` : liste des décisions `A_VALIDER`.
- `REPORTS/maturity_report.md` : maturité par type (actuellement ~71/100).
- `REPORTS/missing_report.md` : manques de contenu restants.

---

## Phase B — Générer du contenu externe (autre IA + LLM)

### B.1 Générer les prompts spécialisés
```bash
python3 tools/prompt_gen.py --id objet_fragment_de_souvenir --task objet
python3 tools/prompt_gen.py --family famille_cultures
python3 tools/prompt_gen.py --seq joueur_jardinier --action recolter
```
Chaque prompt est **auto-contextualisé** (canon + ontologie + graphe + manifests +
relations + contraintes). Si une information manque, le prompt contient
`BLOCKED: <raison>` — ne pas générer, remonter la question au propriétaire.

Les prompts d'exemple sont déjà dans `PROMPTS/examples/`.

### B.2 Confier les prompts à l'autre IA
L'autre IA (avec LLM) répond avec **un objet JSON** dans un bloc ```json,
conforme au schéma indiqué, **ou** exactement `BLOCKED: <raison>`.

### B.3 Déposer les réponses
Placer chaque réponse dans `RESULTS/incoming/` :
- réponse JSON → `<entité>.json` ;
- réponse BLOCKED → `<entité>.md` (contenu `BLOCKED: ...`).

---

## Phase C — Importer, valider, corriger

### C.1 Importer et valider les réponses
```bash
python3 tools/import_results.py
```
Chaque réponse est validée (schéma + références + logique + canon + économie +
temps + maps + assets + animations + connectivité) :
- **valide** → `RESULTS/accepted/` ;
- **invalide** → `RESULTS/rejected/` (+ `.raw.txt` et `.errors.json`) ;
- **BLOCKED** → non importée, tracée dans `REPORTS/generation_errors.md`.

### C.2 Lire le rapport d'erreurs
`REPORTS/generation_errors.md` liste, par entité rejetée, les codes d'erreur et
les corrections attendues (référence pendante, terme interdit, recette sans
sortie, asset orphelin, etc.).

### C.3 Régénérer uniquement ce qui a échoué (correction ciblée)
```bash
python3 tools/regenerate.py                 # tous les rejets
python3 tools/regenerate.py --entity objet_graine_d_echo
```
Les prompts de correction sont écrits dans
`PROMPTS/generated/regeneration/regen_<id>.md`, avec le feedback d'erreurs et la
sortie précédente injectés. **Attention** : si l'entité rejetée est
**fabriquée** (absente du canon/graphes/catalogues), la régénération est
**bloquée** — il faut d'abord l'ancrer dans le canon ou la supprimer, jamais
l'inventer pour atteindre une cible.

### C.4 Revalider l'état complet
```bash
python3 tools/import_results.py --revalidate   # rejoue les rejets corrigés
python3 tools/pipeline.py --check              # revalidation globale
```
Répéter C.1→C.4 jusqu'à `passed=True` et 0 erreur.

### C.5 Consolider les dialogues validés dans le catalogue
Les réponses acceptées sont stockées dans `RESULTS/accepted/` (preuve). Pour que
le **compilateur** les prenne en compte, les dialogues validés doivent être
consolidés dans le catalogue `GAME/catalogs/dialogues.json` (une liste
d'objets-dialogues). Ce catalogue est le **point d'intégration** : il est vide
par défaut et préservé d'un run à l'autre.

```bash
# Exemple : consolider tous les dialogues acceptés dans le catalogue.
python3 - <<'PY'
import json, glob
from pathlib import Path
acc = []
for f in glob.glob("RESULTS/accepted/dialogue_*.json"):
    acc.append(json.load(open(f, encoding="utf-8")))
cat = Path("GAME/catalogs/dialogues.json")
env = json.load(open(cat, encoding="utf-8")) if cat.exists() else \
      {"pipeline_version":"5.0.0","schema_version":"5.0.0","kind":"dialogues",
       "generated_deterministic":True,"payload":[]}
env["payload"] = acc
json.dump(env, open(cat,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
print("dialogues consolidés :", len(acc))
PY
python3 tools/pipeline.py --check     # revalidation (schéma + graphe + narratif)
```

Tant que `dialogues.json` est vide, la compilation replie sur les **salutations
essentielles dérivées des PNJ** (3 dialogues déterministes). Dès qu'il contient
des dialogues validés, `compile_dialogs` les compile **tous** (conditions →
lignes → choix → effets) et le repli disparaît. Le volume n'est pas limité :
le compilateur itère sur toute la collection (voir `tests/test_dialogues.py`).

---

## Phase D — Compiler pour le moteur

### D.1 Compiler les sorties runtime (sans LLM)
Déjà fait par `pipeline.py` (étape 12). Vérifier `ENGINE_OUT/` :
- `runtime_data.json` : bundle runtime (entités + relations) ;
- `dialogs_compiled.json` : dialogues en données conditionnelles (conditions →
  lignes → choix → effets + frontière de connaissance du locuteur). Source :
  `GAME/catalogs/dialogues.json` ; si vide, repli déterministe sur les
  salutations essentielles dérivées des PNJ canoniques (3 par défaut) ;
- `rules_compiled.json` : tables de règles/effets déterministes ;
- `save_schema.json` : schéma de sauvegarde versionné + migrations
  (`llm_mutation_forbidden: true`) ;
- `godot/` : amorces de chargement de données (autoload Godot 4).

### D.2 Confirmer l'absence de LLM runtime
`runtime_data.json` porte `llm_required_at_runtime: false`. Un LLM éventuel en
runtime ne peut **jamais** modifier canon, progression, règles, statistiques,
sauvegardes, objets, quêtes majeures ou secrets non débloqués.

---

## Phase E — Vérifier l'intégrité de la pipeline

```bash
python3 tools/run_tests.py            # 120 tests, attendus OK
python3 tools/pipeline.py --check     # validation globale, attendue PASS
```

Attendu :
- **Tests** : `OK` (120 tests) ;
- **Validation** : `passed=True, 0 erreurs` ;
- **Graphe** : 100 % atteignable, 0 référence pendante, 0 orphelin, 0 système
  isolé ;
- **Simulation** : 8/8 profils OK, 8/8 chaînes de production OK.

---

## Procédure de reprise (si l'état est perdu ou modifié)

La pipeline est **idempotente** et **reproductible** : relancer
`python3 tools/pipeline.py` reconstruit tout l'état depuis les 5 entrées, avec
les mêmes artefacts (à entrées et graines fixées). Aucune dépendance à un état
non persisté. Pour repartir de zéro :

```bash
rm -rf CANON ONTOLOGY SCHEMAS GAME PROMPTS/examples PROMPTS/generated \
       REPORTS ENGINE_OUT OUTPUT
python3 tools/pipeline.py
python3 tools/run_tests.py
```

> Ne jamais supprimer `INPUT/`, `CONTRACT/`, `tools/`, `tests/`, `README.md`,
> `DOC/`, ni `RESULTS/accepted` (preuve des imports validés).

---

## Garde-fous à respecter en permanence

1. Ne jamais convertir une décision ouverte en canon silencieusement.
2. Ne jamais inventer un fait narratif ; marquer `A_VALIDER` /
   `DECISION_PROPRIETAIRE`.
3. Quantités, noms, assets, animations, maps : **dérivés** du canon/systèmes,
   jamais arbitraires, jamais numérotés pour atteindre une cible.
4. Aucun objet/asset/animation/quête/recette/map orphelin.
5. Pas de placeholder présenté comme contenu final.
6. Ne pas modifier `CONTRACT/architecture_contract.md` sans le signaler.
7. LLM **hors ligne** uniquement ; jeu final **sans LLM** runtime.
8. Bloquer **uniquement** l'étape concernée si une information manque ; ne pas
   bloquer toute la chaîne.
