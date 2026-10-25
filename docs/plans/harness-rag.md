# Harness foundation and RAG experiment

Status: foundation locally verified; the product now offers request-scoped lexical and optional local vector/reranked evidence search with source previews. Generation is not implemented. Published for review in [PR #1](https://github.com/gaozhemei-hub/guanlan-research-workbench/pull/1); initial remote backend CI passed. Check the PR for current-head status. See the [quality record](../quality-harness.md) for dated results and recovery evidence.

Reference: [OpenAI Harness engineering](https://openai.com/index/harness-engineering/). Adaptation for a small single-user product, not an official framework integration.

## Acceptance

1. A new contributor can find the current product rules and architecture from AGENTS.md.
2. One command runs declared backend checks and optionally an isolated browser suite, reports actual outcomes and cleans up its owned server.
3. Browser suites use the requested instance independently of import order.
4. Normal verification needs no private corpus, paid model call or financial-source refresh.

## Next: RAG experiment

2026-10-25: isolated SQLite lifecycle and lexical baseline implemented. Original small fixture and first results are documented in [experiment v0.1](../retrieval-experiment-v0.1.md). Vector/hybrid/reranking comparisons and product integration remain pending. The comparison split has now been observed; it is not a fresh blind set.

Follow-up: expanded to 24 paragraphs and 17 questions in [experiment v0.2](../retrieval-experiment-v0.2.md). Local vector, hybrid and cross-encoder reranking comparisons executed; neither candidate relevance nor source matching establishes answer sufficiency. Parameters and labels were not tuned on observed comparison results. Product integration remains pending. Next: token-bounded long-document chunks, independent acceptance questions, then explicit browser indexing and evidence previews; answer generation requires separate sufficiency checks.

- Implement and test the proposed [indexing contract](rag-index-contract.md) for browser-owned records, source versions and deletion semantics.
- Prepare original public fixtures with question-to-evidence labels before tuning; keep a held-out set. Private experiments remain local.
- Compare keyword, vector, hybrid and reranked retrieval under identical questions and evidence labels. Do not assume reranking improves results.
- Evaluate retrieval coverage, quote validity and answer support separately. Measure latency and no-evidence cases. Any semantic assessment by AI is labeled as such.
- Only choose models, chunk sizes and cutoffs after checking token limits and experiment results. Earlier character counts and top-k values are hypotheses.
- Integrate historical research associations after retrieval and indexing validation; user confirmation remains mandatory.

## Deferred

Fresh-corpus acceptance completed: [evidence-boundary report](../检索验收与证据边界-v0.1.md). No tuning against observed results; semantic modes still miss one company's missing-contract caveat and return candidates on unanswerable questions. API/UI explicitly mark sufficiency as unassessed. Engineering 85/22 passed. The generation gate remains closed: independent human evaluation, support/contradiction and cross-chunk checks are unresolved. Next delivery work can package the tested retrieval-only feature and review documentation/CI without claiming full RAG answering.

Latest semantic follow-up: optional cached local models are connected to the page via an isolated request worker. 84 backend / 21 UI checks passed, plus real local-model browser checks and an original long-text mechanics check. See [manual v0.2](../历史证据检索-使用说明-v0.2.md). Still needed: independent long-form quality evaluation, cross-chunk context decisions and answer-sufficiency handling before generation. No paid API authorization is inferred; no private corpus was used.

Latest implementation: [evidence search flow](../历史证据检索-使用说明-v0.1.md) now supports explicit selection, in-memory per-request indexing and source highlighting. Token-counted long-text chunks passed cached-tokenizer validation. 79 backend / 19 UI tests passed. Next: connect optional local vector/reranking to the same lifecycle, validate independent long-form questions and latency, and only then consider answer generation with evidence-sufficiency checks. No persistent server corpus is introduced by the first page.

Human blind evaluation, real-user testing, online hosting and fully automated merging. No new paid-model budget is inferred from the earlier dated evaluation authorization.
