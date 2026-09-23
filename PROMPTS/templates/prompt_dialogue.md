{{CONTEXT_HEADER}}

## 8. Tâche

Produis un **dialogue contextuel** du PNJ `{{SPEAKER_ID}}` pour le contexte
donné (lieu, heure, météo, événement récent, relation, objectifs). Le dialogue
est compilé en données conditionnelles : il ne doit JAMAIS révéler un fait que
le PNJ ne connaît pas (`forbidden_knowledge`).

Contexte de déclenchement :
{{DIALOGUE_CONTEXT}}

## 9. Format de réponse attendu

```json
{
  "id": "{{ENTITY_ID}}",
  "speaker_id": "{{SPEAKER_ID}}",
  "conditions": [{"type": "<condition>", "params": {...}}],
  "lines": [{"text": "...", "reveals": ["<fait connu du PNJ uniquement>"],
             "choices": [{"text": "...", "effect": {"type": "...", "params": {...}}}]}],
  "priority": <entier>,
  "voice_consistency": "<rappel de la signature de voix>"
}
```

## 10. Validations appliquées à ta sortie

- structurel : `speaker_id`, `conditions`, `lines` présents ;
- canonique : ton et voix conformes au PNJ ;
- narratif/mémoire : chaque `reveals` ∈ `knowledge` du PNJ ; AUCUN `reveals`
  dans `forbidden_knowledge` (secret progressif respecté) ;
- conditions : types de conditions valides (ontologie) ;
- effets : types d'effets valides ; secrets progressifs (pas de révélation prématurée).

{{TASK_FOOTER}}
