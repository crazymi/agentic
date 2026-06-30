---
name: credential-handling
description: Handle credentials by reference and require approval for sensitive authenticated actions.
requires:
  connectors: []
  tools: []
  resources: []
triggers:
  keywords: ["credential", "secret", "password", "token", "계정", "비밀번호"]
  task_kinds: ["credential_workflow"]
enabled: true
---

Never store raw credentials in prompts, traces, docs, or skill files. Ask for credential references such as environment variable names or local key IDs. Any action that submits credentials, sends messages, purchases, books, or changes account state requires approval.
