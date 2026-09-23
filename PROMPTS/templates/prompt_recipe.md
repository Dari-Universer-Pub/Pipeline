{{CONTEXT_HEADER}}

## 8. Tâche

Produis la **fiche de production** de la recette `{{ENTITY_ID}}` : station,
entrées (ingrédients + quantités), sorties (résultats + quantités), durée,
condition de déblocage. Une recette doit avoir des ingrédients ET un résultat.

## 9. Format de réponse attendu

```json
{
  "id": "{{ENTITY_ID}}",
  "display_name": "<nom>",
  "station_id": "<machine existante>",
  "inputs": [{"item_id": "<objet/ressource existant>", "qty": <n>}],
  "outputs": [{"item_id": "<objet existant>", "qty": <n>}],
  "duration": <nombre>,
  "unlocked_by": "<quête/événement ou null>",
  "animation_id": "<animation de la station>",
  "effect_id": "<effet visuel/logique>"
}
```

## 10. Validations appliquées à ta sortie

- structurel : `inputs` et `outputs` non vides ;
- références : `station_id`, tous les `item_id` existent ;
- logique : chaîne de production complète (entrée → station → sortie) ;
- économique : valeur des sorties ≥ valeur des entrées (sauf exception justifiée) ;
- anti-orphelin : la recette est reachable et a un consommateur.

{{TASK_FOOTER}}
