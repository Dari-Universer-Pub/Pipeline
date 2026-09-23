# Rapport des contradictions et ambiguïtés

Détection des tensions entre canon, brief, contraintes et décisions ouvertes. Chaque finding propose un statut et une action.

## AMBIGUITE (3)

| Sujet | Description | Statut recommandé | Action |
| --- | --- | --- | --- |
| saison | Le système 'saisons' est implicite dans le brief, mais le NOMBRE de saisons est une décision ouverte. Le système est acquis, la quantité reste à valider. | A_VALIDER | Générer les saisons avec un défaut modulaire (4) marqué À_VALIDER ; ne pas verrouiller la quantité. |
| peche | Le Lac Muet est canoniquement une 'zone de pêche', mais l'IMPORTANCE de la pêche est une décision ouverte. L'existence est déduite du canon, la profondeur reste à valider. | DEDUITE | Pêche présente comme système mineur (DEDUITE) ; son ampleur est À_VALIDER. |
| combat | Le canon interdit la 'magie de combat traditionnelle', mais open_decisions demande la 'présence ou non d'un système de combat'. Absence de magie de combat != absence de tout système de combat : ambiguïté à trancher. | A_VALIDER | Défaut technique : aucun système de combat (cohérent avec le ton contemplatif) ; décision finale À_VALIDER. |

## MANQUE (2)

| Sujet | Description | Statut recommandé | Action |
| --- | --- | --- | --- |
| monnaie | Le système 'économie simple' est souhaité mais aucune monnaie n'est définie dans le canon. Nécessaire pour les validateurs économiques. | A_VALIDER | Proposer une monnaie (nom + unité) marquée À_VALIDER ; bloquer seulement la validation économique tant que non tranchée. |
| meteo | Le système 'météo' est souhaité mais aucun état météo n'est défini dans le canon. À déduire des saisons. | DEDUITE | Déduire un ensemble météo minimal par saison (DEDUITE) ; noms À_VALIDER. |
