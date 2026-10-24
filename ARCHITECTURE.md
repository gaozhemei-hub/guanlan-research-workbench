# Architecture and boundaries

The browser owns personal research records in localStorage: materials, confirmed claims, company links, checks, observations and revisions. JSON backup is user-controlled. The Python service does not currently persist those personal records.

`prototype/dist/` contains the UI. `scripts/package-prototype.py` creates the standalone HTML from those sources; do not independently edit the generated HTML. Offline snapshots are dated public data, not live observations.

`server/app.py` routes HTTP requests and performs technical calculations. `deploy.py` owns host/origin/auth configuration; `ai.py` owns model configuration and output validation; `prices.py` owns historical-price fetching; `providers.py` and `ak_worker.py` integrate public data. The server serves only the dist directory, never the repository or data directory.

External credentials stay server-side. AI outputs are proposals until confirmed by the user. Storage failure must not report success or leave changed research records in memory as if persisted.

## Planned RAG boundary (not implemented)

Browser-owned research needs an explicit indexing/synchronization contract before a server-side index can represent it. Stable source IDs, version IDs, deletion propagation and rebuild rules must be designed first. An index is derived data, never the authoritative research record.

Separate ingestion/chunking, retrieval, reranking, generation and citation validation. Retrieval experiments should run without a model API key. A generator must return source IDs and quotes; valid quotes alone do not prove that the conclusion follows.

## Verification

`scripts/verify.py` runs a declared backend suite. Its optional browser suite starts its own server on a selected free port with a temporary data directory, disabled scheduling and disabled model calls. Artifacts persist under ignored `data/verification/`. Test results describe engineering behavior, not investment or user outcomes.
