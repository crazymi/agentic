# User Requirements

This document captures the current product understanding from the grill session. It should prevent the project from drifting back into vague agent-framework design.

## Product Definition

Build a personal 24/7 local agent harness for one user on one RTX 4090 machine.

The harness should be useful before it is general. It should be extensible, but it should not become a generic provider gateway, plugin marketplace, or public automation platform.

## Confirmed Constraints

- Primary models are local GGUF models.
- Runtime backend is local only.
- `LocalGGUFProvider` remains the only model provider for now.
- Development stack is Python with `uv`.
- The harness should prefer small working modules over abstract framework completeness.
- External integrations are allowed, but they should enter through explicit connectors, MCP adapters, tools, channels, skills, or hooks.
- The first extension priority is Channel plus Approval.
- Mobile interaction should start simple: local web page for chat/approval, ntfy for notifications.

## Core Use Cases

### 1. WSJ Newsletter Analysis

The user subscribes to WSJ and receives daily newsletters through Gmail.

Desired behavior:

- ingest WSJ newsletter emails
- analyze them against user-defined goals
- example goals:
  - identify potential startup ideas
  - evaluate relevance to held stocks or portfolio themes
  - extract market/product/technology signals
- preserve source references
- produce concise analysis and follow-up tasks

Required primitives:

- Scheduler or hook for incoming/daily email checks
- Gmail connector or MCP-backed mail connector
- Resource store for source emails
- Skill for newsletter analysis procedure
- Memory for standing goals and user preferences
- Approval policy for authenticated mail actions

### 2. Harness Self-Improvement

The harness should help improve its own codebase over time.

Desired behavior:

- inspect repository state
- propose scoped improvements
- patch code
- run tests
- review its own output
- maintain roadmap/backlog continuity

Required primitives:

- Coding workflow
- File, shell, git, and test tools
- Approval policy for risky shell/git/file operations
- Skills for coding loop and code review procedures
- Trace/replay for debugging failures
- Background tasks for longer implementation runs

### 3. AI Memory And Idea Synthesis

The user wants to send spontaneous ideas from desktop or mobile. The harness should organize them and periodically synthesize insight.

Desired behavior:

- accept quick chat/mobile idea capture
- clean up and tag ideas
- ask follow-up context questions
- link related ideas
- connect to Obsidian
- periodically scan all ideas for patterns, hidden connections, and new inspiration
- apply different analysis tasks to the same idea corpus

Required primitives:

- Channel for inbound ideas and follow-up questions
- Memory store for normalized idea records
- Resource connector for Obsidian
- Scheduler for periodic scans
- Skill for idea triage/synthesis procedure
- Standing orders for user preferences and synthesis style

### 4. Browser Automation And Ticket Watchers

The user wants to give the harness a URL and credential reference, then have it build and run a watcher macro, such as Interpark ticket availability alerts.

Desired behavior:

- inspect a target web page with Chromium/Playwright
- understand page structure through trial and error
- generate a Python automation script
- run the script as a background task
- detect target conditions such as empty seats becoming available
- notify the user
- eventually support booking, but only with explicit approval

Required primitives:

- Browser connector/tool wrapper
- Credential reference model
- Background task pool
- Scheduler/watchdog
- Channel and ntfy notification
- Approval for booking, payment, credential use, or externally visible actions
- Trace with screenshots, logs, and browser events

## Repeated Patterns

The use cases repeat the same framework needs:

- The user must be reachable outside the CLI.
- The harness must ask before doing consequential work.
- Work must survive longer than one chat turn.
- External systems need clean boundaries.
- Procedures should be reusable without becoming executable code.
- Sources, decisions, and actions must be traceable.
- The system needs memory and standing preferences.
- Automation needs hooks, schedules, cancellation, and health checks.

These repeated patterns become the roadmap primitives:

- Channel
- Approval
- Policy
- Scheduler
- Background Task
- Tool
- Connector
- MCP Connector
- Skill
- Hook
- Memory
- Resource Store
- Trace/Replay

## Mobile Communication Decision

The first implementation should be simple:

- local web server for chat, pending approvals, task status, and logs
- ntfy for push notifications
- notification opens or references the local web approval page

Do not start with a full mobile app. Do not start with a complex chat platform integration unless local web plus ntfy fails.

## Open Questions

These should be decided before implementation reaches each related milestone:

- How should the local web server be exposed to mobile: same LAN only, Tailscale, Cloudflare Tunnel, or another path?
- What credential storage mechanism should be used for browser/Gmail workflows?
- Should task state begin with SQLite or append-only JSONL plus snapshots?
- Which MCP servers should be adopted first instead of writing local connectors?
- What is the minimum acceptable UI for approvals and task supervision?
