from __future__ import annotations

import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from agentic.artifacts import ArtifactStore
from agentic.config.settings import AppConfig
from agentic.models.local_gguf import LocalGGUFProvider
from agentic.ops.health import HealthMonitor
from agentic.resources.store import ResourceStore
from agentic.sources import SourceRuntime, SourceStore
from agentic.workflow_kernel import WorkflowBuilder, WorkflowDesigner, WorkflowInterpreter, WorkflowStatus, WorkflowStore
from agentic.workflow_kernel.source_binding import bind_checked_in_local_source


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    ok: bool
    detail: str

    def to_record(self) -> dict[str, object]:
        return {"name": self.name, "ok": self.ok, "detail": self.detail}


@dataclass(frozen=True)
class SmokeResult:
    ok: bool
    checks: list[SmokeCheck]
    state_dir: str

    def to_record(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "state_dir": self.state_dir,
            "checks": [check.to_record() for check in self.checks],
        }


def run_operational_smoke(
    config: AppConfig,
    *,
    state_dir: str | Path | None = None,
    include_model: bool = False,
    model_id: str | None = None,
    model_max_tokens: int | None = None,
    model_prompt: str = "한국의 수도는 어디야? 답변만 한 문장으로 말해.",
) -> SmokeResult:
    tempdir: tempfile.TemporaryDirectory[str] | None = None
    if state_dir is None:
        tempdir = tempfile.TemporaryDirectory()
        root = Path(tempdir.name)
    else:
        root = Path(state_dir)
        root.mkdir(parents=True, exist_ok=True)
    try:
        checks = _run_checks(
            config,
            root=root,
            include_model=include_model,
            model_id=model_id,
            model_max_tokens=model_max_tokens,
            model_prompt=model_prompt,
        )
        return SmokeResult(ok=all(check.ok for check in checks), checks=checks, state_dir=str(root))
    finally:
        if tempdir is not None:
            tempdir.cleanup()


def _run_checks(
    config: AppConfig,
    *,
    root: Path,
    include_model: bool,
    model_id: str | None,
    model_max_tokens: int | None,
    model_prompt: str,
) -> list[SmokeCheck]:
    checks: list[SmokeCheck] = []
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

    proposal = WorkflowDesigner().design(
        "30분마다 주식 커뮤니티 글을 모아서 AI 자동화/반도체/리스크 트렌드 보고서를 만들어줘"
    )
    if proposal.spec is None:
        checks.append(SmokeCheck("workflow_design", False, "designer did not return a spec"))
        return checks
    spec = bind_checked_in_local_source(proposal.spec, source_store=source_store)
    stored = workflow_store.create_spec(spec)
    checks.append(
        SmokeCheck(
            "workflow_source_bound",
            bool(stored.sources and stored.steps[0].config.get("source_id")),
            str(stored.sources[0] if stored.sources else {}),
        )
    )
    workflow_store.transition_spec(stored.workflow_id, WorkflowStatus.APPROVED)
    active = workflow_store.transition_spec(stored.workflow_id, WorkflowStatus.ACTIVE)
    execution = builder.run_approved(active, trigger={"type": "ops_smoke"})
    collected_count = execution.run.step_results.get("collect", {}).get("collected_count")
    checks.append(
        SmokeCheck(
            "workflow_run_completed",
            execution.ok and execution.run.status.value == "completed",
            f"status={execution.run.status.value} collected={collected_count}",
        )
    )
    reports = artifact_store.list(run_id=execution.run.run_id)
    checks.append(
        SmokeCheck(
            "report_artifact_created",
            len(reports) >= 1,
            ",".join(artifact.artifact_id for artifact in reports),
        )
    )
    health = HealthMonitor(
        workflow_store=workflow_store,
        source_store=source_store,
        artifact_store=artifact_store,
    ).snapshot()
    checks.append(SmokeCheck("health_snapshot", health.status in {"ok", "degraded"}, health.status))

    if include_model:
        checks.append(_model_smoke(config, model_id=model_id, max_tokens=model_max_tokens, prompt=model_prompt))
    return checks


def _model_smoke(
    config: AppConfig,
    *,
    model_id: str | None,
    max_tokens: int | None,
    prompt: str,
) -> SmokeCheck:
    selected = model_id or config.runtime.default_master_model
    try:
        model = config.model(selected)
        if max_tokens is not None and max_tokens > 0:
            model = replace(model, max_tokens=max_tokens)
        response = LocalGGUFProvider(model).generate(prompt)
    except Exception as exc:
        return SmokeCheck("model_smoke", False, f"{type(exc).__name__}: {exc}")
    text = response.text.strip()
    return SmokeCheck(
        "model_smoke",
        bool(text),
        f"model={selected} text={text[:200]}",
    )
