# Open Notebook 底座验证

验证日期：2026-10-11。状态：本机技术 PoC，与产品界面原型分开验证。

## 锁定对象

- 上游：[lfnovo/open-notebook](https://github.com/lfnovo/open-notebook)
- 提交：`a0f6f3081ae06328f0a451b3a3ef2959ca25721d`
- `pyproject.toml` 版本：1.15.0
- 许可证：MIT；此次未修改或分发上游代码。后续复制代码需保留版权与许可证。
- 本地工作副本：工作区的 `work/vendor/open-notebook`（不属于交付原型，也不随作品集发布）。

## 为什么继续验证它

已有资料容器、来源导入、全文读取、笔记编辑和自定义 Transformation 接口。我们需要的主要新增部分是研究假设、证据状态、信息缺口、待审更新及历史版本。优先尝试复用这些资料与模型基础能力，不先重做完整知识库。

## 源码确认的接口与差距

| 需求 | 上游已有位置 | 验证结论 / 接入注意事项 |
|---|---|---|
| 文字材料导入 | `api/routers/sources.py`，`POST /api/sources`（表单）、`POST /api/sources/json`（兼容 JSON） | 有 `type=text`、`content`、`notebooks`、`embed`、`async_processing`；PoC 禁用嵌入和 Transformation，隔离模型影响 |
| 来源读回 | `GET /api/sources/{source_id}`；`SourceResponse.full_text` | 可据全文生成段落定位；不等于已有书籍页码或播客时间戳 |
| 笔记编辑 | `api/routers/notes.py`，POST/PUT/GET | 可保存整理结果；笔记保存会提交嵌入任务，不能把笔记写入成功当成嵌入完成 |
| 自定义分析 | `api/routers/transformations.py` | 可保存 prompt 模板并执行；执行依赖有效模型配置 |
| 结构化研究与修订 | 本轮尚未发现直接对应本产品完整链路的接口 | 需新增独立数据模型或受控的结构化笔记层；不能只靠 prompt 实现版本并发控制 |
| 异步处理 | 开发文档要求独立 worker | 没有 worker，异步资料任务可能一直排队；即使 async_processing=false，同步接口内部也会提交任务并等待 worker；不能把“同步”理解成不需要 worker |

源码链接：[sources.py](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/api/routers/sources.py)、[notes.py](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/api/routers/notes.py)、[transformations.py](https://github.com/lfnovo/open-notebook/blob/a0f6f3081ae06328f0a451b3a3ef2959ca25721d/api/routers/transformations.py)。

## 环境验证

- 当前 Mac 为 ARM64，无 Docker / 系统 PATH 上的 Node、npm、uv。
- 使用应用提供的 Node 运行原型检查；原型本身是无构建依赖的 HTML/CSS/JS。
- 将官方 SurrealDB 2.4.0 ARM 二进制放在工作区，启动仅监听 `127.0.0.1:18000` 的临时内存数据库；`/health` 返回 HTTP 200。
- 安装 uv 到工作区独立环境。最初 pip 镜像的证书验证失败；改用官方 PyPI 与系统证书后成功，未关闭 TLS 校验。
- 首次 `uv sync` 自动选择 Intel Anaconda Python，cryptography 触发源码/Rust 构建；已停止这些本次产生的进程，改为显式指定 ARM Python 3.12。
- 模型密钥未配置；没有读取私人凭证，也没有上传用户的书籍或个人材料。

## API 实测

最终复测 **7 / 7 通过**。原始结果：[open-notebook-poc-results.json](open-notebook-poc-results.json)；复现脚本：`scripts/verify-open-notebook.py`。

| 检查 | 结果 | 本次耗时 |
|---|---|---:|
| API 健康检查 | 通过 | 0.020 s |
| 新建 notebook | 通过 | 0.080 s |
| 同步文字导入（后台 worker 在线） | 通过，全文与输入一致 | 1.184 s |
| 原文读回及段落定位基础 | 通过，3 段原文原样保留 | 0.103 s |
| 笔记创建、修改、重新读取 | 通过 | 0.184 s |
| 自定义 Transformation 模板保存、读取 | 通过；未执行模型 | 0.039 s |
| 异步资料入队并处理完成 | 通过，能读回完整原文 | 0.902 s |

这是单次、短文本、本机热缓存测试，不代表生产性能或完整产品验收。数据库为内存模式，未测试重启后的持久化。上游前端未启动；模型生成、向量检索、引用语义准确率均未验证。笔记保存会触发嵌入任务，未配置模型时任务失败，但笔记写入成功；必须分别展示状态。

### 保留的失败与恢复记录

首轮读写可用；随后复测中同步导入超过 45 秒、异步等待超过 25 秒。失败结果保存在 [open-notebook-poc-cold-start-failure.json](open-notebook-poc-cold-start-failure.json)。

观察到 worker 在笔记嵌入开始后长时间没有继续处理，随后分词缓存文件生成，排队的资料任务集中恢复；源码中 `generate_embedding` 在检查模型前调用同步 `token_count`，后者首次获取 `o200k_base`。这些证据与分词缓存冷启动阻塞相符，但本轮没有采集调用栈，因此不声称已严格证明唯一根因。缓存就绪后重跑同一脚本，7 项通过。

部署时应提前准备并校验分词缓存，校验模型配置，对后台任务设置可见状态、超时与重试入口。不能以简单延长前端等待来掩盖问题。

## 架构决定

**基础资料与模板能力验证通过，建议继续以 Open Notebook 作为优先底座。** 下一阶段验证真实模型输出与界面适配，再确定最终接入方式。

本轮可交互原型采用浏览器本地数据，以较小成本验证研究流程。它目前没有调用 Open Notebook 接口，不能描述为“已基于 Open Notebook 完成改造”。原型代码、上游原有能力、未来新增能力须分别说明。

后续优先尝试：自定义三 Tab 界面 → 薄适配层 → Open Notebook 来源与 Transformation；研究记录与修订状态单独管理。是否嵌入上游 Next.js 前端，需在运行和维护成本验证后决定。

## 本轮结束状态

测试使用原创教学数据，未上传用户私有文档。临时 API、worker、内存数据库和预览服务在验证结束后停止；保留代码、依赖与结果，便于后续恢复。原型独立 HTML 不依赖这些服务。
