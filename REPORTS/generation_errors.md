# Rapport des erreurs de génération (import)

- Total : 7
- Acceptés : 2
- Rejetés : 4
- Bloqués (BLOCKED) : 1

## asset_orphan.json — REJECTED
- [ERROR] import.unresolved_ref @ asset_icone_objet_inexistant : référence 'entity_id' -> 'objet_totalement_inexistant' inexistante

## blocked_response.md — BLOCKED
- Raison : dimension de l'asset non spécifiée dans le contexte (width/height absents du manifest).

## broken.json — REJECTED
- [ERROR] import.parse @ broken.json : JSON illisible: Expecting property name enclosed in double quotes: line 1 column 55 (char 54)

## forbidden_name.json — REJECTED
- [ERROR] import.forbidden_term @ objet_epee_cosmique : terme interdit 'épée' dans le nom
- [ERROR] import.forbidden_term @ objet_epee_cosmique : terme interdit 'cosmique' dans le nom
- [ERROR] import.forbidden_term @ objet_epee_cosmique : terme interdit 'laser' dans le nom

## recipe_no_output.json — REJECTED
- [ERROR] import.recipe_no_output @ recette_transformation_cassee : recette sans résultat
