# Architecture and boundaries

The browser owns personal research records in localStorage: materials, confirmed claims, company links, checks, observations and revisions. JSON backup is user-controlled. The Python service does not currently persist those personal records.

`prototype/dist/` contains the UI. `scripts/package-prototype.py` creates the standalone HTML from those sources; do not independently edit the generated HTML. Offline snapshots are dated public data, not live observations.

`server/app.py` routes HTTP requests and performs technical calculations. `deploy.py` owns host/origin/auth configuration; `ai.py` owns model configuration and output validation; `prices.py` owns historical-price fetching; `providers.py` and `ak_worker.py` integrate public data. The server serves only the dist directory, never the repository or data directory.

External credentials stay server-side. AI outputs are proposals until confirmed by the user. Storage failure must not report success or leave changed research records in memory as if persisted.

## RAG experiment boundary (request-scoped retrieval integrated; no generation)

`server/retrieval.py` contains the SQLite/lexical index with atomic current-version replacement, stale states, deletion and exact-quote checking. Its original isolated experiment is recorded in [v0.1](docs/retrieval-experiment-v0.1.md); the request-scoped product path is described below. `scripts/compare-retrieval.py` separately evaluates local vector/hybrid retrieval on original fixtures with optional dependencies; it is not a production index backend. Answer generation is not implemented.

Browser-owned research needs an explicit indexing/synchronization contract before a server-side index can represent it. Stable source IDs, version IDs, deletion propagation and rebuild rules must be designed first. An index is derived data, never the authoritative research record.

Separate ingestion/chunking, retrieval, reranking, generation and citation validation. Retrieval experiments should run without a model API key. A generator must return source IDs and quotes; valid quotes alone do not prove that the conclusion follows.

## First product retrieval path (2026-10-25)

`prototype/dist/retrieval.js` implements explicit selection and source previews. `/api/retrieve` accepts up to 20 selected records / 100,000 characters, builds a request-scoped in-memory lexical index and closes it before returning. It inherits auth/host/origin controls, adds rate limiting and accepts only loopback connections. It does not persist or share source text. The browser remains authoritative; results are invalidated on in-page source/query/scope changes, with original text rechecked before highlighting. Cross-tab synchronization is not implemented.

Lexical candidate chunks are bounded to 600 characters with 20-character overlap and overlapping-hit suppression; this is not a token budget. The shared chunker accepts a tokenizer counting callback; a cached BGE tokenizer has separately validated long-text coverage under 512 tokens. The optional vector/reranking path is described below. No endpoint generates answers.

## Optional semantic path (same day follow-up)

The evidence page now passes an explicit `lexical`, `vector` or `reranked` method. Lexical still uses 600-character chunks. Optional semantic methods use `semantic.py` to invoke `semantic_worker.py` via a separate `.venv-rag` interpreter (or server-configured `GUANLAN_RAG_PYTHON`). Source text travels on stdin, not command arguments or files. Fixed model revisions load from cache with offline flags and `local_files_only`; missing dependencies/models fail explicitly, without downloading or falling back.

One worker at a time, 38-second timeout with process-group TERM/KILL cleanup before unlocking, 10,000 source characters / 150 query characters / at most 100 nonempty paragraphs (preflight) and 100 token chunks bound this experimental path. BGE chunks count 384 tokens including special tokens; reranker pairs are checked against 512 tokens. The worker exits after each request; no persistent embeddings or corpus. This trades repeated model-load latency for dependency/data isolation. Candidate ranking is not answer sufficiency; no answer generation is enabled. See [v0.2 manual](docs/历史证据检索-使用说明-v0.2.md).

All retrieval responses mark evidence status as `unassessed` when candidates exist or `no_candidates` otherwise, with `generated_answer: null`. No score threshold upgrades this to supported/verified. The UI repeats this boundary; it is an explicit absence of sufficiency assessment, not a classifier.

## Verification

`scripts/verify.py` runs a declared backend suite. Its optional browser suite starts its own server on a selected free port with a temporary data directory, disabled scheduling and disabled model calls. Artifacts persist under ignored `data/verification/`. Test results describe engineering behavior, not investment or user outcomes.
