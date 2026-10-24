# Harness foundation and RAG experiment

Status: foundation locally verified (64 backend and 15 browser checks); remote CI not yet executed. RAG not implemented. See the [quality record](../quality-harness.md) for failed attempts and recovery evidence.

Reference: [OpenAI Harness engineering](https://openai.com/index/harness-engineering/). Adaptation for a small single-user product, not an official framework integration.

## Acceptance

1. A new contributor can find the current product rules and architecture from AGENTS.md.
2. One command runs declared backend checks and optionally an isolated browser suite, reports actual outcomes and cleans up its owned server.
3. Browser suites use the requested instance independently of import order.
4. Normal verification needs no private corpus, paid model call or financial-source refresh.

## Next: RAG experiment

2026-10-25: isolated SQLite lifecycle and lexical baseline implemented. Original small fixture and first results are documented in [experiment v0.1](../retrieval-experiment-v0.1.md). Vector/hybrid/reranking comparisons and product integration remain pending. The comparison split has now been observed; it is not a fresh blind set.

- Implement and test the proposed [indexing contract](rag-index-contract.md) for browser-owned records, source versions and deletion semantics.
- Prepare original public fixtures with question-to-evidence labels before tuning; keep a held-out set. Private experiments remain local.
- Compare keyword, vector, hybrid and reranked retrieval under identical questions and evidence labels. Do not assume reranking improves results.
- Evaluate retrieval coverage, quote validity and answer support separately. Measure latency and no-evidence cases. Any semantic assessment by AI is labeled as such.
- Only choose models, chunk sizes and cutoffs after checking token limits and experiment results. Earlier character counts and top-k values are hypotheses.
- Integrate historical research associations after retrieval and indexing validation; user confirmation remains mandatory.

## Deferred

Human blind evaluation, real-user testing, online hosting and fully automated merging. No new paid-model budget is inferred from the earlier dated evaluation authorization.
