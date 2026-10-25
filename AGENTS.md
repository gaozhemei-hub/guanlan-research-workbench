# Working on Guanlan

- Read [ARCHITECTURE.md](ARCHITECTURE.md) and [current plan](docs/plans/harness-rag.md) first.
- Base product: [manual](docs/使用说明书-v0.8.1.md). Retrieval increment: [manual](docs/历史证据检索-使用说明-v0.2.md), [PRD v0.4](docs/PRD-v0.4.md), extending PRD v0.2/v0.3. Historical documents describe their dated versions.
- Develop in this Git repository on a branch. The former main/candidate folders are historical snapshots, not parallel editing targets. Do not copy directories over this checkout.
- Run `python scripts/verify.py` using the application's dependency environment. Add `--ui-python /path/to/playwright/python` for isolated UI verification.
- Inspect the generated report and logs under `data/verification/`. Never equate an unexecuted check with a pass.
- Preserve historical manuals and iteration records. Write product documentation, not interview coaching.
- Never commit `.env`, private source materials, model outputs, personal backups or generated indices. Keep them under ignored local directories.
- AI suggestions require explicit user confirmation. Citation matching does not establish factual truth or entailment.
- Distinguish deterministic tests, mocked AI, live model evaluation and human testing. Human evaluation is still pending.
- External-source probes and paid model evaluations are separate opt-in work; routine verification must not call them.
- Update the current plan and quality record with evidence, limitations and next steps after meaningful changes.
