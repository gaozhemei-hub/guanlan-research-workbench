"""Explicit local-model acceptance run, separate from offline engineering CI."""
import hashlib
import json
from pathlib import Path
import sys
import time
import statistics

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.retrieval import retrieve_selected


def main():
    raw=(ROOT/'examples/retrieval-acceptance-v1.json').read_bytes()
    fixture=json.loads(raw)
    by_id={s['id']:s['text'] for s in fixture['materials']}
    for q in fixture['questions']:
        for label in q['expected']:
            assert label['quote'] in by_id[label['source']], 'invalid evidence label'
    report={'corpus_sha256':hashlib.sha256(raw).hexdigest(),'disclosure':fixture['disclosure'],
            'top_k':5,'comparison':'End-to-end product modes; character/token chunking differs by mode.',
            'questions':[],'summary':{},'errors':[]}
    for method in ('lexical','vector','reranked'):
        print('Running acceptance:',method,flush=True)
        for question in fixture['questions']:
            started=time.perf_counter()
            try:
                result=retrieve_selected({'method':method,'query':question['query'],'materials':fixture['materials']})
                matched=[any(h['source']==label['source'] and label['quote'] in h['text'] for h in result['hits']) for label in question['expected']]
                exact=all(by_id[h['source']][h['start']:h['end']]==h['text'] for h in result['hits'])
                report['questions'].append({'id':question['id'],'method':method,'evidence_labels':len(matched),
                    'matched':sum(matched),'has_candidates':bool(result['hits']),'exact_offsets':exact,
                    'seconds':time.perf_counter()-started,
                    'retrieved':[{'source':h['source'],'start':h['start'],'end':h['end']} for h in result['hits']],
                    'model_revisions':result.get('model_revisions',{})})
            except Exception as error:
                report['errors'].append({'method':method,'id':question['id'],'error':str(error)})
        rows=[r for r in report['questions'] if r['method']==method]
        positive=[r for r in rows if r['evidence_labels']]
        negative=[r for r in rows if not r['evidence_labels']]
        report['summary'][method]={'executed':len(rows),'planned':len(fixture['questions']),
            'mean_evidence_recall_at_5':statistics.mean(r['matched']/r['evidence_labels'] for r in positive) if positive else None,
            'full_coverage_questions':sum(r['matched']==r['evidence_labels'] for r in positive),
            'answerable_questions':len(positive),'unanswerable_with_candidates':sum(r['has_candidates'] for r in negative),
            'unanswerable_questions':len(negative),'all_offsets_exact':all(r['exact_offsets'] for r in rows) if rows else None,
            'mean_end_to_end_seconds':statistics.mean(r['seconds'] for r in rows) if rows else None}
    folder=ROOT/'data/retrieval-acceptance';folder.mkdir(parents=True,exist_ok=True)
    target=folder/(str(time.time_ns())+'.json')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2));print('Report:',target)
    return 1 if report['errors'] else 0


if __name__=='__main__':sys.exit(main())
