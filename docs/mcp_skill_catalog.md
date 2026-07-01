# MCP And Skill Preparation Catalog

This document records the curated MCP and skill surface prepared for the local personal harness.

The goal is not to import a marketplace. The goal is to define which external capabilities are useful for the user's actual workflows, how they map into the harness, and what must be gated by policy and approval before live use.

## Sources Reviewed

- Model Context Protocol architecture: https://modelcontextprotocol.io/docs/learn/architecture
- Official/community MCP server collection: https://github.com/modelcontextprotocol/servers
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Microsoft Playwright MCP: https://github.com/microsoft/playwright-mcp
- OpenClaw skills documentation: https://docs.openclaw.ai/tools/skills
- OpenClaw plugin documentation: https://docs.openclaw.ai/tools/plugin
- OpenClaw automation documentation: https://docs.openclaw.ai/automation

Hermes-style designs were treated as directional references only where publicly discoverable. The implementation should not depend on weakly sourced package behavior.

## Design Interpretation

MCP should be used for external capabilities and context boundaries:

- files and local vaults
- Git/GitHub
- browser automation
- web fetch/search
- Gmail or other inbox access
- document stores
- database/resource inspection

Skills should be used for repeatable task procedures:

- how to analyze a WSJ newsletter
- how to capture and connect an idea
- how to inspect a repo before editing it
- how to design a browser watcher
- how to run a coding loop safely
- how to handle credentials

The distinction matters. MCP exposes tools/resources/prompts. Skills tell the agent how to use available capabilities for a known workflow. Skills must not execute code directly or bypass policy.

## Prepared MCP Tiers

Tier 1 candidates are the first live connectors to evaluate after M7:

- `filesystem`: local project and Obsidian-vault context. Scope to explicit roots. Writes require approval.
- `git`: repository inspection and local development context. Mutating operations require approval.
- `fetch`: documentation/article retrieval. Authenticated fetch or form submission requires approval.
- `playwright`: browser observation and macro construction. Submit/purchase/login flows require approval.
- `obsidian`: prefer filesystem-scoped vault integration first. Community MCPs need code review before use.
- `gmail`: start with read-only newsletter ingestion. Sending or modifying mailbox state requires approval.

Tier 2 candidates:

- `github`: useful for issues and PRs, but credentials and remote mutation make it high risk.
- `memory`: potentially useful, but the repo already has local memory primitives.
- `sqlite`: useful for debugging local state and dashboards.
- `search`: useful for market/web research once one provider is selected.

Tier 3 / defer:

- generic marketplace skills
- write-capable browser/email tools from unknown authors
- payment, shopping, ticket purchase, account-management tools
- broad local shell MCPs without a tight allowlist

The concrete disabled-by-default catalog lives in `config/mcp_catalog.toml`.

## Prepared Local Skills

Existing skills:

- `idea-capture`
- `newsletter-analysis`
- `browser-macro-planning`

New prepared skills:

- `repo-inspect`: inspect codebase layout, tests, config, and current git state before edits.
- `coding-loop`: implement small changes through inspect, patch, test, and summarize.
- `web-research`: collect sources, separate facts from inference, and produce traceable notes.
- `gmail-newsletter-analysis`: convert an email newsletter into evidence-backed investment/startup/user-specific signals.
- `obsidian-knowledge-linking`: normalize notes, tags, links, and follow-up questions for a vault workflow.
- `browser-watcher`: design a monitored browser automation task with approval-safe boundaries.
- `mcp-safety-review`: review a proposed MCP server before enabling it.
- `credential-handling`: collect only credential references and define required approvals for sensitive actions.

All prepared skills are instruction-only `SKILL.md` packages under `skills/`. None of them install dependencies, fetch remote code, or directly execute tools.

## Safety Rules

- MCP servers are disabled until manually reviewed and allowlisted.
- Any externally visible or consequential action goes through deterministic policy.
- Browser submit, email send, payment, ticket booking, file write/delete, remote repo mutation, and credential use require approval.
- Automated tests must use local fixtures, checked-in sample sources, or dry-run adapters instead of live network, Gmail, ntfy, browser, or model calls.
- Secrets must be represented as references such as environment variable names or local credential IDs, never copied into traces or skill text.

## Mapping To User Requirements

WSJ/Gmail newsletter workflow:

- MCP candidate: `gmail` or custom Gmail connector
- Skills: `gmail-newsletter-analysis`, `newsletter-analysis`, `web-research`
- Approval points: label mutation, send email, bulk mark-read, paid API search

Self-improving harness:

- MCP candidates: `filesystem`, `git`, `github`, `fetch`, `sqlite`
- Skills: `repo-inspect`, `coding-loop`, `mcp-safety-review`
- Approval points: file writes, shell execution, commits, pushes, dependency install

AI memory and Obsidian workflow:

- MCP candidates: `filesystem`, `obsidian`, `memory`
- Skills: `idea-capture`, `obsidian-knowledge-linking`
- Approval points: note writes/deletes, bulk retagging, vault migration

Browser watcher and ticket monitoring:

- MCP candidate: `playwright`
- Skills: `browser-macro-planning`, `browser-watcher`, `credential-handling`
- Approval points: login, form submit, booking, payment, notification channel changes

## Activation Order

1. Add read-only filesystem/git/fetch connectors behind config allowlists.
2. Add Playwright observation mode without submit actions.
3. Add Gmail read-only ingestion using fixtures first, then live OAuth.
4. Add Obsidian-vault write proposals with approval, not automatic writes.
5. Add remote GitHub only after credential handling and approval UX are stable.
6. Review any community MCP server with `mcp-safety-review` before enabling.
