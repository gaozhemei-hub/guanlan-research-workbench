"""Compare frozen paragraph labels; --vector explicitly permits model download.

All inference is local on original fixtures. No model service or product endpoint.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.retrieval import Index, paragraphs


def fuse(rankings, depth=10, constant=60):
    scores = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking[:depth], 1):
            scores[key] = scores.get(key, 0) + 1/(constant+rank)
    return sorted(scores, key=lambda key: (-scores[key], key))


def metrics(rows):
    result = {}
    for split in ('dev', 'evaluation'):
        subset = [r for r in rows if r['split'] == split]
        positive = [r for r in subset if r['expected']]
        negative = [r for r in subset if not r['expected']]
        result[split] = {
            'answerable': len(positive),
            'mean_paragraph_recall_at_3': statistics.mean(r['recall'] for r in positive),
            'all_required_evidence_at_3': sum(r['recall'] == 1 for r in positive)/len(positive),
            'mrr_at_3': statistics.mean(r['rr'] for r in positive),
            'unanswerable': len(negative),
            'unanswerable_with_candidates': sum(bool(r['retrieved']) for r in negative),
            'mean_query_ms': statistics.mean(r['ms'] for r in subset),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vector', action='store_true')
    parser.add_argument('--revision', help='Pin the model commit from a previous report')
    parser.add_argument('--rerank', action='store_true', help='Also download and locally rerank hybrid top 10')
    parser.add_argument('--reranker-revision', help='Pin the reranker commit')
    args = parser.parse_args()
    if args.rerank and not args.vector:
        parser.error('--rerank requires --vector')
    raw = (ROOT/'examples/retrieval-benchmark-v2.json').read_bytes()
    fixture = json.loads(raw)
    chunks = {}
    index = Index()
    for source in fixture['sources']:
        index.replace('teaching', source['id'], fixture['version'], source['text'])
        for paragraph, _, _, text in paragraphs(source['text']):
            chunks[f"{source['id']}:{paragraph}"] = text
    for q in fixture['questions']:
        if not set(q['expected']).issubset(chunks):
            raise ValueError('unknown expected paragraph')
    report = dict(corpus_sha256=hashlib.sha256(raw).hexdigest(),
                  disclosure=fixture['disclosure'], python=sys.version,
                  platform=platform.platform(), settings={'top_k': 3, 'rrf_depth': 10, 'rrf_constant': 60},
                  model=None, methods={}, vector_status='not_requested', reranker_status='not_executed',
                  limitation='No answer generation or sufficiency threshold. Candidate matches do not imply answerability.')
    model = None
    if args.vector:
        try:
            from huggingface_hub import HfApi
            from sentence_transformers import SentenceTransformer
            import torch
            torch.set_num_threads(2)
            name = 'BAAI/bge-small-zh-v1.5'
            revision = HfApi().model_info(name, revision=args.revision).sha
            started = time.perf_counter()
            model = SentenceTransformer(name, revision=revision, device='cpu', trust_remote_code=False)
            report['model'] = dict(name=name, revision=revision, device='cpu',
                                  max_seq_length=model.max_seq_length,
                                  setup_seconds=time.perf_counter()-started,
                                  packages={p: importlib.metadata.version(p) for p in
                                            ['sentence-transformers', 'torch', 'transformers', 'huggingface-hub']})
            prefix = '为这个句子生成表示以用于检索相关文章：'
            texts = list(chunks.values()) + [prefix+q['query'] for q in fixture['questions']]
            lengths = [len(model.tokenizer(text, truncation=False)['input_ids']) for text in texts]
            if max(lengths) > model.max_seq_length:
                raise ValueError('token limit exceeded; explicit chunking required, refusing truncation')
            report['model']['max_observed_tokens'] = max(lengths)
            started = time.perf_counter()
            embeddings = model.encode(list(chunks.values()), normalize_embeddings=True, show_progress_bar=False)
            report['model']['index_ms'] = (time.perf_counter()-started)*1000
            report['vector_status'] = 'executed'
        except Exception as error:
            model = None
            report['vector_status'] = 'failed'
            report['vector_error'] = str(error)
    reranker = None
    if args.rerank and model is not None:
        try:
            from sentence_transformers import CrossEncoder
            name = 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'
            revision = HfApi().model_info(name, revision=args.reranker_revision).sha
            started = time.perf_counter()
            reranker = CrossEncoder(name, revision=revision, device='cpu', trust_remote_code=False, max_length=512)
            report['reranker'] = dict(name=name, revision=revision, max_length=512,
                                      setup_seconds=time.perf_counter()-started)
            # Reject overlong pairs before prediction; do not silently truncate evidence.
            longest = max(len(reranker.tokenizer(q['query'], text, truncation=False)['input_ids'])
                          for q in fixture['questions'] for text in chunks.values())
            report['reranker']['max_observed_tokens'] = longest
            if longest > 512:
                raise ValueError('reranker pair exceeds token limit')
            report['reranker_status'] = 'executed'
        except Exception as error:
            reranker = None
            report['reranker_status'] = 'failed'
            report['reranker_error'] = str(error)
    rows = {'lexical': []}
    if model is not None:
        rows.update(vector=[], hybrid=[])
    if reranker is not None:
        rows['hybrid_reranked'] = []
    keys = list(chunks)
    for q in fixture['questions']:
        start = time.perf_counter()
        lexical = [f"{h['source']}:{h['paragraph']}" for h in index.search('teaching', q['query'], 100)]
        lexical_ms = (time.perf_counter()-start)*1000
        rankings = {'lexical': (lexical, lexical_ms)}
        if model is not None:
            start = time.perf_counter()
            query = model.encode([prefix+q['query']], normalize_embeddings=True, show_progress_bar=False)[0]
            scores = embeddings @ query
            vector = sorted(keys, key=lambda k: (-float(scores[keys.index(k)]), k))
            vector_ms = (time.perf_counter()-start)*1000
            start = time.perf_counter()
            hybrid = fuse([lexical, vector])
            hybrid_ms = (time.perf_counter()-start)*1000 + lexical_ms + vector_ms
            rankings.update(vector=(vector, vector_ms), hybrid=(hybrid, hybrid_ms))
            if reranker is not None:
                start = time.perf_counter()
                candidates = hybrid[:10]
                rerank_scores = reranker.predict([(q['query'], chunks[key]) for key in candidates], show_progress_bar=False)
                ordered = sorted(zip(candidates, rerank_scores), key=lambda pair: (-float(pair[1]), pair[0]))
                rankings['hybrid_reranked'] = ([key for key, _ in ordered], hybrid_ms+(time.perf_counter()-start)*1000)
        for method, (ranking, elapsed) in rankings.items():
            retrieved = ranking[:3]
            expected = set(q['expected'])
            rank = next((i for i, key in enumerate(retrieved, 1) if key in expected), None)
            rows[method].append(dict(id=q['id'], split=q['split'], expected=sorted(expected),
                                     retrieved=retrieved, recall=len(expected.intersection(retrieved))/len(expected) if expected else None,
                                     rr=1/rank if rank else 0, ms=elapsed))
    index.close()
    report['methods'] = {method: dict(summary=metrics(data), questions=data) for method, data in rows.items()}
    folder = ROOT/'data/retrieval-comparison'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder/(str(time.time_ns())+'.json')
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({method: value['summary'] for method, value in report['methods'].items()}, indent=2))
    print('Vector:', report['vector_status'], 'Report:', target)
    if report['vector_status'] == 'failed':
        print(report['vector_error'])
        return 1
    if report['reranker_status'] == 'failed':
        print(report['reranker_error'])
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
