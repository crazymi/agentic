from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic.artifacts import ArtifactKind, ArtifactStatus, ArtifactStore
from agentic.resources.store import ResourceStore
from agentic.sources import SourceKind, SourceRuntime, SourceStore
from agentic.workflow_kernel import StepType, WorkflowBuilder, WorkflowInterpreter, WorkflowStore
from agentic.workflow_probes import WorkflowProbeFactory, WorkflowProbeKind, WorkflowProbeRunner


class Milestone9WorkflowProbePackTests(unittest.TestCase):
    def test_probe_factory_builds_all_expected_probe_specs(self) -> None:
        probes = WorkflowProbeFactory().build_all()
        kinds = {probe.kind for probe in probes}

        self.assertEqual(
            kinds,
            {
                WorkflowProbeKind.NEWSLETTER,
                WorkflowProbeKind.SOCIAL_TREND,
                WorkflowProbeKind.IDEA_SYNTHESIS,
                WorkflowProbeKind.BROWSER_WATCHER,
                WorkflowProbeKind.CODING,
            },
        )
        for probe in probes:
            self.assertGreaterEqual(len(probe.spec.steps), 3)
            self.assertTrue(probe.spec.sources)
            self.assertTrue(probe.spec.evals)
            self.assertNotIn("fake", probe.sources[0].kind.value)

    def test_probes_do_not_introduce_bespoke_runtime_steps(self) -> None:
        allowed = {
            StepType.COLLECT,
            StepType.ANALYZE,
            StepType.AGGREGATE,
            StepType.REPORT,
        }

        for probe in WorkflowProbeFactory().build_all():
            step_types = {step.step_type for step in probe.spec.steps}
            self.assertTrue(step_types <= allowed, probe.kind)

    def test_all_probes_execute_with_real_local_sources_and_report_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner, artifact_store, resource_store = _runner(Path(tmpdir))
            results = [runner.install_and_run(probe) for probe in WorkflowProbeFactory().build_all()]

            resources = resource_store.search("AI", limit=20)
            report_artifacts = [
                artifact
                for artifact in artifact_store.list(limit=20)
                if artifact.kind == ArtifactKind.REPORT
            ]

        self.assertEqual(len(results), 5)
        self.assertTrue(all(result.ok for result in results))
        self.assertTrue(all(result.resource_ids for result in results))
        self.assertTrue(all(result.report_artifact_ids for result in results))
        self.assertGreaterEqual(len(resources), 1)
        self.assertEqual(len(report_artifacts), 5)

    def test_browser_watcher_probe_stores_script_for_review_without_execution(self) -> None:
        probe = WorkflowProbeFactory().browser_watcher()

        self.assertEqual(len(probe.artifacts), 1)
        self.assertEqual(probe.artifacts[0].kind, ArtifactKind.SCRIPT)
        self.assertEqual(probe.artifacts[0].status, ArtifactStatus.REVIEW_REQUIRED)
        self.assertNotIn(StepType.RUN_SCRIPT, {step.step_type for step in probe.spec.steps})

        with tempfile.TemporaryDirectory() as tmpdir:
            runner, artifact_store, _ = _runner(Path(tmpdir))
            result = runner.install_and_run(probe)
            review_artifacts = [artifact_store.get(artifact_id) for artifact_id in result.review_artifact_ids]

        self.assertTrue(result.ok)
        self.assertEqual(review_artifacts[0].status, ArtifactStatus.REVIEW_REQUIRED)

    def test_full_local_source_end_to_end_from_request_shape_to_approved_probe_run(self) -> None:
        probe = WorkflowProbeFactory().social_trend()

        with tempfile.TemporaryDirectory() as tmpdir:
            runner, artifact_store, _ = _runner(Path(tmpdir))
            result = runner.install_and_run(probe)
            report = artifact_store.get(result.report_artifact_ids[0])

        self.assertTrue(result.ok)
        self.assertEqual(result.probe_kind, "social_trend")
        self.assertIn("Social Trend Intelligence Probe", report.content)


def _runner(root: Path) -> tuple[WorkflowProbeRunner, ArtifactStore, ResourceStore]:
    workflow_store = WorkflowStore(root / "workflows.sqlite3")
    artifact_store = ArtifactStore(root / "artifacts.sqlite3")
    source_store = SourceStore(root / "sources.sqlite3")
    resource_store = ResourceStore(root / "resources.sqlite3")
    source_runtime = SourceRuntime(source_store=source_store, resource_store=resource_store)
    builder = WorkflowBuilder(
        WorkflowInterpreter(
            workflow_store=workflow_store,
            artifact_store=artifact_store,
            source_runtime=source_runtime,
            resource_store=resource_store,
        )
    )
    return (
        WorkflowProbeRunner(
            workflow_store=workflow_store,
            source_store=source_store,
            resource_store=resource_store,
            artifact_store=artifact_store,
            workflow_builder=builder,
        ),
        artifact_store,
        resource_store,
    )


if __name__ == "__main__":
    unittest.main()
