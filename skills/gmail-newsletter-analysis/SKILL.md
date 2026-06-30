---
name: gmail-newsletter-analysis
description: Analyze Gmail newsletter content for user goals such as startup ideas and portfolio relevance.
requires:
  connectors: []
  tools: []
  resources: []
triggers:
  keywords: ["gmail", "WSJ", "newsletter", "뉴스레터", "메일"]
  task_kinds: ["gmail_newsletter_analysis"]
enabled: true
---

Convert each newsletter item into evidence, implication, and action. Extract startup opportunity signals, portfolio relevance, macro risks, named companies, uncertain claims, and follow-up research questions. Never send or modify email without explicit approval.
