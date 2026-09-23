{{CONTEXT_HEADER}}

## 8. Tâche

Produis la **fiche de production** de la quête `{{ENTITY_ID}}`. Principe :
**Simulation avant narration** — la quête ne doit produire aucune conséquence
que le moteur ne sait pas simuler (effets limités à l'ontologie des effets).

## 9. Format de réponse attendu

```json
{
  "id": "{{ENTITY_ID}}",
  "display_name": "<nom>",
  "giver_id": "<donneur existant>",
  "trigger": {"type": "<déclencheur valide>", "params": {...}},
  "preconditions": [{"type": "...", "params": {...}}],
  "participants": ["<PNJ existants>"],
  "location_id": "<lieu existant>",
  "steps": [{"id": "step_1", "objective": "...", "effects": [...]}],
  "choices": [{"text": "...", "effects": [...]}],
  "effects": [{"type": "<effet valide>", "params": {...}}],
  "consequences": ["<conséquences durables simulables>"],
  "fallback": "<solution de repli si bloqueur>",
  "failure_conditions": [...],
  "missable": <true/false>,
  "discovery": "<méthode de découverte>"
}
```

## 10. Validations appliquées à ta sortie

- structurel : `trigger` et `effects` présents ;
- références : `giver_id`, `location_id`, `participants` existent ;
- logique : conditions atteignables, effets valides, pas de boucle impossible ;
- atteignabilité : la quête est déclenchable depuis l'état initial ;
- conséquence : au moins un effet durable (pas de quête sans conséquence) ;
- simulation : chaque effet existe dans l'ontologie des effets.

{{TASK_FOOTER}}
