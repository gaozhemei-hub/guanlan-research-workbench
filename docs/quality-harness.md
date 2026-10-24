# Harness quality record — 2026-10-24

## Follow-up — 2026-10-25

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
