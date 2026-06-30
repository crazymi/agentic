---
name: web-research
description: Research web sources and separate sourced facts from analysis.
requires:
  connectors: []
  tools: []
  resources: []
triggers:
  keywords: ["research", "web search", "검색", "조사"]
  task_kinds: ["web_research"]
enabled: true
---

Gather primary or high-trust sources first. Record source URLs, dates when relevant, and separate facts from inference. Do not treat search snippets as final evidence when the underlying page can be read.
