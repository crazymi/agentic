from __future__ import annotations

from pathlib import Path

from agentic.artifacts import ArtifactKind, ArtifactRecord, ArtifactStatus
from agentic.sources import SourceDefinition, SourceKind, SourcePolicy
from agentic.workflow_kernel import IntentType, StepType, WorkflowSpec, WorkflowStatus, WorkflowStep
from agentic.workflow_probes.models import WorkflowProbe, WorkflowProbeKind


class WorkflowProbeFactory:
    def build_all(self) -> list[WorkflowProbe]:
        return [
            self.newsletter(),
            self.social_trend(),
            self.idea_synthesis(),
            self.browser_watcher(),
            self.coding(),
        ]

    def newsletter(self) -> WorkflowProbe:
        source = _source(
            kind=SourceKind.MAIL,
            name="WSJ newsletter local mail source",
            locator=_example_source("wsj_newsletter.jsonl"),
        )
        spec = _spec(
            name="Newsletter Analysis Probe",
            goal="Analyze newsletter items for startup ideas and portfolio relevance.",
            intent_type=IntentType.SCHEDULED_WORKFLOW,
            source=source,
            steps=[
                _collect(source),
                _analyze("Extract signals, risks, startup ideas, and portfolio relevance."),
                _report("newsletter_report"),
            ],
            cadence="cron:daily",
        )
        return WorkflowProbe(
            kind=WorkflowProbeKind.NEWSLETTER,
            request="매일 WSJ 뉴스레터를 읽고 스타트업/포트폴리오 시그널 보고서로 정리해줘.",
            spec=spec,
            sources=[source],
        )

    def social_trend(self) -> WorkflowProbe:
        source = _source(
            kind=SourceKind.FEED,
            name="Market community local feed source",
            locator=_example_source("market_community_posts.jsonl"),
        )
        spec = _spec(
            name="Social Trend Intelligence Probe",
            goal="Collect community market posts and summarize trend shifts.",
            intent_type=IntentType.SCHEDULED_WORKFLOW,
            source=source,
            steps=[
                _collect(source),
                WorkflowStep(
                    step_id="aggregate",
                    step_type=StepType.AGGREGATE,
                    name="Aggregate keyword counts",
                    depends_on=["collect"],
                ),
                _analyze("Interpret trend shifts and unusual signals.", depends_on=["aggregate"]),
                _report("social_trend_report"),
            ],
            cadence="interval:1800s",
        )
        return WorkflowProbe(
            kind=WorkflowProbeKind.SOCIAL_TREND,
            request="30분마다 주식 커뮤니티 글을 모아서 트렌드 보고서를 만들어줘.",
            spec=spec,
            sources=[source],
        )

    def idea_synthesis(self) -> WorkflowProbe:
        source = _source(
            kind=SourceKind.LOCAL_FILE,
            name="Idea inbox local source",
            locator=_example_source("idea_inbox.jsonl"),
        )
        spec = _spec(
            name="Idea Synthesis Probe",
            goal="Capture ideas, link related concepts, and produce synthesis prompts.",
            intent_type=IntentType.SCHEDULED_WORKFLOW,
            source=source,
            steps=[
                _collect(source),
                _analyze("Find related ideas, tags, contradictions, and follow-up questions."),
                _report("idea_synthesis_report"),
            ],
            cadence="cron:daily",
        )
        return WorkflowProbe(
            kind=WorkflowProbeKind.IDEA_SYNTHESIS,
            request="내 아이디어 메모들을 주기적으로 연결하고 인사이트를 뽑아줘.",
            spec=spec,
            sources=[source],
        )

    def browser_watcher(self) -> WorkflowProbe:
        source = _source(
            kind=SourceKind.LOCAL_FILE,
            name="Browser watcher local page source",
            locator=_example_source("browser_watcher_page.html"),
        )
        script = ArtifactRecord(
            kind=ArtifactKind.SCRIPT,
            name="browser watcher draft script",
            content="# generated watcher draft\nprint('watch condition dry-run placeholder')\n",
            status=ArtifactStatus.REVIEW_REQUIRED,
            metadata={"probe": WorkflowProbeKind.BROWSER_WATCHER.value, "execution": "not_allowed_in_probe"},
        )
        spec = _spec(
            name="Browser Watcher Probe",
            goal="Watch a target page state and report when the target condition appears.",
            intent_type=IntentType.WATCHER_WORKFLOW,
            source=source,
            steps=[
                _collect(source),
                _analyze("Detect whether the target condition is present."),
                _report("browser_watcher_report"),
            ],
            cadence="interval:manual_review",
        )
        return WorkflowProbe(
            kind=WorkflowProbeKind.BROWSER_WATCHER,
            request="이 사이트에서 빈자리가 뜨면 알려줘.",
            spec=spec,
            sources=[source],
            artifacts=[script],
        )

    def coding(self) -> WorkflowProbe:
        source = _source(
            kind=SourceKind.REPO_STATE,
            name="Repository state source",
            locator=str(_repo_root()),
        )
        spec = _spec(
            name="Coding Workflow Probe",
            goal="Inspect repository state, propose a scoped patch plan, and report verification.",
            intent_type=IntentType.CODING_WORKFLOW,
            source=source,
            steps=[
                _collect(source),
                _analyze("Summarize repo status, risks, patch plan, and tests."),
                _report("coding_workflow_report"),
            ],
            cadence="manual",
        )
        return WorkflowProbe(
            kind=WorkflowProbeKind.CODING,
            request="이 repo를 점검하고 작은 개선 계획과 테스트 보고서를 만들어줘.",
            spec=spec,
            sources=[source],
        )


def _source(
    *,
    kind: SourceKind,
    name: str,
    locator: str,
    requires_approval: bool = False,
) -> SourceDefinition:
    return SourceDefinition(
        kind=kind,
        name=name,
        locator=locator,
        enabled=True,
        policy=SourcePolicy(read_only=True, requires_approval=requires_approval),
    )


def _spec(
    *,
    name: str,
    goal: str,
    intent_type: IntentType,
    source: SourceDefinition,
    steps: list[WorkflowStep],
    cadence: str,
) -> WorkflowSpec:
    trigger_type = "manual"
    if cadence.startswith("interval:"):
        trigger_type = "interval"
    elif cadence.startswith("cron:"):
        trigger_type = "cron"
    return WorkflowSpec(
        name=name,
        description=f"M9 validation probe: {name}",
        goal=goal,
        success_criteria=["Represented as WorkflowSpec", "Uses real local sources", "Produces report artifact"],
        owner_channel="web",
        status=WorkflowStatus.PROPOSED,
        intent_type=intent_type,
        triggers=[{"type": trigger_type, "value": cadence}],
        inputs={"source_id": source.source_id, "cadence": cadence},
        sources=[{"source_id": source.source_id, "kind": source.kind.value, "locator": source.locator}],
        steps=steps,
        capabilities=[{"capability": f"source:{source.kind.value}:read", "risk": "low"}],
        policy={"probe": True, "production_external_source": False},
        outputs=[{"type": "report", "channel": "web"}],
        evals=[{"type": "probe", "required": True}],
        assumptions=["Probe uses checked-in local sources or current repository state."],
    )


def _collect(source: SourceDefinition) -> WorkflowStep:
    return WorkflowStep(
        step_id="collect",
        step_type=StepType.COLLECT,
        name="Collect source items",
        config={"source": source.kind.value, "source_id": source.source_id},
    )


def _analyze(instruction: str, *, depends_on: list[str] | None = None) -> WorkflowStep:
    return WorkflowStep(
        step_id="analyze",
        step_type=StepType.ANALYZE,
        name="Analyze probe data",
        config={"instruction": instruction},
        depends_on=depends_on or ["collect"],
    )


def _report(output: str) -> WorkflowStep:
    return WorkflowStep(
        step_id="report",
        step_type=StepType.REPORT,
        name="Render probe report",
        config={"output": output},
        depends_on=["analyze"],
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _example_source(name: str) -> str:
    return (_repo_root() / "examples" / "sources" / name).as_uri()
