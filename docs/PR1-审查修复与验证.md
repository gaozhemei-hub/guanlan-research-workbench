# PR #1 审查修复与验证

最新复审结果：本地后端 **111/111**、界面 **28/28**；见文末“第二轮复审修复”。下文第一轮数据保留为历史记录。

日期：2026-10-25。基线为 `d28e634`，所有修改位于 `engineering/harness-foundation`。本轮只本地修复和验收，未推送、未合并。没有读取私人纪要、密钥、个人备份或既有模型原始输出；没有付费调用或模型下载。

## 改动与复现证据

先在未修改的产品代码上加入复现测试，再实施修复。完整本机日志位于忽略上传的 `data/review-fixes/`；下表列出可复跑的测试文件及结论。失败数量按 unittest 的子用例计数，与测试方法数量不同。

| 项目 | 改动 | 修复前失败 → 修复后通过 |
| --- | --- | --- |
| Unicode 词法检索 | `server/retrieval.py`：NFKC＋casefold；Unicode 字母数字；汉字单字＋双字，复合查询单字权重 0.25；原文和偏移不变。无词查询报明确输入错误 | `test_review_retrieval` 的 single_han、unicode_normalization、empty_terms；HTTP 的 no_terms 由原先 200 改为 400 |
| 段落及 token 上限 | 请求端提前计算非空行（本产品段落定义），超过 100 不启动 worker；页面同样预检。worker 用固定错误码区分缺依赖/模型、块数超限、token 超限及其他失败 | `test_review_retrieval.test_101_paragraphs_rejected_before_worker`；`test_semantic_worker` 的 100/101、直接 worker 超块、reranker token、missing_model、other_error；界面 101 段用例 |
| 进程生命周期 | `server/semantic.py`：独立进程组、38 秒超时，TERM 后等 0.5 秒，再 KILL；回收直接子进程，确认组内没有执行中的后代后释放锁。正常退出也清理包装脚本留下的后台后代 | `test_semantic_worker` 的 timeout_reaps 与 normal_exit_reaps：原实现未建立独立进程组，两项均失败；现均通过。测试故意让后代忽略 TERM，覆盖 KILL 路径 |
| 跨词法块边界 | 专用 600 字符/20 重叠分块，步进 580；同来源同段落相交候选按分数去重；语义 token 分块不变 | `test_review_retrieval` 的 boundary_bigram 与 overlapping_chunks：原实现漏掉跨界“库存”且没有重叠；现命中、覆盖及偏移通过 |
| 过期提示 | `prototype/dist/retrieval.js`：发现材料变化清除 snapshot，同时作废请求编号，避免空快照误接受迟到结果；改问题清空提示 | `test_retrieval_ui` 的 stale_notice：修复前两个子用例失败；修复后改问题/改方式都消除提示 |
| 输入及 metadata | method 先验证字符串；ID/正文孤立代理字符转为安全中文错误；worker metadata 解析成对象 | `test_review_retrieval` 的 non_string_method、unpaired_surrogate，`test_semantic_worker` 的 offsets_metadata：修复前失败，修复后通过 |
| 文档 | README、架构能力声明改正；v0.2 使用说明数字注明当时；PRD 写明最坏 38 秒超时和额外清理时间 | `test_review_docs` 四个子用例原均失败，现通过；文意另外人工式逐项核对（由开发代理执行，不是人工盲评） |

`red-backend.log` 是原实现上的首轮记录（19 个测试方法，25 次失败、5 次错误）。其中两个进程用例最初因过短的测试启动等待而出现测试装置错误，不能作为产品缺陷证据；调长启动等待后，在仍未修改的语义实现上重跑，`red-process.log` 两项均因未建立独立进程组而失败。`red-docs.log` 保留文档四个子用例失败。修复后 `green-new.log` 20/20 通过。

修复前统一检查 `data/verification/run-j0xu1dl8/`：原有后端 85 项通过，加入新页面用例后的 28 项出现 3 次失败（段落预检一项、过期提示两个子用例）。修复后统一检查 `data/verification/run-ki7_nmlt/report.json`：`passed: true`，backend/UI 均 exit_code 0；日志分别为 **105/105、28/28**。后端新增 20 个方法，界面新增 6 个方法。

## 测试类型和覆盖范围

- 确定性测试：词法、Unicode 偏移、输入错误、HTTP 403/429/400、文档、分块覆盖、生命周期。进程生命周期使用会 sleep 的假 worker，不是模型推理。
- 模拟模型：`tests/fixtures/semantic_models/` 的 torch 和 sentence_transformers。tokenizer 每码点一个 token，并加入 CLS/SEP；确定性向量、模型加载参数记录。由不使用 exec 的包装脚本真正执行 `semantic_worker.py`；覆盖 vector/reranked、ZWJ emoji、CRLF、模型 revision 与 local_files_only=True。这些不能称为真实模型结果。
- 页面四项请求中变更测试（范围、方式、清空、材料）使用受控迟到响应，原实现已通过，新增的是回归覆盖，不能宣称修复了四个已有缺陷。HTTP 非回环 403 和第 21 次 429 也在修复前已通过。
- 新后端模块已加入 `scripts/verify.py` 的 BACKEND，今后的 CI 将执行真正 worker＋假依赖测试。本轮没有推送，不能宣称远程 CI 已通过本轮改动。

复跑：使用项目 `.venv/bin/python scripts/verify.py --ui-python <已有 Playwright 的 Python>`。运行 `scripts/package-prototype.py` 生成离线 HTML；生成件不直接编辑。

## 词法基准变化

算法标识改为 `lexical-bm25-unicode-v2`，词法分块标识改为 `characters-600-overlap20-v2`。没有调整原始题目或标签，也没有根据分数反复调参。新增单字增加候选和改变词频统计，因此旧指标仍保留为历史结果，新结果另记：

| 集合 | 本轮结果 | 与历史比较 |
| --- | --- | --- |
| examples/retrieval-benchmark.json | dev/evaluation 来源 recall@3、MRR 均为 1；无答案返回候选分别 0/1、2/2 | 测量对象是来源级，不与下面的段落级指标混用 |
| examples/retrieval-benchmark-v2.json | evaluation 段落 recall@3 = 70.83%；找全 50%；MRR 0.75；无答案有候选 3/3 | 历史段落召回 66.7%；找全及 MRR 未变 |
| examples/retrieval-acceptance-v1.json | 词法 6 道有答案题找全 5 道，平均证据召回 83.33%；4 道无答案题全部返回候选 | 原找全 4/6、平均召回 66.7%，无答案有候选 3/4；本轮召回更广，也更容易返回无用候选 |

本机输出：`data/review-fixes/lexical-v1.log`、`lexical-v2.log`、`lexical-acceptance.json`。有答案题 a2 仍未找全。无答案题候选增加不能解释为成功回答；`evidence_status` 仍仅为 unassessed/no_candidates，`generated_answer` 始终 null。

## 限制及原有流程

没有引入答案生成、持久服务端语料、下载模型或付费服务。新增单字匹配可能增加噪声，重叠去重可能省略相邻块的独有内容；候选仍需回到原文核对。语义长段拆成 token 块后仍可能超过 100 块，即便非空段落不超过 100，此时返回分块超限而不是模型缺失。跨标签页同步、真人试用和人工盲评仍未执行。

归档、修订、备份没有改动其存储和业务代码；统一界面套件继续覆盖原有流程。离线 HTML 由源码重建，仍禁用需要本机服务的检索，不把离线文件描述为独立模型应用。进程组方案面向当前 macOS/Linux 环境，不声明 Windows 支持。

## 真实缓存模型页面复核与生成件

本轮额外实际执行 vector、reranked 两条页面流程，各 1 次，均通过。输入为原创机械检查样本，含 ZWJ emoji 和 CRLF；校验返回候选、unassessed/null 边界及点击回原文后的高亮。向量约 5.630 秒，重排约 4.561 秒，包含模型加载与页面操作；不能当作性能基准。通过服务端离线环境及固定 revision/local_files_only 加载已有缓存，没有下载或付费调用。记录：`data/review-fixes/real-model-page.json`；可复跑脚本在同目录 `real-model-page.py`，需已有本机模型缓存和 Playwright。该结果不是模拟模型，也不代表真人质量评价。

重新运行 `scripts/package-prototype.py` 后生成 HTML 哈希未变化，确认生成幂等且包含当前 retrieval.js。证据：`data/review-fixes/package.json`。离线 HTML 仍由唯一 dist 源码生成。

## 第二轮复审修复（2026-10-25）

在第一轮未提交的工作区继续修改，没有推送或合并。以下结论基于复现用例、代码核对及回归范围，不代表项目没有其他缺陷。

| 复审项 | 文件与修改 | 修复前/后证据 |
| --- | --- | --- |
| 相邻窗口的不同证据丢失 | `server/retrieval.py`：只有命中完全包含在共享区域、共享区域外没有查询词命中时才抑制低分窗口。比较完整窗口与共享区域的命中计数，避免跨边界单词被切开后误去重。原文偏移和 600 字符上限不变 | 新增 `test_adjacent_windows_keep_distinct_evidence`，给定“库存下降/现金流转负”样本修复前失败、修复后通过；额外 `test_match_crossing_overlap_edge_is_not_dropped` 捕捉初版修正仍会漏掉跨边界 alpha 的问题，先失败后通过。原同一处命中去重测试继续通过 |
| 清理截止时间与 ps 缺失 | `server/semantic.py`：整个清理阶段 5 秒预算，包含直接子进程 wait、ps 查询及后代轮询；ps 缺失、执行失败或查询超时走 killpg(pgid, 0) 后备。清理超时给明确中文错误，不改报启动失败 | 新增 `test_timeout_without_ps_preserves_error_and_reaps_before_unlock`，修复前误报启动失败、修复后超时提示且解锁时无存活后代；`test_cleanup_deadline_is_bounded` 修复前触发测试的防无限循环异常，修复后明确清理超时 |
| 清理与解锁顺序证据 | `tests/test_semantic_worker.py`：替换 LOCK 对象包装真实锁，在 release 调用瞬间断言组内没有非僵尸进程；删除返回后的两秒宽限。新增 communicate 非超时异常路径 | 正常、超时及非超时异常的加强断言在修改产品实现前已经通过，属于覆盖补强，不宣称新缺陷。非超时异常测试首次打桩范围过宽影响了 ps 子进程；收窄为 worker communicate 后在未修复实现上通过，见 corrected 日志 |
| 清理失败后不并发启动新模型 | `server/semantic.py`：清理期限届满释放请求锁，但设置阻断状态，后续请求不启动 worker，要求人工检查并重启服务，避免尚未确认退出的进程与新 worker 并发 | 新增 `test_cleanup_failure_blocks_next_worker_until_restart`，修复前仍会启动第二个 worker、修复后只启动一次。属于确定性故障注入测试，不是真实模型 |
| 改勾选清除提示 | `prototype/dist/retrieval.js`：onchange 清空 error；运行打包脚本生成离线 HTML | `test_stale_notice_clears_on_new_query_or_method` 加 selection 子用例；修复前仍显示过期提示，修复后清空。测试方法数未增加 |
| 文档版本数字 | README 标注 85/22 是初始值；PRD 标注原版本词法 4/6，并明确当前 5/6 和无答案候选 4/4；当前工程数量更新为 111/28 | `test_review_docs` 新增 README/PRD 两个子断言，修复前均失败，修复后通过 |

### 本机证据与复跑

- `data/review-round2/red-backend.log`：相邻不同证据、缺 ps、无截止时间的原行为；其中非超时异常的初次失败来自测试打桩过宽，不能当产品缺陷证据。修正后的原实现通过记录为 `red-unexpected-corrected.log`。
- `data/review-round2/red-overlap-edge.log`、`red-quarantine.log`、`red-docs.log`：对应新增缺陷/文档断言的失败记录。
- 修复前统一检查 `data/verification/run-c1m_7awi/report.json` 为 false，界面日志明确 selection 子用例失败。
- 最终 `.venv/bin/python scripts/verify.py --ui-python /Users/irene/.workbuddy/binaries/python/envs/gl-pw/bin/python`：`data/verification/run-nkq346m2/report.json` 为 **passed=true**，后端 **111/111**、界面 **28/28**；相对第一轮新增 6 个后端测试方法，界面只扩展子用例。上述新增测试均进入已有 BACKEND 模块；当前未推送，不宣称远程 CI 通过。
- 重跑 `scripts/compare-retrieval.py`（未启用 vector）和 `examples/retrieval-acceptance-v1.json` 的词法请求。输出位于 `data/review-round2/lexical-comparison.log` 和 `lexical-acceptance.json`。比较集 evaluation recall@3 **70.83%**、找全 **50%**、MRR **0.75**、无答案有候选 **3/3**；验收集找全 **5/6**、平均证据召回 **83.33%**、无答案有候选 **4/4**，均与第一轮相同。给定长段落回归单独修复，不能因小验收集数字未变而认为它没有影响。
- 本轮测试包含确定性检查、真实子进程上的假模型/假 worker 检查、受控响应页面检查。没有付费调用、下载模型或重跑真实缓存模型；上节真实模型记录属于第一轮，不能当作本轮最新结果。

### 尚有限制

无 ps 时 killpg 无法区分僵尸与执行中的进程，可能保守地报清理超时并阻止后续语义请求；不会无限持有请求锁。需要人工确认残留进程状态并重启服务恢复。测试没有模拟操作系统永久不可中断的真实进程，而是用确定性时钟/故障注入验证截止与阻断行为。当前进程组实现面向 macOS/Linux，不声明 Windows 支持。

词法仍为相关候选检索：未召回的 a2 以及无答案也返回候选的问题仍存在。没有生成答案、持久化服务器语料或更改归档/修订/备份业务；原流程回归通过。离线 HTML 已由 dist 重建，检索依然需要本机服务。人工盲评、真人试用及本轮远程 CI 未执行。
