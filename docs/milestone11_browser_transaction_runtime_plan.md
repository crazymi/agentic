# Milestone 11 Plan: Interactive Browser Transaction Runtime

## Summary

Milestone 11 makes the harness capable of handling high-risk, login-gated browser workflows such as:

```text
MSI 2026 final tickets, please book them for me.
```

This is not an MSI-specific automation. MSI ticketing is the validation probe for reusable framework primitives:

- session-backed workflow design
- deep research source verification
- browser observe/action runtime
- user input checkpoints
- approval-gated consequential actions
- retryable watcher mode for sold-out or not-yet-open states

## Human Baseline

If a careful human operator handled the MSI ticket request, the procedure would be:

1. Clarify the user's target:
   - event: MSI 2026 Grand Final
   - date/time: July 12, 2026, KST
   - venue: Daejeon Convention Center II
   - quantity, max price, seat preference, account/payment constraints
2. Verify official sources:
   - LoL Esports official news/schedule
   - official ticketing platform
   - venue/event policies
   - ticket sale wave and eligibility rules
3. Decide the route:
   - if ticket sales are not open, create a watcher
   - if sold out, watch for cancellations/re-openings
   - if available, proceed to booking attempt
4. Open the official ticketing site in a real browser session.
5. If login is required, stop and ask the user to log in.
6. After login, inspect the page state:
   - queue/waiting room
   - event search result
   - date/session selector
   - seat map or price/section list
   - sold-out/available status
7. If seats are available, select according to user constraints.
8. Stop before any purchase, payment, or irreversible submission.
9. Ask for explicit approval with a concise summary:
   - event/session
   - seat/section/price
   - account being used, if visible
   - exact action to be performed
10. If approved, submit only the approved action.
11. Record confirmation, screenshots, receipt/booking reference, and final report.
12. If unavailable or blocked, classify the failure and schedule a retry or ask the user.

## Current Harness Gaps

The M10 probe showed these missing framework pieces:

- Master routing is still Phase-1-style and too narrow for high-risk multi-step requests.
- Workflow design is stateless; follow-up answers are not attached to a design session.
- `ASK_USER` exists as a step type but is not executable.
- `APPROVAL` exists conceptually but workflow runs cannot resume after approval.
- Browser work is represented as a local file source, not a live browser session.
- There is no browser state classifier for login, queue, sold-out, seat-available, captcha, or submit-ready pages.
- There is no first-class retry policy for watcher loops.
- ntfy is available as a project concept, but external delivery can be blocked by policy and needs a local fallback path.

## New Framework Primitives

### Planning Session

Add durable design sessions so vague user requests can be interviewed over multiple turns.

Required fields:

- `session_id`
- `original_request`
- `intent`
- `slots`
- `missing_slots`
- `questions`
- `answers`
- `proposal_id`
- `status`

Ticket/booking slots:

- target event
- target date/session
- quantity
- max budget
- seat preference
- official source/platform
- account/login path
- notification channel
- retry policy
- purchase approval boundary

### Browser Session

Represent a real browser context as a durable runtime resource.

Fields:

- `browser_session_id`
- `workflow_id`
- `run_id`
- `profile_ref`
- `current_url`
- `state`
- `last_observation_at`
- `screenshot_artifact_id`
- `dom_snapshot_artifact_id`
- `requires_user_presence`

States:

- `created`
- `navigating`
- `login_required`
- `waiting_room`
- `event_not_found`
- `sold_out`
- `available`
- `selection_ready`
- `approval_required`
- `submitted`
- `blocked`
- `failed`

### Browser Observation

A deterministic adapter should capture page state before any model decides what to do.

Observation outputs:

- URL and title
- visible text summary
- buttons/forms/links
- detected login forms
- detected queue/waiting room
- detected seat availability text
- screenshots
- DOM snapshot artifact

### Browser Action

Browser actions must be typed and policy-gated.

Allowed low-risk actions:

- navigate to known official URL
- search within page
- click non-submitting navigation
- open event detail page

Approval-required actions:

- credential submit
- browser form submit
- seat selection lock/hold
- payment step
- ticket booking confirmation

Denied by default:

- captcha bypass
- payment without exact approval
- non-official ticket resale purchase unless explicitly allowed

### User Checkpoint

`ASK_USER` becomes executable.

Use cases:

- ask missing design slot
- ask user to log in
- ask for captcha/manual verification
- ask for purchase approval
- ask whether to switch strategy after repeated failures

Run states:

- `waiting_for_input`
- `waiting_for_approval`
- `resume_requested`

### Retry Policy

Watcher mode should be explicit and durable.

Fields:

- `cadence_seconds`
- `jitter_seconds`
- `max_attempts`
- `quiet_hours`
- `state_change_only`
- `rate_limit`
- `failure_backoff`

Decision outcomes:

- retry same route
- reduce cadence
- ask user
- switch source
- pause workflow
- mark unhealthy

## Proposed Workflow Shape

```text
User request
 -> IntentRouter: browser_transaction / booking
 -> PlanningSession
    -> ask missing slots one by one
 -> DeepResearchSourceVerifier
    -> official event info
    -> official ticketing platform
 -> WorkflowSpec proposal
 -> User approval to activate
 -> BrowserSession start
 -> BrowserObserve
 -> StateClassifier
    -> login_required: ASK_USER + notify
    -> sold_out: schedule retry
    -> available: select candidate seat
    -> approval_required: ask user
 -> BrowserAction
 -> Artifact/Trace/Report
```

## MSI Booking Probe Workflow

```text
Goal:
  Try to book MSI 2026 Grand Final tickets.

Trigger:
  manual first run, then retry watcher if unavailable.

Steps:
  1. verify_official_sources
  2. ask_missing_booking_slots
  3. open_browser_session
  4. navigate_to_official_ticket_platform
  5. observe_page_state
  6. if login_required -> notify user and wait
  7. after user resumes -> find event/session
  8. if sold_out -> schedule retry
  9. if available -> select seats within constraints
  10. ask approval before submit/payment
  11. submit only after approval
  12. save confirmation artifacts
```

## 24/7 Behavior

The harness should not keep the model running continuously. It should use cheap deterministic checks first and call agents only when state changes or interpretation is needed.

Recommended loop:

```text
scheduled tick
 -> acquire workflow singleton lock
 -> browser/source observe
 -> classify state deterministically
 -> if unchanged: record heartbeat and sleep
 -> if changed/ambiguous: call subagent for interpretation
 -> if action required: policy gate
 -> ask user or act within approval boundary
 -> record artifact and next retry
```

For ticketing:

- 1 minute cadence is acceptable only if the site allows it and the adapter rate-limits requests.
- Use jitter to avoid exact periodic traffic.
- Store last availability hash to avoid duplicate alerts.
- Keep only one active browser session per ticket workflow.
- Pause or degrade cadence after repeated blocks, captchas, or queue failures.
- Never attempt payment/booking confirmation without fresh explicit approval.

## Implementation Packages

### M11-A: Intent And Planning Sessions

Owned areas:

- `agentic/workflow_kernel/intent.py`
- `agentic/workflow_kernel/planning_session.py`
- `agentic/workflow_kernel/designer.py`
- web routes for session answers

Acceptance:

- `MSI 2026 결승전 표 예매해줘` routes to a high-risk browser transaction/design session.
- The designer asks one missing slot at a time.
- Follow-up answers update the same session.

### M11-B: Browser Capability Models

Owned areas:

- `agentic/browser/models.py`
- `agentic/policy/engine.py`
- `agentic/workflow_kernel/capabilities.py`

Acceptance:

- browser observe/action capabilities are typed.
- submit/payment/booking actions require approval.
- captcha bypass and unapproved payment are denied.

### M11-C: Browser Adapter Boundary

Owned areas:

- `agentic/browser/adapter.py`
- `agentic/browser/local_playwright.py`
- artifact integration for screenshots/DOM snapshots

Acceptance:

- adapter can navigate to a URL, observe page title/text/buttons, click a safe selector, and save screenshot artifact.
- automated tests use local HTML pages, not live ticketing.

### M11-D: User Checkpoints And Resume

Owned areas:

- `agentic/runtime/task_control.py`
- `agentic/workflow_kernel/interpreter.py`
- `agentic/app/server.py`
- `agentic/channels/`

Acceptance:

- `ASK_USER` creates a pending input request.
- web UI can resume a waiting run with a user answer.
- approval can resume a waiting workflow run.

### M11-E: Retry/Watcher Runtime

Owned areas:

- `agentic/scheduler/`
- `agentic/workflow_kernel/interpreter.py`
- `agentic/runtime/daemon.py`

Acceptance:

- sold-out/not-yet-open state schedules the next attempt.
- repeated failure backs off.
- singleton lock prevents duplicate browser attempts.

### M11-F: MSI Ticket Probe

Owned areas:

- `agentic/workflow_probes/`
- `docs/milestone11_status.md`
- eval fixture pages

Acceptance:

- blurry request creates a planning session.
- answered slots produce a high-risk browser transaction workflow.
- local fixture page can exercise login-required, sold-out, available, approval-required, and completed paths.
- no real purchase or payment occurs in tests.

## Non-Goals

- bypassing captcha or anti-bot systems
- buying tickets without explicit user approval
- storing raw credentials in prompts, traces, docs, or specs
- building an MSI-only one-off script as the architecture
- relying on the model for deterministic state transitions where code can classify state

## Final Acceptance

Default tests:

```bash
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
```

Manual smoke:

```text
1. Open local web UI.
2. Send "MSI 2026 결승전 표 예매해줘".
3. Confirm planning session asks for missing booking details.
4. Provide target session/quantity/budget.
5. Confirm workflow proposal is high-risk and approval-gated.
6. Run against local fixture pages:
   - login required
   - sold out
   - available
   - approval required before submit
7. Confirm the run can pause and resume.
8. Confirm watcher retry state persists across restart.
```

