---
name: "vague-workflow-builder"
description: "A procedure for building automation workflows from vague requests."
requires:
  connectors: []
  tools: []
  resources: []
triggers:
  keywords: ["automation", "builder", "skill", "vague", "workflow", "워크플로우", "자동화", "제안"]
  task_kinds: ["vague_workflow_builder"]
enabled: true
---

# Vague Workflow Builder
- **Trigger**: User requests an automation or workflow.
- **Interview**: Ask one question at a time to clarify data sources, frequency, and output formats.
- **Discovery**: Identify required tools (HTTP, API, Scrapers, Scripts).
- **Proposal**: Propose a structured workflow spec for review.
- **Approval**: Require user confirmation before executing risky or complex steps.
- **Recording**: Log execution results to refine future builds.
- **Evolution**: Review feedback to propose skill updates or new automation patterns.
