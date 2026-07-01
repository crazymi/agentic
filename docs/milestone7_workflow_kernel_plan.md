# Milestone 7 Plan: Workflow Kernel

Milestone 7 creates the framework layer that turns vague natural-language requests into reviewed, durable, runnable workflows.

This replaces the previous "newsletter-first" framing. Newsletter, social trend, browser watcher, idea synthesis, and coding workflows become validation probes for the same kernel.

## Decisions Locked

- Build a harness framework, not individual apps.
- Keep workflow definitions data-first and persisted.
- Keep model reasoning inside selected steps; the workflow engine owns lifecycle and control flow.
- Use SQLite for workflow specs/runs.
- Use fake connectors/scripts in default tests.
- Generated scripts are artifacts requiring admission and approval before execution.
- No public marketplace, no multi-provider model routing, no automatic activation of third-party MCP servers.

## Work Packages

### M7-A: Intent Router

Goal: classify user requests into framework work classes.

Deliverables:

- `RequestIntent` model and classifier.
- Initial intent types: `answer_now`, `one_off_task`, `deep_research`, `workflow_design`, `scheduled_workflow`, `watcher_workflow`, `coding_workflow`, `unknown`.
- Trace event for intent classification.
- Tests for immediate, recurring, watcher, research, coding, and ambiguous requests.

Acceptance:

- "1+1은?" routes to `answer_now`.
- "매일 WSJ 읽고 보고서 줘" routes to `scheduled_workflow`.
- "이 사이트 빈자리 뜨면 알려줘" routes to `watcher_workflow`.
- Ambiguous requests return `unknown` with one clarifying question.

### M7-B: Workflow Spec, Store, And Lifecycle

Goal: create durable workflow definitions separate from task records.

Deliverables:

- `WorkflowSpec`, `WorkflowStep`, `WorkflowRun`, and lifecycle status models.
- SQLite-backed workflow store with create/get/list/update/version behavior.
- Validation for required fields and invalid state transitions.

Acceptance:

- Draft workflow persists and reloads from a new store instance.
- `draft -> proposed -> approved -> active -> paused -> retired` is valid.
- Activation without approval fails.
- Step definitions remain JSON-compatible.

### M7-C: Workflow Designer

Goal: turn vague user requests into proposals through a short interview loop.

Deliverables:

- `WorkflowDesignSession` state.
- Slot extraction for goal, source, cadence, output, alert path, risk, and missing inputs.
- One-question-at-a-time design interview.
- Proposal renderer for web/chat review.

Acceptance:

- A vague recurring request produces a proposal plus one missing-info question.
- A sufficiently complete request produces a proposed spec.
- Designer does not activate workflows.
- Designer records assumptions separately from user-confirmed fields.

### M7-D: Capability Planner And Admission

Goal: decide whether a workflow needs existing tools, connectors, MCP servers, generated scripts, or new skills.

Deliverables:

- `CapabilityPlan` model.
- Planner that maps workflow steps to required capabilities.
- Admission result: allowed, requires approval, missing capability, or needs generated artifact review.
- Integration with existing policy engine.

Acceptance:

- Read-only source collection can be allowed when connector is allowlisted.
- Browser submit, email send, file write, shell, booking, payment, and generated script execution require approval.
- Missing connector produces a clear blocker.
- Skills cannot bypass capability admission.

### M7-E: Workflow Builder And Interpreter V0

Goal: compile approved specs into executable runs using existing task runtime.

Deliverables:

- Builder that turns approved specs into run records and task submissions.
- Interpreter for deterministic fake step types: collect, transform, analyze, report, notify.
- Step-level context and artifact references.
- Trace events for workflow_started, step_started, step_completed, workflow_completed.

Acceptance:

- Approved fake scheduled workflow runs through collect -> analyze -> report.
- Failed step marks run failed and records error.
- Waiting-for-approval step pauses without executing sensitive action.
- Completed run links to report artifact/resource.

### M7-F: Scheduler And Hook Interface V0

Goal: add trigger registration without building a full ops daemon yet.

Deliverables:

- Schedule model for manual, interval, and cron-like text.
- Scheduler store and due-run calculation.
- Hook interface for external events.
- Manual trigger API for tests and UI.

Acceptance:

- Interval schedule can produce a due workflow run.
- Paused workflow does not run.
- Manual trigger creates a run immediately.
- No real network or browser calls in scheduler tests.

### M7-G: Workflow Review UI/API

Goal: expose workflow proposal, approval, activation, and run status through the existing local web UI.

Deliverables:

- Routes for listing workflow specs/runs.
- Proposal review page with approve/reject/activate/pause controls.
- Recent run status and report links.
- Minimal mobile-safe HTML.

Acceptance:

- User can review a proposed workflow before activation.
- User can pause an active workflow.
- UI shows latest run status and errors.
- Existing chat/task/approval pages keep working.

### M7-H: Kernel Probe Evals And Docs

Goal: prove that vertical examples use the kernel rather than bespoke architecture.

Deliverables:

- Fake specs/evals for newsletter, social trend, idea synthesis, browser watcher, and coding workflow.
- `docs/workflow_kernel_status.md`.
- Roadmap update marking vertical workflows as probes.

Acceptance:

- Each probe can be represented as a `WorkflowSpec`.
- At least one probe executes end-to-end with fake steps.
- No probe introduces a top-level use-case-specific runtime path.
- Full default eval suite passes without GPU, network, browser, or live Gmail.

## Integration Order

1. M7-A and M7-B first.
2. M7-C depends on M7-A/B.
3. M7-D can start after M7-B.
4. M7-E depends on M7-B/D.
5. M7-F depends on M7-B/E.
6. M7-G depends on M7-B/C/E/F.
7. M7-H runs last and owns acceptance probes.

## Final Acceptance

Default checks:

```bash
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
```

Manual smoke:

- Open the local web UI.
- Submit: "주식 커뮤니티 글을 주기적으로 모아서 트렌드 보고서로 알려줘."
- Confirm the harness creates a workflow design session, asks one missing-info question, renders a proposal, waits for approval, persists the approved workflow, and can run a fake collect/analyze/report cycle.

## Non-Goals

- No production Reddit/DCInside crawler in M7.
- No live Gmail OAuth in M7.
- No browser automation execution in M7.
- No marketplace skill/plugin install.
- No autonomous script execution before artifact admission and approval.
