# Milestone 7 Plan: Workflow Kernel

Milestone 7 is now the framework milestone for workflow design, proposal, approval, activation, scheduling, and run orchestration.

The previous newsletter-first M7 plan is preserved as a vertical probe, not the architecture.

Canonical documents:

- `docs/framework_reference_review.md`
- `docs/workflow_kernel_design.md`
- `docs/milestone7_workflow_kernel_plan.md`

Newsletter, social trend intelligence, idea synthesis, browser watcher, and coding workflows should all be represented as `WorkflowSpec` probes. If a use case cannot fit the workflow kernel, improve the kernel instead of adding a bespoke runtime path.

## Acceptance Summary

- classify user requests into framework work classes
- create workflow design sessions from vague requests
- ask one missing-info question at a time
- render workflow proposals before activation
- persist versioned workflow specs and runs
- map specs to capabilities, policy, approvals, schedules, and artifacts
- execute fake collect/analyze/report workflow runs through the existing task runtime
- prove multiple vertical probes can be represented without bespoke architecture
