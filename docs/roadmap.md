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

- Phase 0 completed: module-level proof of the local GGUF provider, prompt builder, tool parser, local arithmetic tool, task object, trace logger, and evals.
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
| Experience Loop | Convert attempts, failures, bottlenecks, and lessons into reusable state | requirement smoke, tooling backlog, skill proposals, roadmap updates |

OpenClaw separates concepts such as skills, plugins, and automation. MCP standardizes external capability exposure through servers and capabilities such as tools, resources, prompts, lifecycle, and discovery. This harness borrows those shapes but keeps the implementation local, small, and personal.

References:

- OpenClaw Skills: https://docs.openclaw.ai/tools/skills
- OpenClaw Plugin: https://docs.openclaw.ai/tools/plugin
- OpenClaw Automation: https://docs.openclaw.ai/automation
- Model Context Protocol architecture: https://modelcontextprotocol.io/docs/concepts/architecture

## Cross-Cutting: Experience Loop

Goal: prevent agent work from remaining one-off by recording what was tried, what evidence was observed, where the harness got stuck, and which reusable primitive should be added next.

Scope:

- structured `ExperienceEvent` JSONL log
- script-only requirement probes
- bottleneck extraction
- conversion of capability gaps into tooling backlog
- retrieval command for recent experience
- docs/work-log updates after substantive work

Modules:

- `agentic/experience/`
- `agentic/tooling/`
- `docs/work_log.md`
- `docs/experience_loop.md`
- `docs/requirements_smoke_status.md`

Acceptance criteria:

- user-shaped requirements can be smoke-tested without UI
- each probe reports current level: completed, blocked by approval, blocked by tooling, or needs input
- smoke results are appended to `traces/experience.jsonl`
- repeated bottlenecks are visible as durable data, not chat-only memory
- default tests do not require live network, real browser, live ntfy, Gmail, or GPU
- real user-requirement benchmarks use `real-bench` and must not count fake, dummy, synthetic, fixture, or preapproved shortcuts as completed capability

Evaluation:

- `.venv/bin/python -m agentic.app.cli requirements-smoke`
- `.venv/bin/python -m agentic.app.cli real-bench`
- `.venv/bin/python -m agentic.app.cli experience-list --limit 20`
- evals covering experience store and requirement smoke

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

- connector discovery test: tools/resources/prompts discovery
- local MCP stdio protocol test: call one tool through adapter
- policy test: connector tool requiring approval cannot bypass approval
- real-bench follow-up: live connector paths report credentials, network, or tooling blockers explicitly

## Milestone 5: Skill System

Goal: represent reusable procedures separately from executable tools.

Scope:

- skill package format
- skill loader
- skill routing metadata
- skill prompt injection
- required tools/connectors declaration
- skill eval scenarios
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
- skill behavior can be evaluated with real or clearly bounded developer scenarios

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

## Milestone 7: Workflow Kernel

Goal: create the framework layer that turns vague natural-language requests into reviewed, durable, runnable workflows.

Scope:

- request intent classification
- workflow design sessions and proposal review
- durable workflow specs and run records
- workflow lifecycle and versioning
- capability planning and admission
- workflow builder and interpreter v0
- scheduler/hook interface v0
- web UI for proposals, activation, pause, and run status

Modules:

- `agentic/workflow_kernel/`
- `agentic/scheduler/`
- `agentic/artifacts/`
- `agentic/app/server.py`

Acceptance criteria:

- harness can classify a request as immediate, one-off task, deep research, scheduled workflow, watcher workflow, coding workflow, or unknown
- harness can turn a vague recurring request into a workflow design session
- designer asks one missing-info question at a time
- proposed workflow can be approved, persisted, activated, paused, and retired
- approved workflow can run through real local-source collect/analyze/report steps
- sensitive capabilities require deterministic policy and approval

Evaluation:

- intent router tests across example request classes
- workflow lifecycle transition tests
- local-source workflow execution test
- policy/admission tests for generated scripts and external actions
- probe tests proving newsletter, social trend, idea synthesis, browser watcher, and coding requests can be represented as workflow specs

Plan:

- See `docs/milestone7_workflow_kernel_plan.md`.
- See `docs/workflow_kernel_design.md`.
- See `docs/framework_reference_review.md`.

## Milestone 8: Source, Capability, And Artifact Runtime

Goal: make workflow specs useful by connecting them to reviewed source connectors, generated artifacts, and capability admission.

Scope:

- source connector abstraction for web pages, feeds, Gmail-like mail, browser pages, local files, and repo state
- artifact registry for generated scripts, crawler configs, reports, screenshots, and datasets
- generated script review and dry-run path
- connector/MCP allowlist activation
- credential reference model
- rate limit, dedupe, and retention policies

Modules:

- `agentic/sources/`
- `agentic/artifacts/`
- `agentic/credentials/`
- `agentic/connectors/`
- `agentic/policy/`

Acceptance criteria:

- workflow can declare a source without hardcoding a vertical implementation
- source collection can store raw resources and derived artifacts
- generated script cannot run before admission and approval
- connector/MCP activation is allowlisted and traceable
- credential values never enter prompts, docs, traces, or specs

Evaluation:

- local source connector tests
- artifact admission tests
- credential reference tests
- policy tests for browser submit, email send, file write, shell, booking, payment, and generated script execution

## Milestone 9: Workflow Probe Pack

Goal: validate the framework with real user-shaped probes without letting any one probe become the architecture.

Probe scenarios:

- newsletter analysis: scheduled mail-like source ingestion, grounded analysis, report, notification
- social trend intelligence: scheduled community source collection, dedupe, trend rollup, report
- idea synthesis: channel capture, memory write, note linking, periodic synthesis
- browser watcher: browser/page source inspection, condition detection, alert, optional generated watcher artifact
- coding workflow: repo inspection, plan, patch, test, report, approval for risky actions

Acceptance criteria:

- each probe is represented as a `WorkflowSpec`
- at least one run per probe can execute with checked-in local sources or current repository state
- no probe adds a bespoke daemon, scheduler, or top-level runtime path
- reports and artifacts are linked to workflow runs and traces

Evaluation:

- real-bench coverage per user-shaped probe
- full local-source end-to-end eval from request shape to approved run
- regression check that existing Phase 1, M2, M3, M4, M5, and M6 behavior still works

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

## Milestone 11: Interactive Browser Transaction Runtime

Goal: make high-risk, login-gated browser workflows possible without turning any one site into a bespoke automation path.

Validation probe:

- "MSI 2026 결승전 표 예매해줘"

Scope:

- durable planning sessions for blurry user requests and follow-up answers
- browser transaction intent classification
- browser observe/action capability model
- live browser adapter boundary
- user input checkpoints for login, captcha/manual verification, and missing slots
- approval-resumable workflow runs
- retry/watch mode for not-yet-open, sold-out, queue, and transient failure states

Modules:

- `agentic/workflow_kernel/planning_session.py`
- `agentic/browser/`
- `agentic/workflow_kernel/interpreter.py`
- `agentic/scheduler/`
- `agentic/app/server.py`

Acceptance criteria:

- vague booking request opens a planning session instead of falling through the Phase 1 loop
- designer asks one missing slot at a time and stores follow-up answers
- official source discovery produces a reviewed source/platform candidate
- workflow can pause at `login_required` and resume after the user confirms login
- browser observe/action steps save screenshots and DOM snapshots as artifacts
- booking/payment/submit actions require fresh explicit approval
- sold-out or unavailable states create durable retry attempts with rate limits
- real benchmark reports missing URL, missing live adapter, or live browser progress without fabricating state

Evaluation:

- real-bench ticket probe: missing URL requests user input
- real-bench ticket probe: provided URL is blocked until live adapter exists
- restart test: waiting and retrying workflow survives process restart
- policy test: unapproved submit/payment is blocked

Plan:

- See `docs/milestone11_browser_transaction_runtime_plan.md`.

## Non-Goals Until Later

- multi-provider model gateway
- public plugin marketplace
- remote multi-user deployment
- automatic purchasing/booking without explicit approval
- complex distributed orchestration
- cloud-first storage
