{{CONTEXT_HEADER}}

## 8. Tâche

Produis **toute la famille visuelle** `{{FAMILY}}` de manière cohérente. Les
éléments d'une même famille sont visuellement interdépendants : ils doivent
partager dimensions, palette, style, échelle et logique de variantes. Ne
produis PAS les éléments un par un de façon indépendante.

Membres de la famille (imposés par le contexte) :
{{FAMILY_MEMBERS}}

## 9. Format de réponse attendu

```json
{
  "family": "{{FAMILY}}",
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

{{TASK_FOOTER}}
