<!-- statut: OK -->
<!-- généré par la Pipeline V5 (injecteur de contexte) -->

<!-- EN-TÊTE DE CONTEXTE COMMUN — injecté automatiquement dans CHAQUE prompt.
     Aucune prompt ne doit fonctionner sans ce contexte canonique (constraints#IA). -->

# PROMPT SPÉCIALISÉ — objet : Graine d’Écho

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
  "base_value": null,
  "category": "graine",
  "decorative_only": false,
  "display_name": "Graine d’Écho",
  "function": "Graine mémorielle canonique ; fait pousser la Floraison d'Écho.",
  "gameplay_verb": "planter",
  "id": "objet_graine_d_echo",
  "justification": "Graine mémorielle canonique ; fait pousser la Floraison d'Écho.",
  "loop_stage": 1,
  "obtention": [
    "canon"
  ],
  "source": "INPUT/canon_initial.md#Objets canoniques",
  "stackable": true,
  "status": "CANONIQUE",
  "transforms_into": [],
  "users": [
    "system_memoire",
    "system_agriculture"
  ]
}
```

## 5. Relations dans le graphe du monde

- Relations entrantes (ce qui pointe vers l'entité) :
  - `culture_floraison_d_echo` —[consomme]→ **objet_graine_d_echo**
  - `system_memoire` —[utilise]→ **objet_graine_d_echo**
  - `system_agriculture` —[utilise]→ **objet_graine_d_echo**
  - `fait_graines_echo` —[decrit]→ **objet_graine_d_echo**
- Relations sortantes (ce vers quoi l'entité pointe) :
  - (aucune)

## 6. Contraintes visuelles et techniques

- Style : pixel art 16×16, contours souples, mise à l'échelle entière, ambiance contemplative et chaleureuse
- Palette imposée : #2e2a24, #6b5d4f, #a89279, #d9c7a3, #7fae6b, #c9a86a, #5b7d8c, #e8dcc0
- Résolution : 16px/tuile, échelle entière x2..x4
- Tuile logique : 16×16 px ; échelle entière obligatoire.
- Dimensions : voir la fiche entité ci-dessus (ne pas inventer).

## 7. Dépendances (éléments déjà produits à respecter)

- (aucune dépendance identifiée)


## 8. Tâche

Produis la **fiche de production complète** de l'objet `objet_graine_d_echo`, ainsi
que la spécification de son icône d'inventaire. Respecte strictement la
catégorie, la fonction et le verbe de gameplay indiqués dans le contexte.

## 9. Format de réponse attendu

Réponds avec UN objet JSON conforme au schéma `SCHEMAS/objet.schema.json`,
dans un bloc de code ```json :

```json
{
  "id": "objet_graine_d_echo",
  "display_name": "<nom affiché, accents autorisés, cohérent avec le canon>",
  "category": "<catégorie imposée par le contexte>",
  "function": "<fonction>",
  "gameplay_verb": "<verbe>",
  "obtention": ["<moyens déjà présents dans le graphe>"],
  "users": ["<entités qui le consomment, déjà présentes dans le graphe>"],
  "base_value": <nombre ou null>,
  "asset": {
    "id": "<asset_id du contexte>",
    "width": 16, "height": 16,
    "palette": ["<codes hex issus de PALETTE>"],
    "description_visuelle": "<description pixel art 16×16>",
    "variants": ["<variantes imposées par le contexte>"]
  }
}
```

## 10. Validations appliquées à ta sortie

- structurel : champs obligatoires, types, ID interne inchangé ;
- canonique : nom cohérent, aucun terme interdit (fantasy générique, cosmique,
  tech moderne), distinction canon/proposition respectée ;
- références : `obtention`, `users`, `asset.id` existent déjà dans le graphe ;
- logique : l'objet a au moins un usage réel (pas d'objet orphelin) ;
- économique : `base_value` cohérent avec la catégorie et la boucle.

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

