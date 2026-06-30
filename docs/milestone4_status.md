# Milestone 4 Status

Status: implemented.

Completed:

- `Connector` capability model
- `ConnectorRegistry`
- `FakeConnector`
- `ConnectorToolBridge`
- MCP stdio client adapter
- resource reference model
- connector policy integration
- evals for fake connector, approval path, and fake MCP server
- curated MCP candidate catalog in `config/mcp_catalog.toml`
- MCP/skill mapping and activation notes in `docs/mcp_skill_catalog.md`

Notes:

- M4 uses fake/local connectors only.
- Production Gmail, browser, and Obsidian integrations remain deferred to M7+.
- Curated candidates are disabled by default and require review before enabling.
