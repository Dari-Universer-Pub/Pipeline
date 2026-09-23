{{CONTEXT_HEADER}}

## 8. Tâche

Produis la **spécification de production** de la carte `{{ENTITY_ID}}` :
taille, régions, zones, chemins, entrées/sorties, collisions, terrains,
transitions, points d'intérêt, bâtiments, zones secrètes, ressources, règles
de placement, de navigation et de spawn. Une carte n'est pas une simple
collection d'images.

## 9. Format de réponse attendu

```json
{
  "id": "{{ENTITY_ID}}",
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

{{TASK_FOOTER}}
