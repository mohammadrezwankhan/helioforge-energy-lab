"""Generate browser catalogue and example from the packaged canonical data."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/api'))
from helioforge.hybrid import catalog,HybridRequest,applicability
from helioforge.engines.hybrid import simulate_hybrid
c=catalog()
r=simulate_hybrid(HybridRequest(**c['systems'][0]['preset']))
text=lambda x:json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False)
(ROOT/'apps/web/src/hybrid-data.ts').write_text('namespace HF {\n export const HYBRID_CATALOG:HybridCatalogue = '+text(c)+';\n export const HYBRID_EXAMPLE:HybridResult = '+text(r)+';\n}\n',encoding='utf-8')
(ROOT/'examples/hybrid-default.json').write_text(json.dumps(c['systems'][0]['preset'],indent=2)+'\n')
(ROOT/'examples/hybrid-catalog.json').write_text(json.dumps(c,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(f'Generated {len(c["systems"])} architectures, {len(c["scenarios"])} scenarios and {len(c["lessons"])} lessons.')

# Capability matrix is derived from the same Python applicability function.
matrix=[]
for system in c['systems']:
    for scenario in c['scenarios']:
        mode=('inapplicable' if not applicability(system,scenario) else
              'runnable' if system['mode']==scenario['mode']=='screening' else 'study')
        matrix.append({'system_id':system['id'],'scenario_id':scenario['id'],'capability':mode})
(ROOT/'examples/hybrid-matrix.json').write_text(json.dumps({'catalogue_version':c['version'],'matrix':matrix},indent=2)+'\n')
