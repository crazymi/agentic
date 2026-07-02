# Experience Loop

The harness should improve through accumulated operational experience, not through one-off chat conclusions. This applies to both the Agentic runtime and the Codex operator working on this repository.

## External References

OpenClaw's public docs separate reusable capability and automation layers:

- Skills are markdown instruction packages with frontmatter, dependency gates, loading precedence, allowlists, and environment/config checks. OpenClaw also has a Skill Workshop where the agent drafts reusable skill proposals for user review instead of editing active skills directly: https://docs.openclaw.ai/tools/skills
- Automation is split across cron, background tasks, inferred commitments, Task Flow, standing orders, hooks, and heartbeat. Their docs describe Task Flow as the durable orchestration substrate above background tasks, while heartbeat batches routine checks into periodic main-session turns: https://docs.openclaw.ai/automation
- Plugin docs emphasize discovery, install source, allowlists, runtime registration checks, and restart/reload behavior. This maps to our connector/tooling backlog and approval gates: https://docs.openclaw.ai/tools/plugin

Hermes Agent coverage is less available in primary docs during this pass, but current public reporting describes it as leaning into task refinement through self-learning: after tasks, it evaluates the result, distills what worked into reusable skill-like files, and retrieves those lessons for similar future tasks. We should treat that as a pattern, not as an implementation dependency: https://www.techradar.com/pro/how-to-automate-workflows-using-open-source-ai-agents

Related self-evolving agent research reinforces the same shape:

- EvolveR frames self-improvement as an experience-driven lifecycle: offline distillation of trajectories into reusable strategic principles, then online retrieval and accumulation of new trajectories: https://arxiv.org/abs/2510.16079
- Autogenesis describes versioned resources and a closed loop for proposing, assessing, and committing improvements with lineage/rollback: https://arxiv.org/abs/2604.15034
- Memory-for-agents surveys model agent memory as a write-manage-read loop coupled to perception and action, with reflection and retrieval as recurring mechanisms: https://arxiv.org/abs/2603.07670

## Our Translation

The local harness should use this loop:

```text
attempt
 -> observe evidence
 -> classify outcome
 -> record experience
 -> extract bottleneck/lesson
 -> create tooling/skill/eval/roadmap item
 -> retrieve before similar work
```

This loop is deliberately smaller than a self-modifying agent:

- No automatic code changes without review.
- No skill file mutation without approval.
- No live external action unless policy allows it.
- No invented success. A probe must say whether it completed, paused for approval, or exposed missing tooling.

## Codex Operator Bootstrap

The repo also has a lightweight Codex-operator bootstrap under `.agent/`:

- `.agent/OPERATING_ROUTINE.md` defines the start/work/finish routine.
- `.agent/MEMORY.md` keeps durable repo/user/workflow context that is useful before editing.
- `.agent/LESSONS.md` keeps reusable lessons from actual work and feedback.
- `.agent/TASK_LOG.md` keeps short recent operator context.

These files do not replace the structured runtime experience store. They are the human-readable operating layer that tells Codex when to inspect and update:

- `traces/experience.jsonl` for structured evidence from probes, real-bench runs, decisions, bottlenecks, and lessons
- `docs/work_log.md` for project history and roadmap impact
- Skill Workshop proposal state for repeated workflow procedures that should not become active skills without review

Use `.agent/` sparingly. Durable evidence should stay machine-readable when possible, and repeated procedures should graduate through the Skill Workshop proposal boundary before becoming active skills.

## Implemented Backbone

The first implementation is `agentic.experience`:

- `ExperienceEvent`
- `ExperienceStore`
- `RequirementProbe`
- `RequirementSmokeResult`
- `run_requirement_smoke()`

CLI:

```bash
.venv/bin/python -m agentic.app.cli requirements-smoke
.venv/bin/python -m agentic.app.cli experience-list --limit 20
```

Default output:

- machine-readable JSON to stdout
- structured JSONL experience events in `traces/experience.jsonl`
- temporary or configured SQLite stores for workflow/source/artifact/tooling state

## Real Benchmark

`requirements-smoke` is useful for framework coverage, but product usefulness is measured by `real-bench`:

```bash
.venv/bin/python -m agentic.app.cli real-bench
```

`real-bench` must not use fake, dummy, synthetic, fixture, or preapproved shortcuts. It attempts actual paths and records exact blockers:

- `needs_credential`
- `needs_input`
- `blocked_by_tooling`
- `failed_live_attempt`
- `completed`
- `completed_empty`

## User Requirement Probes

Current probes:

- WSJ newsletter analysis
- stock community trend crawler
- idea memory synthesis
- harness self-improvement coding workflow
- browser ticket transaction
- mobile approval notification loop

Each probe answers:

- Did the request route to the right intent?
- Could it produce a workflow spec?
- Could it run end-to-end on checked-in local sources?
- Did it stop correctly at approval?
- Did it produce tooling backlog for missing capabilities?
- What lesson should be reused next time?

## Operating Rules

- Before substantial Codex work, inspect recent experience when it is relevant to the task.
- During Agentic runtime execution, blocked workflows should become structured experience, tooling backlog, approval requests, or retry state.
- Run `requirements-smoke` after major workflow/kernel/tooling changes.
- Run `real-bench` when judging whether user requirements actually work.
- Treat every failed smoke as experience, not just a test failure.
- Add a regression eval when a bottleneck is fixed.
- Promote recurring bottlenecks into roadmap items.
- Keep concrete probes as validation cases for framework primitives, not as bespoke top-level systems.
- Prefer finish-line probes that prove a workflow reaches a terminal useful state on a real path.
