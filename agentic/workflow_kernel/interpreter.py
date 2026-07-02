from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic.artifacts import ArtifactKind, ArtifactRecord, ArtifactStore
from agentic.artifacts.report_quality import evaluate_report_quality
from agentic.resources.store import ResourceRecord, ResourceStore
from agentic.sources.runtime import SourceRuntime
from agentic.sources.strategy import source_strategy_tuning_request
from agentic.synthesis.report import ReportSynthesisResult, ReportSynthesizer
from agentic.traces.logger import TraceLogger
from agentic.workflow_kernel.capabilities import (
    CapabilityAdmission,
    CapabilityPlanner,
)
from agentic.workflow_kernel.models import (
    StepType,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowSpec,
)
from agentic.workflow_kernel.store import WorkflowStore


@dataclass(frozen=True)
class WorkflowExecutionResult:
    run: WorkflowRun
    ok: bool


class SourceQualityError(RuntimeError):
    def __init__(self, reports: list[dict[str, Any]]):
        self.reports = reports
        failed = [report for report in reports if not report.get("ok")]
        reasons = sorted({reason for report in failed for reason in report.get("reasons", [])})
        reason_text = ", ".join(reasons) if reasons else "unknown"
        super().__init__(f"source quality below threshold: {reason_text}")


class WorkflowInterpreter:
    def __init__(
        self,
        *,
        workflow_store: WorkflowStore,
        artifact_store: ArtifactStore,
        source_runtime: SourceRuntime | None = None,
        resource_store: ResourceStore | None = None,
        capability_planner: CapabilityPlanner | None = None,
        tooling_store: Any | None = None,
        source_recovery_enqueuer: Any | None = None,
        report_synthesizer: ReportSynthesizer | None = None,
        trace: TraceLogger | None = None,
    ):
        self.workflow_store = workflow_store
        self.artifact_store = artifact_store
        self.source_runtime = source_runtime
        self.resource_store = resource_store
        self.capability_planner = capability_planner or CapabilityPlanner()
        self.tooling_store = tooling_store
        self.source_recovery_enqueuer = source_recovery_enqueuer
        self.report_synthesizer = report_synthesizer
        self.trace = trace

    def run(self, spec: WorkflowSpec, *, trigger: dict[str, Any] | None = None) -> WorkflowExecutionResult:
        capability_plan = self.capability_planner.plan(spec)
        blocking_need = next(
            (
                need
                for need in capability_plan.needs
                if need.admission
                in {
                    CapabilityAdmission.DENIED,
                    CapabilityAdmission.MISSING,
                    CapabilityAdmission.NEEDS_ARTIFACT_REVIEW,
                }
            ),
            None,
        )
        run = self.workflow_store.create_run(
            spec,
            trigger=trigger or {"type": "manual"},
            context={"capability_plan": capability_plan.to_record()},
        )
        self._trace("workflow_started", {"workflow_id": spec.workflow_id, "run_id": run.run_id})
        if blocking_need is not None:
            updated = self.workflow_store.transition_run(
                run.run_id,
                WorkflowRunStatus.WAITING_FOR_APPROVAL
                if blocking_need.admission == CapabilityAdmission.NEEDS_ARTIFACT_REVIEW
                else WorkflowRunStatus.FAILED,
                error={
                    "type": "capability_blocked",
                    "need": blocking_need.to_record(),
                },
                event_type="workflow_capability_blocked",
            )
            return WorkflowExecutionResult(run=updated, ok=False)
        if capability_plan.requires_approval:
            updated = self.workflow_store.transition_run(
                run.run_id,
                WorkflowRunStatus.WAITING_FOR_APPROVAL,
                error={"type": "approval_required", "plan": capability_plan.to_record()},
                event_type="workflow_waiting_for_approval",
            )
            return WorkflowExecutionResult(run=updated, ok=False)

        run = self.workflow_store.transition_run(run.run_id, WorkflowRunStatus.RUNNING)
        context = dict(run.context)
        step_results = dict(run.step_results)
        artifacts = list(run.artifacts)
        try:
            for step in spec.steps:
                self._trace(
                    "workflow_step_started",
                    {"workflow_id": spec.workflow_id, "run_id": run.run_id, "step_id": step.step_id},
                )
                result = self._execute_step(spec, run, step.step_type, step.config, context, step_results)
                step_results[step.step_id] = result
                if "artifact_id" in result:
                    artifacts.append(str(result["artifact_id"]))
                context[step.step_id] = result
                self.workflow_store.append_event(
                    "workflow_step_completed",
                    {"step_id": step.step_id, "result": result},
                    workflow_id=spec.workflow_id,
                    run_id=run.run_id,
                )
                self._trace(
                    "workflow_step_completed",
                    {"workflow_id": spec.workflow_id, "run_id": run.run_id, "step_id": step.step_id},
                )
            run = self.workflow_store.transition_run(
                run.run_id,
                WorkflowRunStatus.COMPLETED,
                context=context,
                step_results=step_results,
                artifacts=artifacts,
                result={"status": "completed", "artifact_ids": artifacts},
                event_type="workflow_completed",
            )
            self._trace("workflow_completed", {"workflow_id": spec.workflow_id, "run_id": run.run_id})
            return WorkflowExecutionResult(run=run, ok=True)
        except Exception as exc:
            error = {"type": exc.__class__.__name__, "message": str(exc)}
            if hasattr(exc, "reports"):
                error["reports"] = getattr(exc, "reports")
            failed = self.workflow_store.transition_run(
                run.run_id,
                WorkflowRunStatus.FAILED,
                context=context,
                step_results=step_results,
                artifacts=artifacts,
                error=error,
                event_type="workflow_failed",
            )
            self._trace(
                "workflow_failed",
                {"workflow_id": spec.workflow_id, "run_id": run.run_id, "error": str(exc)},
            )
            return WorkflowExecutionResult(run=failed, ok=False)

    def _execute_step(
        self,
        spec: WorkflowSpec,
        run: WorkflowRun,
        step_type: StepType,
        config: dict[str, Any],
        context: dict[str, Any],
        step_results: dict[str, Any],
    ) -> dict[str, Any]:
        if step_type == StepType.COLLECT:
            if self.source_runtime is None or self.resource_store is None:
                raise RuntimeError("collect step requires SourceRuntime and ResourceStore")
            source_ids = _collect_source_ids(config)
            if not source_ids:
                raise RuntimeError("collect step requires source_id or source_ids")
            collections = [self.source_runtime.collect(source_id) for source_id in source_ids]
            quality_reports = [
                {
                    "source_id": collection.source_id,
                    **collection.quality.to_record(),
                }
                for collection in collections
            ]
            resource_ids = [
                resource_id
                for collection in collections
                for resource_id in collection.resource_ids
            ]
            recent_resource_ids = [
                resource_id
                for collection in collections
                for resource_id in collection.recent_resource_ids
            ]
            analysis_resource_ids = resource_ids or recent_resource_ids
            resources = [
                self.resource_store.get(resource_id)
                for resource_id in analysis_resource_ids
            ]
            if any(not report["ok"] for report in quality_reports):
                tooling_request = source_strategy_tuning_request(
                    workflow_id=spec.workflow_id,
                    run_id=run.run_id,
                    reports=quality_reports,
                )
                if self.tooling_store is not None:
                    tooling_request = self.tooling_store.add(tooling_request)
                recovery_task = None
                if self.source_recovery_enqueuer is not None:
                    recovery_task = self.source_recovery_enqueuer.enqueue(tooling_request)
                self.workflow_store.append_event(
                    "workflow_source_quality_failed",
                    {
                        "reports": quality_reports,
                        "tooling_request": tooling_request.to_record(),
                    },
                    workflow_id=spec.workflow_id,
                    run_id=run.run_id,
                )
                self.workflow_store.append_event(
                    "workflow_source_strategy_tuning_requested",
                    {"tooling_request": tooling_request.to_record()},
                    workflow_id=spec.workflow_id,
                    run_id=run.run_id,
                )
                if recovery_task is not None:
                    recovery_payload = {
                        "tooling_id": tooling_request.tooling_id,
                        "task_id": recovery_task.task_id,
                        "task_kind": recovery_task.kind,
                        "task_status": recovery_task.status.value,
                    }
                    self.workflow_store.append_event(
                        "workflow_source_strategy_recovery_enqueued",
                        recovery_payload,
                        workflow_id=spec.workflow_id,
                        run_id=run.run_id,
                    )
                    self._trace(
                        "workflow_source_strategy_recovery_enqueued",
                        {
                            "workflow_id": spec.workflow_id,
                            "run_id": run.run_id,
                            **recovery_payload,
                        },
                    )
                self._trace(
                    "workflow_source_quality_failed",
                    {
                        "workflow_id": spec.workflow_id,
                        "run_id": run.run_id,
                        "reports": quality_reports,
                        "tooling_id": tooling_request.tooling_id,
                    },
                )
                raise SourceQualityError(quality_reports)
            return {
                "items": [_resource_to_item(resource) for resource in resources],
                "source_ids": source_ids,
                "collected_count": sum(collection.collected_count for collection in collections),
                "new_count": sum(collection.new_count for collection in collections),
                "resource_ids": resource_ids,
                "recent_resource_ids": recent_resource_ids,
                "analysis_resource_ids": analysis_resource_ids,
                "quality": quality_reports,
            }
        if step_type == StepType.TRANSFORM:
            return {"transformed": True, "input_keys": sorted(step_results.keys())}
        if step_type == StepType.ANALYZE:
            collected = self._first_items(step_results)
            keywords = _keyword_counts(collected)
            top_keywords = [word for word, _count in keywords[:8]]
            return {
                "summary": f"Analyzed {len(collected)} item(s) for goal: {config.get('goal') or spec.goal}",
                "signals": _signal_lines(collected, limit=8),
                "top_keywords": top_keywords,
                "keyword_counts": dict(keywords[:12]),
            }
        if step_type == StepType.AGGREGATE:
            collected = self._first_items(step_results)
            words: dict[str, int] = {}
            for item in collected:
                for word in str(item.get("text") or item.get("title") or "").split():
                    words[word.lower()] = words.get(word.lower(), 0) + 1
            return {"keyword_counts": words}
        if step_type == StepType.REPORT:
            synthesis = self._synthesize_report(spec, step_results)
            report = self._render_report(spec, step_results, synthesis=synthesis)
            report_quality = evaluate_report_quality(report)
            metadata = {
                "output": config.get("output", "report"),
                "report_quality": report_quality.to_record(),
            }
            if synthesis is not None:
                metadata["report_synthesis"] = synthesis.to_record()
            artifact = self.artifact_store.create(
                ArtifactRecord(
                    kind=ArtifactKind.REPORT,
                    name=f"{spec.name} report",
                    content=report,
                    workflow_id=spec.workflow_id,
                    run_id=run.run_id,
                    metadata=metadata,
                )
            )
            return {
                "artifact_id": artifact.artifact_id,
                "content": report,
                "report_quality": report_quality.to_record(),
                "report_synthesis": synthesis.to_record() if synthesis is not None else None,
            }
        if step_type == StepType.NOTIFY:
            return {"notified": True, "channel": config.get("channel", "web")}
        if step_type == StepType.ASK_USER:
            answer = config.get("answer") or spec.inputs.get(str(config.get("slot") or ""))
            if not answer:
                raise RuntimeError("ask_user step requires an answer or interactive runtime support")
            return {
                "answered": True,
                "slot": config.get("slot"),
                "question": config.get("question"),
                "answer": str(answer),
            }
        if step_type == StepType.BROWSER_OBSERVE:
            raise RuntimeError("browser_observe step requires a real browser adapter")
        if step_type == StepType.BROWSER_ACTION:
            raise RuntimeError("browser_action step requires a real browser adapter")
        if step_type == StepType.APPROVAL:
            raise RuntimeError("approval step requires approval service integration")
        if step_type == StepType.RUN_SCRIPT:
            raise RuntimeError("run_script step requires artifact admission")
        return {"ok": True, "step_type": step_type.value}

    @staticmethod
    def _first_items(step_results: dict[str, Any]) -> list[dict[str, Any]]:
        for result in step_results.values():
            items = result.get("items") if isinstance(result, dict) else None
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return []

    def _synthesize_report(
        self,
        spec: WorkflowSpec,
        step_results: dict[str, Any],
    ) -> ReportSynthesisResult | None:
        if self.report_synthesizer is None:
            return None
        analyze = next(
            (
                result
                for result in step_results.values()
                if isinstance(result, dict) and "summary" in result
            ),
            {},
        )
        items = self._first_items(step_results)
        synthesis = self.report_synthesizer.synthesize(spec=spec, items=items, analyze=analyze)
        self._trace(
            "workflow_report_synthesized",
            {
                "workflow_id": spec.workflow_id,
                "ok": synthesis.ok,
                "mode": synthesis.mode,
                "model_id": synthesis.model_id,
                "insight_count": len(synthesis.insights),
                "error": synthesis.error,
            },
        )
        return synthesis

    @staticmethod
    def _render_report(
        spec: WorkflowSpec,
        step_results: dict[str, Any],
        *,
        synthesis: ReportSynthesisResult | None = None,
    ) -> str:
        analyze = next(
            (
                result
                for result in step_results.values()
                if isinstance(result, dict) and "summary" in result
            ),
            {},
        )
        items = WorkflowInterpreter._first_items(step_results)
        collect = next(
            (
                result
                for result in step_results.values()
                if isinstance(result, dict) and "quality" in result
            ),
            {},
        )
        signals = [str(item) for item in analyze.get("signals") or [] if str(item)]
        top_keywords = analyze.get("top_keywords") or []
        keyword_counts = analyze.get("keyword_counts") or {}
        if len(signals) < 3:
            signals.extend(_derived_signal_lines(top_keywords, keyword_counts, needed=3 - len(signals)))
        evidence = _evidence_lines(items, limit=8)
        source_quality = collect.get("quality") if isinstance(collect, dict) else []
        source_quality_lines = _source_quality_lines(source_quality)
        keyword_lines = [
            f"- {word}: {count}"
            for word, count in list(keyword_counts.items())[:10]
        ] or ["- No keyword counts available."]
        lines = [
            f"# {spec.name}",
            "",
            f"Goal: {spec.goal}",
            "",
            "## Executive Summary",
            "",
            f"- {str(analyze.get('summary') or 'No analysis summary.')}",
            f"- Top themes: {', '.join(str(item) for item in top_keywords[:6]) or 'not enough signal yet'}",
            f"- Evidence window: {len(items)} item(s)",
            "",
            "## Evidence",
            "",
        ]
        lines.extend(evidence or ["- No evidence items were available."])
        if synthesis is not None:
            lines.extend(["", "## Model-Assisted Insights", ""])
            if synthesis.ok and synthesis.insights:
                for insight in synthesis.insights:
                    evidence_refs = ", ".join(f"[{item}]" for item in insight.evidence_ids)
                    implication = f" Implication: {insight.implication}" if insight.implication else ""
                    lines.append(
                        f"- {insight.claim} Evidence: {evidence_refs}. Confidence: {insight.confidence}.{implication}"
                    )
            else:
                lines.append(f"- Model synthesis unavailable: {synthesis.error or 'unknown_error'}")
        lines.extend(["", "## Signals", ""])
        lines.extend(f"- {signal}" for signal in (signals[:8] or ["No signals detected."]))
        lines.extend(["", "## Keyword Counts", ""])
        lines.extend(keyword_lines)
        lines.extend(["", "## Source Quality", ""])
        lines.extend(source_quality_lines or ["- Source quality evidence was not recorded."])
        lines.extend(
            [
                "",
                "## Next Watch Points",
                "",
                "- Watch whether repeated titles, new tickers, or unusual sentiment terms persist across the next run.",
                "- Compare the next report against this evidence window before treating a theme as durable.",
                "- If collection quality drops, let the source strategy recovery task revise extraction before delivery.",
            ]
        )
        return "\n".join(lines)

    def _trace(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.trace is not None:
            self.trace.record(event_type, payload)


class WorkflowBuilder:
    def __init__(self, interpreter: WorkflowInterpreter):
        self.interpreter = interpreter

    def run_approved(self, spec: WorkflowSpec, *, trigger: dict[str, Any] | None = None) -> WorkflowExecutionResult:
        if spec.status.value not in {"approved", "active"}:
            raise ValueError("workflow must be approved or active before execution")
        return self.interpreter.run(spec, trigger=trigger)


def _resource_to_item(resource: ResourceRecord) -> dict[str, Any]:
    return {
        "id": resource.resource_id,
        "uri": resource.uri,
        "title": resource.title,
        "text": resource.content_text,
        "metadata": resource.metadata,
    }


def _collect_source_ids(config: dict[str, Any]) -> list[str]:
    raw_ids = config.get("source_ids")
    if isinstance(raw_ids, list):
        return [str(source_id) for source_id in raw_ids if str(source_id)]
    source_id = str(config.get("source_id") or "")
    return [source_id] if source_id else []


def _signal_lines(items: list[dict[str, Any]], *, limit: int) -> list[str]:
    signals: list[str] = []
    for item in items[:limit]:
        title = str(item.get("title") or "").strip()
        text = str(item.get("text") or "").strip()
        if not title and not text:
            continue
        signals.append(f"{title or text[:80]} :: {_compact_text(text or title, limit=120)}")
    return signals


def _evidence_lines(items: list[dict[str, Any]], *, limit: int) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(items[:limit], start=1):
        title = _compact_text(str(item.get("title") or "Untitled"), limit=90)
        uri = str(item.get("uri") or "")
        text = _compact_text(str(item.get("text") or title), limit=140)
        lines.append(f"- [{index}] {title} | {text} | {uri}")
    return lines


def _source_quality_lines(reports: Any) -> list[str]:
    if not isinstance(reports, list):
        return []
    lines: list[str] = []
    for report in reports:
        if not isinstance(report, dict):
            continue
        lines.append(
            "- source={source_id} ok={ok} score={score} items={items} reasons={reasons}".format(
                source_id=report.get("source_id", ""),
                ok=report.get("ok", ""),
                score=report.get("score", ""),
                items=report.get("item_count", ""),
                reasons=",".join(str(reason) for reason in report.get("reasons", [])),
            )
        )
    return lines


def _keyword_counts(items: list[dict[str, Any]]) -> list[tuple[str, int]]:
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "http",
        "https",
        "www",
        "com",
    }
    counts: dict[str, int] = {}
    for item in items:
        text = f"{item.get('title') or ''} {item.get('text') or ''}"
        for raw in text.replace("/", " ").replace("|", " ").split():
            word = raw.strip(".,:;!?()[]{}<>\"'`").lower()
            if len(word) < 2 or word in stopwords:
                continue
            counts[word] = counts.get(word, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _derived_signal_lines(top_keywords: Any, keyword_counts: Any, *, needed: int) -> list[str]:
    if needed <= 0:
        return []
    keywords = [str(word) for word in top_keywords if str(word)] if isinstance(top_keywords, list) else []
    if not keywords and isinstance(keyword_counts, dict):
        keywords = [str(word) for word in list(keyword_counts)[:5] if str(word)]
    derived: list[str] = []
    if keywords:
        derived.append(f"Recurring terms to watch: {', '.join(keywords[:5])}.")
    if isinstance(keyword_counts, dict) and keyword_counts:
        top_pairs = list(keyword_counts.items())[:5]
        derived.append(
            "Term concentration: "
            + ", ".join(f"{word}={count}" for word, count in top_pairs)
            + "."
        )
    derived.append("The next run should compare whether these terms persist or disappear.")
    return derived[:needed]


def _compact_text(text: str, *, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."
