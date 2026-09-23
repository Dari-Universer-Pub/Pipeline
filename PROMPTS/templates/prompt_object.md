{{CONTEXT_HEADER}}

## 8. Tâche

Produis la **fiche de production complète** de l'objet `{{ENTITY_ID}}`, ainsi
que la spécification de son icône d'inventaire. Respecte strictement la
catégorie, la fonction et le verbe de gameplay indiqués dans le contexte.

## 9. Format de réponse attendu

Réponds avec UN objet JSON conforme au schéma `SCHEMAS/objet.schema.json`,
dans un bloc de code ```json :

```json
{
  "id": "{{ENTITY_ID}}",
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

{{TASK_FOOTER}}
