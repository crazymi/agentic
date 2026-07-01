# Milestone 11 Status

Status: started, with planning/tooling backbone completed. Real browser execution is still blocked by missing live adapter.

Completed in backbone step:

- Added `IntentType.BROWSER_TRANSACTION`.
- Added `StepType.BROWSER_OBSERVE` and `StepType.BROWSER_ACTION`.
- Updated intent routing so requests such as `MSI 2026 결승전 표 예매해줘` become browser transaction planning work instead of falling through the Phase 1 loop.
- Extended `WorkflowDesigner` for high-risk browser transaction workflows.
- Browser transaction designs now include reusable steps:
  - official/source verification
  - user constraint checkpoint
  - browser observe
  - browser action
  - approval before consequential submit
  - report/notification
- Added durable `PlanningSessionStore`.
- Added multi-turn design continuation through `WorkflowDesigner.continue_design()`.
- Added web routes:
  - `GET /planning-sessions`
  - `POST /planning-sessions/{session_id}/answer`
  - `GET /tooling`
- Added web UI panels for planning sessions and tooling backlog.
- Added `agentic/tooling/`:
  - `ToolingRequest`
  - `ToolingPlan`
  - `ToolingPlanner`
  - `ToolingBacklogStore`
- Capability gaps now become explicit tooling backlog items.
- Missing live browser runtime is represented as `connector:browser` with priority `0`, suggested module `agentic/browser/`.

Corrected in real-only benchmark step:

- Removed the local fixture browser adapter from product capability planning and interpreter execution.
- Removed `preapproved` approval bypass from product workflow execution.
- Added `real-bench` so user-shaped requirements are measured by actual paths only.
- Browser transaction real benchmark now reports `needs_input` or `blocked_by_tooling` until an official URL and real browser adapter exist.

What this enables:

- The harness can receive a blurry automation request.
- It can open a durable planning session.
- It can ask the next missing question.
- A user answer can advance the session into a proposed workflow.
- The proposed workflow can reveal which tooling/capability primitives must be implemented before execution.
- Real benchmark execution can now report exact blockers instead of fabricating browser progress.

Current boundary:

- This is still not live browser automation.
- `BROWSER_OBSERVE`, `BROWSER_ACTION`, and approval-resume are not executable until real adapters/services are implemented.
- Real pause/resume for user login and approval-resume are still not complete.
- No real Playwright/Chrome adapter is included in this step.
- No real purchase, booking, submit, or payment action is possible.

Verification:

```bash
.venv/bin/python -m unittest evals.test_milestone11_harness_backbone
.venv/bin/python -m agentic.app.cli config-check
.venv/bin/python -m agentic.app.cli real-bench
```

Latest real-bench expectation:

- Real memory/repo/ntfy/network/model probes should attempt actual paths.
- Gmail should report `needs_credential` until real credentials are configured.
- Ticket browser should report `needs_input` or `blocked_by_tooling` until an official URL and live adapter exist.

Next:

- Implement M11 resume/retry slice:
  - workflow run pause/resume for live user input
  - approval-resumable workflow runs
  - retry policy state for sold-out/not-yet-open/blocked pages
  - live browser adapter boundary with no fixture/dummy substitute
  - login-required state that notifies the user and resumes after confirmation
