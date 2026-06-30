---
name: mcp-safety-review
description: Review an MCP server candidate before enabling it in the harness.
requires:
  connectors: []
  tools: []
  resources: []
triggers:
  keywords: ["MCP", "connector", "server", "marketplace", "커넥터"]
  task_kinds: ["mcp_review"]
enabled: true
---

Review source reputation, install path, declared tools/resources/prompts, credential needs, network/file/write capabilities, maintenance status, and sandboxing before enabling an MCP server. Recommend an allowlist and approval rules.
