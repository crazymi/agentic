# Roadmap

This project is a personal local-first agent harness for one RTX 4090 machine. It is not a general AI gateway, model marketplace, provider router, or plugin store.

The core product bet is simple:

```text
local GGUF models + durable task runtime + channels/approval + skills/tools/connectors
```

The harness should become useful for four concrete use cases:

- read WSJ newsletters from Gmail and analyze them against standing goals
- improve this harness through coding and self-review workflows
- act as an AI memory and idea synthesis layer connected to chat/mobile and Obsidian
- create, run, and supervise browser automations such as Interpark ticket availability alerts

## Current Baseline

Completed legacy milestones are archived in `docs/legacy/`.

- Phase 0 completed: module-level proof of the local GGUF provider, prompt builder, tool parser, dummy tool, task object, trace logger, and evals.
- Phase 1 completed: minimal full loop from user input to master delegation, subagent tool call, tool result, trace, and final response.

The active roadmap starts after this baseline.

## Design Principles

- Local-first: the primary runtime is local GGUF on the user's machine.
- Personal-first: optimize for one user's 24/7 workflows, not general public deployment.
- Small core, explicit extensions: keep the core runtime small and expose repeatable extension primitives.
- Approval before consequence: irreversible, paid, authenticated, or externally visible actions require a policy gate.
- Durable by default: long-running jobs, traces, approvals, and background tasks must survive restarts.
- Skills are procedures, tools are actions, connectors expose outside capabilities.
- Prefer MCP-style connectors for external systems when a durable server boundary is useful.
- Avoid premature marketplaces, provider discovery, or multi-backend abstraction.

## Extension Primitives

These are framework-level modules, not individual user skills.

| Primitive | Purpose | Example uses |
| --- | --- | --- |
| Channel | Communicate with the user and accept inbound messages | local web chat, mobile replies, ntfy notification links |
| Approval | Ask permission before sensitive actions | send email, book ticket, write files, run shell, spend money |
| Tool | Execute one typed local action | add, read file, run script, launch browser step |
| Connector | Adapt an external system into resources/tools/prompts | Gmail, Obsidian, browser, ntfy, GitHub |
| MCP Connector | Standard connector boundary for external tool/resource servers | filesystem, browser automation, mail, search, code tools |
| Skill | Reusable procedure/instructions for accomplishing a class of task | newsletter analysis procedure, coding loop, browser macro creation |
| Hook | Event-triggered runtime entry point | new email, task completed, approval timed out, trace anomaly |
| Scheduler | Time-based trigger and recurring execution | daily WSJ scan, periodic idea synthesis, watchdog checks |
| Background Task | Durable long-running work with lifecycle and heartbeat | ticket watcher, crawler, self-review daemon |
| TaskFlow | Multi-step orchestration across agents, tools, approvals, and retries | investigate newsletter, draft report, ask follow-up, store memory |
| Memory Store | Durable internal memory and user context | preferences, standing goals, task history, idea graph metadata |
| Resource Store | External documents and assets referenced by agents | Obsidian vault, Gmail messages, web pages, screenshots |
| Policy | Rules for capability limits, credentials, and approvals | which tools need approval, which jobs may run unattended |
| Trace/Replay | Structured event log for debugging and evals | reproduce a failed browser macro or newsletter analysis |

OpenClaw separates concepts such as skills, plugins, and automation. MCP standardizes external capability exposure through servers and capabilities such as tools, resources, prompts, lifecycle, and discovery. This harness borrows those shapes but keeps the implementation local, small, and personal.

References:

- OpenClaw Skills: https://docs.openclaw.ai/tools/skills
- OpenClaw Plugin: https://docs.openclaw.ai/tools/plugin
- OpenClaw Automation: https://docs.openclaw.ai/automation
- Model Context Protocol architecture: https://modelcontextprotocol.io/docs/concepts/architecture

## Milestone 2: Channel And Approval Core

Goal: make the harness reachable and controllable from desktop/mobile with a simple local web UI plus ntfy notifications.

Scope:

- local web server for chat, task inbox, and approval cards
- ntfy outbound notifications for important events
- inbound message model for user replies
- approval request lifecycle
- approval policy registry
- channel event tracing
- no public multi-user auth system yet

Modules:

- `agentic/channels/`
- `agentic/approvals/`
- `agentic/app/server.py`
- `agentic/runtime/events.py`
- `agentic/policy/`

Acceptance criteria:

- user can open a local web page and send a message to the harness
- harness can send an ntfy notification when approval is needed
- approval can be approved/denied from the web UI
- denied approval prevents tool execution
- approval decisions are written to JSONL trace
- restart does not lose pending approvals

Evaluation:

- unit test: approval state transitions
- unit test: policy requires approval for sensitive tool
- integration test: channel message creates runtime event
- integration test: approval denial blocks tool execution
- manual test: ntfy notification arrives on phone

## Milestone 3: Durable Runtime And Background Task Pool

Goal: support long-running work without relying on one foreground CLI process.

Scope:

- task ledger persisted to SQLite or append-only JSONL plus snapshot
- background task lifecycle
- heartbeats and watchdog
- cancellation and pause/resume
- bounded concurrency
- restart recovery
- task log view in web UI

Modules:

- `agentic/runtime/daemon.py`
- `agentic/runtime/task_pool.py`
- `agentic/runtime/heartbeat.py`
- `agentic/tasks/store.py`
- `agentic/tasks/state_machine.py`

Acceptance criteria:

- a background task can be started from a chat command
- task state survives process restart
- task can be cancelled
- stuck task is detected by heartbeat timeout
- trace and task state agree on lifecycle events

Evaluation:

- integration test: start task, persist state, reload state
- integration test: cancellation reaches running task
- integration test: heartbeat timeout marks task unhealthy
- replay test: task trace reconstructs state

## Milestone 4: Connector And MCP Boundary

Goal: introduce a small connector model and decide when to use local tools versus MCP servers.

Scope:

- connector interface for resources/tools/prompts
- MCP client adapter
- connector capability discovery cached into config/state
- resource references in prompts and tasks
- connector-level permission policy
- no plugin marketplace

Modules:

- `agentic/connectors/`
- `agentic/connectors/mcp_client.py`
- `agentic/resources/`
- `agentic/policy/capabilities.py`

Acceptance criteria:

- a connector can expose tools to the runtime
- a connector can expose read-only resources
- MCP tool calls pass through the same approval/policy path as local tools
- connector failures are traceable and retryable

Evaluation:

- fake connector test: tools/resources/prompts discovery
- fake MCP server test: call one tool through adapter
- policy test: connector tool requiring approval cannot bypass approval

## Milestone 5: Skill System

Goal: represent reusable procedures separately from executable tools.

Scope:

- skill package format
- skill loader
- skill routing metadata
- skill prompt injection
- required tools/connectors declaration
- skill eval fixtures
- user-editable local skill directory

Modules:

- `agentic/skills/`
- `skills/`
- `evals/skills/`

Acceptance criteria:

- a skill can describe when it should be used
- a skill can declare required tools/connectors
- runtime can load skill instructions into an agent turn
- missing required capability produces a clear blocker
- skill behavior can be evaluated with fixtures

Evaluation:

- unit test: skill manifest loads
- unit test: required connector check
- integration test: selected skill changes model prompt
- eval: malformed/missing skill package fails safely

## Milestone 6: Memory And Resource Layer

Goal: make ideas, user preferences, standing goals, and external documents durable and queryable.

Scope:

- standing orders and user preferences
- idea capture records
- tags, links, and follow-up questions
- Obsidian connector/resource store
- periodic synthesis inputs
- lightweight retrieval

Modules:

- `agentic/memory/`
- `agentic/resources/obsidian.py`
- `agentic/synthesis/`

Acceptance criteria:

- user can send an idea from chat/mobile
- harness stores it with tags, source, timestamp, and open questions
- harness can link a new idea to prior notes
- periodic synthesis can produce a short insight report
- Obsidian export/import path is explicit and reversible

Evaluation:

- integration test: inbound idea creates memory record
- eval: generated follow-up question is relevant
- eval: synthesis references multiple stored ideas
- manual test: Obsidian note appears in expected vault location

## Milestone 7: Newsletter And Research Workflows

Goal: turn incoming newsletters and web material into goal-directed analysis.

Scope:

- Gmail connector or MCP-backed mail resource
- newsletter ingestion and deduplication
- standing analysis goals
- citation/source retention
- report generation
- approval before sending or archiving mail

Modules:

- `agentic/connectors/gmail.py`
- `agentic/workflows/newsletter.py`
- `skills/newsletter_analysis/`

Acceptance criteria:

- harness can identify WSJ newsletter emails
- extracted content is stored as a resource
- analysis can be run against a named goal
- output separates facts, model judgments, and follow-up tasks
- citations point back to source email/resource

Evaluation:

- fixture test: sample newsletter parsed
- eval: startup idea extraction returns grounded ideas
- eval: portfolio relevance analysis includes confidence and reasons
- policy test: authenticated mail action requires approval

## Milestone 8: Browser Automation Workbench

Goal: support agent-assisted creation and supervision of Playwright/Chromium automations.

Scope:

- browser connector/tool wrapper
- credential reference model
- script generation workspace
- supervised trial-and-error loop
- screenshot/log capture
- background watcher integration
- notification on event match

Modules:

- `agentic/connectors/browser.py`
- `agentic/workflows/browser_macro.py`
- `agentic/credentials/`
- `macros/`

Acceptance criteria:

- user can provide URL plus credential reference
- harness can inspect the page through Playwright
- generated watcher script is stored as an artifact
- script can run in background task pool
- watcher can notify user on target condition
- booking/purchase actions require explicit approval

Evaluation:

- fake site test: watcher detects available seat
- integration test: Playwright run emits screenshots and trace events
- policy test: submit/purchase action requires approval
- recovery test: browser task can restart after crash

## Milestone 9: Coding Agent Workflow

Goal: let the harness improve itself and work on repositories with bounded autonomy.

Scope:

- repo inspection skill
- plan/patch/test/summarize workflow
- shell/git/file tools behind approval policy
- test runner integration
- code review and self-review loop
- branch/task isolation

Modules:

- `agentic/workflows/coding.py`
- `agentic/tools/shell.py`
- `agentic/tools/git.py`
- `skills/coding_loop/`

Acceptance criteria:

- harness can inspect its own repo and propose a scoped plan
- file edits are traceable
- tests run and output is summarized
- risky shell/git actions require approval
- final report lists changed files and verification

Evaluation:

- fixture repo test: fix a simple bug
- integration test: patch + test + trace
- policy test: destructive git command is blocked without approval

## Milestone 10: 24/7 Hardening

Goal: make the system reliable enough to run continuously.

Scope:

- daemon/service management
- restart recovery
- GPU/RAM usage guardrails
- logs and dashboard
- alerting
- backup/export
- model unloading policy

Modules:

- `agentic/ops/`
- `agentic/app/dashboard.py`
- `agentic/models/resource_manager.py`

Acceptance criteria:

- service can restart without losing active tasks
- memory/GPU pressure is detected
- runaway task can be stopped
- dashboard shows health, active tasks, pending approvals, recent traces
- critical failures send ntfy notifications

Evaluation:

- soak test: daemon runs overnight
- restart test: active task recovered
- pressure test: model/resource manager avoids concurrent VRAM overload
- backup test: memory/task state can be exported and restored

## Non-Goals Until Later

- multi-provider model gateway
- public plugin marketplace
- remote multi-user deployment
- automatic purchasing/booking without explicit approval
- complex distributed orchestration
- cloud-first storage
