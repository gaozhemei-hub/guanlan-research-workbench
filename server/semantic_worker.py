"""Offline-only optional model process. No credentials or remote inference."""
import contextlib
import json
import sys
import time
from retrieval import Index, bounded_chunks, digest

EMBEDDING = ('BAAI/bge-small-zh-v1.5', '7999e1d3359715c523056ef9478215996d62a620')
RERANKER = ('cross-encoder/mmarco-mMiniLMv2-L12-H384-v1', '1427fd652930e4ba29e8149678df786c240d8825')
PREFIX = '为这个句子生成表示以用于检索相关文章：'


def run(payload):
    from sentence_transformers import SentenceTransformer, CrossEncoder
    import torch
    torch.set_num_threads(2)
    started = time.perf_counter()
    model = SentenceTransformer(EMBEDDING[0], revision=EMBEDDING[1], device='cpu',
                                local_files_only=True, trust_remote_code=False)
    count = lambda text: len(model.tokenizer(text, truncation=False, verbose=False)['input_ids'])
    query = PREFIX+payload['query']
    if count(query) > model.max_seq_length:
        raise ValueError('query exceeds token budget')
    index = Index()
    try:
        for material in payload['materials']:
            index.replace('request', material['id'], digest(material['text']), material['text'],
                          chunker=lambda text: bounded_chunks(text, 384, count),
                          chunking_version='bge-384-v1')
        chunks = [dict(row) for row in index.db.execute('SELECT * FROM chunks ORDER BY source,start')]
        if not chunks or len(chunks) > 100:
            raise ValueError('chunk count exceeds budget')
        texts = [c['text'] for c in chunks]
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        scores = vectors @ model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        by_id = {c['chunk_id']: c for c in chunks}
        score_map = {c['chunk_id']: float(score) for c, score in zip(chunks, scores)}
        ordered = sorted(by_id, key=lambda key: (-score_map[key], key))
        method = 'local-vector-bge-v1'
        revisions = {'embedding': EMBEDDING[1]}
        if payload['method'] == 'reranked':
            lexical = [c['chunk_id'] for c in index.search('request', payload['query'], limit=10)]
            fused = {}
            for ranking in (lexical, ordered[:10]):
                for rank, key in enumerate(ranking, 1):
                    fused[key] = fused.get(key, 0)+1/(60+rank)
            candidates = sorted(fused, key=lambda key: (-fused[key], key))[:10]
            reranker = CrossEncoder(RERANKER[0], revision=RERANKER[1], device='cpu',
                                    local_files_only=True, trust_remote_code=False, max_length=512)
            pairs = [(payload['query'], by_id[key]['text']) for key in candidates]
            if any(len(reranker.tokenizer(a,b,truncation=False,verbose=False)['input_ids']) > 512 for a,b in pairs):
                raise ValueError('reranker pair exceeds token budget')
            reranked = reranker.predict(pairs, show_progress_bar=False)
            score_map = dict(zip(candidates, map(float, reranked)))
            ordered = sorted(candidates, key=lambda key: (-score_map[key], key))
            method = 'local-hybrid-reranked-v1'
            revisions['reranker'] = RERANKER[1]
        hits = []
        for key in ordered[:5]:
            item = by_id[key]
            item.update(score=score_map[key], method=method, content_hash=digest(item['text']))
            hits.append(item)
        return dict(hits=hits, method=method, scope='request-memory-only', chunking='bge-384-v1',
                    model_revisions=revisions, seconds=round(time.perf_counter()-started,3),
                    warning='相关度不是证据充分性。未生成答案，未调用外部模型。')
    finally:
        index.close()


if __name__ == '__main__':
    try:
        payload=json.load(sys.stdin)
        with contextlib.redirect_stdout(sys.stderr):
            result=run(payload)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except Exception:
        # Do not echo source material or third-party error contents to the caller/logs.
        print('Local semantic worker failed', file=sys.stderr)
        sys.exit(1)
