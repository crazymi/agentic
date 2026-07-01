# Architecture

This harness is a personal local-first agent runtime. The implementation should stay small, but the concepts need to be explicit enough to support 24/7 work.

The system should grow around a narrow core:

```text
message/event -> intent/workflow -> policy/approval -> task runtime -> agent loop -> tools/connectors -> trace/memory
```

## System Map

```mermaid
flowchart TD
    User["User<br/>desktop/mobile"]
    Web["Local Web Channel<br/>chat, inbox, approvals"]
    Ntfy["ntfy Channel<br/>push notifications"]
    EventBus["Runtime Event Bus"]
    Intent["Intent Router"]
    Workflow["Workflow Kernel<br/>design, spec, builder, run"]
    Approval["Approval Service"]
    Policy["Policy Engine"]
    Scheduler["Scheduler"]
    TaskPool["Background Task Pool"]
    Master["Master Agent<br/>Gemma GGUF"]
    Sub["Subagent<br/>DiffusionGemma GGUF"]
    Skills["Skill Loader<br/>procedural instructions"]
    Tools["Tool Registry<br/>typed actions"]
    Connectors["Connectors<br/>local and MCP"]
    Memory["Memory Store<br/>preferences, ideas, standing goals"]
    Resources["Resource Store<br/>emails, notes, pages, screenshots"]
    Trace["Trace and Replay<br/>JSONL then durable store"]

    User --> Web
    Ntfy --> User
    Web --> EventBus
    EventBus --> Intent
    Intent --> Workflow
    Workflow --> Approval
    EventBus --> Approval
    Approval --> Policy
    Policy --> TaskPool
    Scheduler --> EventBus
    Workflow --> Scheduler
    Workflow --> TaskPool
    TaskPool --> Master
    Master --> Sub
    Master --> Skills
    Sub --> Skills
    Master --> Tools
    Sub --> Tools
    Tools --> Connectors
    Connectors --> Resources
    Master --> Memory
    Sub --> Memory
    EventBus --> Trace
    Approval --> Trace
    TaskPool --> Trace
    Tools --> Trace
    Connectors --> Trace
```

## User Communication

The first extension primitive is the user communication and approval surface.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Web as Local Web UI
    participant Runtime as Runtime Event Bus
    participant Policy as Policy Engine
    participant Approval as Approval Service
    participant Ntfy as ntfy
    participant Tool as Sensitive Tool
    participant Trace as Trace

    User->>Web: send message or task request
    Web->>Runtime: inbound_message
    Runtime->>Policy: check requested capability
    Policy-->>Runtime: approval_required
    Runtime->>Approval: create approval request
    Approval->>Trace: approval_requested
    Approval->>Ntfy: notify user
    Ntfy-->>User: push notification
    User->>Web: approve or deny
    Web->>Approval: approval decision
    Approval->>Trace: approval_decided

    alt approved
        Runtime->>Tool: execute
        Tool-->>Runtime: result
    else denied
        Runtime-->>Web: blocked by policy
    end
```

The local web channel is the simplest control plane: chat, approval cards, task status, and logs. ntfy is the low-friction mobile notification layer. Mobile reply can start as "tap notification, open web page" before implementing a richer mobile chat channel.

## Runtime Loop

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Channel as Channel
    participant Runtime as Runtime
    participant Intent as Intent Router
    participant Workflow as Workflow Kernel
    participant Master as Master Agent
    participant Skill as Skill Loader
    participant Task as Task Pool
    participant Sub as Subagent
    participant Tool as Tool/Connector
    participant Approval as Approval
    participant Trace as Trace

    User->>Channel: request
    Channel->>Runtime: inbound_message
    Runtime->>Trace: user_message_received
    Runtime->>Intent: classify request

    alt workflow design or scheduled work
        Intent->>Workflow: create or update design session
        Workflow-->>Channel: proposal, question, or approval request
    else immediate or one-off work
    Runtime->>Skill: select applicable procedures
    Runtime->>Master: prompt + skills + context
    Master-->>Runtime: answer, plan, or delegation
    end

    alt delegated work
        Runtime->>Task: create background task
        Task->>Sub: execute task
        Sub->>Tool: request capability
        Tool->>Approval: policy gate if required
        Approval-->>Tool: approved or denied
        Tool-->>Sub: result or blocker
        Sub-->>Task: report
        Task-->>Master: result
        Master-->>Channel: final response
    else direct answer
        Master-->>Channel: final response
    end

    Runtime->>Trace: final event sequence
```

## Primitive Boundaries

| Module | Owns | Does not own |
| --- | --- | --- |
| Channel | user messages, notifications, approval UI | model reasoning, tool logic |
| Intent Router | classify user requests into work classes | executing workflows |
| Workflow Kernel | design sessions, workflow specs, lifecycle, builder, run orchestration | connector implementation details |
| Approval | approval lifecycle and decision records | deciding task strategy |
| Policy | capability rules and safety gates | executing tools |
| Scheduler | time-based event creation | long-running execution internals |
| Task Pool | lifecycle, heartbeats, cancellation, recovery | skill content |
| Agent | planning, delegation, reporting | direct external side effects |
| Skill | procedural guidance and routing metadata | executable side effects |
| Tool | one typed executable action | workflow strategy |
| Connector | external system boundary and capability exposure | business workflow logic |
| MCP Connector | standard MCP server/client adapter | local provider abstraction |
| Memory | durable user context and internal records | raw external source of truth |
| Resource Store | external artifacts and references | user preference policy |
| Trace | event history and replay | operational decisions |

## Workflow Kernel

The Workflow Kernel is the framework layer that prevents the project from becoming a set of bespoke apps.

```mermaid
flowchart TD
    Request["Natural language request"]
    Router["Intent Router"]
    Session["Workflow Design Session"]
    Proposal["Workflow Proposal"]
    Spec["Workflow Spec<br/>versioned, durable"]
    Builder["Workflow Builder"]
    Run["Workflow Run"]
    Scheduler["Scheduler / Hook"]
    Capabilities["Tools / Connectors / MCP / Scripts"]
    Stores["Memory / Resources / Artifacts"]
    Report["Report / Notification"]

    Request --> Router
    Router --> Session
    Session --> Proposal
    Proposal --> Spec
    Spec --> Builder
    Builder --> Scheduler
    Scheduler --> Run
    Run --> Capabilities
    Capabilities --> Stores
    Stores --> Report
```

Rules:

- Workflow specs are data-first and persisted.
- Workflow steps own control flow; agents provide intelligence inside steps.
- Generated scripts are artifacts and require admission before execution.
- Use cases such as newsletters, social trends, browser watchers, coding, and idea synthesis are probes for the same workflow kernel.

## Tool, Connector, MCP, Skill

```mermaid
flowchart LR
    Agent["Agent"]
    Skill["Skill<br/>how to do it"]
    Tool["Tool<br/>do one action"]
    Connector["Connector<br/>adapt one system"]
    MCP["MCP Connector<br/>standard external server boundary"]
    External["External system<br/>Gmail, Obsidian, Browser, Search"]
    Trace["Trace"]
    Policy["Policy/Approval"]

    Agent --> Skill
    Skill --> Agent
    Agent --> Tool
    Tool --> Policy
    Policy --> Connector
    Connector --> MCP
    Connector --> External
    Tool --> Trace
    Connector --> Trace
```

Rules of thumb:

- Use a skill when the reusable part is "how to perform a class of work."
- Use a tool when the reusable part is "perform one typed action."
- Use a connector when the reusable part is "talk to this outside system."
- Use MCP when that connector benefits from a separate server/process, capability discovery, or reuse by other clients.
- Use a hook when work begins because an event happened.
- Use a scheduler when work begins because time passed.
- Use a background task when work must continue after the current chat turn.

## Use Case Mapping

```mermaid
flowchart TD
    WSJ["WSJ Newsletter Analysis"]
    Self["Harness Self-Improvement"]
    Ideas["AI Memory / Idea Synthesis"]
    Tickets["Interpark Ticket Watcher"]

    Channel["Channel + Approval"]
    Scheduler["Scheduler + Hooks"]
    TaskPool["Background Task Pool"]
    Approval["Approval"]
    Skills["Skills"]
    Connectors["Connectors / MCP"]
    Memory["Memory / Resources"]
    Browser["Browser Automation"]
    Coding["Coding Workflow"]

    WSJ --> Scheduler
    WSJ --> Skills
    WSJ --> Connectors
    WSJ --> Memory

    Self --> Coding
    Self --> Skills
    Self --> TaskPool
    Self --> Channel

    Ideas --> Channel
    Ideas --> Memory
    Ideas --> Scheduler
    Ideas --> Skills

    Tickets --> Browser
    Tickets --> TaskPool
    Tickets --> Channel
    Tickets --> Approval
```

## Local Model Runtime

The model runtime remains intentionally narrow:

```mermaid
flowchart LR
    Runtime["Python Harness"]
    Provider["LocalGGUFProvider"]
    Completion["llama-completion<br/>Gemma master"]
    Diffusion["llama-diffusion-cli<br/>DiffusionGemma subagent"]
    GPU["RTX 4090"]
    Config["config/config.toml"]
    Prompts["prompts/"]

    Runtime --> Provider
    Runtime --> Config
    Runtime --> Prompts
    Provider --> Completion
    Provider --> Diffusion
    Completion --> GPU
    Diffusion --> GPU
```

Do not add multi-provider routing until the local harness proves useful.
