# Documentation des formats de données

*Livrable 98 — Documentation des formats.*

Tous les artefacts de la pipeline sont en **JSON UTF-8** (sans BOM), produits de
façon déterministe. Ce document décrit les formats.

---

## 1. Enveloppe versionnée

Tout artefact JSON produit par la pipeline est enveloppé :

```json
{
  "pipeline_version": "5.0.0",
  "schema_version": "5.0.0",
  "kind": "objects",
  "generated_deterministic": true,
  "seed": 20260922,
  "payload": { "...": "contenu réel" }
}
```

- `kind` identifie la nature du payload (`canon_locked`, `ontology`, `objects`,
  `world_graph`, `manifest_assets`, `validation_report`, ...).
- `seed` n'est présent que pour les artefacts procéduraux (maps).
- Les modules lisent le payload via `common.unwrap()` (tolère aussi le brut).

---

## 2. Statuts (champ `status`)

Toute entité porte un `status` parmi :

| Valeur | Sens |
| --- | --- |
| `CANONIQUE` | Défini explicitement dans `INPUT/canon_initial.md`, non négociable. |
| `DEDUITE` | Dérivée logiquement du canon ou des systèmes. |
| `PROPOSEE` | Recommandation technique ou créative de la pipeline. |
| `A_VALIDER` | Décision qui dépend du propriétaire (jamais verrouillée en canon). |

---

## 3. Identifiants et noms

- **ID interne** (`id`) : stable, unique, minuscules, sans espaces, sans accents,
  caractères `[a-z0-9_]`, préfixé par la catégorie. Exemple :
  `objet_arrosoir_de_cuivre`, `pnj_alba`, `map_vallee_claire`,
  `asset_tileset_herbe`, `anim_joueur_jardinier_marche_down`.
- **Nom affiché** (`display_name`) : accents et langue du jeu autorisés.
  Exemple : `Arrosoir de cuivre`, `La Vallée Claire`.
- Règle : `slugify()` retire les accents, remplace espaces/tirets/apostrophes par
  `_`, met en minuscules, et préfixe un `x_` si l'ID commence par un chiffre.

---

## 4. Bloc `derivation` (justification obligatoire)

Chaque entité dérivée embarque :

```json
"derivation": {
  "why": "pourquoi l'élément existe",
  "system": "quel(s) système(s) l'utilise(nt)",
  "obtention": "comment il est obtenu",
  "consumers": "quelles entités le consomment",
  "consequences": "quelles conséquences il produit",
  "assets": "quels assets sont nécessaires",
  "animations": "quelles animations sont nécessaires",
  "tests": "quels tests le couvrent"
}
```

---

## 5. Format des entités

Les champs exacts par type sont définis dans `SCHEMAS/<type>.schema.json`
(dérivés de `ONTOLOGY/ontology.json`). Points clés :

### Objet (`objet.schema.json`)
`id`, `display_name`, `status`, `category` (outil/graine/ressource/produit/
fragment/consommable/artisanat/cle/decoratif/quotidien), `function`,
`gameplay_verb`, `obtention[]`, `loop_stage`, `users[]`, `transforms_into[]`,
`base_value`, `decorative_only`, `derivation`.

### Culture (`culture.schema.json`)
`id`, `display_name`, `status`, `seed_id`, `yield_id`, `seasons[]`,
`growth_days`, `stages[]`, `water_needed`, `memory_plant`, `regrows`.

### Recette (`recette.schema.json`)
`id`, `display_name`, `status`, `station_id`, `inputs[{item_id, qty}]`,
`outputs[{item_id, qty}]`, `duration`, `unlocked_by`, `kind`.

### Quête (`quete.schema.json`)
`id`, `display_name`, `status`, `giver_id`, `trigger{type, params}`,
`preconditions[]`, `participants[]`, `location_id`, `steps[]`, `choices[]`,
`effects[]`, `consequences[]`, `fallback`, `failure_conditions[]`, `missable`,
`discovery`.

### Événement (`evenement.schema.json`)
`id`, `display_name`, `status`, `trigger`, `preconditions[]`, `participants[]`,
`location_id`, `timing`, `effects[]`, `missable`, `repeatable`.

### PNJ (`pnj.schema.json`)
`id`, `display_name`, `status`, `function`, `goals[]`, `needs[]`, `beliefs[]`,
`knowledge[]`, `forbidden_knowledge[]`, `emotions[]`, `routines[]`,
`frequented_places[]`, `voice`, `home`, `roles[]`.

### Asset (`asset.schema.json`)
`id`, `display_name`, `status`, `entity_id` (propriétaire, jamais isolé),
`family`, `kind` (sprite/tileset/tile/transition/objet/portrait/particule/ui/
icone), `width`, `height`, `resolution`, `style`, `palette[]`, `variants[]`,
`usage_rules[]`, `fingerprint` (empreinte unique), `validation{}`.

### Animation (`animation.schema.json`)
`id`, `entity_id`, `state_or_action`, `direction` (down/up/left/right/null),
`frames`, `fps`, `loop`, `impact_event`, `logic_effect`, `transitions[]`,
`required_assets[]`.

### Map (`map.schema.json`)
`id`, `display_name`, `status`, `size{w,h}`, `tile_size`, `terrains[]` (noms),
`regions[]`, `zones[]`, `paths[]`, `entrances[]`, `exits[]`, `collisions[]`,
`height_levels[]`, `transitions[]`, `points_of_interest[]`, `buildings[]`,
`secret_zones[]`, `resources[]`, `placement_rules[]`, `navigation_rules[]`,
`spawn_rules[]`, `seasonal_conditions[]`, `linked_maps[]`, `seed`.

---

## 6. Relations (`relation.schema.json`)

```json
{
  "id": "produit:culture_navet_de_la_vallee->objet_navet",
  "type": "produit",
  "source": "culture_navet_de_la_vallee",
  "target": "objet_navet",
  "status": "DEDUITE",
  "implies_usage": true
}
```

`type` ∈ 18 relations de l'ontologie. `implies_usage` distingue usage réel et
relation technique.

---

## 7. Conditions (`condition.schema.json`)

```json
{ "type": "item_count", "params": { "item_id": "objet_navet", "op": ">=", "qty": 2 } }
```

Types : `flag`, `item_count`, `relationship`, `season`, `weather`,
`time_of_day`, `location`, `quest_state`, `fact_known`, `secret_discovered`,
`crop_stage`, `and`, `or`, `not`. Opérateurs : `< <= == >= > !=`.

---

## 8. Effets (`effect.schema.json`)

```json
{ "type": "add_item", "params": { "item_id": "objet_fragment_de_souvenir", "qty": 1 } }
```

Types : `add_item`, `remove_item`, `set_flag`, `change_relationship`,
`unlock_location`, `trigger_event`, `advance_quest`, `reveal_fact`,
`discover_secret`, `spawn_entity`, `transform_item`, `modify_economy`.
Chaque effet est **déterministe** et exécutable sans LLM (voir `simulator.py`).

---

## 9. État du monde (`world_state.schema.json`)

```json
{
  "time":    { "day": 1, "hour": 6, "season": "saison_des_epis", "weather": "pluie" },
  "player":  { "location": "lieu_vallee_claire", "inventory": {"objet_navet": 2},
               "money": 50, "relationships": {"pnj_alba": 10},
               "flags": {}, "unlocked_locations": [], "known_facts": [] },
  "world":   { "discovered_secrets": [], "active_quests": [], "completed_quests": [],
               "crops": {}, "global_flags": {} }
}
```

C'est le format des **sauvegardes** (voir `ENGINE_OUT/save_schema.json`).

---

## 10. Manifests

Un manifest est une **spécification de production**, pas le contenu produit.
Chaque entrée de manifest de contenu reprend l'entité du catalogue + champs de
production :

```json
{
  "id": "objet_navet", "display_name": "Navet", "...": "...",
  "required_assets": ["asset_icone_objet_navet"],
  "required_animations": [],
  "validation": { "structure": "...", "references": "...", "no_orphan": "..." }
}
```

Les manifests `assets`, `animations`, `maps`, `placement`, `navigation`,
`transitions`, `effects` ont leurs structures propres (voir schémas + exemples
dans `GAME/manifests/`).

---

## 11. Prompts

Un prompt généré est un **markdown** composé de :
1. en-tête de contexte commun (`_context_header.md`) : rôle, contexte canonique
   verrouillé, ontologie pertinente, entité cible, relations entrantes/sortantes,
   contraintes visuelles, dépendances ;
2. section tâche spécifique au type (`prompt_<type>.md`) : tâche, format de
   réponse attendu (JSON), validations appliquées ;
3. pied commun (`_task_footer.md`) : stratégie de correction + comportement
   **BLOCKED** si information manquante.

Réponse attendue de l'autre IA : un objet JSON dans un bloc ```json, conforme au
schéma, ou exactement `BLOCKED: <raison>`.

---

## 12. Rapports

Les rapports sont en **markdown** (lisibles) + **JSON** (exploitables) :
`validation_report.md`/`validation.json`, `maturity_report.md`,
`missing_report.md`, `isolated_report.md`, `open_decisions_report.md`,
`decision_report.md`, `contradiction_report.md`, `generation_errors.md`/`.json`,
`simulation.json`, `reports.json`.

Une `Issue` de validation a le format :
```json
{ "severity": "ERROR|WARNING|INFO", "code": "canon.forbidden_term",
  "entity": "objet_x", "message": "...", "fix": "..." }
```
