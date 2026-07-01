# Milestone 9 Status

Status: implemented.

Completed:

- workflow probe model and kind enum
- `WorkflowProbeFactory` for newsletter, social trend, idea synthesis, browser watcher, and coding probes
- probe specs represented as `WorkflowSpec` objects
- checked-in local source definitions or current repository source definitions for every probe
- browser watcher generated script represented as a review-required artifact, not an executable step
- `WorkflowProbeRunner` that installs real local sources, writes raw resources, stores review artifacts, approves/activates workflow specs, and runs them through the Workflow Kernel
- evals proving every probe produces source resources and report artifacts without bespoke daemon paths

Verification:

```bash
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
```

Notes:

- M9 validates framework expressiveness. It does not implement production Reddit/DCInside/Gmail/browser/coding automation.
- All probes use M7/M8 primitives: `WorkflowSpec`, source runtime, artifact store, workflow builder/interpreter.
- Browser watcher scripts remain review-required artifacts and are not executed.

Next:

- M10 should harden the system for continuous local operation: service lifecycle, dashboard, health checks, GPU/RAM guardrails, backup/export, and alerts.
