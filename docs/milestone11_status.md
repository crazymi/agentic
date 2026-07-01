# Milestone 11 Status

Status: started.

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

What this enables:

- The harness can receive a blurry automation request.
- It can open a durable planning session.
- It can ask the next missing question.
- A user answer can advance the session into a proposed workflow.
- The proposed workflow can reveal which tooling/capability primitives must be implemented before execution.

Current boundary:

- This is still framework backbone, not live browser automation.
- `ASK_USER`, `BROWSER_OBSERVE`, `BROWSER_ACTION`, and approval-resume are represented but not fully executable in the interpreter yet.
- No real Playwright/Chrome adapter is included in this step.
- No real purchase, booking, submit, or payment action is possible.

Verification:

```bash
.venv/bin/python -m unittest evals.test_milestone11_harness_backbone
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
```

Latest result:

- `Ran 158 tests`
- `OK (skipped=2)`
- config-check passed

Next:

- Implement M11 runtime execution slice:
  - executable `ASK_USER` step
  - workflow run pause/resume for user input
  - approval-resumable workflow runs
  - local browser adapter boundary using fixture pages first
  - browser observation artifacts for screenshot/DOM/text state
  - retry policy state for sold-out/not-yet-open/blocked pages

