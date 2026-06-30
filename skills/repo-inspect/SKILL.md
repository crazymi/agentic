---
name: repo-inspect
description: Inspect a repository before proposing or making code changes.
requires:
  connectors: []
  tools: []
  resources: []
triggers:
  keywords: ["repo", "repository", "codebase", "리포", "코드베이스"]
  task_kinds: ["repo_inspect"]
enabled: true
---

Inspect the current repository structure, git state, relevant docs, tests, and nearby implementation before changing code. Summarize concrete files and risks, then keep edits scoped to the requested behavior.
