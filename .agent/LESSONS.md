# Agentic Lessons

Reusable lessons from actual work, failures, and user feedback.

## 2026-07-02 - Codex Is Harness Operator, Not Workflow Performer

- Context: User corrected the operator boundary again after Codex drifted toward improving a concrete crawling path. The correct role is to observe the Harness agent, answer as `User` inside the Harness session, and only add generic primitives when the agent repeatedly lacks a reusable capability.
- Lesson: If an agent result is noisy, weak, or wrong, the first response is an in-session user feedback turn. Codex must not convert that feedback into hidden URL, selector, crawler, noise-filter, schedule, script, or report-shape code.
- Apply next time: Before touching implementation for a real-use probe, classify the edit as either `general Harness primitive` or `vertical workflow patch`. Only the former is allowed.

## 2026-07-02 - Operator Feedback Must Stay Inside The Harness Session

- Context: User clarified again that Codex must not directly fix a concrete crawler/workflow result. When the agent returns noisy or weak output, the operator should answer as the user inside the Harness session and observe whether the agent can diagnose and recover.
- Lesson: Agent-facing feedback is allowed; hidden operator-authored domain fixes are not. The boundary is crossed when Codex adds a site-specific source, selector, filter, script, schedule, or report shape outside the agent loop.
- Apply next time: For real-use probes, report the exact separation between `Agent did`, `Operator answered as user`, `Harness primitive added`, and `Still operator-assisted`.

## 2026-07-02 - Operator Must Build Harness, Not Workflows

- Context: User clarified that Codex must not hand-code crawlers, workflow-specific filters, source URLs, or scripts to make a scenario pass.
- Lesson: The operator observes the Harness agent, answers as the user, and fills only reusable primitives. If a workflow result is noisy, the next step is to tell the agent inside the Harness session and observe recovery, not to add a domain-specific filter by hand.
- Apply next time: Separate `operator-built framework primitive` from `agent-created workflow behavior` in every report, benchmark, and implementation plan.

## 2026-07-02 - Preseeded Sources Are Not Agent Discovery

- Context: The social-trend finish-line benchmark reached report delivery, but it pre-registered `주식갤` aliases and the DCInside URL before the workflow request.
- Lesson: A benchmark with preseeded source bindings proves runtime execution after binding, not agent autonomy in discovering or registering sources.
- Apply next time: For source-discovery claims, run a no-preseed benchmark where the agent only has tools; if it cannot discover/register/bind a real source through those tools, score the run as blocked at source discovery.

## 2026-07-02 - Model Synthesis Needs Artifact Admission

- Context: A live Q4 finish-line benchmark initially returned `100/100`, but manual artifact inspection found one prompt-meta line admitted as a report insight.
- Lesson: Model-assisted report synthesis can improve usefulness, but local model output must pass deterministic admission and artifact inspection before the score is trusted.
- Apply next time: Filter prompt/schema/meta claims, clean embedded reasoning debris, and inspect the generated artifact before raising a real-usefulness score.

## 2026-07-02 - Broad Tool Surfaces Need Policy-Aware Entrypoints

- Context: Adding file, patch, shell, process, Python, and API search tools made the default `ToolRegistry` much more capable, but direct `ToolBridge` execution does not enforce policy by itself.
- Lesson: Powerful tools should be paired with approval-aware entrypoints and tests. Read-only tools can be allowed; mutating and execution tools should require approval on approval-gated paths.
- Apply next time: When adding browser, email, connector, script, or API tools, update both the registry and the policy/approval tests in the same slice.

## 2026-07-02 - Source Identity Is Part Of Report Quality

- Context: A live finish-line benchmark initially passed report quality and sent ntfy, but manual artifact inspection showed many evidence links came from `dcbest` instead of the requested DCInside stock gallery.
- Lesson: A well-structured report is still wrong if its evidence drifted from the requested source. Source quality needs identity checks such as path/query constraints, and report admission should depend on those checks.
- Apply next time: For web, forum, Gmail, browser, and API connectors, verify source identity/provenance before scoring a delivered artifact as useful.

## 2026-07-02 - Source Strategy Filters Need AND Semantics

- Context: Source recovery appended `/board/view` as an OR-style `href_contains` filter, which extracted forum posts but allowed the wrong board id.
- Lesson: Recovery needs both broad link-shape filters and required identity fragments. OR filters widen candidate sets; AND filters constrain them.
- Apply next time: When source recovery tries to fix off-source or noisy extraction, prefer explicit required fragments, selector constraints, or connector-specific source identity guards.

## 2026-07-02 - Finish-Line Benchmarks Must Use The Front Door

- Context: The harness could already prove pieces of the path through service calls and CLI ticks, but the user evaluates whether a vague request plus a few answers reaches a delivered report.
- Lesson: Capability benchmarks must exercise the same channel/front-door route that the user will operate, including interview turns, session logs, lifecycle gates, scheduler/tick, recovery, artifacts, and delivery.
- Apply next time: For any claimed user-facing capability, add or run a scriptable front-door benchmark before raising the autonomy score.

## 2026-07-02 - Owner Notifications Are Delivery, Not Approval

- Context: A live read-only social-trend workflow reached active status but initially stopped at `channel:ntfy` approval, even though the user expects credentialless personal reports to run unattended.
- Lesson: For low-risk read-only workflows, ntfy to the owner is part of report delivery and should be allowed by deterministic policy. Consequential actions such as browser submit, payment, email send, file write, shell, and generated script execution still need approval/admission gates.
- Apply next time: When a workflow is blocked by approval, check whether the capability is genuinely consequential or merely an owner-visible delivery fact.

## 2026-07-02 - Session Logs Belong At The Front Door

- Context: The repo had a `SessionLogStore`, but web workflow design initially only persisted planning sessions and workflow events. That made real user-facing runs harder to audit end to end.
- Lesson: Full session logs must start when the user enters the request and include user request, interview turns, proposed workflow, lifecycle advance, runtime blockers, and agent response.
- Apply next time: Any new channel, workflow designer, browser planning, or skill workshop entrypoint should create or attach a session log before producing durable artifacts.

## 2026-07-01 - Real Paths Beat Synthetic Success

- Context: The harness added requirement smoke and real-bench paths, then removed product runtime behavior that silently generated fake source/model/connector success.
- Lesson: Developer fixtures are fine for low-level tests, but user-facing capability must be backed by real execution paths or explicit blockers.
- Apply next time: When verifying a user-shaped requirement, choose `real-bench` or another real path; if credentials/tooling are missing, record the exact blocker.

## 2026-07-01 - Skill Evolution Needs Proposal Boundaries

- Context: OpenClaw-style skill workshop work showed that active skill mutation is too risky as the first autonomy unit.
- Lesson: The safer primitive is a pending skill proposal with evidence, review, rejection/quarantine, and later approval-gated apply.
- Apply next time: For repeated workflows, prefer `skill-workshop create` or equivalent proposal state before creating an active skill file.

## 2026-07-01 - Blurry Requests Need Interview And Durable Progress

- Context: Early vague workflow requests fell through the master loop; later prompt/runtime recovery got to pending proposals but foreground `ask` remained slow.
- Lesson: The harness needs one-question-at-a-time interviews and durable background progress for vague workflow-building tasks.
- Apply next time: Do not solve vague recurring workflows as one-shot chat; preserve planning state, ask the missing slot, and expose progress through durable runtime/UI.

## 2026-07-01 - Codex Operator Memory Should Reuse Existing Harness Memory

- Context: The repo already had `agentic.experience`, `docs/experience_loop.md`, and `docs/work_log.md` before adding `.agent/` bootstrap files.
- Lesson: Repo-specific learning loop setup should adapt existing primitives instead of creating a parallel memory system.
- Apply next time: Use `.agent/` for concise operator routine and durable preferences, while structured runtime evidence stays in `traces/experience.jsonl` and project history stays in `docs/work_log.md`.

## 2026-07-01 - Long Model Calls Need Independent Task Heartbeats

- Context: A real durable workflow-builder probe looked stuck while the local subagent model was still running; after adding worker-level heartbeat it completed with 28 heartbeat events.
- Lesson: A 24/7 harness cannot rely on executor internals to prove liveness. Durable workers need independent heartbeat and trace events around model calls.
- Apply next time: For any long-running model, browser, crawler, or connector task, verify task heartbeat continues and provider-level start/completion/failure events are visible before judging autonomy quality.

## 2026-07-01 - Finish-Line Probes Need Artifact Quality Gates

- Context: Earlier real workflow-builder probes completed but created truncated proposal bodies; a later run became useful only after adding a seven-label quality gate and compact delegation.
- Lesson: A completed task is not a completed user requirement. The harness must validate the generated artifact against the intended primitive before claiming progress.
- Apply next time: For workflow specs, skill proposals, reports, scripts, browser plans, and research outputs, check the persisted artifact after generation and record a bottleneck when it is incomplete.

## 2026-07-02 - Compact Tool Interfaces Beat Full JSON Dumps

- Context: Real local subagent runs repeatedly failed when asked to emit a full nested WorkflowSpec JSON object, but succeeded once the `workflow_spec` tool accepted compact fields and normalized them into a spec.
- Lesson: For local models, tool interfaces should capture agent choices at the right abstraction level and let deterministic Harness code fill schema detail.
- Apply next time: Prefer compact, typed tool arguments plus post-store quality gates over long nested JSON prompts for workflow specs, browser plans, reports, and skill proposals.

## 2026-07-02 - Lifecycle Gates Beat Claimed Readiness

- Context: A real social-trend automation run created a valid proposed WorkflowSpec, but lifecycle review found missing source binding and approval was blocked.
- Lesson: Proposed workflow artifacts should not be treated as executable capability. Review, source binding, approval, activation, and run admission are separate runtime facts.
- Apply next time: Score real Harness progress by the last lifecycle gate reached, and record the blocker when source, connector, scheduler, or delivery binding is missing.

## 2026-07-02 - Fast Models Need Tool-Call Reliability Checks

- Context: The IQ2/IQ2 fast config finished the same WorkflowSpec probe faster than Q4/Q4, but failed because the subagent emitted thought text instead of a valid JSON tool call.
- Lesson: Smaller local models improve iteration speed and reduce memory pressure, but capability claims still require the same finish-line probe evidence. Model choice is an execution parameter, not a substitute for lifecycle gates.
- Apply next time: Use the default IQ2/IQ2 path for rapid Harness development, and run Q4/DiffusionGemma opt-in probes only when comparing quality or diagnosing model-specific behavior.

## 2026-07-02 - Scheduled Completion Is Not Report Usefulness

- Context: The live social-trend workflow bound sources, activated a schedule, collected live web resources, and created report artifacts, but extracted mostly navigation links.
- Lesson: Scheduler/run completion proves runtime reach, not user usefulness. Collection quality and report quality need their own gates before notifications are sent.
- Apply next time: Add source extraction quality checks, recent-window analysis, and report admission before scoring a recurring workflow near complete.

## 2026-07-02 - Quality Gates Should Fail Before Reports

- Context: A live DCInside raw page collection returned 10 items, but they were navigation/off-path links such as skip links and site menu entries.
- Lesson: The runtime should fail a workflow run before analysis/report/notify when source quality evidence is below threshold. A blocked run with structured evidence is better than an apparently successful useless report.
- Apply next time: When a quality gate fails, create a source-strategy tuning task or proposal using the quality evidence instead of retrying the same extraction blindly.

## 2026-07-02 - Failures Need Next-Action Artifacts

- Context: Source quality failures were correctly blocking bad reports, but initially left the workflow at a terminal error.
- Lesson: Harness failures should produce durable next-action artifacts such as tooling backlog, skill proposals, approval requests, or retry state. Otherwise the agent cannot improve from evidence.
- Apply next time: For every new runtime gate, define the follow-up artifact that lets the agent or user continue the loop.

## 2026-07-02 - Recurring Analysis Needs Recent Windows

- Context: After applying a source strategy proposal, live collection quality passed, but the workflow initially analyzed 0 items because all posts were already deduped as existing resources.
- Lesson: Recurring workflows need separate concepts for newly collected resources and recent analysis windows. Dedupe should prevent duplicate storage, not erase the report input.
- Apply next time: Any scheduler, crawler, newsletter, or memory synthesis workflow should expose recent-window resource IDs and use them when there are no new resources in the current run.

## 2026-07-02 - Recovery Should Be Durable Work

- Context: Source strategy tuning could be manually proposed/applied/rerun through CLI, but that still left the self-improvement loop outside the task runtime.
- Lesson: Any autonomous repair path should be representable as a durable task with heartbeat, terminal status, evidence, and cleanup of the original backlog/tooling item.
- Apply next time: When adding workflow repair, browser recovery, connector fallback, or skill revision execution, expose it as a task executor first, then wire hooks/schedulers to enqueue it.

## 2026-07-02 - Failure Hooks Should Enqueue Repair, Not Hide Failure

- Context: A live workflow still failed honestly at the source quality gate, but the same failure event automatically created a queued `source_strategy_recovery` task.
- Lesson: Runtime hooks should not pretend the original run succeeded. They should preserve the failed run and enqueue durable repair work with evidence and traceability.
- Apply next time: For browser transaction failures, connector auth failures, report quality failures, and model malformed-output failures, keep the failed run intact and create a typed recovery task.

## 2026-07-02 - Report Delivery Is A Runtime Fact

- Context: A live recovery task created a report artifact, but the user had not received anything until a durable delivery record and ntfy send path were added.
- Lesson: Report creation and report delivery are separate finish-line gates. Delivery needs its own state, retry, and evidence.
- Apply next time: For newsletter reports, social-trend reports, browser watcher alerts, and self-review summaries, score progress only after a delivery record reaches `sent` or a clear delivery blocker is recorded.

## 2026-07-02 - Continuous Loops Need Visible Runtime State

- Context: `runtime-tick` proved report delivery, but it still depended on the operator to manually run the command.
- Lesson: A 24/7 harness needs a visible continuous loop with tick count, last tick, last error, and delivery state. Otherwise background progress is not auditable.
- Apply next time: When adding scheduler, watcher, browser, Gmail, or self-review execution, expose both the loop state and the resulting delivery/task artifacts in the web/API surface.
