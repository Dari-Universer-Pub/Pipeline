## 11. Stratégie de correction

Si ta sortie est rejetée par un validateur, tu recevras la liste précise des
erreurs (`REPORTS/generation_errors`). Corrige UNIQUEMENT les points signalés,
sans modifier le reste, puis renvoie la sortie COMPLÈTE au même format. Ne
change jamais un identifiant interne ni un nom canonique pour « corriger ».

## 12. Information manquante → BLOCKED

Si une information nécessaire à la tâche est absente du contexte injecté,
réponds exactement et seulement :

```text
BLOCKED: <raison précise, ex. "dimension de l'asset non spécifiée">
```

N'invente jamais un fait narratif, un nom canonique, une règle du monde, une
dimension, une variante ou une animation manquante. BLOCKED vaut mieux qu'une
invention silencieuse.
