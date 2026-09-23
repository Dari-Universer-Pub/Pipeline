{{CONTEXT_HEADER}}

## 8. Tâche

Produis la **spécification de production** de l'asset `{{ENTITY_ID}}`
(famille `{{FAMILY}}`). L'asset doit être visuellement cohérent avec sa
famille et avec les assets déjà produits (mêmes dimensions, palette, style).

## 9. Format de réponse attendu

```json
{
  "id": "{{ENTITY_ID}}",
  "family": "{{FAMILY}}",
  "kind": "<imposé par le contexte>",
  "width": <largeur imposée>, "height": <hauteur imposée>,
  "palette": ["<codes hex issus de PALETTE>"],
  "variants": ["<variantes imposées>"],
  "directions": ["<down/up/left/right si applicable>"],
  "description_visuelle": "<description pixel art précise>",
  "usage_rules": ["<règles d'utilisation du contexte>"],
  "prompt_image": "<prompt textuel pour un modèle d'image, incluant style+palette+dimensions>"
}
```

## 10. Validations appliquées à ta sortie

- structurel : dimensions > 0, `family`/`kind` conformes ;
- références : `entity_id` existe ; l'asset n'est jamais isolé ;
- cohérence de famille : palette et style identiques aux autres assets de la famille ;
- empreinte unique : `fingerprint` différent de tout asset existant (pas de doublon) ;
- variants/directions : tous ceux exigés par le contexte sont présents.

{{TASK_FOOTER}}
