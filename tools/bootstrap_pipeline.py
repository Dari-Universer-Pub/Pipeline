from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'INPUT'
CONTRACT = ROOT / 'CONTRACT'
OUTPUT = ROOT / 'OUTPUT'
OUTPUT.mkdir(exist_ok=True)

def read(name):
    path = INPUT / name
    if not path.exists():
        raise SystemExit(f'MISSING_INPUT: {path}')
    return path.read_text(encoding='utf-8')

brief = read('game_brief.md')
canon = read('canon_initial.md')
constraints = read('constraints.md')
decisions = read('open_decisions.md')
contract = (CONTRACT / 'architecture_contract.md').read_text(encoding='utf-8')

spec = f'''# Spécification initiale de pipeline

Générée le : {datetime.now().isoformat(timespec="seconds")}

Cette sortie est une spécification de fabrication. Elle ne constitue pas le jeu final.

## Statut des entrées

- brief : chargé
- canon : chargé
- contraintes : chargées
- décisions ouvertes : chargées
- contrat architectural : chargé

## Règles de travail

1. Ne jamais inventer silencieusement un élément canonique.
2. Déduire les quantités depuis les systèmes et les chaînes de gameplay.
3. Générer des prompts contextualisés à partir du graphe et des manifests.
4. Refuser les objets, assets, animations et quêtes orphelins.
5. Importer et valider chaque sortie externe.
6. Préparer un jeu fonctionnant sans LLM runtime.

## Modules à construire

- extraction du canon ;
- ontologie ;
- schémas ;
- catalogue fonctionnel ;
- graphe du monde ;
- manifestes ;
- placement de map ;
- assets par familles ;
- animations par états et actions ;
- prompts contextualisés ;
- importateur ;
- validateurs ;
- simulateur de partie ;
- compilateur moteur.

## Canon et contexte

{canon}

## Brief

{brief}

## Contraintes

{constraints}

## Décisions ouvertes

{decisions}

## Contrat architectural

{contract}

## Première étape obligatoire

Produire d’abord l’arborescence, les schémas, l’ontologie, le graphe initial, les manifests et les rapports de décisions. Ne pas générer massivement le contenu final.
'''
(OUTPUT / 'BOOTSTRAP_SPEC.md').write_text(spec, encoding='utf-8')
print(f'CREATED {OUTPUT / "BOOTSTRAP_SPEC.md"}')
