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
    utc_now,
)


REQUIRED_DESIGN_SLOTS = ("goal", "source", "cadence", "output")
BROWSER_TRANSACTION_SLOTS = (
    "goal",
    "source",
    "target",
    "constraints",
    "retry_policy",
    "approval_boundary",
    "output",
)


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
        missing = [slot for slot in self._required_slots(intent.intent_type) if not slots.get(slot)]
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
                answers=session.answers,
                assumptions=session.assumptions,
                proposed_workflow_id=spec.workflow_id,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
        return WorkflowProposal(session=session, spec=spec)

    def continue_design(self, session: WorkflowDesignSession, answer: str) -> WorkflowProposal:
        if not session.missing_slots:
            return WorkflowProposal(session=session, spec=None)
        slot = session.missing_slots[0]
        slots = dict(session.extracted_slots)
        slots[slot] = self._normalize_slot_answer(slot, answer)
        if answer.strip():
            slots[f"{slot}_raw"] = answer.strip()
        missing = [item for item in self._required_slots(session.intent.intent_type) if not slots.get(item)]
        question = self._question_for(missing[0]) if missing else None
        answers = [
            *session.answers,
            {"slot": slot, "answer": answer.strip(), "created_at": utc_now()},
        ]
        updated = WorkflowDesignSession(
            session_id=session.session_id,
            user_request=session.user_request,
            intent=session.intent,
            status="needs_input" if question else "proposed",
            extracted_slots=slots,
            missing_slots=missing,
            question=question,
            answers=answers,
            assumptions=self._assumptions(slots, missing),
            proposed_workflow_id=session.proposed_workflow_id,
            created_at=session.created_at,
            updated_at=utc_now(),
        )
        spec = (
            self._build_spec(session.user_request, session.intent.intent_type, slots, updated.assumptions)
            if not missing
            else None
        )
        if spec is None:
            return WorkflowProposal(session=updated, spec=None)
        proposed = WorkflowDesignSession(
            session_id=updated.session_id,
            user_request=updated.user_request,
            intent=updated.intent,
            status="proposed",
            extracted_slots=updated.extracted_slots,
            missing_slots=[],
            question=None,
            answers=updated.answers,
            assumptions=updated.assumptions,
            proposed_workflow_id=spec.workflow_id,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )
        return WorkflowProposal(session=proposed, spec=spec)

    @staticmethod
    def _normalize_slot_answer(slot: str, answer: str) -> str:
        cleaned = answer.strip()
        if not cleaned:
            return ""
        lowered = cleaned.lower()
        if slot == "source":
            inferred = WorkflowDesigner._source_from(lowered)
            return inferred or cleaned
        if slot == "cadence":
            inferred = WorkflowDesigner._cadence_from(lowered, IntentType.SCHEDULED_WORKFLOW)
            if inferred and inferred != "interval:manual_review":
                return inferred
            if any(token in lowered for token in ("인터뷰", "확정", "decide", "clarify")):
                return ""
            return inferred or cleaned
        if slot == "output":
            return WorkflowDesigner._output_from(lowered) or cleaned
        if slot == "constraints":
            return cleaned
        if slot == "retry_policy":
            if "1분" in lowered or "1 minute" in lowered:
                return "interval:60s"
            if "5분" in lowered or "5 minute" in lowered:
                return "interval:300s"
            if "변화" in lowered or "state change" in lowered:
                return "state_change_only"
        return cleaned

    def _extract_slots(self, text: str, intent_type: IntentType) -> dict[str, Any]:
        lowered = text.lower()
        slots: dict[str, Any] = {}
        slots["goal"] = text.strip() if len(text.strip()) > 8 else ""
        slots["source"] = self._source_from(lowered)
        slots["cadence"] = self._cadence_from(lowered, intent_type)
        slots["output"] = self._output_from(lowered)
        slots["alert_path"] = "ntfy" if any(token in lowered for token in ("알림", "알려", "notify", "ntfy")) else "web"
        slots["risk"] = self._risk_from(lowered)
        slots["target"] = self._target_from(text, lowered, intent_type)
        slots["constraints"] = self._constraints_from(lowered)
        slots["retry_policy"] = self._retry_policy_from(lowered, intent_type)
        slots["approval_boundary"] = self._approval_boundary_from(lowered, intent_type)
        return slots

    @staticmethod
    def _required_slots(intent_type: IntentType) -> tuple[str, ...]:
        if intent_type == IntentType.BROWSER_TRANSACTION:
            return BROWSER_TRANSACTION_SLOTS
        return REQUIRED_DESIGN_SLOTS

    @staticmethod
    def _source_from(text: str) -> str:
        if any(token in text for token in ("wsj", "gmail", "메일", "뉴스레터")):
            return "mail"
        if any(token in text for token in ("reddit", "레딧")):
            return "reddit"
        if any(token in text for token in ("주식갤", "dcinside", "디시", "커뮤니티")):
            return "community_web"
        if any(token in text for token in ("사이트", "url", "http", "브라우저", "ticket", "티켓", "표")):
            return "web_page"
        if any(token in text for token in ("repo", "repository", "리포", "코드")):
            return "repo"
        if any(
            token in text
            for token in (
                "idea",
                "아이디어",
                "메모",
                "노트",
                "채팅 기록",
                "chat history",
                "승인 이벤트",
                "approval event",
                "채널 이벤트",
            )
        ):
            return "channel"
        return ""

    @staticmethod
    def _target_from(text: str, lowered: str, intent_type: IntentType) -> str:
        if intent_type != IntentType.BROWSER_TRANSACTION:
            return ""
        if len(text.strip()) <= 8:
            return ""
        return text.strip()

    @staticmethod
    def _constraints_from(text: str) -> str:
        if any(token in text for token in ("1장", "2장", "3장", "4장", "예산", "가격", "좌석", "자리", "section")):
            return "provided"
        return ""

    @staticmethod
    def _retry_policy_from(text: str, intent_type: IntentType) -> str:
        if intent_type != IntentType.BROWSER_TRANSACTION:
            return ""
        if any(token in text for token in ("24/7", "계속", "재시도", "빈자리", "나면", "뜨면", "매크로")):
            return "watch_with_backoff"
        return "manual_then_watch"

    @staticmethod
    def _approval_boundary_from(text: str, intent_type: IntentType) -> str:
        if intent_type != IntentType.BROWSER_TRANSACTION:
            return ""
        if any(token in text for token in ("승인", "확인", "물어", "결제 전", "예매 전")):
            return "fresh_user_approval_before_submit"
        return "fresh_user_approval_before_submit"

    @staticmethod
    def _cadence_from(text: str, intent_type: IntentType) -> str:
        if "1분" in text or "1 minute" in text:
            return "interval:60s"
        if "1시간" in text or "1 hour" in text or "hourly" in text:
            return "interval:3600s"
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
            "target": "정확히 어떤 대상/세션을 처리할까요? 예: MSI 2026 결승, 날짜, 회차, 공식 사이트 후보",
            "constraints": "자동화 제약을 정해주세요. 예: 수량, 예산 상한, 좌석 선호, 허용/금지 행동",
            "retry_policy": "실패하거나 빈자리가 없으면 어떻게 재시도할까요? 예: 1분마다, 5분마다, 상태 변화시에만",
            "approval_boundary": "어떤 행동 직전에 반드시 멈추고 승인을 받을까요? 예: 좌석 선택, 예매확정, 결제",
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
        if slots.get("risk") == "high":
            assumptions.append("Consequential actions require fresh user approval before execution.")
        if slots.get("retry_policy") == "manual_then_watch":
            assumptions.append("First attempt is manual; unavailable states become a watched retry workflow.")
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
        if intent_type == IntentType.BROWSER_TRANSACTION:
            return self._build_browser_transaction_spec(text, slots, assumptions)
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
            inputs={
                "source": source,
                "cadence": cadence,
                "output": slots["output"],
                "slot_answers": _slot_answers(slots),
            },
            sources=[{"type": source, "mode": "requires_real_source_binding"}],
            steps=steps,
            status=WorkflowStatus.PROPOSED,
            policy={
                "risk": slots["risk"],
                "activation_requires_approval": slots["risk"] != "low",
            },
            outputs=[{"type": slots["output"], "channel": slots.get("alert_path", "web")}],
            evals=[{"type": "real_local_source_probe", "required": True}],
            assumptions=assumptions,
        )

    @staticmethod
    def _name_for(source: str, intent_type: IntentType) -> str:
        if intent_type == IntentType.BROWSER_TRANSACTION:
            return "Browser Transaction Workflow"
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

    def _build_browser_transaction_spec(
        self,
        text: str,
        slots: dict[str, Any],
        assumptions: list[str],
    ) -> WorkflowSpec:
        steps = [
            WorkflowStep(
                step_id="verify_sources",
                step_type=StepType.COLLECT,
                name="Verify official sources",
                config={"source": slots["source"], "purpose": "official_source_verification"},
            ),
            WorkflowStep(
                step_id="ask_user_constraints",
                step_type=StepType.ASK_USER,
                name="Confirm user constraints",
                config={
                    "question": "수량, 예산 상한, 좌석 선호, 허용/금지 행동을 확인해주세요.",
                    "slot": "constraints",
                },
                depends_on=["verify_sources"],
            ),
            WorkflowStep(
                step_id="browser_observe",
                step_type=StepType.BROWSER_OBSERVE,
                name="Observe browser state",
                config={
                    "target": slots["target"],
                    "source": slots["source"],
                    "save_artifacts": True,
                },
                depends_on=["ask_user_constraints"],
            ),
            WorkflowStep(
                step_id="browser_action",
                step_type=StepType.BROWSER_ACTION,
                name="Perform approved browser action",
                config={
                    "allowed_actions": ["navigate", "safe_click", "select_candidate"],
                    "blocked_actions": ["payment", "booking_confirm_without_approval"],
                    "approval_boundary": slots["approval_boundary"],
                },
                depends_on=["browser_observe"],
            ),
            WorkflowStep(
                step_id="approval",
                step_type=StepType.APPROVAL,
                name="Wait for approval before consequential submit",
                config={"boundary": slots["approval_boundary"]},
                depends_on=["browser_action"],
            ),
            WorkflowStep(
                step_id="report",
                step_type=StepType.REPORT,
                name="Render transaction report",
                config={"output": slots["output"]},
                depends_on=["approval"],
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
        retry_policy = slots.get("retry_policy") or "manual_then_watch"
        trigger = {"type": "manual_then_interval", "value": retry_policy}
        return WorkflowSpec(
            name="Browser Transaction Workflow",
            description=text.strip(),
            goal=slots["goal"],
            success_criteria=[
                "Verify official source/platform",
                "Pause for user login or missing constraints",
                "Observe browser state and save artifacts",
                "Require approval before consequential submit",
                "Retry unavailable states according to policy",
            ],
            intent_type=IntentType.BROWSER_TRANSACTION,
            triggers=[trigger],
            inputs={
                "source": slots["source"],
                "target": slots["target"],
                "constraints": slots["constraints"],
                "retry_policy": retry_policy,
                "approval_boundary": slots["approval_boundary"],
                "output": slots["output"],
                "slot_answers": _slot_answers(slots),
            },
            sources=[{"type": slots["source"], "mode": "requires_real_source_binding"}],
            steps=steps,
            status=WorkflowStatus.PROPOSED,
            policy={
                "risk": "high",
                "activation_requires_approval": True,
                "requires_user_presence": True,
                "payment_without_approval": "deny",
            },
            outputs=[{"type": slots["output"], "channel": slots.get("alert_path", "web")}],
            evals=[{"type": "live_browser_transaction_probe", "required": True}],
            assumptions=assumptions,
        )


def _slot_answers(slots: dict[str, Any]) -> dict[str, str]:
    answers: dict[str, str] = {}
    for key, value in slots.items():
        if not key.endswith("_raw"):
            continue
        slot = key[: -len("_raw")]
        if value:
            answers[slot] = str(value)
    return answers
