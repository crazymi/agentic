# Agentic Memory

Durable context for future work in this repository. Keep this short and replace stale entries instead of appending endlessly.

## Project Identity

- This is a personal local-first Agent Harness / Framework for one RTX 4090 machine.
- The product bet is local GGUF models plus durable task runtime plus channels/approval plus skills/tools/connectors.
- The project is not a general AI gateway, provider router, public plugin marketplace, cloud-first platform, or pile of bespoke automations.

## User-Shaped Validation Probes

- WSJ/Gmail newsletter analysis against investing and startup goals.
- Harness self-improvement through repo inspection, coding, test, and self-review workflows.
- AI memory and idea synthesis connected to chat/mobile and eventually Obsidian.
- Browser automations such as ticket availability alerts and approval-gated booking flows.
- Social/community trend collection is a probe for generic source collection, scheduler, resource, and report primitives.

## Persistent Operating Preferences

- Prefer framework primitives over vertical one-offs.
- Real capability claims require real execution paths.
- Missing credentials, URLs, connectors, approvals, or live network access should be reported as blockers, not hidden behind fixtures.
- Substantive work should leave reusable evidence in `docs/work_log.md` and, when relevant, `traces/experience.jsonl`.
- Simple Q&A, inventory, or inspection-only responses that do not change code/runtime behavior should not add `docs/work_log.md` entries unless the user explicitly asks for logging.
- Final responses should include the next recommended roadmap step.
- When researching OpenClaw, Hermes Agent, or Codex-like harness behavior, document source links, confidence, and reusable design conclusions in project docs so future turns do not repeat the same investigation.

## Current Durable Bottlenecks

- Gmail/WSJ live ingestion needs a credentialed connector path.
- Browser transaction workflows need a real Playwright/Chrome adapter, login checkpoints, screenshots/DOM artifacts, and approval-resumable runs.
- Reddit live collection has hit HTTP 403 and needs a robust real connector or strategy.
- Foreground `ask` is too slow for real workflow-building tasks; durable background execution and progress visibility should carry that work.

## Memory Discipline

Do not store:

- one-off chat,
- temporary guesses,
- facts already obvious from nearby code,
- logs, secrets, stack traces, or raw command output.

Do store:

- stable user preferences,
- recurring project constraints,
- repeated bottlenecks,
- reusable process lessons that change future work.
