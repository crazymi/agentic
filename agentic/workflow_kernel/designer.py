from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agentic.workflow_kernel.intent import IntentRouter
from agentic.workflow_kernel.models import (
    IntentType,
    StepType,
    WorkflowDesignSession,
    WorkflowSpec,
    WorkflowStatus,
    WorkflowStep,
)


REQUIRED_DESIGN_SLOTS = ("goal", "source", "cadence", "output")


@dataclass(frozen=True)
class WorkflowProposal:
    session: WorkflowDesignSession
    spec: WorkflowSpec | None

    def to_markdown(self) -> str:
        lines = [
            f"## Workflow Proposal: {self.spec.name if self.spec else 'Needs more input'}",
            "",
            f"- Status: {self.session.status}",
            f"- Intent: {self.session.intent.intent_type.value}",
        ]
        if self.session.question:
            lines.append(f"- Question: {self.session.question}")
        if self.session.missing_slots:
            lines.append(f"- Missing: {', '.join(self.session.missing_slots)}")
        if self.spec is not None:
            lines.extend(
                [
                    f"- Goal: {self.spec.goal}",
                    f"- Trigger: {self.spec.triggers[0] if self.spec.triggers else 'manual'}",
                    f"- Steps: {', '.join(step.step_type.value for step in self.spec.steps)}",
                ]
            )
        return "\n".join(lines)


class WorkflowDesigner:
    def __init__(self, router: IntentRouter | None = None):
        self.router = router or IntentRouter()

    def design(self, user_request: str) -> WorkflowProposal:
        intent = self.router.classify(user_request)
        slots = self._extract_slots(user_request, intent.intent_type)
        missing = [slot for slot in REQUIRED_DESIGN_SLOTS if not slots.get(slot)]
        question = self._question_for(missing[0]) if missing else None
        status = "needs_input" if question else "proposed"
        session = WorkflowDesignSession(
            user_request=user_request,
            intent=intent,
            status=status,
            extracted_slots=slots,
            missing_slots=missing,
            question=question,
            assumptions=self._assumptions(slots, missing),
        )
        spec = self._build_spec(user_request, intent.intent_type, slots, session.assumptions) if not missing else None
        if spec is not None:
            session = WorkflowDesignSession(
                session_id=session.session_id,
                user_request=session.user_request,
                intent=session.intent,
                status="proposed",
                extracted_slots=session.extracted_slots,
                missing_slots=[],
                question=None,
                assumptions=session.assumptions,
                proposed_workflow_id=spec.workflow_id,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
        return WorkflowProposal(session=session, spec=spec)

    def _extract_slots(self, text: str, intent_type: IntentType) -> dict[str, Any]:
        lowered = text.lower()
        slots: dict[str, Any] = {}
        slots["goal"] = text.strip() if len(text.strip()) > 8 else ""
        slots["source"] = self._source_from(lowered)
        slots["cadence"] = self._cadence_from(lowered, intent_type)
        slots["output"] = self._output_from(lowered)
        slots["alert_path"] = "ntfy" if any(token in lowered for token in ("알림", "알려", "notify", "ntfy")) else "web"
        slots["risk"] = self._risk_from(lowered)
        return slots

    @staticmethod
    def _source_from(text: str) -> str:
        if any(token in text for token in ("wsj", "gmail", "메일", "뉴스레터")):
            return "mail"
        if any(token in text for token in ("reddit", "레딧")):
            return "reddit"
        if any(token in text for token in ("주식갤", "dcinside", "디시", "커뮤니티")):
            return "community_web"
        if any(token in text for token in ("사이트", "url", "http", "브라우저", "ticket", "티켓")):
            return "web_page"
        if any(token in text for token in ("repo", "repository", "리포", "코드")):
            return "repo"
        if any(token in text for token in ("idea", "아이디어", "메모", "노트")):
            return "channel"
        return ""

    @staticmethod
    def _cadence_from(text: str, intent_type: IntentType) -> str:
        if "1분" in text or "1 minute" in text:
            return "interval:60s"
        if "30분" in text or "30 minute" in text:
            return "interval:1800s"
        if "매일" in text or "daily" in text:
            return "cron:daily"
        if "매주" in text or "weekly" in text:
            return "cron:weekly"
        if "마다" in text or "주기" in text or "interval" in text:
            return "interval:manual_review"
        if intent_type == IntentType.WATCHER_WORKFLOW:
            return "interval:manual_review"
        if intent_type == IntentType.SCHEDULED_WORKFLOW:
            return ""
        return "manual"

    @staticmethod
    def _output_from(text: str) -> str:
        if any(token in text for token in ("보고서", "report")):
            return "report"
        if any(token in text for token in ("알림", "notify", "알려")):
            return "notification"
        if any(token in text for token in ("저장", "db", "database")):
            return "resource"
        return "report"

    @staticmethod
    def _risk_from(text: str) -> str:
        if any(token in text for token in ("구매", "예매", "결제", "send", "메일 보내", "submit")):
            return "high"
        if any(token in text for token in ("로그인", "credential", "비밀번호", "계정")):
            return "medium"
        return "low"

    @staticmethod
    def _question_for(slot: str) -> str:
        questions = {
            "goal": "이 workflow의 최종 목표를 한 문장으로 정해주세요.",
            "source": "어떤 데이터 소스를 사용할까요? 예: Gmail, Reddit, 특정 사이트 URL, Obsidian, repo",
            "cadence": "얼마나 자주 실행할까요? 예: 1분마다, 30분마다, 매일 오전",
            "output": "결과는 어떤 형태로 받을까요? 예: 웹 보고서, ntfy 알림, 메일 초안, 메모 저장",
        }
        return questions[slot]

    @staticmethod
    def _assumptions(slots: dict[str, Any], missing: list[str]) -> list[str]:
        assumptions: list[str] = []
        if "output" not in missing and slots.get("output") == "report":
            assumptions.append("Output defaults to a local report visible in the web UI.")
        if slots.get("alert_path") == "web":
            assumptions.append("Notifications default to web UI unless ntfy is requested.")
        if slots.get("risk") == "low":
            assumptions.append("Workflow starts read-only until a capability plan requires approval.")
        return assumptions

    def _build_spec(
        self,
        text: str,
        intent_type: IntentType,
        slots: dict[str, Any],
        assumptions: list[str],
    ) -> WorkflowSpec:
        source = slots["source"]
        cadence = slots["cadence"]
        steps = [
            WorkflowStep(
                step_id="collect",
                step_type=StepType.COLLECT,
                name="Collect source items",
                config={"source": source},
            ),
            WorkflowStep(
                step_id="analyze",
                step_type=StepType.ANALYZE,
                name="Analyze collected items",
                config={"goal": slots["goal"]},
                depends_on=["collect"],
            ),
            WorkflowStep(
                step_id="report",
                step_type=StepType.REPORT,
                name="Render report",
                config={"output": slots["output"]},
                depends_on=["analyze"],
            ),
        ]
        if slots.get("alert_path") == "ntfy":
            steps.append(
                WorkflowStep(
                    step_id="notify",
                    step_type=StepType.NOTIFY,
                    name="Notify user",
                    config={"channel": "ntfy"},
                    depends_on=["report"],
                )
            )
        trigger_type = "manual" if cadence == "manual" else "interval" if cadence.startswith("interval:") else "cron"
        return WorkflowSpec(
            name=self._name_for(source, intent_type),
            description=text.strip(),
            goal=slots["goal"],
            success_criteria=["Collect source items", "Analyze against the goal", "Produce a reviewable report"],
            intent_type=intent_type,
            triggers=[{"type": trigger_type, "value": cadence}],
            inputs={"source": source, "cadence": cadence, "output": slots["output"]},
            sources=[{"type": source, "mode": "fake_or_allowlisted"}],
            steps=steps,
            status=WorkflowStatus.PROPOSED,
            policy={"risk": slots["risk"], "activation_requires_approval": True},
            outputs=[{"type": slots["output"], "channel": slots.get("alert_path", "web")}],
            evals=[{"type": "fake_probe", "required": True}],
            assumptions=assumptions,
        )

    @staticmethod
    def _name_for(source: str, intent_type: IntentType) -> str:
        if source == "mail":
            return "Mail Intelligence Workflow"
        if source in {"reddit", "community_web"}:
            return "Social Trend Intelligence Workflow"
        if source == "web_page" or intent_type == IntentType.WATCHER_WORKFLOW:
            return "Browser Watcher Workflow"
        if source == "repo" or intent_type == IntentType.CODING_WORKFLOW:
            return "Coding Workflow"
        if source == "channel":
            return "Idea Synthesis Workflow"
        return "Designed Workflow"
