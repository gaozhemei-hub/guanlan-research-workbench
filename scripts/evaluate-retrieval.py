"""Frozen synthetic baseline; no model, network, private data or answer generation."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.retrieval import Index


def main():
    path = ROOT / 'examples/retrieval-benchmark.json'
    raw = path.read_bytes()
    fixture = json.loads(raw)
    index = Index()
    results = []
    try:
        for source in fixture['sources']:
            index.replace('teaching', source['id'], fixture['version'], source['text'])
        for question in fixture['questions']:
            start = time.perf_counter()
            hits = index.search('teaching', question['query'], limit=3)
            elapsed = (time.perf_counter()-start)*1000
            retrieved = list(dict.fromkeys(hit['source'] for hit in hits))
            expected = set(question['expected'])
            rank = next((i for i, source in enumerate(retrieved, 1) if source in expected), None)
            results.append(dict(id=question['id'], split=question['split'], expected=sorted(expected),
                                retrieved=retrieved, recall_at_3=len(expected.intersection(retrieved))/len(expected) if expected else None,
                                reciprocal_rank=1/rank if rank else 0, latency_ms=round(elapsed, 3),
                                current_quotes_valid=all(index.citation_valid('teaching', hit['chunk_id'], hit['text']) for hit in hits)))
    finally:
        index.close()
    summary = {}
    for split in ('dev', 'evaluation'):
        rows = [r for r in results if r['split'] == split]
        positive = [r for r in rows if r['expected']]
        negative = [r for r in rows if not r['expected']]
        summary[split] = dict(answerable_questions=len(positive),
            mean_source_recall_at_3=sum(r['recall_at_3'] for r in positive)/len(positive),
            mrr_at_3=sum(r['reciprocal_rank'] for r in positive)/len(positive),
            unanswerable_questions=len(negative),
            unanswerable_with_candidates=sum(bool(r['retrieved']) for r in negative))
    report = dict(corpus_sha256=hashlib.sha256(raw).hexdigest(), method='lexical-bm25-han-bigram-v1',
                  disclosure=fixture['disclosure'], summary=summary, results=results,
                  limitation='Candidate retrieval is not answerability. No answer generation, semantic support assessment, vector comparison or human evaluation performed.')
    output = ROOT / 'data/retrieval-baseline'
    output.mkdir(parents=True, exist_ok=True)
    target = output / (str(time.time_ns())+'.json')
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(summary, indent=2))
    print('Report:', target)


if __name__ == '__main__':
    main()
