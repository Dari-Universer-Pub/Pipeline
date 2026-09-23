{{CONTEXT_HEADER}}

## 8. Tâche

Produis la **fiche de production** du PNJ `{{ENTITY_ID}}` : identité, fonction,
objectifs, besoins, croyances, connaissances LIMITÉES, relations, émotions,
routines, lieux fréquentés, horaires, voix. Respecte strictement la frontière
entre `knowledge` (ce qu'il sait) et `forbidden_knowledge` (ce qu'il ignore/tait).

## 9. Format de réponse attendu

```json
{
  "id": "{{ENTITY_ID}}",
  "display_name": "<nom canonique>",
  "function": "<imposé>",
  "goals": [...], "needs": [...], "beliefs": [...],
  "knowledge": ["<faits/entités connus, déjà dans le graphe>"],
  "forbidden_knowledge": ["<ce qu'il ne sait pas>"],
  "emotions": [...],
  "routines": [{"hour": <0-23>, "location_id": "<lieu existant>", "activity": "..."}],
  "frequented_places": ["<lieux existants>"],
  "voice": "<signature de voix>",
  "spritesheet_asset": "<asset_id du contexte>",
  "portrait_asset": "<asset_id du contexte>"
}
```

## 10. Validations appliquées à ta sortie

- structurel : champs obligatoires, ID inchangé ;
- canonique : nom et fonction conformes au canon ;
- narratif : voix distincte, motivations cohérentes ;
- mémoire : `knowledge` ⊆ faits/entités du graphe ; aucun chevauchement avec
  `forbidden_knowledge` ;
- routines : chaque `location_id` existe ; au moins une routine (anti-orphelin) ;
- assets : spritesheet et portrait référencés existent.

{{TASK_FOOTER}}
