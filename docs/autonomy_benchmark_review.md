# Autonomy Benchmark Review

## Current Harness Autonomy

Current overall level: **L2.3 / L5**.

This is a strong framework backbone with real benchmark instrumentation, but not yet a high-autonomy live executor.

## Scale

| Level | Meaning |
| --- | --- |
| L0 | Chat-only assistant. No durable state or tools. |
| L1 | Single-turn tool user. Can call simple tools but does not manage long-running work. |
| L2 | Supervised workflow planner. Can turn vague requests into workflow specs, approvals, traces, and backlog. |
| L3 | Supervised executor. Can run multi-step workflows with pause/resume, real tools, and user checkpoints. |
| L4 | Unattended recurring operator. Can run 24/7 watchers with recovery, retries, monitoring, and escalation. |
| L5 | Self-improving autonomous operator. Can safely build missing tooling, validate it, and improve its own workflows over time. |

## Dimension Scores

| Dimension | Score | Notes |
| --- | ---: | --- |
| Intent classification | 3 / 5 | Routes major user-shaped requests, including browser transaction. Still rule-heavy. |
| Workflow planning | 3 / 5 | Produces durable workflow specs and planning sessions. Multi-turn design is early. |
| Durable execution | 2.5 / 5 | SQLite tasks/runs exist and local-source workflows can reach terminal reports. Live pause/resume is still incomplete. |
| Real tool use | 1.5 / 5 | Local add/source/report works. No live browser/Gmail/crawler/coding patch execution yet. |
| Approval and policy | 3 / 5 | Sensitive capabilities stop correctly. Approval-resume is not complete. |
| 24/7 operation | 2 / 5 | Task pool, health, scheduler primitives exist. No production watcher retry loop yet. |
| Browser autonomy | 0.6 / 5 | Browser transaction can be represented and measured by real-bench, but no live adapter exists. |
| Coding autonomy | 1.5 / 5 | Repo inspection/report works. No patch/test/PR loop yet. |
| Memory/learning | 2.5 / 5 | Experience JSONL and requirement smoke exist. Retrieval is manual/CLI, not yet agent-in-loop. |
| Self-improvement | 1.5 / 5 | Tooling backlog exists. No autonomous implementation/validation cycle yet. |

## Current Capability Summary

Can do now:

- receive a blurry automation request
- classify many requirement shapes
- open a durable planning session
- ask one missing question
- produce a workflow spec
- bind local checked-in sources
- run local-source collect/analyze/report workflows
- stop sensitive work at approval/tooling boundaries
- append structured experience from probes
- expose bottlenecks and missing tooling
- run real-bench probes that expose actual blockers

Cannot do yet:

- operate real browser pages
- log in, wait for user, then resume browser work
- run real Gmail ingestion
- run production Reddit/DCInside crawling
- patch/test code as an approval-gated workflow
- perform long-running retry watchers with state hashing/backoff
- automatically consume past experience before each new decision
- self-build missing tooling end-to-end

## Expected External Benchmark Performance Today

| Benchmark family | Expected current result | Why |
| --- | --- | --- |
| WebArena / VisualWebArena / Mind2Web | near zero | no live/simulated benchmark browser adapter yet. |
| OSWorld / Windows Agent Arena | near zero | no GUI/desktop action layer. |
| WorkArena / BrowserGym | near zero | no browser action adapter; enterprise workflow state not modeled. |
| SWE-bench | near zero | no patch/test loop or repository edit runtime yet. |
| GAIA / BrowseComp | low | no live web research connector in product runtime. |
| AgentBench | low to partial | can represent tasks, but many interactive environments/tools are missing. |
| τ-bench | partial scaffold only | approval/policy/tooling concepts map well, but domain API tools and user simulator are missing. |
| MCP-Bench / ToolBench | partial scaffold only | MCP/tool boundary exists, but broad MCP tool execution and complex cross-tool tasks are not production-ready. |

## Benchmarks To Track

- Web/UI agents: WebArena, VisualWebArena, Mind2Web, WorkArena/BrowserGym.
- Computer-use agents: OSWorld, Windows Agent Arena.
- Coding agents: SWE-bench, SWE-bench Verified/Pro, SWE-Skills-Bench.
- Tool-use agents: ToolBench, AgentBench, MCP-Bench, BFCL.
- User/tool policy agents: τ-bench.
- General assistant autonomy: GAIA, BrowseComp.

## Recommendation

Use public benchmarks as directional targets, but build an internal benchmark first:

```text
RequirementSmoke
 -> real-bench
 -> live browser benchmark
 -> coding patch/test benchmark
 -> memory/Obsidian benchmark
 -> external benchmark subset
```

Next implementation target:

- workflow run pause/resume
- approval-resume
- retry state for unavailable/sold-out/browser-blocked states
- live browser adapter with no fixture or dummy substitute
- finish-line benchmarks that require terminal useful states, not just workflow representation
