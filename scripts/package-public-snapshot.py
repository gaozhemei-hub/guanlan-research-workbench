"""Bundle a small, clearly dated public preview. Never copy model config or user data."""
import json
from pathlib import Path
from datetime import datetime,timezone
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
from providers import AK_SOURCES
raw=json.loads((ROOT/'data'/'public-cache.json').read_text())
sources={}
for sid,value in raw.get('sources',{}).items():
    s={k:v for k,v in value.items() if k not in ('points','items','reports')}
    if value.get('reports'):s['reports']=value['reports'][:8]
    if value.get('points'):s['points']=value['points'][-40:]
    if value.get('items'):
        s['items']=value['items'][:12]
        s['previewCount']=len(s['items']);s['cachedCount']=len(value['items'])
    sources[sid]=s
catalog=[{k:v for k,v in s.items() if k not in ('points','items','reports','fields','error','checkedAt','status','fetchedAt','publishedAt','previewCount','cachedCount')} for s in sources.values()]
snapshot={'sources':sources,'catalog':catalog,'checkedAt':raw.get('checkedAt'),'snapshotAt':datetime.now(timezone.utc).isoformat(),'ai':{'configured':False},'snapshot':True}
encoded=json.dumps(snapshot,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
(ROOT/'prototype'/'dist'/'public-snapshot.js').write_text('// Dated public-data preview only; no private records or keys.\nconst PUBLIC_SNAPSHOT = '+encoded+';\n')
print('Packaged dated preview:',len(sources),'sources; max 40 observations / 12 headlines per source')
