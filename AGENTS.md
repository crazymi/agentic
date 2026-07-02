# Agentic Harness Instructions

## Non-Negotiable Project Boundary

This repository builds an **Agent Harness / Framework**, not individual crawlers, ticket bots, reports, or one-off workflows.

Codex is the **Harness operator and evaluator**. Codex must not secretly perform the target workflow. The Agentic Harness must receive the user's rough request, ask questions, choose tools, create artifacts/workflows/scripts when needed, run them, observe failures, and recover through its own exposed loop.

### Codex May Do

- Act as the `User` inside a Harness session: send rough requests, answer interview questions, and give feedback on weak results.
- Inspect session logs, traces, tasks, artifacts, delivery records, and failure evidence.
- Implement only reusable Harness primitives when a gap is general across workflows, such as search/source discovery, task runtime, scheduler, approval, artifact admission, connector boundary, skill workshop, trace/replay, or session feedback.
- Report exactly what the Agent did, what Codex changed as generic infrastructure, what Codex still assisted, and what must become autonomous next.

### Codex Must Not Do

- Write or run the concrete crawler, macro, report, schedule, source strategy, or workflow for the Agent.
- Add hidden domain knowledge such as a target URL, selector, site filter, noise rule, report shape, script, or schedule to make a specific probe pass.
- Patch for a specific site or use case such as DCInside, Reddit, WSJ/Gmail, Interpark, or Obsidian and call it framework progress.
- Claim Agent autonomy from preseeded sources, fixtures, fake/dummy paths, or operator-authored shortcuts.
- Report searches, discoveries, retries, or fixes as Agent behavior unless they are visible in Harness state produced by the Agent/runtime.

### Decision Rule

- If the Agent needs to search, build a generic search/source-discovery capability.
- If the Agent collects noisy data, do not add a site-specific filter. Give in-session user feedback such as "the result is too noisy; diagnose and revise your strategy with your tools" and observe the Agent's recovery.
- If the same blocker repeats across probes, convert it into a generic Harness primitive, lifecycle gate, policy rule, skill proposal, or benchmark.

### Evaluation Rule

Real-use evaluation starts from the Harness front door with no hidden source registry and no operator-provided solution details. Success requires reviewable state for discovery, candidate storage, source binding, activation, execution, artifact/report creation, and delivery or a precise blocker.

## Agent Learning Loop Bootstrap

This repo uses a repo-local agent learning loop. The loop is implemented through both:

- operator-facing routine files in `.agent/`
- runtime-facing structured experience in `agentic.experience` and `traces/experience.jsonl`

Before starting substantial work:

1. Read this `AGENTS.md`.
2. Read `.agent/OPERATING_ROUTINE.md` if it exists.
3. Read `.agent/MEMORY.md` if it exists.
4. Read `.agent/LESSONS.md` if it exists.
5. Check `.agent/TASK_LOG.md`, `docs/work_log.md`, and recent `experience-list` output when relevant.
6. Then inspect the actual repo files needed for the task.

During work:

1. Follow the current user request first.
2. Prefer existing repo conventions and framework primitives over generic best practices or vertical one-offs.
3. Keep changes proportional to the request.
4. If the task is ambiguous, make a reasonable assumption and state it briefly.
5. If the action is destructive, risky, expensive, authenticated, or externally visible, ask before doing it.

After work:

1. Report what changed.
2. Report what was verified.
3. Report any remaining risks or next steps.
4. Update `docs/work_log.md` for substantive completed work.
5. Update `.agent/TASK_LOG.md` when the work creates useful recent context.
6. Update `.agent/MEMORY.md` only for durable context.
7. Update `.agent/LESSONS.md` when user feedback or task outcome reveals a reusable lesson.
8. If a workflow repeats, prefer a Skill Workshop proposal before creating or editing active skill files.

Memory discipline:

- Do not save everything.
- Save only information that will improve future work.
- Merge or replace outdated memories instead of endlessly appending.
- Keep memory files short, practical, and easy to scan.

## Completion Reporting

- Keep the normal final chat response for every task.
- Also send a short Korean ntfy completion summary after finishing user-requested work.
- Prefer this command when available:

  ```bash
  "${CODEX_HOME:-$HOME/.codex}/skills/notify-user/scripts/send_ntfy.sh" "Codex 완료" "요청한 작업을 완료했습니다."
  ```

- Keep the ntfy body to 1-2 concise Korean lines.
- When reporting real Harness evaluation progress over ntfy, include a 0-100 score plus one short reason.
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
