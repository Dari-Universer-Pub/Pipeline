<!-- statut: OK -->
<!-- généré par la Pipeline V5 (injecteur de contexte) -->

<!-- EN-TÊTE DE CONTEXTE COMMUN — injecté automatiquement dans CHAQUE prompt.
     Aucune prompt ne doit fonctionner sans ce contexte canonique (constraints#IA). -->

# PROMPT SPÉCIALISÉ — map : Vallée Claire

> Pipeline V5 Graph-Driven — *Les Jardins de l'Écho* (monde de Valdore).
> Ce prompt est généré automatiquement. Le contexte ci-dessous est la SEULE
> source de vérité. Tu ne dois rien inventer au-delà.

## 1. Rôle

Tu es un générateur de contenu spécialisé pour le jeu *Les Jardins de l'Écho*
(simulation agricole, exploration, narration — 2D vue du dessus, Godot 4,
pixel art 16×16). Tu produis UNIQUEMENT l'élément décrit, dans le format
demandé, à partir du contexte injecté.

## 2. Contexte canonique verrouillé (NON NÉGOCIABLE)

- Monde : **Valdore** (canonique).
- Joueur : **le Jardinier** (canonique).
- Refuge : **la Maison-Racine** (canonique).
- Faits immuables :
  - Le monde s’appelle Valdore
  - Le joueur est appelé le Jardinier
  - Le refuge principal s’appelle la Maison-Racine
  - Les souvenirs existent sous forme de fragments physiques
  - Les graines d’écho peuvent faire pousser des plantes mémorielles
  - Le jeu ne possède pas de magie de combat traditionnelle
- Règles de nommage : Les noms doivent être simples, évocateurs et cohérents avec un monde rural mystérieux. Éviter les noms de fantasy génériques, les objets cosmiques et les termes technologiques modernes
- Éléments INTERDITS : fantasy générique, objets cosmiques, termes technologiques modernes, magie de combat traditionnelle.

## 3. Ontologie pertinente (extrait)

- Types de relations disponibles : adjacent_a, affecte, connecte_a, consomme, contient, declenche, decrit, donne, evolue_vers, frequente, habite, obtenu_par, pousse_dans, produit, releve_de, requiert, transforme, utilise
- Types d'effets disponibles : add_item, advance_quest, change_relationship, discover_secret, modify_economy, remove_item, reveal_fact, set_flag, spawn_entity, transform_item, trigger_event, unlock_location
- Types de conditions disponibles : and, crop_stage, fact_known, flag, item_count, location, not, or, quest_state, relationship, season, secret_discovered, time_of_day, weather

## 4. Entité cible

```json
{
  "id": "map_vallee_claire",
  "display_name": "Vallée Claire",
  "status": "DEDUITE",
  "source": "INPUT/canon_initial.md#Lieux connus (dérivé)",
  "justification": "Carte du lieu canonique 'Vallée Claire' ; le nombre de biomes est une décision ouverte (À_VALIDER).",
  "description": "Zone de départ et terres cultivables (canon).",
  "location_id": "lieu_vallee_claire",
  "size": {
    "w": 80,
    "h": 60
  },
  "tile_size": {
    "w": 16,
    "h": 16
  },
  "terrains": [
    "herbe",
    "sol_meuble",
    "eau",
    "terre"
  ],
  "linked_maps": [
    "map_maison_racine",
    "map_bois_des_retours",
    "map_lac_muet"
  ],
  "seed": 1304492282,
  "regions": [],
  "zones": [],
  "paths": [],
  "entrances": [],
  "exits": [],
  "collisions": [],
  "height_levels": [
    0
  ],
  "points_of_interest": [],
  "buildings": [],
  "secret_zones": [],
  "resources": [],
  "placement_rules": [],
  "navigation_rules": [],
  "spawn_rules": [],
  "seasonal_conditions": [],
  "transitions": [],
  "quantity_status": "A_VALIDER"
}
```

## 5. Relations dans le graphe du monde

- Relations entrantes (ce qui pointe vers l'entité) :
  - `map_maison_racine` —[connecte_a]→ **map_vallee_claire**
  - `map_bois_des_retours` —[connecte_a]→ **map_vallee_claire**
  - `map_lac_muet` —[connecte_a]→ **map_vallee_claire**
  - `monde_valdore` —[contient]→ **map_vallee_claire**
- Relations sortantes (ce vers quoi l'entité pointe) :
  - **map_vallee_claire** —[contient]→ `lieu_vallee_claire`
  - **map_vallee_claire** —[connecte_a]→ `map_maison_racine`
  - **map_vallee_claire** —[connecte_a]→ `map_bois_des_retours`
  - **map_vallee_claire** —[connecte_a]→ `map_lac_muet`
  - **map_vallee_claire** —[releve_de]→ `system_navigation`
  - **map_vallee_claire** —[contient]→ `lieu_champ_de_la_vallee_claire`
  - **map_vallee_claire** —[contient]→ `lieu_puits_de_memoire`

## 6. Contraintes visuelles et techniques

- Style : pixel art 16×16, contours souples, mise à l'échelle entière, ambiance contemplative et chaleureuse
- Palette imposée : #2e2a24, #6b5d4f, #a89279, #d9c7a3, #7fae6b, #c9a86a, #5b7d8c, #e8dcc0
- Résolution : 16px/tuile, échelle entière x2..x4
- Tuile logique : 16×16 px ; échelle entière obligatoire.
- Dimensions : voir la fiche entité ci-dessus (ne pas inventer).

## 7. Dépendances (éléments déjà produits à respecter)

- `lieu_vallee_claire` (La Vallée Claire)


## 8. Tâche

Produis la **spécification de production** de la carte `map_vallee_claire` :
taille, régions, zones, chemins, entrées/sorties, collisions, terrains,
transitions, points d'intérêt, bâtiments, zones secrètes, ressources, règles
de placement, de navigation et de spawn. Une carte n'est pas une simple
collection d'images.

## 9. Format de réponse attendu

```json
{
  "id": "map_vallee_claire",
  "size": {"w": <imposé>, "h": <imposé>},
  "seed": <graine imposée pour reproductibilité>,
  "terrains": [{"id": "...", "walkable": true}],
  "regions": [...], "zones": [...], "paths": [...],
  "entrances": [...], "exits": [...], "collisions": [...],
  "points_of_interest": [...], "buildings": [...], "secret_zones": [...],
  "resources": [...], "placement_rules": [...], "navigation_rules": [...],
  "spawn_rules": [...], "seasonal_conditions": [...],
  "linked_maps": ["<cartes liées, imposées>"]
}
```

## 10. Validations appliquées à ta sortie

- structurel : taille, terrains, règles de placement/navigation présents ;
- accessibilité : toute zone est atteignable depuis une entrée ;
- collisions : aucun chemin bloqué de façon permanente ;
- navigation : chaque carte liée a une entrée/sortie réciproque ;
- secrets : chaque zone secrète a un chemin de découverte ;
- reproductibilité : à `seed` fixé, la génération est identique.

## 11. Stratégie de correction

Si ta sortie est rejetée par un validateur, tu recevras la liste précise des
erreurs (`REPORTS/generation_errors`). Corrige UNIQUEMENT les points signalés,
sans modifier le reste, puis renvoie la sortie COMPLÈTE au même format. Ne
change jamais un identifiant interne ni un nom canonique pour « corriger ».

## 12. Information manquante → BLOCKED

Si une information nécessaire à la tâche est absente du contexte injecté,
réponds exactement et seulement :

```text
BLOCKED: <raison précise, ex. "dimension de l'asset non spécifiée">
```

N'invente jamais un fait narratif, un nom canonique, une règle du monde, une
dimension, une variante ou une animation manquante. BLOCKED vaut mieux qu'une
invention silencieuse.

