# Milestone 4 Status

Status: implemented.

Completed:

- `Connector` capability model
- `ConnectorRegistry`
- `ConnectorToolBridge`
- MCP stdio client adapter
- resource reference model
- connector policy integration
- evals for local connector fixture, approval path, and local MCP stdio fixture server
- curated MCP candidate catalog in `config/mcp_catalog.toml`
- MCP/skill mapping and activation notes in `docs/mcp_skill_catalog.md`

Notes:

- M4 exposes connector and MCP boundaries; live external connectors remain disabled until explicitly configured and approved.
- Production Gmail, browser, and Obsidian integrations remain deferred to M7+.
- Curated candidates are disabled by default and require review before enabling.
