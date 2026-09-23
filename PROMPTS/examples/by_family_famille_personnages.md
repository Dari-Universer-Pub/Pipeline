<!-- statut: OK -->
<!-- généré par la Pipeline V5 (injecteur de contexte) -->

<!-- EN-TÊTE DE CONTEXTE COMMUN — injecté automatiquement dans CHAQUE prompt.
     Aucune prompt ne doit fonctionner sans ce contexte canonique (constraints#IA). -->

# PROMPT SPÉCIALISÉ — famille : famille_personnages

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

- Type d'entité `asset` : champs requis = id, display_name, status, entity_id, family, kind, width, height.
- Types de relations disponibles : adjacent_a, affecte, connecte_a, consomme, contient, declenche, decrit, donne, evolue_vers, frequente, habite, obtenu_par, pousse_dans, produit, releve_de, requiert, transforme, utilise
- Types d'effets disponibles : add_item, advance_quest, change_relationship, discover_secret, modify_economy, remove_item, reveal_fact, set_flag, spawn_entity, transform_item, trigger_event, unlock_location
- Types de conditions disponibles : and, crop_stage, fact_known, flag, item_count, location, not, or, quest_state, relationship, season, secret_discovered, time_of_day, weather

## 4. Entité cible

Famille `famille_personnages` — 7 membres interdépendants.

## 5. Relations dans le graphe du monde

- Relations entrantes (ce qui pointe vers l'entité) :
  - (famille transverse)
- Relations sortantes (ce vers quoi l'entité pointe) :
  - (famille transverse)

## 6. Contraintes visuelles et techniques

- Style : pixel art 16×16, contours souples, mise à l'échelle entière, ambiance contemplative et chaleureuse
- Palette imposée : #2e2a24, #6b5d4f, #a89279, #d9c7a3, #7fae6b, #c9a86a, #5b7d8c, #e8dcc0
- Résolution : 16px/tuile, échelle entière x2..x4
- Tuile logique : 16×16 px ; échelle entière obligatoire.
- Dimensions : voir la fiche entité ci-dessus (ne pas inventer).

## 7. Dépendances (éléments déjà produits à respecter)

- Tous les membres doivent partager palette/style/échelle.


## 8. Tâche

Produis **toute la famille visuelle** `famille_personnages` de manière cohérente. Les
éléments d'une même famille sont visuellement interdépendants : ils doivent
partager dimensions, palette, style, échelle et logique de variantes. Ne
produis PAS les éléments un par un de façon indépendante.

Membres de la famille (imposés par le contexte) :
- `asset_spritesheet_jardinier` (Spritesheet du Jardinier) — 64×128, variantes ['idle_down', 'idle_up', 'idle_left', 'idle_right', 'marche_down', 'marche_up', 'marche_left', 'marche_right', 'labourer_down', 'labourer_up', 'labourer_left', 'labourer_right', 'arroser_down', 'arroser_up', 'arroser_left', 'arroser_right', 'planter_down', 'planter_up', 'planter_left', 'planter_right', 'recolter_down', 'recolter_up', 'recolter_left', 'recolter_right', 'pecher_down', 'pecher_up', 'pecher_left', 'pecher_right', 'fabriquer_None', 'cuisiner_None', 'parler_None', 'offrir_None']
- `asset_spritesheet_pnj_alba` (Spritesheet Alba) — 64×96, variantes ['idle_down', 'idle_up', 'idle_left', 'idle_right', 'marche_down', 'marche_up', 'marche_left', 'marche_right', 'interaction_None']
- `asset_portrait_pnj_alba` (Portrait Alba) — 64×64, variantes ['neutre', 'content', 'inquiet']
- `asset_spritesheet_pnj_marin` (Spritesheet Marin) — 64×96, variantes ['idle_down', 'idle_up', 'idle_left', 'idle_right', 'marche_down', 'marche_up', 'marche_left', 'marche_right', 'interaction_None']
- `asset_portrait_pnj_marin` (Portrait Marin) — 64×64, variantes ['neutre', 'content', 'inquiet']
- `asset_spritesheet_pnj_nox` (Spritesheet Nox) — 64×96, variantes ['idle_down', 'idle_up', 'idle_left', 'idle_right', 'marche_down', 'marche_up', 'marche_left', 'marche_right', 'interaction_None']
- `asset_portrait_pnj_nox` (Portrait Nox) — 64×64, variantes ['neutre', 'content', 'inquiet']

## 9. Format de réponse attendu

```json
{
  "family": "famille_personnages",
  "shared": {
    "palette": ["<codes hex communs>"],
    "style": "<style commun>",
    "tile_size": {"w": 16, "h": 16},
    "scale": "<échelle entière>"
  },
  "members": [
    {"id": "<asset_id>", "variants": ["..."], "description_visuelle": "...",
     "prompt_image": "..."}
  ]
}
```

## 10. Validations appliquées à ta sortie

- structurel : tous les membres listés dans le contexte sont présents ;
- cohérence : `shared.palette`/`style` identiques pour tous les membres ;
- références : chaque `id` de membre existe dans le manifest des assets ;
- transitions : pour une famille de terrains, chaque paire adjacente a sa transition ;
- anti-doublon : empreintes uniques par membre.

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

