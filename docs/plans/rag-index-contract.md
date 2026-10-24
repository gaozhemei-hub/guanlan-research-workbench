# RAG indexing contract — proposed experiment

Status: proposed product contract. A subset is implemented in the isolated lexical experiment (see [record](../retrieval-experiment-v0.1.md)); no product indexing endpoint exists yet. Historical search, answer caches and browser synchronization remain unimplemented.

## Source of truth and consent

Research records remain browser-owned. The first experiment uses original public fixtures. A later UI must explicitly offer to index selected material on the local server; it cannot silently copy the entire browser history. Sending selected evidence to a remote generator is a separate, visible operation.

## Indexed objects

Each object has `workspace_id`, stable `source_id`, `source_version`, `object_type`, `text`, optional framework nodes and observation date. Types distinguish source text, confirmed claims, checks and watches. A claim with an attached source is still a user interpretation, not an independently verified fact.

Each chunk has a stable identifier derived from source/version/chunking version and position, original character offsets, parent paragraph and content hash. Chunk sizes are constrained by the selected embedding model's token limit; arbitrary character counts must not silently truncate context.

## Lifecycle

- Reimporting an unchanged source is idempotent.
- Updating a source builds the new version before atomically replacing its active index entries. Failed updates retain the previous version with an explicit stale state.
- Deleting a source removes its searchable chunks and invalidates references in outstanding answers. Cached answers must not resurrect deleted text.
- Search defaults to current versions within the selected workspace. Historical versions require an explicit option and clear labels.
- Rebuilding an index reads authoritative source objects; the index itself is never used to reconstruct lost records.

## Retrieval and output

Return chunk IDs, source/version, offsets, scores and method before generation. Keep semantic similarity distinct from factual support. Generation returns cited claims or insufficient-evidence status. Check quotes against the retrieved version, then require user confirmation before creating research links or revisions.

## Experiment acceptance

Test idempotent import, revision, delete, failed replacement and workspace isolation. Freeze question/evidence labels before tuning; separate development from held-out questions. Compare lexical, vector, hybrid and reranked approaches on the same corpus. Report retrieval coverage and latency independently of citation validity and answer support. Record dependency/model versions and corpus hashes, never private text in public traces.
