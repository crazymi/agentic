# Agentic Harness Instructions

## Completion Reporting

- Keep the normal final chat response for every task.
- Also send a short Korean ntfy completion summary after finishing user-requested work.
- Prefer this command when available:

  ```bash
  "${CODEX_HOME:-$HOME/.codex}/skills/notify-user/scripts/send_ntfy.sh" "Codex 완료" "요청한 작업을 완료했습니다."
  ```

- Keep the ntfy body to 1-2 concise Korean lines.
- Do not include logs, secrets, stack traces, or long output in ntfy messages.
- If the task could not be completed, send a short Korean failure/blocker summary instead of a success message.

## Roadmap And Work Log

- At the end of every user-requested work item, review `docs/roadmap.md` and state the next recommended step in the final response.
- Include a short "Lessons learned" section in the final response when the work changed architecture, roadmap, runtime behavior, tests, or project process.
- Append a work-log entry to `docs/work_log.md` for every substantive completed task.
- Maintain the table of contents at the top of `docs/work_log.md` whenever adding a new entry.
- Work-log entries should include:
  - date and local time with timezone, for example `2026-07-01 12:01 KST`
  - task summary
  - changed areas
  - verification
  - roadmap impact
  - next step
  - lessons learned

## Experience Loop

- This loop applies to both:
  - the Codex operator working in this repository
  - the Agentic runtime and agents being built in this repository
- Treat every substantive task, smoke test, failed attempt, and architectural decision as experience that should be reusable later.
- User-facing capability claims and internal benchmarks must use real execution paths only. Do not count fake, dummy, synthetic, fixture, or preapproved shortcuts as product capability.
- Prefer scriptable probes over one-off manual checks. When a user requirement is discussed, add or run a probe that can be executed without UI when possible.
- Use `requirements-smoke` to evaluate current coverage of user-shaped requirements and record bottlenecks.
- Use `real-bench` to evaluate actual user-requirement execution. If a credential, URL, approval, or live connector is missing, record that exact blocker and notify the user instead of substituting test data.
- Store structured experience events in `traces/experience.jsonl` through the `agentic.experience` module.
- Convert repeated bottlenecks into one of:
  - tooling backlog item
  - skill proposal
  - roadmap milestone
  - policy/approval rule
  - eval regression
- Do not let a failed run end as chat-only memory. Record:
  - what was attempted
  - what evidence was observed
  - where the agent/runtime got stuck
  - what reusable lesson or tooling gap follows
- Before implementing a similar task again, inspect recent experience and avoid repeating known failure paths.
- Before substantial Codex work, inspect recent experience when relevant, then choose the next implementation slice based on observed bottlenecks.
- During Agentic runtime execution, convert blocked workflows into structured events, tooling backlog, approval requests, or retry state instead of silent failure.
- Prefer "finish-line" evaluations: tests and probes should prove that a workflow can reach a terminal useful state, not merely that a spec can be represented.
- "Finish-line" means a real useful state on a real path. Local fixtures can remain for low-level developer tests only, but they must not be presented as harness autonomy or requirement completion.
- Keep learning auditable: experience entries must be structured, timestamped, and tied to evidence such as command output, trace event, workflow run, or test result.

## Product Direction

- This project is an Agent Harness / Framework, not a collection of bespoke automations.
- Concrete workflows such as newsletter analysis, social trend crawling, ticket watching, coding, and idea synthesis are validation probes for reusable primitives.
- Prefer framework primitives over one-off vertical paths:
  - Intent Router
  - Workflow Designer
  - Workflow Spec
  - Workflow Builder
  - Scheduler / Hook
  - Capability Admission
  - Artifact Registry
  - Task Runtime
  - Connector / MCP boundary
  - Skill System
  - Memory / Resource stores
  - Trace / Replay

## Verification

- Default developer verification command:

  ```bash
  .venv/bin/python -m unittest discover -s evals
  .venv/bin/python -m agentic.app.cli config-check
  ```

- Default tests must not require GPU, live network, real Gmail, real browser automation, or live ntfy.
- Real user-requirement verification command:

  ```bash
  .venv/bin/python -m agentic.app.cli real-bench
  ```

- Real model/GPU, network, ntfy, Gmail, and browser probes are expected to expose actual blockers when credentials/tooling are missing.
