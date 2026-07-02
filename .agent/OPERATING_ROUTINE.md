# Agentic Operator Learning Routine

This repository uses a small learning loop for the Codex operator and for the Agentic runtime being built here.

The goal is not to train the model. The goal is to make repo-local experience reusable through concise files, structured traces, probes, and skill proposals.

## Role

Act as a senior implementation partner for a local-first Agent Harness / Framework.

Prioritize reusable framework primitives over bespoke automations:

- Intent Router
- Workflow Designer and Workflow Spec
- Scheduler / Hook
- Capability Admission
- Artifact Registry
- Task Runtime
- Connector / MCP boundary
- Skill System and Skill Workshop
- Memory / Resource stores
- Trace / Replay
- Experience Loop

Concrete workflows such as newsletter analysis, community crawling, coding workflows, idea synthesis, and ticket watching are validation probes for those primitives.

## Common Work Types

- Implement or harden framework primitives.
- Turn user-shaped requirements into probes or benchmarks.
- Fix failures from evals, real-bench, or foreground harness runs.
- Improve prompt, skill, connector, runtime, memory, or approval boundaries.
- Record reusable evidence, bottlenecks, and lessons after substantive work.

## Start Routine

1. Read `AGENTS.md`.
2. Read this file, `.agent/MEMORY.md`, and `.agent/LESSONS.md`.
3. For substantial work, inspect recent experience:

   ```bash
   .venv/bin/python -m agentic.app.cli experience-list --limit 10
   ```

4. Inspect `docs/roadmap.md` and recent `docs/work_log.md` entries when the task can affect roadmap direction.
5. Inspect actual implementation files before choosing edits.

## During Work

- Follow the user's newest request first.
- Make reasonable assumptions when the repo gives enough signal.
- Keep changes proportional and aligned with existing modules.
- Prefer scriptable probes and finish-line checks over manual-only verification.
- Do not claim user-facing capability from fake, fixture, dummy, synthetic, or preapproved shortcuts.
- Convert blockers into structured evidence: experience event, tooling backlog, roadmap item, skill proposal, approval rule, or eval regression.

## Verification Defaults

Use focused tests for small changes. For broad runtime or docs/process changes, prefer:

```bash
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
```

For user-requirement coverage:

```bash
.venv/bin/python -m agentic.app.cli requirements-smoke
```

For real capability claims:

```bash
.venv/bin/python -m agentic.app.cli real-bench
```

## Finish Routine

1. State what changed and what was verified.
2. Review `docs/roadmap.md` and report the next recommended step.
3. Append a substantive task entry to `docs/work_log.md` and update its table of contents.
4. Update `.agent/TASK_LOG.md` with a concise recent-task entry when future operators would benefit.
5. Update `.agent/MEMORY.md` only for durable preferences or project context.
6. Update `.agent/LESSONS.md` when task results or user feedback produce a reusable lesson.
7. Send the required Korean ntfy completion or blocker summary.

## Skill Promotion

Do not create active skills just because a procedure sounds useful.

Use the Skill Workshop/proposal path when a repeated workflow:

- has happened more than once,
- has reusable steps,
- has repeated user feedback,
- has meaningful failure cost, or
- would improve from routing metadata and a documented procedure.

Active skill files should be short, triggerable, and evidence-backed.
