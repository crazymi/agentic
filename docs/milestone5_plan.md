# Milestone 5 Plan: Skill System

Milestone 5 represents reusable procedures as local skill packages.

Scope:

- local `skills/<name>/SKILL.md` packages
- strict frontmatter parser
- skill loader and router
- requirement checking against connector/tool registries
- prompt context generation
- sample local skills for M7 planning
- no marketplace, no remote install, no executable skill code

Security note:

- Public OpenClaw/ClawHub-style skill marketplaces have had repeated malicious skill incidents.
- This harness therefore treats third-party skills as untrusted and keeps M5 local-only.
- Remote installation, executable install scripts, and marketplace sync are intentionally out of scope.

Acceptance:

- valid local skills load
- disabled skills are ignored
- invalid frontmatter fails clearly
- missing required connectors/tools produce blockers
- selected skills produce prompt context
- skills cannot bypass policy or execute tools directly
