# Requirements Smoke Status

Last run:

```bash
.venv/bin/python -m agentic.app.cli requirements-smoke \
  --state-dir traces/state/requirements_smoke_rerun \
  --experience-path traces/experience.jsonl
```

Result:

- Overall: passed
- Experience events appended to `traces/experience.jsonl`
- Script-only execution; no UI, GPU, live browser, live Gmail, live ntfy, or external network required

## Probe Results

| Probe | Current level | What works | Bottleneck |
| --- | --- | --- | --- |
| WSJ newsletter analysis | completed | request routes to scheduled workflow, checked-in mail source collects, report artifact is produced | production Gmail OAuth/WSJ ingestion is missing |
| Stock community trend crawler | completed | request routes to scheduled workflow, checked-in feed source collects, report artifact is produced | production Reddit/DCInside collectors are missing |
| Idea memory synthesis | completed | channel/local idea source can collect and report | interpreter does not yet write/link durable memory records during workflow runs |
| Harness self-improvement | completed | repo source can be inspected and reported | patch/test execution is not yet modeled as safe approval-gated coding actions |
| Browser ticket transaction | blocked_by_tooling | request routes to browser transaction, planning continuation produces workflow, tooling backlog is generated | live `connector:browser`, browser observe/action runtime, approval-resume, and retry state are missing |
| Mobile approval notification | blocked_by_approval | request routes to channel workflow and correctly stops at approval for `channel:ntfy` | live external ntfy delivery depends on policy/environment |

## Current Learning

- Local-source probes are useful for regression checks, but every completed local probe should still name its production connector gap.
- Browser transactions are the highest-priority missing infrastructure because they produce multiple p0/policy backlog items.
- Coding self-improvement needs a safe patch/test action model rather than just repo-state reporting.
- Memory workflows need interpreter steps that write and link `MemoryStore` records, not only report over local files.
- Mobile notifications must keep a local web approval fallback because external ntfy delivery can be blocked.

## Next Smoke Improvements

- Add fixture-page browser adapter once `agentic/browser/` exists.
- Add memory-write workflow step and assert idea synthesis creates durable memory links.
- Add coding-action workflow steps that stop at approval before file/shell/git operations.
- Add summary aggregation over `traces/experience.jsonl` to surface repeated bottlenecks automatically.

