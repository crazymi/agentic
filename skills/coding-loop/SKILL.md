---
name: coding-loop
description: Implement a scoped code change with inspect, patch, test, and handoff steps.
requires:
  connectors: []
  tools: []
  resources: []
triggers:
  keywords: ["implement", "fix", "patch", "구현", "수정"]
  task_kinds: ["coding_task"]
enabled: true
---

Use a tight coding loop: inspect the smallest relevant surface, make focused patches, run targeted tests, run broader tests when shared behavior changed, and report changed files plus verification. Preserve unrelated user changes.
