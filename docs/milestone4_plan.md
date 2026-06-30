# Milestone 4 Plan: Connector And MCP Boundary

Milestone 4 introduces a small connector boundary for external systems and an MCP stdio adapter.

Scope:

- local connector interface
- connector capability registry
- MCP stdio JSON-RPC client adapter
- connector tool calls through policy and approval
- fake connector and fake MCP server evals
- no real Gmail, browser, Obsidian, or remote plugin marketplace

Security note:

- MCP server admission is deny-by-default at the policy layer.
- M4 supports stdio client integration and capability discovery, but real third-party MCP servers must be allowlisted before M7 use.
- Connector tools must go through the same approval path as local tools.

Acceptance:

- fake connector exposes one tool, one resource, and one prompt
- connector capabilities can be listed and filtered
- connector tool calls pass through policy
- unknown external connector tools require approval
- fake MCP stdio server supports initialize, discovery, tool call, resource read, and prompt get
