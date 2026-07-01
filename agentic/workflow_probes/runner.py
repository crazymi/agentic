from __future__ import annotations

from dataclasses import dataclass

from agentic.artifacts import ArtifactAdmissionService, ArtifactStore
from agentic.resources.store import ResourceStore
from agentic.sources import SourceRuntime, SourceStore
from agentic.workflow_kernel import WorkflowBuilder, WorkflowStatus, WorkflowStore
from agentic.workflow_probes.models import WorkflowProbe


@dataclass(frozen=True)
class WorkflowProbeRunResult:
    probe_kind: str
    workflow_id: str
    run_id: str
    ok: bool
    resource_ids: list[str]
    report_artifact_ids: list[str]
    review_artifact_ids: list[str]


class WorkflowProbeRunner:
    def __init__(
        self,
        *,
        workflow_store: WorkflowStore,
        source_store: SourceStore,
        resource_store: ResourceStore,
        artifact_store: ArtifactStore,
        workflow_builder: WorkflowBuilder,
    ):
        self.workflow_store = workflow_store
        self.source_store = source_store
        self.resource_store = resource_store
        self.artifact_store = artifact_store
        self.workflow_builder = workflow_builder
        self.source_runtime = SourceRuntime(source_store=source_store, resource_store=resource_store)
        self.artifact_admission = ArtifactAdmissionService(artifact_store)

    def install_and_run(self, probe: WorkflowProbe) -> WorkflowProbeRunResult:
        review_artifact_ids: list[str] = []
        for source in probe.sources:
            self.source_store.add_source(source)
        for artifact in probe.artifacts:
            stored = self.artifact_admission.submit_for_review(artifact)
            review_artifact_ids.append(stored.artifact_id)

        self.workflow_store.create_spec(probe.spec)
        approved = self.workflow_store.transition_spec(probe.spec.workflow_id, WorkflowStatus.APPROVED)
        active = self.workflow_store.transition_spec(approved.workflow_id, WorkflowStatus.ACTIVE)
        execution = self.workflow_builder.run_approved(
            active,
            trigger={"type": "probe", "probe": probe.kind.value},
        )
        report_artifact_ids = [
            artifact.artifact_id
            for artifact in self.artifact_store.list(run_id=execution.run.run_id)
            if artifact.kind.value == "report"
        ]
        resource_ids = _run_resource_ids(execution.run.step_results)
        return WorkflowProbeRunResult(
            probe_kind=probe.kind.value,
            workflow_id=active.workflow_id,
            run_id=execution.run.run_id,
            ok=execution.ok,
            resource_ids=resource_ids,
            report_artifact_ids=report_artifact_ids,
            review_artifact_ids=review_artifact_ids,
        )


def _run_resource_ids(step_results: dict[str, object]) -> list[str]:
    collect = step_results.get("collect")
    if not isinstance(collect, dict):
        return []
    resource_ids = collect.get("resource_ids")
    if not isinstance(resource_ids, list):
        return []
    return [str(resource_id) for resource_id in resource_ids]
