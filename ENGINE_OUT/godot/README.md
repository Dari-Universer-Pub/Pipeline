# ENGINE_OUT — Sorties compilées pour le moteur (Godot 4)

Ces fichiers sont produits par la **pipeline**, pas par le jeu. Ils constituent
le bundle de données déterministe que le jeu final charge à l'exécution.

## Contenu
- `runtime_data.json` : entités, relations, manifests (canon verrouillé inclus).
- `dialogs_compiled.json` : dialogues essentiels en données conditionnelles.
- `rules_compiled.json` : tables conditions/effets pour un moteur déterministe.
- `save_schema.json` : schéma de sauvegarde, versionnement, migrations.
- `godot/` : amorces minimales de chargement (autoload + project.godot).

## Contrat sans LLM
Le jeu final **ne requiert aucun LLM** à l'exécution. Un LLM éventuel ne peut
jamais modifier : canon, progression, règles, statistiques, sauvegardes,
objets, quêtes majeures, secrets non débloqués.

## Important
La pipeline **ne développe pas le jeu**. Ces amorces montrent uniquement
comment charger les données compilées dans Godot 4. Le développement du jeu
(Vertical Slice, scènes, sprites finaux) est une étape ultérieure, hors du
périmètre de cette pipeline.
