# Framework Reference Review For The Harness

This review exists to keep the project pointed at an agent harness, not a pile of one-off automations.

The concrete use cases are probes. The framework primitives are the product.

## Sources Reviewed

- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- AutoGen overview and Core quickstart: https://microsoft.github.io/autogen/stable/
- CrewAI docs and Flows: https://docs.crewai.com/
- LlamaIndex Agent Workflows: https://developers.llamaindex.ai/python/llamaagents/workflows/
- Semantic Kernel Agent Framework: https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/
- AgentSPEX paper: https://arxiv.org/abs/2604.13346

OpenClaw, Codex, MCP, and Hermes-style prior notes remain in `docs/mcp_skill_catalog.md` and `docs/roadmap.md`.

## Patterns To Borrow

| Framework | Useful pattern | Harness implication |
| --- | --- | --- |
| LangGraph | Low-level orchestration runtime for long-running stateful agents, with persistence, human-in-the-loop, streaming, memory, and observability. | Keep the core as an orchestration runtime, not a use-case app. Workflow state and execution must be durable and inspectable. |
| AutoGen | Separates agent logic from message delivery via an agent runtime; supports event-driven multi-agent systems, topics, subscriptions, and extensions such as MCP workbenches. | Introduce a request/event router and workflow runtime boundary. Agents should not own scheduling or transport. |
| CrewAI | Separates agents/crews/tasks from flows; flows are event-driven, can branch, manage state, persist, and resume. | Use `WorkflowSpec` for deterministic control flow and reserve agents/subagents for intelligence inside steps. |
| LlamaIndex Workflows | Workflows are event-driven steps; typed events define edges; human input is modeled as input-required and response events; context can be snapshotted/restored. | Human review, approvals, and follow-up questions should be workflow events, not ad hoc chat pauses. |
| Semantic Kernel Agents | Separates agents, threads, plugins, and orchestration patterns such as sequential, concurrent, handoff, group chat, and magentic. | Make orchestration pattern a first-class field. Do not hardcode every workflow as the same master/subagent loop. |
| AgentSPEX | Declarative workflow spec with typed steps, branching, loops, submodules, parallel execution, explicit state, checkpointing, tracing, replay, and verification. | Make workflow definitions data-first and versionable. Python implementation is the interpreter, not the workflow itself. |

## Core Design Correction

The harness should not implement `newsletter`, `crawler`, `ticket watcher`, or `coding agent` as top-level architecture.

Those are vertical probes for this framework shape:

```text
User request
 -> Intent Router
 -> Workflow Designer
 -> Workflow Proposal
 -> Approval
 -> Workflow Spec
 -> Workflow Builder
 -> Scheduler / Hook / Task Runtime
 -> Agents / Tools / Connectors / MCP
 -> Resource / Memory / Artifact Store
 -> Report / Notification / Trace
 -> Review / Iterate / Retire
```

The framework owns the lifecycle. Use cases provide fixtures and acceptance tests.

## Target Primitive Set

Keep these primitives distinct:

- `RequestIntent`: what kind of work the user is asking for.
- `WorkflowDesignSession`: the interactive planning state for turning vague intent into a runnable spec.
- `WorkflowSpec`: durable, versioned description of goal, triggers, steps, capabilities, policy, outputs, and notifications.
- `WorkflowRun`: one execution of a spec, with step state, context, approvals, artifacts, and trace linkage.
- `WorkflowStep`: a typed operation such as collect, transform, analyze, ask_user, approve, call_tool, call_connector, run_agent, report, notify, or subworkflow.
- `CapabilityPlan`: declared tools/connectors/MCP/scripts needed by a workflow, with admission and approval requirements.
- `Artifact`: durable output such as generated scripts, reports, screenshots, crawled pages, summaries, or dataset snapshots.
- `WorkflowTemplate`: reusable pattern created from an approved workflow or skill.

## What To Avoid

- Do not create a `StockCrawler` architecture module as the framework boundary.
- Do not encode each use case as bespoke daemon logic.
- Do not let generated scripts bypass policy, trace, or artifact admission.
- Do not treat Skills as executable plugins. Skills remain instructions/procedures.
- Do not enable broad MCP/tool surfaces without capability allowlists.
- Do not make the model decide safety. Policy remains deterministic Python.

## Vertical Probes

Each probe must validate framework behavior rather than become the architecture:

- Newsletter probe: scheduled source ingestion, grounded analysis, report, notification.
- Social trend probe: scheduled community source ingestion, dedupe, trend analysis, report.
- Idea synthesis probe: channel capture, memory write, periodic synthesis, follow-up question.
- Browser watcher probe: browser source inspection, generated watcher artifact, background run, alert.
- Coding workflow probe: repo source inspection, plan/patch/test/report with approval.

If a probe needs a feature that cannot be expressed through `WorkflowSpec`, improve the spec instead of adding a one-off path.
