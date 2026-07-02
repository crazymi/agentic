# Agent Loop Reference Notes

This document records reference notes for agent-loop, skill, and workflow-building behavior observed in OpenClaw and publicly discoverable Hermes Agent material.

The purpose is not to copy either project. The purpose is to keep this harness focused on agent-driven workflow creation, where the agent interviews the user, discovers missing capabilities, proposes reusable skills, and only mutates the system after approval.

## Sources Reviewed

- OpenClaw repository: https://github.com/openclaw/openclaw
- OpenClaw Skills: https://docs.openclaw.ai/tools/skills
- OpenClaw Skill Workshop: https://docs.openclaw.ai/tools/skill-workshop
- OpenClaw Automation: https://docs.openclaw.ai/automation
- OpenClaw Task Flow: https://docs.openclaw.ai/automation/taskflow
- OpenClaw Scheduled Tasks: https://docs.openclaw.ai/automation/cron-jobs
- TechRadar Hermes/OpenClaw overview: https://www.techradar.com/pro/how-to-automate-workflows-using-open-source-ai-agents
- WildClawBench abstract mentioning Hermes Agent as a native-runtime harness: https://arxiv.org/abs/2605.10912

## Source Confidence

OpenClaw confidence is high because official docs and the public repository were available.

Hermes Agent confidence is limited. Search found secondary references and benchmark mentions, but did not identify a primary Hermes Agent docs or repository URL with enough confidence to treat it as implementation truth. Until a primary Hermes source is provided or found, Hermes should be used only as directional input: self-learning, task reflection, and skill evolution after real task attempts.

## 2026-07-02 Comparison Refresh

Additional web review confirmed the earlier confidence split:

- OpenClaw official docs remain the best primary reference for skills, Skill Workshop, automation, scheduled tasks, and Task Flow.
- OpenClaw's Skill Workshop explicitly keeps agent/operator proposals out of live `SKILL.md` files until review/apply. It records target binding, scanner state, hashes, support-file metadata, rollback metadata, stale state, and consistent chat/CLI/Gateway surfaces.
- OpenClaw's automation docs separate exact scheduling, heartbeat-style periodic awareness, background tasks, Task Flow, hooks, standing orders, and inferred commitments. Task Flow is the durable multi-step orchestration layer above individual background tasks.
- OpenClaw's scheduled tasks run in the Gateway/runtime, persist schedules and run history in SQLite, create background task records, handle startup/reschedule behavior, and treat blocked commands, model failures, and timeouts as job errors rather than green runs.
- OpenClaw's skills are loaded through deterministic eligibility gates, per-agent allowlists, environment/config checks, prompt injection, and session snapshots. This means AI can use selected skills, but the runtime decides which skills are visible.
- Hermes Agent still lacks a primary documentation source in this repo's research trail. Secondary reporting describes it as narrower and more self-learning oriented: after tasks, it evaluates outcomes, turns repeatable behavior into reusable skill files, and reuses them for similar future work. Treat that only as a design pattern, not as verified API behavior.
- Security research around always-on agents reinforces the need for provenance gates, approval-bound persistent changes, and explicit authority separation because memory, skills, schedules, filesystem patches, and shell access can become delayed attack surfaces.

Design conclusion for this harness:

- AI should propose, interpret ambiguity, summarize, critique, and repair.
- The deterministic Harness should own eligibility, visibility, persistence, state transitions, policy, approval, scheduling, execution admission, provenance, replay, and failure classification.

## OpenClaw Patterns To Borrow

OpenClaw treats skills as instruction packages, not executable tools. A skill is a `SKILL.md` directory with metadata and procedure text. Skills are loaded by precedence, can be scoped per workspace or per agent, and can be allowlisted per agent.

The most important pattern is Skill Workshop. The agent must not directly write active `SKILL.md` files when it notices reusable work. It creates a pending proposal first. The proposal is inspectable, reviewable, scanner-gated, hash-bound, and only becomes active after apply/approval.

For our harness, this means:

- agent-generated skills should be proposals, not live files
- proposal records need status, target, content, scanner/review metadata, and rollback or supersession metadata
- apply/reject/quarantine must be approval-gated
- the active runtime should never let a model bypass the workshop by writing skill files directly

OpenClaw automation separates recurring schedules, background tasks, task flows, hooks, standing orders, inferred commitments, and heartbeat. That separation matters because a user request like "watch this every minute and report trends hourly" is not one feature. It is schedule + durable task + flow + resource capture + analysis + notification + experience review.

Task Flow sits above individual tasks. It coordinates multi-step progress and durable state while tasks remain the unit of detached work. Reliable recurring workflows should separate timing, orchestration, deterministic preflight, LLM summary, approval, and delivery.

## Hermes-Style Patterns To Treat As Directional

Secondary sources describe Hermes Agent as narrower than OpenClaw and focused on depth: after tasks, it evaluates what worked, turns repeatable behavior into skill files, and reuses them on similar future tasks.

Because primary docs were not found, this project should not implement against assumed Hermes APIs. Instead, borrow the abstract pattern:

- every substantial attempt produces an experience record
- repeated successful or failed patterns become skill-proposal candidates
- skill changes require evidence, not vibes
- the harness should preserve decision history so future agents understand why a skill exists or changed

## Required Loop For This Harness

The next useful loop is not another concrete crawler or another fixed workflow.

Target loop:

```text
User vague request
 -> Master interview turn
 -> one missing question at a time
 -> user answers
 -> Master capability discovery
 -> Master proposes workflow shape
 -> Master identifies missing tools/connectors/skills
 -> proposal records are created
 -> user approval gates mutation/execution
 -> execution attempt runs
 -> experience event records outcome and bottlenecks
 -> repeated pattern creates skill proposal, not active skill
```

Important constraints:

- Codex/operator must not hand-author the workflow or tool when the experiment is to observe the agent.
- The agent must first state what it thinks is missing.
- Generated scripts, generated tools, and generated skills are artifacts or proposals before activation.
- Real execution matters; toy QA or unrelated smoke tests are not useful for this phase.

## Current Harness Observation

Request sent to the current harness:

```text
workflow building 자체를 재사용 가능한 SKILL로 만들기 위한 skill proposal을 작성해줘. 단, 실제 파일을 쓰지 말고 proposal 형태로: 언제 발동되는지, 유저 인터뷰 loop, capability 발견, approval 전환, experience 기록, skill 후보 생성까지 포함해.
```

Observed result:

- `user_message_received`
- `master_model_called`
- `master_delegation_decision` with `answer: 답변을 정리하지 못했습니다.`
- `master_final_answer` with the same failure text

Interpretation:

- The current Phase 1 master loop cannot create a skill proposal.
- It does not know how to enter an interview loop.
- It does not discover required capabilities.
- It does not create proposal artifacts.
- It does not route skill creation through a workshop/review boundary.

## Immediate Design Implication

The next milestone should be an agent-observation and proposal loop, not more hand-authored primitives.

Minimum useful capability:

- accept a vague request
- ask exactly one clarifying question
- persist the design session
- accept the user's answer
- ask the next question or propose a plan
- when reusable behavior is detected, create a `SkillProposal` record instead of writing a skill
- expose proposal inspect/reject/apply actions behind approval

This is the smallest path that respects the user's direction: the harness must let the agent try to build workflows and skills, while the operator observes and approves rather than pre-building the solution.

## Implemented First Step

The harness now has a minimal Skill Workshop-style proposal boundary:

- `SkillProposal` model with pending/rejected/quarantined/applied/stale statuses
- SQLite-backed `SkillWorkshopStore`
- `SkillWorkshopService`
- agent-facing `skill_workshop` tool
- CLI-facing `skill-workshop` command

The current `skill_workshop` tool supports:

- `create`
- `list`
- `inspect`
- `revise`
- `reject`
- `quarantine`

It intentionally does not support `apply` yet. Applying a proposal would write an active `SKILL.md`, so it needs an approval-bound implementation with scanner/review metadata first.

This first step makes it possible for a future Master/subagent turn to create pending skill proposals without mutating active skills directly.

## Remaining Gap To OpenClaw/Codex Level

OpenClaw's mature shape includes proposal scanning, support-file hashing, stale detection, rollback metadata, approval-gated apply, chat and CLI parity, and policy boundaries preventing direct writes. Codex's skill creator works as an operator-guided skill authoring process with progressive disclosure, validation, and explicit user review.

The current harness only has the durable proposal queue and tool surface. It still needs:

- Master prompt/tool loop that chooses `skill_workshop` when reusable behavior is detected
- proposal scanning and size/support-file policy
- approval-gated `apply`
- stale detection when active skills change
- workbench UI for inspect/revise/apply/reject
- experience-driven proposal creation after repeated real attempts
