# Harness quality record — 2026-10-24

## Remote publication — 2026-10-25

The retrieval increment is published for review in [PR #1](https://github.com/gaozhemei-hub/guanlan-research-workbench/pull/1), not merged into main. GitHub Actions [run 40180159168](https://github.com/gaozhemei-hub/guanlan-research-workbench/actions/runs/40180159168) passed on commit `613a763bb8d2d26a8d14802df98165f5d9c9e915`, including dependency installation and the declared backend suite on Ubuntu/Python 3.12. Current-head checks are shown on the PR. This remote job does not execute browser tests, download models, evaluate real-model quality or deploy a website. Prior local evidence and dated failure records below remain unchanged.

## Fresh synthetic acceptance and evidence status — 2026-10-25

An original corpus separate from development fixtures ran through all three product modes: 6 materials, 10 questions, 30 retrievals including 20 local model requests. Full evidence coverage: lexical 4/6, vector 5/6, reranked 5/6 answerable questions. Both semantic modes returned candidates for all 4 unanswerable questions. This is AI-authored labeled data, not human blind evaluation. See [acceptance report](检索验收与证据边界-v0.1.md); local raw report is `data/retrieval-acceptance/1792904474584235000.json`.

No ranking tuning followed the observed results. API responses now explicitly carry `unassessed` or `no_candidates` and `generated_answer: null`; the page states that sufficiency is unassessed. This is not an automated sufficiency classifier. Run `data/verification/run-r10hef4v/`: **85 backend / 22 UI tests passed**, including high-score/non-answer boundary and an unanswerable browser question. Standalone HTML rebuilt. No private corpus, paid API calls or remaining worker/server processes.

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


## PR #1 审查修复（2026-10-25，本地待确认）

已完成 Unicode 词法召回、词法重叠块、100 段预检、worker 分类错误、进程组清理、输入和 metadata 校验、过期提示修复。新增真实 worker＋假模型 CI 覆盖及请求中页面状态回归。修复前失败日志和修复后 105 后端 / 28 界面通过记录见 [审查修复与验证](PR1-审查修复与验证.md)。统一报告：`data/verification/run-ki7_nmlt/report.json`，passed=true。原有 85/22 是先前版本数字。

词法验收找全从 4/6 到 5/6，同时无答案有候选从 3/4 到 4/4；不生成答案、不持久化语料，不能把候选当作证据充分。模拟模型与真实本机模型分别记录；人工盲评和真人试用仍延期。本轮未推送、未合并，下一步由用户确认是否发布这批修改。

额外真实缓存模型页面检查：vector、reranked 各一次通过，约 5.630/4.561 秒（含加载及页面操作），含 ZWJ/CRLF 高亮；与 CI 假模型测试分开。生成 HTML 重建幂等且嵌入当前源码。原始本机证据路径见修复记录。


### 第二轮复审（2026-10-25）

修复相邻重叠窗口丢不同证据；清理阶段增加 5 秒截止和无 ps 后备，无法确认退出时阻止后续 worker 并要求人工检查/重启。测试在 LOCK.release 瞬间检查进程组，新增非超时异常覆盖；勾选清除过期提示。README/PRD 标明历史数字。完整证据见 PR1 审查修复记录文末。

`data/verification/run-nkq346m2/report.json`：passed=true，111 后端 / 28 界面通过；词法比较与验收数字和第一轮一致（验收找全 5/6，无答案候选 4/4）。本轮未重跑真实模型，没有推送或合并。不能将工程通过解释为没有其他缺陷。
