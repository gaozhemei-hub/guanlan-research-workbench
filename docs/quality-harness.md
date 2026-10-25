# Harness quality record — 2026-10-24

## Optional local semantic retrieval — 2026-10-25

Run `data/verification/run-5x80lox_/`: **84 backend / 21 UI tests passed**. New deterministic checks mock worker failures/timeouts/concurrency and assert offline/no-fallback behavior; UI checks method changes and explicit errors. They do not run real models.

Separately, the main task ran the actual local vector and reranked endpoints, then a real browser through both methods, source highlighting and clearing. Browser calls took about 3.8/4.3 seconds in this run; results and screenshot are in `data/retrieval-ui/semantic-flow.json` and `semantic-search.png`. The screenshot was visually inspected and copied to the public manual because it contains original teaching fixtures only. Direct adapter results are in `data/retrieval-comparison/product-semantic-check.json`.

An original 4,049-character repeated-padding fixture with a cashflow target sentence returned that sentence under both modes with exact original offsets (`product-long-text-check.json`). This is a mechanical smoke check, not independent retrieval-quality evidence. Optional dependencies/models stayed local, no paid API or private corpus. Worker processes and temporary verification servers exited. Remaining: independent quality evaluation and sufficiency handling; no generated answers, human blind review or user testing.

## Product retrieval follow-up — 2026-10-25

Explicit material selection, request-scoped lexical retrieval, original-text highlighting and invalidation are implemented. Final run `data/verification/run-2h8xlxs5/`: **79 backend / 19 UI tests passed**. UI scenarios exercise the real endpoint after teaching-material archival; also cover Unicode offsets, source changes, late responses and offline HTML. The standalone HTML was rebuilt. Separate real-server screenshots were visually checked and contain original teaching data only.

The first run `run-dtdil__a` failed one new HTTP test because it omitted the required same-origin header (403 rather than the expected 200); all 19 UI tests passed. The test was corrected without weakening endpoint checks. An initial ad-hoc tokenizer assertion compared reconstructed paragraph content with trailing whitespace still present; the corrected assertion explicitly excludes paragraph-edge whitespace and checks every original offset. Cached BGE tokenizer validation: 15,300 input characters, 19 chunks, max 512 tokens, exact trimmed-paragraph reconstruction. No content truncation, private corpus or paid API. This validates chunk mechanics, not retrieval/answer quality.

See [usage and boundaries](历史证据检索-使用说明-v0.1.md). The page uses lexical retrieval only; vector/reranking remains experimental, with no generated answers.

## Follow-up — 2026-10-25

Second follow-up: paragraph-level lexical/vector/hybrid/reranked comparison completed on original fixtures; see [v0.2 results](retrieval-experiment-v0.2.md). Optional local model dependencies are isolated from product dependencies. Engineering run `data/verification/run-10jq2dku/`: **74 backend tests passed**, including two scoring/fusion tests. After the optional reranker path was added, all 10 retrieval lifecycle/metric tests passed; the actual four-method experiment also completed. No UI changes; no new browser run. No paid API call or private corpus use. Model downloads and inference occurred locally; no generated answers or human assessment.

The isolated lexical retrieval experiment adds 8 lifecycle tests (idempotence/offsets, revision/deletion, stale recovery, transactional rollback, workspace isolation, version/quote validation, empty/no-overlap search, persistence). Unified verification in `data/verification/run-akrw36wf/` passed: **72 backend tests and 15 browser tests**. No product UI integration, real model call or human evaluation was performed. The synthetic retrieval benchmark is documented separately in [experiment v0.1](retrieval-experiment-v0.1.md); candidate recall is not answer accuracy. The dated foundation record below is preserved.

Foundation branch: `engineering/harness-foundation`. Product remains v0.8.1; RAG is not implemented.

Implemented: short knowledge entry, architecture/data ownership map, current execution plan, isolated verification runner, shared test target URL, backend-only CI definition.

First local run: browser suite 15/15 passed on an independently started port and temporary data directory. Backend process exceeded 180 seconds during dependency loading. Report correctly marks the overall run failed; logs and report are retained under ignored `data/verification/run-ougc2ms3/`.

A separate diagnostic traceback showed Python loading pandas module files. This is an observation, not a confirmed root cause. Earlier 64/64 results describe the October 13 release and do not replace the current run.

A retry remained in dependency loading without test output and was terminated explicitly; it is not a pass. The diagnostic process was also stopped. Investigate the dependency environment before rerunning or merging.

## Verified recovery

A fresh isolated `.venv` was created in this checkout using Python 3.12.6 and the unchanged `requirements.txt`. The previous environment was preserved. The diagnostic showed delays across multiple dependency imports; the underlying cause remains unconfirmed.

Command: `.venv/bin/python scripts/verify.py --ui-python /path/to/playwright/python`.

Run `data/verification/run-_v8fo6gk/`: backend **64/64 passed** (6.397 seconds in unittest; 16.372 seconds including process startup), browser **15/15 passed** (20.907 seconds in unittest; 21.057 seconds including startup). Overall report: `passed: true`. The browser suite used an isolated server and temporary cache. These are engineering checks using test fixtures/mocks, not live model quality measurements or a new full user-journey acceptance run.

Direct requirements are pinned; transitive dependencies are not fully locked. The successful local environment is not proof of cross-platform reproducibility.

The [index lifecycle contract](plans/rag-index-contract.md) now defines ownership, explicit indexing, revisions, deletion, failure handling and workspace isolation. This is a proposed contract, not a functioning RAG endpoint.

No CI run has been executed for this branch. No new paid model calls or private corpus indexing occurred. Remaining: run CI after publication, then implement and evaluate the RAG retrieval experiment against frozen original fixtures and held-out questions.
