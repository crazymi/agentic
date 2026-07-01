# Real Benchmark Status

Last updated: 2026-07-01 18:45 KST

Command run:

```bash
CODEX_HOME=/mnt/c/Users/TAZO/.codex .venv/bin/python -m agentic.app.cli real-bench --model master-gemma-iq2 --model-max-tokens 12
CODEX_HOME=/mnt/c/Users/TAZO/.codex .venv/bin/python -m agentic.app.cli real-bench --skip-network --skip-ntfy --model master-gemma-q4 --model-max-tokens 32
```

## Result Summary

| Probe | Current real status | Evidence | Next action |
| --- | --- | --- | --- |
| AI memory / idea synthesis | `completed` | real SQLite memory records and synthesis insight created under `traces/state/real_bench/memory.sqlite3` | wire channel capture and Obsidian export into this path |
| Harness self-inspection | `completed` | real `git status` and tracked file inventory read | promote into approval-gated patch/test workflow |
| Gmail WSJ newsletter | `needs_credential` | `AGENTIC_GMAIL_IMAP_USER` and `AGENTIC_GMAIL_IMAP_APP_PASSWORD` are not configured | add read-only Gmail credential/OAuth connector |
| Ticket browser transaction | `needs_input` | no official ticket URL was provided; live browser adapter is also missing | provide URL, implement real Playwright/Chrome adapter |
| ntfy delivery | `completed` | real ntfy notification sent through `notify-user` path | integrate notification path into approval/input checkpoints |
| Reddit stock crawl | `failed_live_attempt` | live request reached Reddit but returned HTTP 403 | implement Reddit API/OAuth or compliant crawler connector |
| DCInside stock crawl | `completed` | fetched live HTML from `https://gall.dcinside.com/board/lists/?id=neostock` and extracted 10 titles | add site-specific parser, rate policy, ResourceStore persistence |
| Local GGUF model | `completed_empty` | GPU visible and command returned 0, but output was empty for both `master-gemma-iq2` and `master-gemma-q4` smoke | debug llama.cpp command/template/runner output path |

## Interpretation

What actually works today:

- real local memory write and synthesis
- real repo inspection
- real ntfy push delivery
- real DCInside live HTML crawl
- real GPU-visible model process launch

What does not yet satisfy the user requirements:

- Gmail/WSJ cannot run without credentials.
- Reddit crawl is blocked by HTTP 403, so it needs a proper connector/API strategy.
- Ticket booking cannot proceed without an official URL and a real browser adapter.
- Local model execution launches but returns empty text, so the current configured inference path is not usable for autonomous judgment yet.

No fake, dummy, fixture, synthetic, or preapproved result is counted as completed capability in this status.
