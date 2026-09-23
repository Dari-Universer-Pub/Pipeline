# Pipeline V5 Graph-Driven — *Les Jardins de l'Écho*

> **Ceci n'est pas le jeu.** C'est la **fabrique de production** — autonome,
> documentée, testable et réutilisable — qui permet à une autre IA de générer le
> jeu de manière cohérente, contrôlée, interconnectée et validée.

Pipeline construite à partir du **bootstrapper** (`PIPELINE_BOOTSTRAPPER_EXEMPLE 2.zip`)
et de ses quatre fichiers d'entrée (`INPUT/`) + le contrat d'architecture
(`CONTRACT/`). Elle transforme :

```text
Brief + Canon initial + Contraintes + Décisions ouvertes + Contrat architectural
        ↓
Pipeline de production spécifique au jeu (canon verrouillé, ontologie, schémas,
systèmes, catalogues, graphe du monde, manifests, prompts contextualisés,
importateur, validateurs, tests, simulateur, rapports, compilation moteur)
```

Le jeu cible : **simulation agricole, exploration et narration** dans le monde de
**Valdore**, 2D vue du dessus, **Godot 4**, pixel art 16×16, **sans LLM à
l'exécution**.

---

## Démarrage rapide

Aucune dépendance externe : **Python 3.11+ stdlib uniquement** (autonomie garantie).

```bash
# 1. Exécuter la pipeline complète (INPUT -> ENGINE_OUT)
python3 tools/pipeline.py

# 2. Vérifier la validation (0 erreur attendue)
python3 tools/pipeline.py --check

# 3. Lancer la suite de tests (120 tests)
python3 tools/run_tests.py

# 4. (Optionnel) régénérer la spécification du bootstrapper
python3 tools/bootstrap_pipeline.py
```

Après exécution, tous les artefacts sont produits dans `CANON/`, `ONTOLOGY/`,
`SCHEMAS/`, `GAME/`, `PROMPTS/`, `REPORTS/` et `ENGINE_OUT/`.

---

## Le flux obligatoire (contrat d'architecture)

```text
INPUT/ + CONTRACT/
   ↓ (1) analyse des entrées
CANON/canon_locked.json ................. canon central verrouillé
REPORTS/decision_report.md .............. statuts CANONIQUE/DEDUITE/PROPOSEE/À_VALIDER
REPORTS/contradiction_report.md ......... contradictions & ambiguïtés
   ↓ (2) ontologie + schémas
ONTOLOGY/ontology.json .................. types d'entités, relations, états, effets
SCHEMAS/*.schema.json ................... 21 schémas JSON (draft-07)
   ↓ (3) systèmes de gameplay
GAME/systems/systems.json ............... 15 systèmes + exigences de contenu
   ↓ (4) catalogues (quantités DÉRIVÉES)
GAME/catalogs/*.json .................... objets, cultures, machines, recettes, PNJ...
GAME/catalogs/quantity_plan.json ........ quantités calculées + justifiées
GAME/functional_catalog/................ catalogue fonctionnel unifié
   ↓ (5) graphe du monde
GAME/graph/world_graph.json ............. nœuds + relations
GAME/graph/connectivity.json ............ orphelins, atteignabilité, profondeur
   ↓ (6) manifests
GAME/manifests/*.json ................... objets, maps, assets, animations, placement...
   ↓ (7) prompts spécialisés contextualisés
PROMPTS/templates/ ...................... gabarits de prompts
PROMPTS/examples/ ....................... exemples générés (injecteur de contexte)
   ↓ (8) génération externe par une autre IA  ← VOUS (autre IA)
   ↓ (9) importation
RESULTS/ ................................ incoming -> accepted / rejected
   ↓ (10) validation
REPORTS/validation_report.md ............ 16 familles de validateurs
   ↓ (11) régénération ciblée si nécessaire
PROMPTS/generated/regeneration/ ......... prompts de correction
   ↓ (12) compilation pour le moteur
ENGINE_OUT/ ............................. runtime sans LLM + amorces Godot 4
```

---

## Statuts de l'information (règle fondamentale)

La pipeline distingue **toujours** quatre statuts, et **ne convertit jamais
silencieusement une décision créative ouverte en fait canonique** :

| Statut | Signification | Exemple |
| --- | --- | --- |
| `CANONIQUE` | Défini explicitement, non négociable | Le monde s'appelle Valdore |
| `DEDUITE` | Dérivée logiquement du canon/systèmes | Ligne de pêche (Lac Muet canonique) |
| `PROPOSEE` | Recommandation technique/créative | Nom de saison, valeur économique |
| `A_VALIDER` | Décision du propriétaire | Nombre exact de cultures, de quêtes |

Le **canon verrouillé** (`CANON/canon_locked.json`) ne contient QUE des éléments
`CANONIQUE`. Tout le reste vit dans les catalogues/rapports, jamais dans le canon.

---

## Contenu dérivé (blueprint minimal, non massif)

La pipeline **ne génère pas massivement** le jeu. Elle calcule un blueprint
minimal, complet et justifié — chaque quantité est **dérivée** des systèmes, de
la boucle principale, des chaînes de production et du canon, puis **expliquée** :

| Type | Quantité | Statut de la quantité |
| --- | --- | --- |
| Saisons | 4 | À_VALIDER (décision ouverte) |
| Lieux | 11 (4 canon + 7 zones/POI déduits) | DEDUITE |
| Cultures | 6 | À_VALIDER |
| Objets | 25 (5 canon + dérivés) | DEDUITE |
| Machines | 4 | PROPOSEE |
| Recettes | 8 | À_VALIDER |
| PNJ | 3 (canon) | À_VALIDER |
| Créatures | 2 | PROPOSEE |
| Quêtes | 4 | À_VALIDER |
| Événements | 4 | PROPOSEE |
| Secrets | 2 | À_VALIDER |
| Maps | 4 (1 par lieu canon) | À_VALIDER |
| Assets | ~100 (8 familles) | dérivés |
| Animations | ~107 (états × directions) | dérivées |

Chaque entité embarque un bloc `derivation` : *pourquoi elle existe, quel système
l'utilise, comment elle est obtenue, qui la consomme, quelles conséquences elle
produit, quels assets/animations elle nécessite, quels tests la couvrent.*

---

## Pour une autre IA : comment générer le jeu

Lisez **`DOC/EXECUTION_PROCEDURE.md`** — la procédure pas-à-pas complète. En résumé :

1. Lisez la documentation (`README.md`, `DOC/`).
2. Exécutez `python3 tools/pipeline.py` pour (re)générer l'état de la pipeline.
3. Choisissez un élément à produire dans `GAME/manifests/`.
4. Générez le prompt contextualisé : `python3 tools/prompt_gen.py --id <entity_id> --task <type>`
   (ou par famille / par séquence animée).
5. Exécutez ce prompt (avec un LLM) et déposez la réponse dans `RESULTS/incoming/`.
6. Importez : `python3 tools/import_results.py --revalidate`.
7. Si rejet : `python3 tools/regenerate.py` produit un prompt de correction ciblée.
8. Répétez. Les sorties valides sont compilées dans `ENGINE_OUT/` (sans LLM runtime).

**Vous n'avez jamais à deviner** : canon, contexte, fonction, relations, style,
dimensions, variantes, animations, placement, validations — tout est injecté dans
chaque prompt. Si une information manque, le prompt retourne `BLOCKED`.

---

## Arborescence

Voir **`DOC/TREE.md`** pour l'arborescence complète et **`DOC/SCRIPTS.md`** pour
le rôle de chaque script. Structure de haut niveau :

```text
Pipeline/
├── README.md                  ← ce fichier (documentation principale)
├── INPUT/                     ← 4 entrées canoniques (brief, canon, contraintes, décisions)
├── CONTRACT/                  ← contrat d'architecture Graph-Driven
├── CANON/                     ← canon central verrouillé + extractions
├── ONTOLOGY/                  ← ontologie (entités, relations, états, effets)
├── SCHEMAS/                   ← 21 schémas JSON (draft-07)
├── GAME/                      ← systèmes, catalogues, graphe, manifests
│   ├── systems/  ├── catalogs/  ├── functional_catalog/  ├── graph/  └── manifests/
├── PROMPTS/                   ← templates, exemples, prompts générés
│   ├── templates/  ├── examples/  └── generated/
├── RESULTS/                   ← import des résultats d'une autre IA
│   ├── incoming/  ├── accepted/  └── rejected/
├── REPORTS/                   ← rapports (validation, maturité, manquants, ...)
├── ENGINE_OUT/                ← sorties compilées pour Godot 4 (sans LLM)
├── DOC/                       ← documentation détaillée
├── OUTPUT/                    ← spécification bootstrap + journal de run
├── tools/                     ← scripts de la pipeline
│   ├── lib/                   ← modules (canon, ontology, catalog, graph, ...)
│   ├── pipeline.py            ← orchestrateur
│   ├── run_tests.py           ← runner de tests
│   ├── import_results.py      ← importateur
│   ├── regenerate.py          ← régénération ciblée
│   ├── prompt_gen.py          ← générateur de prompts (CLI)
│   └── bootstrap_pipeline.py  ← script du bootstrapper d'origine
└── tests/                     ← 120 tests (connectivité, production, simulation, dialogues, ...)
```

---

## Garanties de fin (conditions vérifiées)

La pipeline n'est déclarée terminée que si toutes ces conditions sont remplies
(vérifiées par `tools/run_tests.py` et `tools/pipeline.py --check`) :

- [x] Les quatre fichiers d'entrée ont été lus (UTF-8 valides).
- [x] Le canon central verrouillé est produit.
- [x] Les décisions ouvertes sont listées (21).
- [x] Les contradictions/ambiguïtés sont signalées (5).
- [x] L'ontologie est cohérente (17 types d'entités, 18 relations).
- [x] Les schémas passent leurs tests (21 schémas).
- [x] Le graphe est construit (103 nœuds, ~280 arêtes, 100 % atteignables).
- [x] Les relations sont validées (0 référence pendante).
- [x] Les manifests sont générés (15 manifests).
- [x] Les prompts contextualisés sont générés (injecteur + exemples).
- [x] L'importation fonctionne (valides acceptés).
- [x] Les validateurs fonctionnent (16 familles, 0 erreur).
- [x] Les entités orphelines sont détectées (0 ; détection testée).
- [x] Les assets manquants sont détectés.
- [x] Les animations manquantes sont détectées.
- [x] Les résultats invalides sont rejetés (4/4 fixtures).
- [x] Les corrections ciblées sont documentées (`regenerate.py`).
- [x] Le test minimal de bout en bout réussit (`test_end_to_end.py`).
- [x] Le jeu final n'a pas besoin d'un LLM à l'exécution (`ENGINE_OUT/`, testé).

---

## Documentation

| Document | Contenu |
| --- | --- |
| `DOC/ARCHITECTURE.md` | Architecture complète de la pipeline (livrable 1) |
| `DOC/FORMATS.md` | Documentation des formats de données (livrable 98) |
| `DOC/IO.md` | Entrées/sorties de chaque étape + format d'échange (livrables 50, 51, 99) |
| `DOC/SCRIPTS.md` | Liste des scripts et rôle de chacun (livrables 48, 49) |
| `DOC/TREE.md` | Arborescence finale commentée (livrable 47) |
| `DOC/EXECUTION_PROCEDURE.md` | Procédure complète d'exécution par une autre IA (livrables 52, 100) |
| `DOC/BOOTSTRAPPER_README.md` | README du bootstrapper d'origine |

---

## Licence / provenance

Construit à partir du bootstrapper `PIPELINE_BOOTSTRAPPER_EXEMPLE 2.zip`
(INPUT/, CONTRACT/, tools/bootstrap_pipeline.py, OUTPUT/BOOTSTRAP_SPEC.md). Le
contrat d'architecture universel (`CONTRACT/architecture_contract.md`) n'a **pas
été modifié**. Les quatre fichiers d'entrée ont été **lus intégralement** et
respectés ; aucune invention ne les remplace.
