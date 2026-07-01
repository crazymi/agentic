# Work Log

This log records substantive project work. Keep the table of contents updated when adding entries.

## Table Of Contents

- [2026-07-01 11:40 KST - M7 Workflow Kernel Implementation](#2026-07-01-1140-kst---m7-workflow-kernel-implementation)
- [2026-07-01 11:58 KST - Roadmap Review And Work Log Rule](#2026-07-01-1158-kst---roadmap-review-and-work-log-rule)
- [2026-07-01 12:01 KST - M8 Source Capability And Artifact Runtime](#2026-07-01-1201-kst---m8-source-capability-and-artifact-runtime)
- [2026-07-01 12:11 KST - M9 Workflow Probe Pack](#2026-07-01-1211-kst---m9-workflow-probe-pack)
- [2026-07-01 12:51 KST - README Implementation Summary Refresh](#2026-07-01-1251-kst---readme-implementation-summary-refresh)
- [2026-07-01 13:38 KST - M10 Real-Only Runtime Boundary](#2026-07-01-1338-kst---m10-real-only-runtime-boundary)
- [2026-07-01 13:54 KST - M10 Operational Health Primitives](#2026-07-01-1354-kst---m10-operational-health-primitives)
- [2026-07-01 14:02 KST - Browser Smoke And Workflow Source Binding](#2026-07-01-1402-kst---browser-smoke-and-workflow-source-binding)
- [2026-07-01 14:14 KST - M10 Ops Smoke And Real GPU Model Validation](#2026-07-01-1414-kst---m10-ops-smoke-and-real-gpu-model-validation)
- [2026-07-01 14:28 KST - DeepResearch Ticket Booking Probe](#2026-07-01-1428-kst---deepresearch-ticket-booking-probe)
- [2026-07-01 14:39 KST - M11 Browser Transaction Runtime Design](#2026-07-01-1439-kst---m11-browser-transaction-runtime-design)
- [2026-07-01 15:10 KST - M11 Planning And Tooling Backbone](#2026-07-01-1510-kst---m11-planning-and-tooling-backbone)
- [2026-07-01 18:02 KST - Experience Loop And Requirement Smoke](#2026-07-01-1802-kst---experience-loop-and-requirement-smoke)
- [2026-07-01 18:19 KST - Autonomy Benchmark Review](#2026-07-01-1819-kst---autonomy-benchmark-review)
- [2026-07-01 18:30 KST - M11 Finish-Line Fixture Runtime](#2026-07-01-1830-kst---m11-finish-line-fixture-runtime)
- [2026-07-01 18:45 KST - Real Benchmark And Fake Path Removal](#2026-07-01-1845-kst---real-benchmark-and-fake-path-removal)

## 2026-07-01 11:40 KST - M7 Workflow Kernel Implementation

Summary:

- Implemented the M7 Workflow Kernel as a framework layer rather than a vertical newsletter/crawler feature.

Changed areas:

- Added `agentic/workflow_kernel/` for intent routing, workflow design, workflow specs/runs, capability planning, and interpreter/builder v0.
- Added `agentic/scheduler/` for schedule records, schedule store, and due-runner v0.
- Added `agentic/artifacts/` for report/script/screenshot/dataset/config/log artifact records.
- Extended the local web UI/API with workflow design, approve, activate, pause, run, and status routes.
- Updated M7 docs and roadmap to mark newsletter/social trend/browser/coding/idea workflows as probes.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M7 is implemented.
- M8 should focus on source connectors, capability runtime, credential references, artifact admission, and generated-script review/dry-run.

Next step:

- Implement M8 Source, Capability, And Artifact Runtime.

Lessons learned:

- The harness must keep workflow control flow outside individual agents. Agents provide intelligence inside steps; the workflow engine owns lifecycle.
- Generated scripts must be artifacts first, executable capabilities later, and only after admission plus approval.
- Vertical use cases should prove `WorkflowSpec` expressiveness, not create separate daemon paths.

## 2026-07-01 11:58 KST - Roadmap Review And Work Log Rule

Summary:

- Added durable project instructions requiring roadmap review, next-step reporting, lessons learned, and append-only work-log maintenance after each substantive task.

Changed areas:

- Added root `AGENTS.md`.
- Added this `docs/work_log.md` file with a maintained table of contents.

Verification:

- Documentation-only change. No code verification required beyond file inspection.

Roadmap impact:

- No milestone implementation changed.
- Project process now requires every completed work item to reconnect to the roadmap.

Next step:

- M8 Source, Capability, And Artifact Runtime remains the recommended next milestone.

Lessons learned:

- The project is moving fast enough that process memory matters. The work log prevents roadmap drift and preserves why each framework-level decision was made.

## 2026-07-01 12:01 KST - M8 Source Capability And Artifact Runtime

Summary:

- Implemented the M8 framework primitives that let workflows declare sources, collect fake/default-safe source items, store raw resources, hold credential references, and gate generated artifacts.

Changed areas:

- Added `agentic/sources/` for source definitions, source policies, source items, dedupe store, fake collector, and source runtime.
- Added `agentic/credentials/` for secret-free credential references and SQLite persistence.
- Added artifact admission and dry-run gating to `agentic/artifacts/`.
- Extended policy gates for generated scripts, external connectors, browser submit, email send, file write, shell, booking, and payment.
- Added `docs/milestone8_status.md`.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M8 is implemented as framework substrate.
- Production crawlers and live OAuth remain intentionally deferred to M9 probes or later production hardening.

Next step:

- Implement M9 Workflow Probe Pack using the M7/M8 primitives.

Lessons learned:

- Source collection needs a durable raw-item layer before analysis. Otherwise reports lose auditability.
- Credential handling should store references only; even metadata keys can leak secrets if not filtered.
- Generated scripts need admission and dry-run semantics before execution becomes a runtime capability.

## 2026-07-01 12:11 KST - M9 Workflow Probe Pack

Summary:

- Implemented M9 probes that validate the harness framework with user-shaped scenarios without introducing bespoke runtime paths.

Changed areas:

- Added `agentic/workflow_probes/` with probe models, factory, and runner.
- Added probe specs for newsletter analysis, social trend intelligence, idea synthesis, browser watcher, and coding workflow.
- Added fake/default-safe source definitions for every probe.
- Represented browser watcher generated script as a review-required artifact instead of an executable step.
- Added `docs/milestone9_status.md`.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M9 is implemented as framework validation.
- M10 should harden the local runtime for continuous operation.

Next step:

- Implement M10 24/7 Hardening.

Lessons learned:

- A probe pack is useful only if it proves the framework shape. Keeping all probes on `WorkflowSpec` exposed whether primitives were truly reusable.
- Browser automation must keep generated scripts as review artifacts until M10+ operational controls and approvals are stronger.
- Fake/default-safe probes let the full suite verify architecture without requiring network, GPU, real browser, or credentials.

## 2026-07-01 12:51 KST - README Implementation Summary Refresh

Summary:

- Rewrote `README.md` as a current implementation overview covering Phase 0/1 and M2 through M9.

Changed areas:

- Documented the project as a local-first agent harness framework rather than a collection of one-off automations.
- Summarized implemented modules for local models, agent loop, channel/approval, durable runtime, connectors/MCP boundary, skills, memory/resources, workflow kernel, sources/capabilities/artifacts, and workflow probes.
- Added explicit "not implemented yet" boundaries for live Gmail, WSJ, Reddit/DCInside crawling, Playwright execution, autonomous scripts, public auth, marketplace, and 24/7 hardening.
- Refreshed command examples, runtime state paths, GPU smoke paths, WSL memory guidance, and latest verification status.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- No implementation milestone changed.
- Documentation now reflects M9 as the current completed framework-validation milestone and M10 as the next hardening milestone.

Next step:

- Implement M10 24/7 Hardening: daemon reliability, startup/shutdown behavior, observability, operational safety, and manual long-running smoke checks.

Lessons learned:

- The README needs to distinguish framework primitives from deferred production integrations, otherwise the milestone list can sound more production-ready than it is.
- The project has enough modules now that a repository map is part of the product surface, not just documentation polish.

## 2026-07-01 13:38 KST - M10 Real-Only Runtime Boundary

Summary:

- Started M10 by removing product runtime paths that silently generated fake source/model/connector behavior and replacing workflow probes with real local source execution.

Changed areas:

- Removed `ModelConfig.fake()` and the CLI `smoke --fake` path.
- Removed runtime `FakeConnector` from the product connector package.
- Removed `SourceKind.FAKE` and the default fake source collector.
- Added local collectors for files, mail-like JSONL, feed-like JSONL, browser-page files, and repository state.
- Changed `WorkflowInterpreter` collect steps to require `SourceRuntime` and `ResourceStore`.
- Changed workflow probes to use checked-in local source files or current repo state.
- Added `evals/test_milestone10_real_e2e.py` for a source-backed collect -> aggregate -> analyze -> report flow.
- Updated README, roadmap, and milestone status docs to describe the real-only boundary.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M10 is started.
- The first hardening step is complete: product runtime paths should fail clearly when real configuration is missing instead of inventing success data.

Next step:

- M10 step 2 should add operational health primitives: process uptime, task-pool health, collector health, recent failure panels, restart-safe status export, and alert hooks.

Lessons learned:

- A harness can use local fixtures in evals, but the product runtime must not generate invented source data.
- Workflow proposals without source binding should be blocked or fail clearly; completing them with synthetic collect results hides the exact problems M10 is supposed to surface.

## 2026-07-01 13:54 KST - M10 Operational Health Primitives

Summary:

- Added the first production-facing operational health layer for the local harness.

Changed areas:

- Added `agentic/ops/` with `HealthMonitor`, `HealthSnapshot`, and `RuntimeHealthStatus`.
- Health snapshots now summarize task, workflow, source, artifact, approval, and task-pool status.
- Added recent task/workflow failure reporting.
- Added missing enabled local-source warnings.
- Added `GET /ops/health` and `POST /ops/health/export`.
- Added an Ops Health panel to the web UI.
- Added CLI `ops-status`.
- Added `evals/test_milestone10_ops_health.py`.
- Updated README and `docs/milestone10_status.md`.

Verification:

- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- `.venv/bin/python -m agentic.app.cli ops-status`
- `timeout 5s .venv/bin/python -m agentic.app.cli serve --host 127.0.0.1 --port 8890`

Roadmap impact:

- M10 step 2 is complete.
- The harness now has a concrete operational surface for observing whether local runtime pieces are healthy, degraded, or unhealthy.

Next step:

- M10 step 3 should harden service lifecycle: graceful shutdown timing, restart smoke script, health-based exit checks, and manual long-running serve/worker smoke checklist.

Lessons learned:

- A local daemon needs a status surface before more automation is added; otherwise failures only appear as scattered traces.
- CLI health without a running server can be degraded because no task pool is attached. That distinction is useful because it tells us whether we are inspecting state offline or observing the live service.

## 2026-07-01 14:02 KST - Browser Smoke And Workflow Source Binding

Summary:

- Attempted Chrome plugin validation, found a Chrome bridge runtime blocker, then completed real HTTP/UI-path validation and fixed workflow design source binding.

Changed areas:

- Added `agentic/workflow_kernel/source_binding.py`.
- Web workflow design now binds known request sources to checked-in local sources or current repo state before persisting the `WorkflowSpec`.
- Updated server/channel app wiring to pass `SourceStore` into workflow design.
- Updated milestone docs and README.

Verification:

- Attempted Chrome plugin via `mcp__node_repl.js`; blocked by `codex/sandbox-state-meta: sandboxCwd is not a local file URI`.
- Started `serve` on `127.0.0.1:8891`.
- Executed real HTTP flow: workflow design -> approve -> activate -> run.
- Confirmed social trend workflow bound `community_web` to `examples/sources/market_community_posts.jsonl`.
- Confirmed run completed and created report artifact.
- Confirmed `GET /ops/health` returned `ok`.
- Confirmed `POST /ops/health/export` wrote `traces/state/health_snapshot.json`.
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M10 operational smoke exposed and fixed the gap between workflow design and real source execution.
- Chrome plugin validation remains blocked by the local tool bridge, not by the harness server.

Next step:

- M10 step 3 should add service lifecycle hardening and a repeatable browser/HTTP smoke checklist.

Lessons learned:

- Workflow design is not operational until its abstract source is bound to a concrete source record.
- Smoke tests are more useful when they include the web route sequence, not only unit-level workflow execution.

## 2026-07-01 14:14 KST - M10 Ops Smoke And Real GPU Model Validation

Summary:

- Added repeatable operational smoke checks and validated the configured local models on the RTX 4090 path.

Changed areas:

- Added `agentic/ops/smoke.py`.
- Added CLI `ops-smoke`.
- Added `ops-smoke --include-model --model ... --model-max-tokens ...`.
- Fixed `response_sanitizer` to preserve complete master decision JSON.
- Added safe extraction for explicit direct answers inside internal model text without exposing the full internal text.
- Added `evals/test_milestone10_ops_smoke.py`.
- Updated README and `docs/milestone10_status.md`.

Verification:

- `.venv/bin/python -m agentic.app.cli ops-smoke`
- `.venv/bin/python -m agentic.app.cli ops-smoke --include-model --model master-gemma-q4 --model-max-tokens 256`
- `.venv/bin/python -m agentic.app.cli smoke --model master-gemma-iq2 --max-tokens 192 --prompt '한국의 수도는 어디야? 답변만 한 문장으로 말해.'`
- `.venv/bin/python -m agentic.app.cli smoke --model master-gemma-q4 --max-tokens 256 --prompt '한국의 수도는 어디야? 답변만 한 문장으로 말해.'`
- `.venv/bin/python -m agentic.app.cli smoke --model subagent-diffusiongemma-q4 --max-tokens 64 --prompt 'Use add to compute 7+5. Return only the tool call JSON.'`
- `.venv/bin/python -m agentic.app.cli ask '7+5는 뭐지?'`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M10 step 3 is complete.
- The harness now has a repeatable operational smoke command and proof that the configured local GPU model path can execute the minimal master/subagent/tool loop.

Next step:

- M10 step 4 should harden service lifecycle: graceful shutdown timing, restart smoke scripts, health-based exit checks, and a longer running serve/worker soak checklist.

Lessons learned:

- Real model smoke exposed a sanitizer bug that unit tests had not caught: complete master decision JSON must be preserved for the harness loop.
- IQ2 needs more generation budget than the default short smoke for this prompt; `--max-tokens 192` produced the expected answer.
- DiffusionGemma Q4 can produce the intended tool-call JSON for the subagent role, and the full loop now completes with real GPU model calls.

## 2026-07-01 14:28 KST - DeepResearch Ticket Booking Probe

Summary:

- Ran a live probe for the blurry request "MSI 2026 결승전 표 예매해줘" across the current Master path, workflow-design path, local web UI/API, and notification boundary.

Changed areas:

- Documentation-only log entry. No code changes were made in this probe.

Verification:

- Attempted Chrome plugin control; blocked by `codex/sandbox-state-meta: sandboxCwd is not a local file URI`.
- Searched current public sources for MSI 2026 ticketing. LoL Esports shows MSI running June 28 to July 12, 2026, but no official ticketing page was found through search/Ticketlink/Interpark queries.
- Ran real GPU Master full loop: `.venv/bin/python -m agentic.app.cli ask 'MSI 2026 결승전 표 예매해줘'`; current Phase 1 path returned "답변을 정리하지 못했습니다."
- Ran real GPU Master raw smoke with `max_tokens=512`; Master correctly delegated research for official ticketing schedule/platform discovery.
- Submitted the blurry request to the web workflow designer on `127.0.0.1:8892`; it asked for a source/URL, proving partial interview behavior.
- Submitted a natural follow-up mentioning official ticket site discovery and ntfy; the designer proposed a high-risk Browser Watcher workflow.
- Approved, activated, and ran the proposal; capability planning stopped at `waiting_for_approval` for `channel:ntfy`.
- Attempted notify-user ntfy push. Sandbox DNS failed first, and escalated network egress was rejected by policy for external data transfer to ntfy.sh.

Roadmap impact:

- This probe confirms the next M10 work should not be another vertical automation. It should add framework primitives for interactive planning sessions, browser capability execution, login/input checkpoints, and approval-resumable workflow runs.

Next step:

- Implement the `Interactive Planning And Browser Action Runtime` slice: session-backed workflow design, `ASK_USER` runtime support, browser-action capability specs, credential/login checkpoints, approval-to-resume for waiting workflow runs, and a real browser adapter boundary.

Lessons learned:

- The local Master can reason about ticket booking when given enough generation budget, but the Phase 1 prompt/loop is not the right route for high-risk multi-step work.
- The workflow designer has the beginning of grilling/interview behavior, but it is stateless; follow-up answers must attach to a design session.
- High-risk tasks need first-class `ASK_USER`, `APPROVAL`, and `BROWSER_ACTION` primitives before the harness can safely attempt login-gated ticketing.
- ntfy is configured conceptually, but external delivery can be blocked by policy; the harness needs a local notification fallback and a clear external-egress approval story.

## 2026-07-01 14:39 KST - M11 Browser Transaction Runtime Design

Summary:

- Designed the framework gap needed for the MSI 2026 ticket booking workflow and converted it into a reusable browser transaction runtime milestone.

Changed areas:

- Added `docs/milestone11_browser_transaction_runtime_plan.md`.
- Updated `docs/roadmap.md` with Milestone 11: Interactive Browser Transaction Runtime.

Verification:

- Reviewed the current roadmap and M10 status.
- Rechecked current LoL Esports MSI 2026 public information: Daejeon Convention Center II, Grand Final on July 12, 2026, and NOL World ticket sales waves.
- Documentation-only change; no code tests were required.

Roadmap impact:

- M11 is now the next framework milestone after M10 hardening.
- The MSI ticket request is explicitly treated as a validation probe for planning sessions, live browser actions, login checkpoints, approval resume, and watcher retry primitives.

Next step:

- Implement M11-A through M11-F, starting with durable planning sessions and browser transaction intent routing.

Lessons learned:

- A ticket booking workflow is not a scraper plus click macro. It is a high-risk transaction workflow with official-source verification, user presence, approvals, and retryable state handling.
- The agent should not run continuously in 24/7 mode. Deterministic observation and state hashing should run cheaply, while model calls happen only on ambiguity or state changes.
- The reusable framework shape is `observe -> classify -> policy -> ask/act -> record -> retry`, not an MSI-specific script.

## 2026-07-01 15:10 KST - M11 Planning And Tooling Backbone

Summary:

- Implemented the first M11 backbone slice so blurry automation requests can become durable planning sessions, browser transaction workflow specs, and explicit tooling backlog items.

Changed areas:

- Added `IntentType.BROWSER_TRANSACTION`.
- Added `StepType.BROWSER_OBSERVE` and `StepType.BROWSER_ACTION`.
- Updated intent routing for ticket/booking/purchase/browser transaction requests.
- Extended `WorkflowDesigner` with browser transaction slot extraction and multi-turn continuation.
- Added `PlanningSessionStore`.
- Added `agentic/tooling/` with tooling request models, planner, and SQLite backlog store.
- Wired planning sessions and tooling backlog into the FastAPI app and web UI.
- Added `evals/test_milestone11_harness_backbone.py`.
- Updated README and added `docs/milestone11_status.md`.

Verification:

- `.venv/bin/python -m unittest evals.test_milestone11_harness_backbone`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`

Roadmap impact:

- M11 is now implemented at the backbone level.
- The harness can now represent "I need new tooling/capabilities before I can execute this workflow" as durable state instead of losing it as an ad hoc blocker.

Next step:

- Implement M11 runtime execution: executable `ASK_USER`, workflow pause/resume, approval-resume, local browser observation adapter with fixture pages, and retry state for unavailable/sold-out/browser-blocked states.

Lessons learned:

- The missing layer was not another connector; it was a durable translation layer from capability gaps to buildable tooling backlog.
- Planning sessions are the core bridge between blurry user intent and executable workflow specs.
- For 24/7 automation, the harness needs to remember both workflow state and tooling debt. Otherwise the agent cannot improve its environment over time.

## 2026-07-01 18:02 KST - Experience Loop And Requirement Smoke

Summary:

- Added a structured experience loop and script-only requirement smoke runner so user-shaped automation probes continuously produce reusable lessons and bottleneck data.

Changed areas:

- Added `agentic/experience/` with experience events, JSONL store, requirement probes, and requirement smoke runner.
- Added CLI commands:
  - `requirements-smoke`
  - `experience-list`
- Added `evals/test_experience_loop.py`.
- Updated `AGENTS.md` with Experience Loop operating rules.
- Added `docs/experience_loop.md`.
- Added `docs/requirements_smoke_status.md`.
- Updated README, roadmap, and user requirements docs.

Verification:

- `.venv/bin/python -m unittest evals.test_experience_loop`
- `.venv/bin/python -m agentic.app.cli requirements-smoke --state-dir traces/state/requirements_smoke_rerun --experience-path traces/experience.jsonl`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- `.venv/bin/python -m agentic.app.cli experience-list --limit 3`

Roadmap impact:

- Added Experience Loop as a cross-cutting backbone.
- User requirement probes are now executable without UI and append structured events to `traces/experience.jsonl`.
- The harness can now accumulate evidence about what works, what is blocked by approval, and what missing tooling must be built next.

Next step:

- Implement M11 runtime execution slice: executable `ASK_USER`, workflow pause/resume, approval-resume, local browser fixture adapter, browser observation artifacts, and retry state.

Lessons learned:

- A failing smoke is productive when it records structured evidence. The first mobile approval probe exposed a source-routing gap and was immediately fixed.
- Completed local-source probes still need production bottlenecks recorded; otherwise local fixtures can make the harness look more ready than it is.
- Experience must be queryable by scripts, not just readable in narrative docs, so future agents can retrieve recent lessons before repeating work.

## 2026-07-01 18:19 KST - Autonomy Benchmark Review

Summary:

- Evaluated the current harness autonomy level and mapped common autonomous-agent benchmarks to the project roadmap.

Changed areas:

- Added `docs/autonomy_benchmark_review.md`.

Verification:

- Research/documentation task only.
- Reviewed current requirements smoke and M11 status docs.
- Browsed public benchmark references for WebArena, GAIA, OSWorld, WorkArena/BrowserGym, AgentBench, τ-bench, Mind2Web, SWE-bench, MCP-Bench, and related benchmark families.

Roadmap impact:

- Current harness is assessed as L2.2 / L5: strong workflow/backbone maturity, low real-world execution autonomy.
- Public benchmark readiness is currently near-zero for browser/OS/coding benchmarks until live adapters and action runtimes exist.
- Internal requirement smoke should remain the primary benchmark until M11 runtime execution is implemented.

Next step:

- Implement M11 runtime execution slice and add a browser fixture benchmark before attempting WebArena/Mind2Web-style evaluation.

Lessons learned:

- The project is ahead in orchestration and experience capture, but behind in grounded action.
- Public agent benchmarks mostly evaluate execution in real/simulated environments; our current system mostly evaluates representation and gating.
- The right near-term benchmark is not WebArena yet; it is a local fixture benchmark that exercises pause/resume, approval, browser observation, and retry state.

## 2026-07-01 18:30 KST - M11 Finish-Line Fixture Runtime

Superseded by the 2026-07-01 18:45 KST real-only correction below.

Summary:

- Implemented the first M11 finish-line execution slice so a browser transaction workflow can reach a completed report through local HTML fixtures.

Changed areas:

- Added `agentic/browser/` with `BrowserObservation`, `BrowserActionResult`, and `LocalFixtureBrowserAdapter`.
- Updated `CapabilityPlanner` so `connector:browser_fixture` is allowed only for local regression execution while live `connector:browser` remains missing.
- Updated `WorkflowInterpreter` so fixture/preapproved paths can execute `ASK_USER`, `BROWSER_OBSERVE`, `BROWSER_ACTION`, `APPROVAL`, and `REPORT`.
- Added checked-in browser fixtures for available, sold-out, and login-required states.
- Added `evals/test_milestone11_runtime_execution.py`.
- Updated `AGENTS.md`, README, roadmap, M11 status, autonomy benchmark review, and experience-loop docs.

Verification:

- `.venv/bin/python -m unittest evals.test_milestone11_runtime_execution`
- `.venv/bin/python -m unittest discover -s evals`
- `.venv/bin/python -m agentic.app.cli config-check`
- `.venv/bin/python -m agentic.app.cli requirements-smoke`

Roadmap impact:

- M11 now has a script-only finish-line browser transaction benchmark for the safe local fixture path.
- Live browser automation remains intentionally blocked until a real adapter, user resume, approval-resume, and retry-state runtime are implemented.
- Autonomy score updated from L2.2 to L2.6 because execution can now complete in a local browser-contract environment, but not on live sites.

Next step:

- Implement M11 resume/retry runtime: pause/resume for user login, approval-resumable workflow runs, retry state for sold-out/not-open states, and then a real browser adapter behind the same contract.

Lessons learned:

- "End-to-end" must mean terminal useful state, not just workflow representation. The new fixture benchmark forces that distinction.
- A local fixture adapter is useful only if live paths stay blocked and explicit; otherwise it becomes fake product capability.
- Experience-loop rules apply to both Codex and Agentic. Codex should inspect recent experience before similar work, and Agentic should turn blocked runs into structured state.

## 2026-07-01 18:45 KST - Real Benchmark And Fake Path Removal

Summary:

- Removed fixture/preapproved browser execution from product paths and added a real user-requirement benchmark that actually attempts live/local capabilities.

Changed areas:

- Added `agentic/benchmarks/` with `real-bench` probes for memory, repo inspection, Gmail/WSJ, ticket browser readiness, ntfy, Reddit, DCInside, and local GGUF model execution.
- Removed `LocalFixtureBrowserAdapter` and browser fixture eval files from product/eval path.
- Removed `preapproved` approval bypass and `connector:browser_fixture` capability admission.
- Replaced product Gmail fixture connector with a real `GmailImapConnector`.
- Updated `AGENTS.md`, README, roadmap, M11 status, autonomy benchmark review, experience-loop docs, and added `docs/real_benchmark.md` plus `docs/real_benchmark_status.md`.

Verification:

- `.venv/bin/python -m py_compile agentic/benchmarks/models.py agentic/benchmarks/real.py agentic/connectors/gmail/imap.py agentic/app/cli.py agentic/workflow_kernel/interpreter.py agentic/workflow_kernel/capabilities.py agentic/workflow_kernel/designer.py`
- `.venv/bin/python -m agentic.app.cli config-check`
- `CODEX_HOME=/mnt/c/Users/TAZO/.codex .venv/bin/python -m agentic.app.cli real-bench --model master-gemma-iq2 --model-max-tokens 12`
- `CODEX_HOME=/mnt/c/Users/TAZO/.codex .venv/bin/python -m agentic.app.cli real-bench --skip-network --skip-ntfy --model master-gemma-q4 --model-max-tokens 32`
- `.venv/bin/python -m agentic.app.cli real-bench --skip-network --skip-ntfy --skip-model --no-persist-experience`
- `.venv/bin/python -m unittest discover -s evals` (`Ran 160 tests`, `OK (skipped=2)`)

Roadmap impact:

- Internal benchmark priority moved from fixture/representation checks to real execution checks.
- Autonomy assessment corrected to L2.3 / L5.
- Current real blockers are Gmail credentials, official ticket URL, live browser adapter, Reddit access strategy, and local model empty output.

Next step:

- Fix the local GGUF runner/template path so the model produces non-empty output, then implement real browser adapter + approval/input resume.

Lessons learned:

- A process that launches and returns code 0 is not enough; empty model output is not useful autonomy.
- ntfy and DCInside crawling work on real paths today, while Reddit needs a compliant connector/API path.
- Credential/input/tooling blockers should be first-class benchmark outcomes, not reasons to substitute fake data.
