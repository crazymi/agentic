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

- Default verification command:

  ```bash
  .venv/bin/python -m unittest discover -s evals
  .venv/bin/python -m agentic.app.cli config-check
  ```

- Default tests must not require GPU, live network, real Gmail, real browser automation, or live ntfy.
- Real model/GPU tests remain opt-in.
