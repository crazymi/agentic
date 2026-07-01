# Milestone 7 Status

Status: implemented.

Completed:

- intent router with core request classes
- workflow design session and proposal renderer
- durable SQLite `WorkflowSpec` and `WorkflowRun` store
- workflow lifecycle validation
- capability planner and admission outcomes
- artifact registry for reports/scripts/datasets/configs/logs
- workflow interpreter v0 for fake collect/analyze/report/notify steps
- scheduler store and due-runner v0
- local web UI/API for workflow design, approve, activate, pause, run, and status
- probe evals for newsletter, social trend, idea synthesis, browser watcher, and coding workflow representation

The earlier newsletter scaffold remains useful as a vertical probe:

- `EmailMessage` model
- `FixtureGmailConnector`
- newsletter ingestion
- deterministic newsletter analyzer
- newsletter workflow
- WSJ fixture
- evals for discovery, ingestion, grounded report, and memory writeback

Verification:

```bash
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
```

Manual smoke:

- Start `serve`.
- Open the local web UI.
- Submit a workflow design request such as "주식 커뮤니티 글을 주기적으로 모아서 트렌드 보고서로 알려줘."
- Confirm a proposal appears.
- Approve/activate/run a safe fake workflow.
- Confirm a workflow run and report artifact are recorded.

Notes:

- M7 is a framework kernel, not a production crawler/Gmail/browser implementation.
- External community/web/browser sources still require connector admission and approval.
- Generated scripts remain artifacts and cannot execute without review/approval.

Remaining for production newsletter use:

- Gmail OAuth connector
- credential storage and approval policy
- daily scheduler/hook
- model-assisted analysis prompt
- WSJ source/citation quality hardening
