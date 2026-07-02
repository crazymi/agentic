# Agentic Task Log

Recent concise operator-facing task context. Longer project history belongs in `docs/work_log.md`.

## 2026-07-02 13:26 KST - No-Preseed Source Feedback Loop

- Request: Continue toward a useful crawling Harness without Codex hand-coding crawlers, URLs, filters, or workflows.
- Done: Ran real no-preseed front-door benchmark in `/tmp/agentic-nopreseed-frontdoor-20260702-1319`; Agent discovered a source, runtime delivered a report, then Codex gave user feedback inside the session for noisy/weak results. Added generic session-feedback audit, context redaction, active lifecycle idempotence, feedback-aware source discovery, and placeholder candidate admission.
- Evidence: Workflow `wf_02be6c4346ff45fbba922ceb168481a2`, sent delivery `del_5cb6bafc77c84b00a3ac1caa6fa9fdd4`, source feedback events in session `sess_a1415b772e894f6cafdb8a4ea3ec2cfe`, alternative source candidate `스톡커` discovered by Agent after feedback.
- Next: Build a semantic/source-usefulness gate and source-switch review loop so menu/category reports or weak source switches become reviewable feedback tasks instead of being counted as useful.

## 2026-07-02 13:08 KST - Boundary Deduplicated At AGENTS Top

- Request: Re-state the project and Codex/operator role boundary clearly at the very top of `AGENTS.md`.
- Done: Replaced duplicated boundary sections with one concise non-negotiable rule set: Codex is the Harness operator/evaluator and must not secretly perform concrete workflow work.
- Key rule: If Agent output is noisy, respond inside the Harness session as `User`; do not add a hidden site-specific filter, crawler, source URL, report shape, or schedule.
- Next: Continue real no-preseed Harness evaluation and implement only generic primitives proven necessary by observed Agent/runtime blockers.

## 2026-07-02 13:04 KST - Dotenv Support For API Keys

- Request: Add Tavily API key to local `.env` and make Harness/test/CLI paths load project `.env` automatically.
- Done: Added ignored `.env` with local Tavily key, `load_dotenv()` support in config loading, `web_search` direct dotenv loading, README note, and dotenv regression tests.
- Verified: 264 evals passed, config-check passed, secret presence verified without printing the value.
- Next: Use `provider=tavily` or `AGENTIC_WEB_SEARCH_PROVIDER=tavily` in live search probes.

## 2026-07-02 12:50 KST - Role Boundary Hardened At AGENTS Top

- Request: Make the project/operator boundary unmistakable at the very top of `AGENTS.md`.
- Done: Added a first-read section stating that Codex is the Harness builder/evaluator, not the performer of concrete crawlers/workflows. Added explicit allowed/forbidden actions and the noisy-result feedback rule.
- Key rule: Agent failure must first receive in-session `User` feedback. Codex may only implement reusable framework primitives, never hidden target-specific fixes.
- Next: Re-run real no-preseed Harness sessions and improve only generic source-discovery/session-recovery/admission primitives proven necessary by those logs.

## 2026-07-02 12:25 KST - Strict Operator/Agent Boundary Rewritten

- Request: Rewrite the top of `AGENTS.md` so the project boundary is unmistakable: Codex builds/evaluates the Harness, the Harness agent performs concrete workflow work.
- Done: Replaced the top boundary section with Korean-first rules covering role split, allowed generic primitive work, forbidden domain-specific patching, and no-preseed autonomy evaluation.
- Key rule: If the agent crawls noisy data, Codex must respond as `User` inside the Harness session and observe recovery; Codex must not directly add a noise filter or site-specific crawler.
- Next: Continue with no-preseed source discovery only as a generic Harness primitive, then evaluate it by running actual Harness sessions and separating agent behavior from operator infrastructure.

## 2026-07-02 12:18 KST - Operator/Harness Boundary Clarified

- Request: Define at the top of `AGENTS.md` that this project builds a Harness, not operator-authored bespoke automations.
- Done: Added a non-negotiable boundary section: Codex may add general primitives and evaluate Harness agent behavior, but must not hand-code scenario-specific crawlers, filters, source URLs, scripts, or hidden setup.
- Next: Implement and test no-preseed source discovery as a generic lifecycle, then evaluate by asking the Harness agent rough requests without preloaded source bindings.

## 2026-07-02 12:07 KST - No-Preseed Autonomy Correction

- Request: Re-run without Codex/operator-provided URLs, code steering, or preseeded source bindings; also start another credential-free requirement probe.
- Done: Ran no-preseed front-door probes for `주식갤` social trend and local idea synthesis. Both created proposed workflows and session logs, but neither discovered/registered/bound a source or delivered a report.
- Correction: The prior `100/100` social-trend result proves a preseeded-source runtime path, not autonomous source discovery. Honest no-preseed score is about `45/100` for this class.
- Next: Add a source-discovery lifecycle where missing source binding creates an agent/tool task using allowed tools only, then stores reviewable source candidates before activation.

## 2026-07-02 11:31 KST - Q4 Model-Assisted Finish-Line Report

- Request: Continue the real Harness goal and close the remaining report usefulness gap with actual GPU/model evidence.
- Done: Hardened report synthesis admission against prompt-meta claims and reran the real front-door finish-line benchmark with `master-gemma-q4` synthesis required.
- Verified: 257 evals passed, config-check passed, and live benchmark `/tmp/agentic-model-synthesis-live-q4-v2` returned `100/100` with sent ntfy delivery `del_6a7a6eed7f424316bcb2469ed927ec5a`.
- Caveat: The current benchmark proves the social-trend/DCInside path only. Gmail/WSJ, Obsidian memory, ticket browser transactions, and coding workflows remain separate finish-line work.
- Next: Package this path into the serve/daemon default mode and add persistent model runner support to avoid repeated GGUF reload overhead.

## 2026-07-02 11:30 KST - Core Tool Surface And API Web Search

- Request: Add OpenClaw-style file/process tools plus API-backed `web_search`.
- Done: Added default tools `read_file`, `write_file`, `edit_file`, `apply_patch`, `list_files`, `search_files`, `exec`, `process`, `python_execute`, and `web_search`; added Brave/Tavily/Exa/Serper/SearXNG providers; added approval policy coverage for mutating/execution tools.
- Verified: 257 evals passed, config-check passed.
- Next: Route workflow source binding/recovery to prefer API-backed `web_search` when static page extraction is blocked or low quality.

## 2026-07-02 10:59 KST - Report Quality And Source Identity Gate

- Request: Continue from 96/100 by making delivered reports genuinely useful, not just delivered.
- Done: Added report quality evaluator/admission, richer generic report sections, report-quality metadata in artifacts, delivery skip for low-quality reports, source identity query checks, `href_contains_all`, and strategy recovery filters for source-bound links plus notice/bracket noise.
- Verified: 242 evals passed, config-check passed, live `finish-line-bench` delivered ntfy report `del_7596e49af61746dc8b39a01662e50663` from workflow `wf_ef215eafca414b64864e80ba5c905ca4`; report quality score 100; inspected artifact links stay on `id=stock_new2`.
- Score: 98/100. Remaining gap is semantic/model-assisted synthesis quality, not lifecycle/source/delivery reach.
- Next: Add model-assisted report synthesis with deterministic provenance/admission so reports become higher-signal insight rather than keyword/evidence summaries.

## 2026-07-02 10:39 KST - Finish-Line Benchmark

- Request: Continue from 92/100 by proving the deliberately blurry-request path with 2 interview answers reaches real delivered report.
- Done: Added `finish-line-bench`, front-door ASGI benchmark engine, regression test, README docs, and fixed `ntfy/알림` source misclassification.
- Verified: 238 evals passed, config-check passed, live `finish-line-bench` delivered ntfy report `del_e8842cc1090e46adbe82fdabd8de16d6` from workflow `wf_c32f09778ac943949610968ed3ef0b57`.
- Score: 96/100. Remaining gap is useful/richer report quality and report admission, not lifecycle reach.
- Next: Add report quality/admission and better synthesis so recurring reports are actually worth reading.

## 2026-07-02 10:31 KST - Front-Door Session Log And Report Delivery

- Request: Continue the active Harness objective and close the gap between vague web request, lifecycle gates, full session log, and real delivered report.
- Done: Wired `SessionLogStore` into web/channel app, added `/sessions` APIs and UI panel, attached session ids to WorkflowSpecs, allowed low-risk read-only ntfy owner notifications, and fixed lifecycle import cycles.
- Verified: 237 evals passed, config-check passed, fresh web/API path created active workflow `wf_8ac08754ff794335b5250237eed5aaa7` with session `sess_14055190e1e2472ea0416e138c11f93e`; real runtime tick sent delivery `del_29bd7cfadafb4193bcde512f6b08a66d`.
- Score: 92/100. Remaining gap is a deliberate 2-3 answer blurry-request finish-line benchmark plus richer report semantics.
- Next: Add the benchmark/probe that proves underspecified workflow design can interview, activate, run, recover, and deliver without operator stitching.

## 2026-07-01 - Learning Loop Bootstrap

- Request: Apply the provided Codex Agent Learning Loop bootstrap to this repo, adapting it to existing project mechanisms.
- Done: Added `.agent/` operator routine, memory, lessons, and task log files that connect the bootstrap loop to `agentic.experience`, `requirements-smoke`, `real-bench`, roadmap review, work-log maintenance, and Skill Workshop proposal boundaries.
- Verified: `.venv/bin/python -m unittest discover -s evals`; `.venv/bin/python -m agentic.app.cli config-check`; `.venv/bin/python -m agentic.app.cli requirements-smoke`.
- Next: Add approval-gated skill proposal apply/review and move slow workflow-building work into durable background execution.

## 2026-07-01 22:02 KST - Durable Workflow-Building Probe

- Request: Continue the single general workflow-building probe until it runs through the harness rather than a one-off foreground path.
- Done: Added durable `workflow_builder_probe` task execution via task kind routing, CLI `harness-probe-task`, and web enqueue route.
- Verified: Real GPU-backed durable task completed and persisted a pending `vague-workflow-builder` proposal; full eval suite passed.
- Next: Add approval-gated proposal review/apply and surface pending proposal details in the web UI.

## 2026-07-01 22:10 KST - Approval-Gated Skill Apply

- Request: Continue the framework loop after durable proposal creation by making pending proposals reviewable and activatable.
- Done: Added approval-gated Skill Workshop apply service, CLI commands, web proposal panel/routes, and activated `vague-workflow-builder` from the real agent-generated proposal.
- Verified: Approval request/approve/apply flow completed; active skill loaded through `SkillLoader`; full eval suite passed.
- Next: Route future vague workflow-building requests through active skill context, then rerun the same scenario to prove the skill is used.

## 2026-07-01 22:23 KST - Active Skill Routing

- Request: Prove the active skill is actually used by the harness on the same single general workflow-building scenario.
- Done: Wired SkillRegistry into Master/Subagent prompts, added selected-skill trace evidence, compacted skill context, fixed broad routing, and added revision proposals for existing active skills.
- Verified: Real durable probe completed with both Master/Subagent selecting only `vague-workflow-builder`; a duplicate active-skill proposal became a pending revision proposal.
- Next: Add proposal diff/review quality for revision proposals before approval/apply.

## 2026-07-01 22:28 KST - Proposal Review Diff

- Request: Continue toward safe self-evolution by making revision proposals reviewable before approval/apply.
- Done: Added Skill Workshop review records, candidate validation, unified diffs, CLI review, web diff preview, and markdown normalization.
- Verified: Real revision proposal `skp_93ae34999ad54d6a8b5fa9cfc99c2637` reviewed successfully; full eval suite passed.
- Next: Bind approval to reviewed candidate text/diff so apply approvals cannot drift from what the user inspected.

## 2026-07-01 22:48 KST - Review-Bound Apply And Real Harness Probe

- Request: Continue by throwing a real user-shaped task at the harness and report whether it improves over the previous run.
- Done: Bound Skill Workshop apply approvals to active/candidate/diff/review hashes, added worker heartbeat during long executor/model calls, and connected model calls to provider-level trace for future runs.
- Verified: Real durable social-trend workflow-builder probe completed as `task_e9ca15a5e7dc41e995a2ae7175ca1d11`, recorded 28 heartbeat events, selected `vague-workflow-builder`, and created pending revision `skp_58908bc02b2f42ab92b37760f901501a`; full eval suite passed.
- Next: Rerun the real durable probe with provider-level trace active and improve the interview/session capture so all requested slots are preserved cleanly.

## 2026-07-01 23:14 KST - Real Workflow-Builder Probe Quality Gate

- Request: Continue by sending real user-shaped requirements into the Harness and report progress versus the previous turn.
- Done: Improved interview answer normalization, preserved extra guidance, compacted skill-workshop delegation, added proposal quality gates, made recovery/quality checks tolerate markdown-bold labels, and added `raw_text_chars` provider trace observability.
- Verified: Real durable task `task_e30c5c605c094b969b242ba17ac05c5d` completed, created pending revision `skp_41825d67d2954946a63c1e19f79e92c6`, recorded 28 heartbeats, and passed the seven-label proposal quality gate; 200 evals and config-check passed.
- Next: Run a finish-line probe where the Harness builds a concrete WorkflowSpec from a vague recurring automation request without Codex writing that workflow.

## 2026-07-02 00:16 KST - Agent-Generated WorkflowSpec Probe

- Request: Continue the same single general workflow-building scenario until the Harness creates a concrete workflow primitive rather than Codex writing a workflow.
- Done: Added `workflow_spec` tool, compact intent-to-WorkflowSpec normalization, durable `workflow_spec_probe`, CLI commands, workflow-spec recovery, and Master routing so explicit WorkflowSpec requests do not fall back to skill proposal creation.
- Verified: Real durable task `task_6f202702698141428dc0d642b28e3a30` completed and created proposed workflow `wf_08fd1c5ecd3f4824957d0517f41ee77b`; 210 evals and config-check passed.
- Next: Add WorkflowSpec review/approval/source-binding checks so proposed specs can become approved/active without Codex manually writing workflow code.

## 2026-07-02 09:00 KST - Session Log And Lifecycle Gate

- Request: Continue toward real Harness evaluation with full session logs and deterministic WorkflowSpec gates; answer whether fast single-model iteration is viable.
- Done: Added SQLite full session log, WorkflowSpec lifecycle service, CLI lifecycle actions, fast IQ2/IQ2 config, and docs. Real Q4/Q4 run created workflow `wf_9b5e45a25852414993e7bb496272aabf`, review passed, source binding failed honestly, and approval was blocked.
- Verified: Real score is 38/100. Q4/Q4 completed in about 446s. Fast IQ2/IQ2 completed in about 169s but failed to emit valid tool-call JSON. 214 evals passed plus default and fast config-check.
- Next: Implement generic live source binding strategy plus scheduler execution admission so a proposed workflow can become active and run repeatedly after real source binding.

## 2026-07-02 09:11 KST - Live Source Binding And Scheduled Run

- Request: Continue from source-binding blocker toward actual scheduled execution without writing a bespoke crawler.
- Done: Added generic source alias registration, multi-source binding/collect, read-only web-page admission, activation-time schedule creation, due-run CLI, and interval next-run calculation. The existing agent-generated workflow bound live `reddit` and `dcinside-gallery` web sources, became active, ran twice, collected live resources, and created report artifacts.
- Verified: Real score is 62/100. First successful scheduled run `wfr_8d8e5e44e936414ca5d92353bb4549e7` collected 20 resources and created report `art_4d59e64235a049e6a662947f4aaf776a`; focused evals passed.
- Next: Add generic source extraction quality gates and agent-driven source tuning; current collection is nav-heavy and not yet useful enough for hourly insight alerts.

## 2026-07-02 09:16 KST - Fast Single Model Default

- Request: Decide whether low GPU utilization/high memory use is expected and whether to use one lighter model for faster iteration.
- Done: Confirmed no active model process in `nvidia-smi`; switched default config to Gemma IQ2 for both Master and Subagent while keeping Q4/DiffusionGemma opt-in.
- Verified: `.venv/bin/python -m agentic.app.cli config-check`.
- Next: Continue source quality gates and real finish-line workflow evaluation.

## 2026-07-02 09:25 KST - Source Quality Gate

- Request: Continue toward real Harness operation where recurring social/community workflows produce useful reports, not just successful runs.
- Done: Added generic `SourceQualityReport`, returned quality from `SourceRuntime`, blocked low-quality workflow collection before report creation, and exposed quality in CLI collection output.
- Verified: 219 evals passed, config-check passed, and a real DCInside raw-page workflow probe failed safely with `SourceQualityError` and zero report artifacts.
- Score: 62/100. The Harness is more honest and safer, but not yet at autonomous source tuning plus hourly notification delivery.
- Next: Convert source-quality failure into agent-driven source strategy tuning/retry rather than a terminal dead-end.

## 2026-07-02 09:31 KST - Source Strategy Tuning Backlog

- Request: Continue from quality gate toward agent-driven source tuning instead of terminal failures.
- Done: Added `source:strategy_tuning` tooling requests with quality reports, candidate actions, and agent review prompt; wired workflow/lifecycle/scheduler/web/CLI paths to persist them.
- Verified: 219 evals passed, config-check passed, and a real DCInside raw-page workflow created one tuning request while producing zero report artifacts.
- Score: 64/100. The Harness now captures the next action after source failure, but still needs agent-consumed strategy revision and rerun.
- Next: Let the agent consume tuning backlog and produce a revised source definition/WorkflowSpec patch through reviewable runtime gates.

## 2026-07-02 09:41 KST - Source Strategy Proposal Apply

- Request: Continue from source strategy tuning backlog toward a real applied recovery path without writing a bespoke crawler.
- Done: Added source strategy proposal store/service/CLI, source metadata update support, and recent-window workflow analysis when no new resources are found.
- Verified: 223 evals passed, config-check passed, live DCInside strategy proposal applied, source quality improved from 47 to 100, and live workflow report analyzed 20 recent items with `new_count=0`.
- Score: 70/100. The Harness can recover a real source quality failure into an applied read-only strategy and produce a report, but agent-autonomous consumption, daemonized scheduling, ntfy report delivery, and better report semantics remain.
- Next: Connect pending strategy proposals/backlog into the Master/Subagent task loop and notification channel.

## 2026-07-02 09:48 KST - Durable Source Strategy Recovery Task

- Request: Continue toward the objective by reducing manual recovery steps after source quality failures.
- Done: Added `source_strategy_recovery` durable task executor and CLI `source-strategy recover/recover-pending/recover-task`.
- Verified: 226 evals passed, config-check passed, and live task `task_40bc9514961e49afbca22e70481324f0` reran the tuned DCInside workflow, produced report `art_031d7c1acb13439c94b756ac46450c4f`, quality score 100, and marked tooling completed.
- Score: 74/100. Recovery now runs as durable runtime work, but automatic enqueue, 24/7 daemon execution, ntfy report delivery, and stronger report writing remain.
- Next: Hook quality-failure events into automatic recovery task enqueue and report delivery.

## 2026-07-02 09:53 KST - Automatic Source Recovery Enqueue

- Request: Continue toward the objective by removing manual recovery setup after source quality failures.
- Done: Added `SourceStrategyRecoveryEnqueuer`; workflow quality failures now enqueue `source_strategy_recovery` tasks and record `workflow_source_strategy_recovery_enqueued`.
- Verified: 227 evals passed, config-check passed, fresh live DCInside workflow failure automatically queued `task_dd5089106fa14da5be4275705ca70e7b`; `source-strategy kick-recovery` ran it to report `art_f1c8754cf7ec40bbbd28ed557d77b1f0`, quality score 100, and tooling completed.
- Score: 78/100. Failure-to-recovery task creation is now automatic, but a continuous worker daemon and report delivery are still missing.
- Next: Add daemon/serve worker loop and ntfy/web inbox report delivery.

## 2026-07-02 10:05 KST - Runtime Tick Report Delivery

- Request: Continue toward 24/7 operation after confirming IQ2 is the fast default; close the manual kick/report delivery gap.
- Done: Added durable report delivery records/store/service, generic `NtfyChannel.send_text`, `RuntimeTickService`, CLI `runtime-tick`, retryable failed delivery, and fixed `recover-task --no-wait` to enqueue only.
- Verified: 232 evals passed, config-check passed, live queued recovery `task_8ec9af9a6b0a4a8580183dcc49621153` was submitted by runtime tick, created report `art_d8a2b38aa7684522b5d96575f3b174fe`, and sent ntfy delivery `del_8150cbdd5a474506ba8466d9efd71726`.
- Score: 82/100. One runtime tick can now run queued recovery to report delivery; remaining gaps are continuous daemon loop, web inbox visibility, richer report semantics, and full vague-chat-to-active-workflow execution.
- Next: Turn runtime tick into a continuous serve/daemon loop and surface report deliveries in the web UI.

## 2026-07-02 10:13 KST - Continuous Runtime Daemon And Delivery UI

- Request: Continue toward the active goal after runtime-tick report delivery; remove manual CLI tick dependence.
- Done: Added `RuntimeDaemonLoop`, CLI `runtime-daemon`, serve-time background daemon startup/shutdown, source recovery executor wiring in serve, `/daemon`, `/daemon/tick`, `/deliveries`, and web panels for daemon/deliveries.
- Verified: 235 evals passed, config-check passed, live daemon submitted `task_bd47ec0c382e4bdb9ad4def467b1ed3b`, produced report `art_f4d7ae40132144b7ad52b91ff8c924b8`, sent delivery `del_8fee4d3afe64433f8ac419c0f5269a5e`, and real serve returned `/daemon` running plus `/deliveries` sent records.
- Score: 86/100. Continuous local loop and web visibility now work; remaining gap is full vague chat -> reviewed/source-bound/approved/active scheduled workflow -> daemon-delivered report without operator CLI stitching.
- Next: Close the start-of-flow gap by wiring the planning/session lifecycle to WorkflowSpec review/source-binding/approval/activation from the web channel.
