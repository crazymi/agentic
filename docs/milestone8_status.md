# Milestone 8 Status

Status: implemented.

Completed:

- source definition and source item models
- source policy fields for read-only mode, approval need, rate limit, retention, and dedupe fields
- SQLite `SourceStore`
- local file, mail-like JSONL, feed-like JSONL, browser-page-file, repo-state collectors, and `SourceRuntime`
- source-item dedupe and raw resource writeback into `ResourceStore`
- credential reference model and SQLite store
- secret-like metadata/reference rejection for sources and credentials
- artifact admission service for generated scripts/configs
- dry-run gate that never executes script code
- policy gates for generated scripts, browser submit, email send, file write, shell, booking, payment, and external connectors

Verification:

```bash
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
```

Notes:

- M8 does not implement production Reddit, DCInside, Gmail, or browser crawling.
- Source collectors remain allowlisted primitives.
- Credential values are intentionally not stored.
- Generated scripts are artifacts first; execution remains gated behind review and approval.

Next:

- M9 should use these primitives to build the workflow probe pack without adding bespoke daemon paths.
