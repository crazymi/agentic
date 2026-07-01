# Real User-Requirement Benchmark

This benchmark is the project-facing measure of actual usefulness. It must not use fake, dummy, synthetic, fixture, or preapproved shortcuts.

Command:

```bash
.venv/bin/python -m agentic.app.cli real-bench
```

What it attempts today:

- Real SQLite memory capture and synthesis for the AI memo requirement.
- Real repository inspection for harness self-improvement.
- Real Gmail/WSJ mailbox access if `AGENTIC_GMAIL_IMAP_USER` and `AGENTIC_GMAIL_IMAP_APP_PASSWORD` are configured.
- Real ntfy delivery through configured ntfy env or the Codex `notify-user` script.
- Real Reddit stock JSON crawl.
- Real DCInside stock-gallery HTML crawl.
- Real local GGUF model execution through `config/config.toml`.
- Real browser transaction readiness check. If no official ticket URL or live browser adapter exists, the probe records that blocker instead of fabricating a site.

Statuses:

- `completed`: reached a real useful state.
- `completed_empty`: real path executed, but no matching data was found.
- `needs_credential`: credential is missing.
- `needs_input`: user input such as a URL is missing.
- `blocked_by_tooling`: live connector/runtime is not implemented.
- `failed_live_attempt`: a real attempt was made and failed.
- `skipped`: intentionally skipped by command flags.

Environment:

- `AGENTIC_GMAIL_IMAP_USER`
- `AGENTIC_GMAIL_IMAP_APP_PASSWORD`
- `AGENTIC_NTFY_TOPIC` or `NOTIFY_USER_TOPIC`
- `AGENTIC_NTFY_SERVER` or `NOTIFY_USER_SERVER`

Rules:

- Missing credentials must trigger a concise user notification when a notification path is available.
- Approval-gated, paid, destructive, authenticated, or externally visible actions remain behind deterministic policy.
- Test fixtures may exist only for low-level developer tests. They do not count as user-requirement completion.
