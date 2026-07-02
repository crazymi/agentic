# Real Benchmark Status

Last updated: 2026-07-01 18:54 KST

Command run:

```bash
CODEX_HOME=/mnt/c/Users/TAZO/.codex .venv/bin/python -m agentic.app.cli real-bench --model master-gemma-iq2 --model-max-tokens 12
CODEX_HOME=/mnt/c/Users/TAZO/.codex .venv/bin/python -m agentic.app.cli real-bench --skip-network --skip-ntfy --model master-gemma-q4 --model-max-tokens 32
.venv/bin/python -m agentic.app.cli smoke --model master-gemma-q4 --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."
.venv/bin/python -m agentic.app.cli smoke --model master-gemma-iq2 --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."
CODEX_HOME=/mnt/c/Users/TAZO/.codex .venv/bin/python -m agentic.app.cli real-bench --skip-network --skip-ntfy --model master-gemma-q4
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
| DCInside stock crawl | `completed` | fetched live HTML from `https://gall.dcinside.com/board/lists/?id=neostock` and stored 10 resources | add scheduler interval and trend report notification |
| Local GGUF model | `completed` | GPU visible and `master-gemma-q4` returned `{"decision":"answer","answer":"한국의 수도는 서울입니다."}` | run through full master/subagent workflow path next |

## Interpretation

What actually works today:

- real local memory write and synthesis
- real repo inspection
- real ntfy push delivery
- real DCInside live HTML crawl
- real DCInside resources persisted through `WebPageSourceCollector`
- real GPU-visible model process launch
- real local model non-empty output after increasing master generation budget

What does not yet satisfy the user requirements:

- Gmail/WSJ cannot run without credentials.
- Reddit crawl is blocked by HTTP 403, so it needs a proper connector/API strategy.
- Ticket booking cannot proceed without an official URL and a real browser adapter.
- Local model execution now returns non-empty text for master Gemma Q4/IQ2 with the corrected generation budget.

No fake, dummy, fixture, synthetic, or preapproved result is counted as completed capability in this status.

## Model Bug Fix Note

The empty-output bug was caused by too small a generation budget. The model was producing only `<|channel>thought` and stopping before the final JSON answer. The sanitizer correctly hid thought content, resulting in an empty user-facing output.

Fix:

- `master-gemma-q4.max_tokens`: `64 -> 256`
- `master-gemma-iq2.max_tokens`: `64 -> 256`
- `real-bench --model-max-tokens` default: `16 -> 256`

## Live Web Collection Note

Added a generic live web collection primitive after the benchmark showed DCInside can be fetched without browser automation:

- `WebPageSourceCollector`
- `web_fetch` tool
- `html_extract_links` tool
- `web-collect` CLI
- `resource-trends` CLI

Latest manual command stored 10 real DCInside link resources under `traces/state/web_collect/resources.sqlite3` and `resource-trends` summarized the stored titles. Remaining quality issue: short slang/noise titles still require better agent-tuned filters or a learned site profile.
