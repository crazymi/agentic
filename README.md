# agentic

Personal local-first agent harness for a single RTX 4090 machine.

This repository is building a **framework**, not a bundle of one-off automations. Concrete workflows such as WSJ newsletter analysis, social trend monitoring, idea synthesis, browser watching, and coding assistance are validation probes for reusable harness primitives.

The project intentionally avoids becoming a public provider gateway, plugin marketplace, multi-user server, or cloud-first automation platform.

## Current Status

Implemented baseline:

- Phase 0: module proof for local GGUF provider, prompt builder, tool parser, local arithmetic tool, task object, trace logger, and evals.
- Phase 1: minimal master/subagent/tool loop with trace and final answer.

Implemented active milestones:

- M2: Channel and Approval Core
- M3: Durable Runtime and Background Task Pool
- M4: Connector and MCP Boundary
- M5: Skill System
- M6: Memory and Resource Layer
- M7: Workflow Kernel
- M8: Source, Capability, and Artifact Runtime
- M9: Workflow Probe Pack

Current roadmap milestone:

- M10: 24/7 Hardening, in progress.
- M11: Interactive Browser Transaction Runtime, started with planning/tooling backbone.

## Implemented Capabilities

### Local Model Runtime

- Single local GGUF provider path through `LocalGGUFProvider`.
- Master model role and subagent model role.
- Config-driven model paths and runner commands via `config/config.toml`.
- Prompt directory support via `prompts/`.
- Chat template/system prompt handling for configured local runners.
- Response sanitizer for model channel markers.
- Real configured model paths for smoke runs; unit tests use local subprocess fixtures only inside evals.

Configured model candidates:

- `master-gemma-q4`: `models/gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf`
- `master-gemma-iq2`: `models/gemma-4-26B-A4B-it-UD-IQ2_XXS.gguf`
- `subagent-diffusiongemma-q4`: `models/diffusiongemma-26B-A4B-it-Q4_K_M.gguf`

### Agent Loop

- Master agent turn loop.
- Subagent task creation and execution loop.
- Tool-call parser and local `add(a, b)` arithmetic tool.
- Full-loop runtime from user message to model/delegation/tool/final response.
- Programmatic trace/replay checks.
- CLI `ask` and `chat` commands.

### Channel And Approval

- FastAPI local web UI.
- Chat form and recent message display.
- Pending approval list with approve/deny buttons.
- ntfy channel implementation with injected test transport support for evals.
- `ApprovalRequest` lifecycle and JSONL-backed approval store.
- Deterministic policy engine for sensitive capabilities.
- Approval-aware tool bridge.
- Trace events for channel messages, approvals, and tool blocking.

### Durable Runtime

- SQLite durable task store at `traces/state/agentic.sqlite3`.
- Durable task state machine.
- Bounded worker pool.
- Background `chat_turn` task enqueue from web messages.
- Heartbeat, watchdog, pause/resume/cancel, and restart recovery.
- Task routes and task status UI.

### Operational Health

- `HealthMonitor` snapshot for task, workflow, source, artifact, approval, and task-pool state.
- `GET /ops/health` JSON endpoint.
- Web UI health panel with component status, warnings, recent failures, and export button.
- `POST /ops/health/export` writes a restart-safe JSON health snapshot.
- CLI `ops-status` prints operational health JSON from local SQLite/JSONL state.

### Connectors And MCP Boundary

- Connector capability model for tools/resources/prompts.
- Connector registry.
- Connector tool bridge through policy.
- MCP stdio JSON-RPC client adapter.
- Local stdio MCP fixture evals.
- Curated disabled-by-default MCP catalog at `config/mcp_catalog.toml`.
- MCP/skill preparation notes at `docs/mcp_skill_catalog.md`.

### Skills

- Local instruction-only `skills/<name>/SKILL.md` packages.
- Skill manifest parser.
- Skill registry and routing by keyword/task kind.
- Requirement checks for needed tools/connectors/resources.
- Prompt context builder.

Prepared local skills include:

- `idea-capture`
- `newsletter-analysis`
- `browser-macro-planning`
- `repo-inspect`
- `coding-loop`
- `web-research`
- `gmail-newsletter-analysis`
- `obsidian-knowledge-linking`
- `browser-watcher`
- `mcp-safety-review`
- `credential-handling`

### Memory And Resources

- SQLite `MemoryStore`.
- SQLite `ResourceStore`.
- Memory kinds for ideas, preferences, standing goals, follow-up questions, and insights.
- Idea capture helper.
- Standing goal prompt context.
- Resource citation metadata.
- Local Obsidian markdown connector skeleton.
- Simple idea synthesis.

### Workflow Kernel

- Intent router for immediate answer, one-off task, deep research, workflow design, scheduled workflow, watcher workflow, browser transaction, coding workflow, and unknown.
- Workflow design session and proposal renderer.
- Durable planning session store for multi-turn workflow design.
- Planning-session answer route that can advance a vague request into a reviewed workflow proposal.
- Workflow design local source binding for checked-in newsletter/feed/idea/page/repo sources.
- Durable SQLite `WorkflowSpec` and `WorkflowRun` store.
- Workflow lifecycle validation.
- Capability planner and admission outcomes.
- Browser transaction step representation for user checkpoints, browser observe, browser action, approval, report, and retry-ready triggers.
- Workflow interpreter v0 for real source collect/analyze/aggregate/report/notify steps.
- Workflow builder.
- Scheduler store and due-runner v0.
- Local web UI/API for workflow design, approve, activate, pause, run, and status.

### Tooling Backlog

- `ToolingPlanner` converts capability gaps into concrete harness build requests.
- SQLite `ToolingBacklogStore` persists proposed tooling work.
- Missing browser capabilities such as `connector:browser` become backlog items instead of silent failures.
- Approval-required capabilities become policy/approval backlog items when a workflow needs them.
- Web UI/API surfaces tooling requests beside planning sessions and workflow runs.

### Source, Capability, And Artifact Runtime

- Source definitions and source policies.
- Source item model with dedupe fingerprints.
- SQLite `SourceStore`.
- Local file, mail-like JSONL, feed-like JSONL, browser-page-file, and repo-state collectors.
- `SourceRuntime` that writes raw source items into `ResourceStore`.
- Credential reference model and SQLite store.
- Secret-like metadata/reference rejection for sources and credentials.
- Artifact registry for reports, scripts, screenshots, datasets, configs, and logs.
- Artifact admission service.
- Generated script/config review gate.
- Dry-run gate that never executes script code.
- Policy gates for generated scripts, browser submit, email send, file write, shell, booking, payment, and external connectors.

### Workflow Probe Pack

The probe pack validates the harness shape without adding bespoke runtime paths:

- Newsletter analysis probe.
- Social trend intelligence probe.
- Idea synthesis probe.
- Browser watcher probe with review-required generated script artifact.
- Coding workflow probe.

Every probe is represented as a `WorkflowSpec`, uses checked-in local source files or current repository state, writes raw resources, and produces report artifacts through the Workflow Kernel.

## What Is Not Implemented Yet

Production integrations are intentionally deferred:

- No live Gmail OAuth connector.
- No production WSJ ingestion.
- No production Reddit/DCInside crawler.
- No live Playwright browser automation execution.
- No live browser transaction adapter yet; browser workflows currently produce planning sessions, workflow specs, capability gaps, and tooling backlog.
- No shell/file/git coding agent with broad powers.
- No autonomous script execution.
- No public auth or multi-user deployment.
- No plugin marketplace.
- No multi-provider model gateway.
- No service manager/systemd unit, overnight soak result, GPU pressure manager, or production alert routing yet.

Anything externally visible, destructive, paid, authenticated, or account-mutating must pass deterministic policy and approval before execution.

## Repository Map

Core modules:

- `agentic/app/`: CLI, web server, channel app, HTML templates.
- `agentic/agents/`: master and subagent wrappers.
- `agentic/models/`: local GGUF provider and response sanitizer.
- `agentic/runtime/`: full loop, durable runtime, worker pool, task control, heartbeat.
- `agentic/tasks/`: durable tasks and legacy subagent task objects.
- `agentic/tools/`: local typed tools and parser.
- `agentic/policy/`: deterministic policy rules.
- `agentic/approvals/`: approval models, service, and store.
- `agentic/channels/`: channel abstractions and ntfy.
- `agentic/connectors/`: connector/MCP boundary.
- `agentic/ops/`: operational health snapshots and status export.
- `agentic/skills/`: skill loader and router.
- `agentic/memory/`: user memory and standing orders.
- `agentic/resources/`: resource records, store, and Obsidian skeleton.
- `agentic/workflow_kernel/`: intent, workflow specs/runs, designer, capability planner, interpreter.
- `agentic/tooling/`: tooling gap planner and durable tooling backlog.
- `agentic/scheduler/`: schedule model/store/runner.
- `agentic/sources/`: source definitions, source items, local collectors, source runtime.
- `agentic/credentials/`: secret-free credential references.
- `agentic/artifacts/`: artifact store and admission.
- `agentic/workflow_probes/`: M9 framework probe pack.

Important docs:

- `docs/roadmap.md`
- `docs/architecture.md`
- `docs/user_requirements.md`
- `docs/workflow_kernel_design.md`
- `docs/framework_reference_review.md`
- `docs/mcp_skill_catalog.md`
- `docs/milestone10_status.md`
- `docs/milestone11_browser_transaction_runtime_plan.md`
- `docs/milestone11_status.md`
- `docs/work_log.md`
- `docs/legacy/`

## Core Commands

This project uses `uv`. The current `.venv` is already prepared, so use the venv Python directly.

Run the default eval suite:

```bash
.venv/bin/python -m unittest discover -s evals
```

Check config, prompt files, and local GGUF model paths:

```bash
.venv/bin/python -m agentic.app.cli config-check
```

Print version:

```bash
.venv/bin/python -m agentic.app.cli --version
```

Run one full-loop agent turn:

```bash
.venv/bin/python -m agentic.app.cli ask "1+1은 뭐지?"
```

Start the simple full-loop REPL:

```bash
.venv/bin/python -m agentic.app.cli chat
```

Start the local web channel:

```bash
.venv/bin/python -m agentic.app.cli serve --host 127.0.0.1 --port 8765
```

Print operational health from local runtime state:

```bash
.venv/bin/python -m agentic.app.cli ops-status
```

Run a repeatable operational smoke check:

```bash
.venv/bin/python -m agentic.app.cli ops-smoke
```

Run operational smoke plus a real configured model call:

```bash
.venv/bin/python -m agentic.app.cli ops-smoke --include-model --model master-gemma-q4 --model-max-tokens 256
```

List configured model candidates:

```bash
.venv/bin/python -m agentic.app.cli list-models
```

Check local runner prerequisites:

```bash
.venv/bin/python -m agentic.app.cli runner-check
```

If `uv` is installed, equivalent commands can be run as:

```bash
uv run python -m unittest discover -s evals
uv run python -m agentic.app.cli config-check
uv run python -m agentic.app.cli serve --host 127.0.0.1 --port 8765
```

## Local Model Smoke Path

The real GGUF paths and CUDA runner commands are wired through:

```bash
config/config.toml
```

Configured runner binaries:

- Gemma master models: `runtimes/llama.cpp/build-cuda/bin/llama-completion`
- DiffusionGemma subagent: DiffusionGemma PR runner `llama-diffusion-cli`

Master Gemma models are configured with `--jinja --single-turn` and `prompts/master_phase1.md` as the system prompt. DiffusionGemma is run through the diffusion CLI with `prompts/subagent_phase1.md` as the system prompt and entropy-bound decoding.

Build or refresh the CUDA runners with conservative parallelism:

```bash
MAX_JOBS=2 CMAKE_BUILD_PARALLEL_LEVEL=2 MAKEFLAGS="-j2" bash scripts/build_llama_cuda.sh
```

Run real GPU smoke checks:

```bash
.venv/bin/python -m agentic.app.cli smoke --model master-gemma-q4 --max-tokens 256 --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."
.venv/bin/python -m agentic.app.cli smoke --model master-gemma-iq2 --max-tokens 384 --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."
.venv/bin/python -m agentic.app.cli smoke --model subagent-diffusiongemma-q4 --max-tokens 256 --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."
```

If running inside a sandboxed tool context, GPU access may be blocked. In that case, run smoke checks in a normal WSL shell.

Run opt-in real-model evals:

```bash
AGENTIC_RUN_REAL_MODELS=1 .venv/bin/python -m unittest evals.test_real_models
AGENTIC_RUN_REAL_PHASE1=1 .venv/bin/python -m unittest evals.test_phase1_real_full_loop
```

Default tests skip real model execution so normal development stays fast.

## Runtime State

Default local state paths:

- durable task DB: `traces/state/agentic.sqlite3`
- workflow DB: `traces/state/workflows.sqlite3`
- artifact DB: `traces/state/artifacts.sqlite3`
- approval JSONL: `traces/state/approvals.jsonl`
- traces: configured by `config/config.toml`

State files under `traces/` are local runtime data and are not intended as source-controlled fixtures.

## WSL Memory

Recommended WSL allocation for this project on a 32GB RAM / 24GB VRAM RTX 4090 machine:

- minimum usable: 24GB RAM with swap enabled
- preferred for 24/7 harness work: 24GB RAM, 32GB swap, build parallelism capped at `-j2` or `-j4`
- avoid: 16GB RAM for CUDA builds or simultaneous model experimentation

Do not run master Q4 and subagent Q4 concurrently on a 24GB GPU unless the runtime is explicitly designed to unload one before loading the other.

## Verification Status

Latest default verification:

```bash
.venv/bin/python -m unittest discover -s evals
# 153 tests passing, 2 skipped

.venv/bin/python -m agentic.app.cli config-check
# passing

.venv/bin/python -m agentic.app.cli ops-smoke --include-model --model master-gemma-q4 --model-max-tokens 256
# passing
```
