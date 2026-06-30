# Milestone 7 Plan: Newsletter And Research Workflows

Milestone 7 starts real user-facing workflows. The first target is newsletter analysis from mail-like resources.

Current implementation starts with:

- Gmail fixture connector
- newsletter ingestion into `ResourceStore`
- goal-directed deterministic analyzer
- source/citation retention
- insight memory writeback
- prepared skill/MCP catalog for live Gmail, web research, Obsidian linking, and browser watcher workflows

Real Gmail OAuth/API integration is intentionally separate because it requires credentials and approval policy.

Reference preparation:

- `docs/mcp_skill_catalog.md`
- `config/mcp_catalog.toml`
- `skills/gmail-newsletter-analysis/SKILL.md`
- `skills/web-research/SKILL.md`
- `skills/obsidian-knowledge-linking/SKILL.md`
- `skills/browser-watcher/SKILL.md`

## Acceptance

- WSJ-like newsletter messages can be discovered from a connector
- messages are stored as email resources with source metadata
- analysis can run against a named goal
- output separates findings and evidence
- findings cite source `gmail://message/<id>` URIs
- insight report is stored in memory

## Deferred

- live Gmail OAuth
- WSJ account/web extraction
- send/archive email actions
- model-assisted report writing
- scheduler-based daily runs
