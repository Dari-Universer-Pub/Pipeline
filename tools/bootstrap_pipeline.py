from pathlib import Path
from datetime import datetime
import json
ROOT=Path(__file__).resolve().parents[1]; INPUT=ROOT/'INPUT'; CONTRACT=ROOT/'CONTRACT'; OUTPUT=ROOT/'OUTPUT'; OUTPUT.mkdir(exist_ok=True)
def read(p):
    p=INPUT/p
    if not p.exists(): raise SystemExit(f'MISSING_INPUT: {p}')
    return p.read_text(encoding='utf-8')
files={n:read(n) for n in ['game_brief.md','canon_initial.md','constraints.md','open_decisions.md']}
contract=(CONTRACT/'architecture_contract.md').read_text(encoding='utf-8')
status=[]
for name,text in files.items(): status.append({'file':name,'status':'LOADED','characters':len(text)})
spec=f'''# Bootstrap Specification\n\nGenerated: {datetime.now().isoformat(timespec="seconds")}\n\n## Input status\n\n{json.dumps(status,ensure_ascii=False,indent=2)}\n\n## Mandatory classification\nEvery fact must be classified as CANONICAL, DERIVED, PROPOSED or TO_VALIDATE. Creative unknowns must not be silently invented.\n\n## Required integration proof\nEvery content type must pass import → schema → canon → graph → catalog → compiler → runtime fixture.\n\n## Brief\n{files['game_brief.md']}\n\n## Canon\n{files['canon_initial.md']}\n\n## Constraints\n{files['constraints.md']}\n\n## Open decisions\n{files['open_decisions.md']}\n\n## Architecture contract\n{contract}\n\n## First deliverables\nProduce the architecture, ontology, schemas, canon registry, decision report, graph, catalogs, manifests, prompt templates, importers, validators, traceability matrix and end-to-end fixtures before mass content generation.\n'''
(OUTPUT/'BOOTSTRAP_SPEC.md').write_text(spec,encoding='utf-8')
(OUTPUT/'TRACEABILITY_MATRIX_TEMPLATE.md').write_text('''# Traceability Matrix\n\n| Type | Specified | Schema | Imported | Cataloged | Graph | Compiled | Runtime tested | Status |\n|---|---|---|---|---|---|---|---|---|\n| objects | | | | | | | | |\n| dialogues | | | | | | | | |\n| quests | | | | | | | | |\n| maps | | | | | | | | |\n| assets | | | | | | | | |\n| animations | | | | | | | | |\n''',encoding='utf-8')
print('BOOTSTRAP_OK',OUTPUT/'BOOTSTRAP_SPEC.md')
