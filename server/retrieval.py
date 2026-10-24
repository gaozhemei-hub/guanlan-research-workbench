"""Offline lexical retrieval experiment. No HTTP endpoint or remote model calls.

SQLite stores a derived index only. The caller retains authoritative source text.
Paragraph chunks preserve Python character offsets; no embedding truncation occurs.
"""
import hashlib
import json
import math
import re
import sqlite3
from collections import Counter


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def terms(text):
    """Latin tokens and overlapping Han bigrams; a deliberately simple baseline."""
    result = []
    for token in re.findall(r'[a-z0-9]+|[\u3400-\u9fff]+', text.lower()):
        if re.fullmatch(r'[\u3400-\u9fff]+', token):
            result.extend(token[i:i+2] for i in range(len(token)-1))
            if len(token) == 1:
                result.append(token)
        else:
            result.append(token)
    return Counter(result)


def paragraphs(text):
    for number, match in enumerate(re.finditer(r'[^\r\n]+', text), 1):
        raw = match.group()
        if not raw.strip():
            continue
        start = match.start() + len(raw) - len(raw.lstrip())
        end = match.end() - (len(raw) - len(raw.rstrip()))
        yield number, start, end, text[start:end]


class Index:
    def __init__(self, path=':memory:'):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS sources (
                workspace TEXT NOT NULL, source TEXT NOT NULL, version TEXT NOT NULL,
                fingerprint TEXT NOT NULL, stale INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(workspace, source));
            CREATE TABLE IF NOT EXISTS chunks (
                workspace TEXT NOT NULL, source TEXT NOT NULL, version TEXT NOT NULL,
                chunk_id TEXT NOT NULL, paragraph INTEGER NOT NULL,
                start INTEGER NOT NULL, end INTEGER NOT NULL, text TEXT NOT NULL,
                object_type TEXT NOT NULL, metadata TEXT NOT NULL,
                PRIMARY KEY(workspace, chunk_id),
                FOREIGN KEY(workspace, source) REFERENCES sources(workspace, source)
                    ON DELETE CASCADE);
        ''')

    def close(self):
        self.db.close()

    def replace(self, workspace, source, version, text, object_type='material', metadata=None):
        if not all(isinstance(v, str) and v.strip() for v in (workspace, source, version)):
            raise ValueError('workspace, source and version must be nonempty strings')
        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError('source text must not be empty; use delete explicitly')
            if object_type not in {'material', 'claim', 'check', 'watch'}:
                raise ValueError('unsupported object type')
            meta = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
            fingerprint = digest(json.dumps([text, object_type, meta], ensure_ascii=False))
            old = self.db.execute('SELECT * FROM sources WHERE workspace=? AND source=?',
                                  (workspace, source)).fetchone()
            if old and old['version'] == version and old['fingerprint'] != fingerprint:
                raise ValueError('changed content requires a new version')
            rows = []
            for paragraph, start, end, chunk in paragraphs(text):
                identity = json.dumps([workspace, source, version, 'paragraph-v1', start, end, digest(chunk)])
                rows.append((workspace, source, version, digest(identity), paragraph,
                             start, end, chunk, object_type, meta))
            # Build fully before replacing; transaction rollback retains the previous index.
            with self.db:
                self.db.execute('DELETE FROM sources WHERE workspace=? AND source=?', (workspace, source))
                self.db.execute('INSERT INTO sources VALUES (?,?,?,?,0)',
                                (workspace, source, version, fingerprint))
                self.db.executemany('INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?)', rows)
            return len(rows)
        except Exception:
            with self.db:
                self.db.execute('UPDATE sources SET stale=1 WHERE workspace=? AND source=?', (workspace, source))
            raise

    def delete(self, workspace, source):
        with self.db:
            self.db.execute('DELETE FROM sources WHERE workspace=? AND source=?', (workspace, source))

    def search(self, workspace, query, limit=5):
        if not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError('limit must be between 1 and 100')
        rows = self.db.execute('''SELECT c.*, s.stale FROM chunks c JOIN sources s
            ON c.workspace=s.workspace AND c.source=s.source WHERE c.workspace=?''', (workspace,)).fetchall()
        tokens = [terms(row['text']) for row in rows]
        query_terms = terms(query)
        document_frequency = Counter(t for token in tokens for t in token)
        average_length = sum(sum(t.values()) for t in tokens) / max(len(tokens), 1)
        results = []
        for row, token in zip(rows, tokens):
            score = 0.0
            length = sum(token.values())
            for term in query_terms:
                frequency = token[term]
                if frequency:
                    idf = math.log(1 + (len(rows)-document_frequency[term]+.5)/(document_frequency[term]+.5))
                    score += idf * frequency * 2.2 / (frequency + 1.2*(.25+.75*length/max(average_length, 1)))
            if score > 0:
                result = dict(row)
                result.update(score=score, method='lexical-bm25-han-bigram-v1',
                              content_hash=digest(row['text']), metadata=json.loads(row['metadata']))
                results.append(result)
        return sorted(results, key=lambda r: (-r['score'], r['chunk_id']))[:limit]

    def citation_valid(self, workspace, chunk_id, quote):
        """Current, non-stale exact quote only; this does NOT test entailment."""
        row = self.db.execute('''SELECT c.text, s.stale FROM chunks c JOIN sources s
            ON c.workspace=s.workspace AND c.source=s.source
            WHERE c.workspace=? AND c.chunk_id=?''', (workspace, chunk_id)).fetchone()
        return bool(row and not row['stale'] and isinstance(quote, str) and quote.strip() and quote in row['text'])
