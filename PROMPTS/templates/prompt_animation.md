{{CONTEXT_HEADER}}

## 8. Tâche

Produis la **spécification de production** de l'animation `{{ENTITY_ID}}`
(action `{{ACTION}}`, direction `{{DIRECTION}}`). L'animation doit être
synchronisée avec la logique de gameplay (frame d'impact, effet déclenché).

## 9. Format de réponse attendu

```json
{
  "id": "{{ENTITY_ID}}",
  "entity_id": "<entité propriétaire, imposée>",
  "state_or_action": "{{ACTION}}",
  "direction": "{{DIRECTION}}",
  "frames": <nombre imposé>,
  "fps": <fréquence imposée>,
  "loop": <true/false imposé>,
  "impact_event": "<frame d'impact ou null>",
  "logic_effect": "<effet logique déclenché ou null>",
  "transitions": ["<transitions possibles>"],
  "required_assets": ["<assets requis, déjà présents>"],
  "frame_descriptions": ["<description de chaque frame>"]
}
```

## 10. Validations appliquées à ta sortie

- structurel : `frames` ≥ 1, `fps` ≥ 1 ;
- références : `entity_id` et `required_assets` existent ;
- synchronisation : si `impact_event` présent, `logic_effect` cohérent ;
- complétude : une animation existe pour chaque (action, direction) requise ;
- anti-orphelin : aucune animation sans action/état correspondant.

{{TASK_FOOTER}}
