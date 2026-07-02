from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentic.app.chat import ChatRuntime, run_chat_once
from agentic.config.settings import AppConfig
from agentic.sessions import SessionLogStore
from agentic.skills.workshop import SkillWorkshopStore
from agentic.workflow_kernel import StepType, WorkflowDesigner, WorkflowProposal, WorkflowSpec, WorkflowStore


DEFAULT_PROBE_REQUEST = "반복 자동화 워크플로우 만들어줘"
DEFAULT_PROBE_ANSWERS = [
    "커뮤니티 웹 페이지를 소스로 쓰고, 필요한 경우 에이전트가 HTTP/API/browser/script 중 적절한 수집 전략을 선택하게 해.",
    "1분마다 수집하고 1시간마다 분석해서 웹 보고서와 ntfy 알림으로 알려줘.",
]


@dataclass(frozen=True)
class HarnessProbeResult:
    ok: bool
    request: str
    interview_turns: list[dict[str, str]] = field(default_factory=list)
    final_status: str = ""
    agent_message: str = ""
    agent_response: str = ""
    proposal_count_before: int = 0
    proposal_count_after: int = 0
    new_proposals: list[dict[str, Any]] = field(default_factory=list)
    blocker: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "request": self.request,
            "interview_turns": self.interview_turns,
            "final_status": self.final_status,
            "agent_message": self.agent_message,
            "agent_response": self.agent_response,
            "proposal_count_before": self.proposal_count_before,
            "proposal_count_after": self.proposal_count_after,
            "new_proposals": self.new_proposals,
            "blocker": self.blocker,
        }


@dataclass(frozen=True)
class WorkflowSpecProbeResult:
    ok: bool
    request: str
    session_id: str = ""
    session_event_count: int = 0
    interview_turns: list[dict[str, str]] = field(default_factory=list)
    final_status: str = ""
    agent_message: str = ""
    agent_response: str = ""
    workflow_count_before: int = 0
    workflow_count_after: int = 0
    new_workflows: list[dict[str, Any]] = field(default_factory=list)
    blocker: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "request": self.request,
            "session_id": self.session_id,
            "session_event_count": self.session_event_count,
            "interview_turns": self.interview_turns,
            "final_status": self.final_status,
            "agent_message": self.agent_message,
            "agent_response": self.agent_response,
            "workflow_count_before": self.workflow_count_before,
            "workflow_count_after": self.workflow_count_after,
            "new_workflows": self.new_workflows,
            "blocker": self.blocker,
        }


def run_workflow_builder_probe(
    config: AppConfig,
    *,
    request: str = DEFAULT_PROBE_REQUEST,
    answers: list[str] | None = None,
    state_dir: str | Path | None = None,
    runtime: ChatRuntime | None = None,
) -> HarnessProbeResult:
    selected_answers = list(answers or DEFAULT_PROBE_ANSWERS)
    state_root = Path(state_dir) if state_dir else config.trace_dir / "state"
    workshop_store = SkillWorkshopStore(state_root / "skill_workshop.sqlite3")
    before = workshop_store.list(limit=200)
    before_ids = {proposal.proposal_id for proposal in before}

    proposal = WorkflowDesigner().design(request)
    interview_turns: list[dict[str, str]] = []
    for answer in selected_answers:
        if not proposal.session.question:
            interview_turns.append(
                {
                    "question": "Additional user guidance",
                    "answer": answer,
                }
            )
            continue
        question = proposal.session.question
        interview_turns.append({"question": question, "answer": answer})
        proposal = WorkflowDesigner().continue_design(proposal.session, answer)

    agent_message = _agent_message(request, proposal, interview_turns)
    selected_runtime = runtime
    if selected_runtime is None:
        from agentic.runtime.full_loop import FullLoopRuntime

        selected_runtime = FullLoopRuntime.from_config(config, state_dir=state_root)
    try:
        agent_response = run_chat_once(config, agent_message, runtime=selected_runtime)
    except Exception as exc:
        after = workshop_store.list(limit=200)
        return HarnessProbeResult(
            ok=False,
            request=request,
            interview_turns=interview_turns,
            final_status=proposal.session.status,
            agent_message=agent_message,
            proposal_count_before=len(before),
            proposal_count_after=len(after),
            new_proposals=[
                item.to_record() for item in after if item.proposal_id not in before_ids
            ],
            blocker=f"{exc.__class__.__name__}: {exc}",
        )

    after = workshop_store.list(limit=200)
    new_proposals = [item for item in after if item.proposal_id not in before_ids]
    quality_failures = _proposal_quality_failures(
        [proposal.to_record() for proposal in new_proposals]
    )
    ok = bool(new_proposals) and not quality_failures
    return HarnessProbeResult(
        ok=ok,
        request=request,
        interview_turns=interview_turns,
        final_status=proposal.session.status,
        agent_message=agent_message,
        agent_response=agent_response,
        proposal_count_before=len(before),
        proposal_count_after=len(after),
        new_proposals=[proposal.to_record() for proposal in new_proposals],
        blocker=_probe_blocker(new_proposals, quality_failures),
    )


def run_workflow_spec_probe(
    config: AppConfig,
    *,
    request: str = DEFAULT_PROBE_REQUEST,
    answers: list[str] | None = None,
    state_dir: str | Path | None = None,
    runtime: ChatRuntime | None = None,
) -> WorkflowSpecProbeResult:
    selected_answers = list(answers or DEFAULT_PROBE_ANSWERS)
    state_root = Path(state_dir) if state_dir else config.trace_dir / "state"
    workflow_store = WorkflowStore(state_root / "workflows.sqlite3")
    session_store = SessionLogStore(state_root / "sessions.sqlite3")
    session = session_store.start_session(
        "workflow_spec_probe",
        metadata={"request": request, "probe": "workflow_spec"},
    )
    session_store.append_event(session.session_id, "user_request", role="user", content=request)
    before = workflow_store.list_specs(limit=200)
    before_ids = {workflow.workflow_id for workflow in before}

    proposal, interview_turns = _interview_for_workflow(request, selected_answers)
    for turn in interview_turns:
        session_store.append_event(
            session.session_id,
            "interview_question",
            role="agent",
            content=turn["question"],
        )
        session_store.append_event(
            session.session_id,
            "interview_answer",
            role="user",
            content=turn["answer"],
        )
    agent_message = _workflow_spec_agent_message(request, proposal, interview_turns)
    session_store.append_event(
        session.session_id,
        "agent_instruction",
        role="runtime",
        content=agent_message,
    )
    selected_runtime = runtime
    if selected_runtime is None:
        from agentic.runtime.full_loop import FullLoopRuntime

        selected_runtime = FullLoopRuntime.from_config(config, state_dir=state_root)
    try:
        agent_response = run_chat_once(config, agent_message, runtime=selected_runtime)
    except Exception as exc:
        after = workflow_store.list_specs(limit=200)
        session_store.append_event(
            session.session_id,
            "agent_error",
            role="runtime",
            content=str(exc),
            payload={"error_type": exc.__class__.__name__},
        )
        session_store.close_session(session.session_id, status="failed")
        return WorkflowSpecProbeResult(
            ok=False,
            request=request,
            session_id=session.session_id,
            session_event_count=len(session_store.list_events(session.session_id)),
            interview_turns=interview_turns,
            final_status=proposal.session.status,
            agent_message=agent_message,
            workflow_count_before=len(before),
            workflow_count_after=len(after),
            new_workflows=[
                item.to_record() for item in after if item.workflow_id not in before_ids
            ],
            blocker=f"{exc.__class__.__name__}: {exc}",
        )

    after = workflow_store.list_specs(limit=200)
    new_workflows = [item for item in after if item.workflow_id not in before_ids]
    quality_failures = _workflow_spec_quality_failures(new_workflows)
    ok = bool(new_workflows) and not quality_failures
    session_store.append_event(
        session.session_id,
        "agent_response",
        role="agent",
        content=agent_response,
    )
    for workflow in new_workflows:
        session_store.append_event(
            session.session_id,
            "workflow_spec_created",
            role="runtime",
            payload={"workflow": workflow.to_record()},
        )
    if quality_failures:
        session_store.append_event(
            session.session_id,
            "workflow_spec_quality_failed",
            role="runtime",
            payload={"failures": quality_failures},
        )
    session_store.close_session(session.session_id, status="completed" if ok else "failed")
    return WorkflowSpecProbeResult(
        ok=ok,
        request=request,
        session_id=session.session_id,
        session_event_count=len(session_store.list_events(session.session_id)),
        interview_turns=interview_turns,
        final_status=proposal.session.status,
        agent_message=agent_message,
        agent_response=agent_response,
        workflow_count_before=len(before),
        workflow_count_after=len(after),
        new_workflows=[workflow.to_record() for workflow in new_workflows],
        blocker=_workflow_spec_probe_blocker(new_workflows, quality_failures),
    )


def _agent_message(
    request: str,
    proposal: WorkflowProposal,
    interview_turns: list[dict[str, str]],
) -> str:
    interview = "\n".join(
        f"- Q: {turn['question']}\n  A: {turn['answer']}" for turn in interview_turns
    )
    if not interview:
        interview = "- No interview answer was required."
    return "\n".join(
        [
            "Create a pending skill proposal for a reusable vague-workflow-building procedure.",
            "Do not write active SKILL.md files.",
            "Use the skill_workshop tool.",
            "",
            f"Original request: {request}",
            "",
            "Harness interview transcript:",
            interview,
            "",
            f"Design status: {proposal.session.status}",
            f"Missing slots: {', '.join(proposal.session.missing_slots) if proposal.session.missing_slots else 'none'}",
            f"Extracted slots: {proposal.session.extracted_slots}",
            "",
            "Create a compact but complete proposal_body under 160 words.",
            "The proposal_body must be exactly seven short markdown bullets.",
            "Use these bullet labels exactly: Trigger, Interview, Discovery, Proposal, Approval, Recording, Evolution.",
            "Each bullet must be complete and no longer than 14 words.",
            "Prefer one concise markdown block over a long explanation.",
        ]
    )


def _interview_for_workflow(request: str, answers: list[str]) -> tuple[WorkflowProposal, list[dict[str, str]]]:
    proposal = WorkflowDesigner().design(request)
    stored_turns: list[dict[str, str]] = []
    for answer in answers:
        if not proposal.session.question:
            stored_turns.append({"question": "Additional user guidance", "answer": answer})
            continue
        question = proposal.session.question
        stored_turns.append({"question": question, "answer": answer})
        proposal = WorkflowDesigner().continue_design(proposal.session, answer)
    return proposal, stored_turns


def _workflow_spec_agent_message(
    request: str,
    proposal: WorkflowProposal,
    interview_turns: list[dict[str, str]],
) -> str:
    interview = "\n".join(
        f"- Q: {turn['question']}\n  A: {turn['answer']}" for turn in interview_turns
    )
    if not interview:
        interview = "- No interview answer was required."
    return "\n".join(
        [
            "Create a pending WorkflowSpec for review using the workflow_spec tool.",
            "Do not execute, approve, activate, crawl, script, or write user workflow files.",
            "Output exactly one JSON tool call and no commentary.",
            "",
            f"Original request: {request}",
            "",
            "Harness interview transcript:",
            interview,
            "",
            f"Design status: {proposal.session.status}",
            f"Missing slots: {', '.join(proposal.session.missing_slots) if proposal.session.missing_slots else 'none'}",
            f"Extracted slots: {proposal.session.extracted_slots}",
            "",
            "Use the compact workflow_spec interface:",
            '{"tool":"workflow_spec","arguments":{"action":"create","name":"...",'
            '"goal":"...","description":"...","trigger":"interval:60s",'
            '"source":"community_web+reddit","step_types":["collect","analyze","report","notify"],'
            '"output":"report","success_criteria":["..."],"policy":{"approval":"..."}}}',
            "Keep every string short.",
            "Choose step_types from valid values such as collect, analyze, aggregate, report, notify, approval.",
            "Keep the spec generic; choose capability families, not site-specific scraper code.",
        ]
    )


def _workflow_spec_probe_blocker(new_workflows: list[WorkflowSpec], quality_failures: list[str]) -> str:
    if not new_workflows:
        return "agent did not create a new proposed WorkflowSpec"
    if quality_failures:
        return "workflow spec quality failed: " + "; ".join(quality_failures)
    return ""


def _workflow_spec_quality_failures(workflows: list[WorkflowSpec]) -> list[str]:
    failures: list[str] = []
    required_steps = {StepType.COLLECT.value, StepType.ANALYZE.value, StepType.REPORT.value}
    for workflow in workflows:
        step_types = {step.step_type.value for step in workflow.steps}
        for step_type in required_steps:
            if step_type not in step_types:
                failures.append(f"{workflow.workflow_id}: missing {step_type} step")
        if workflow.status.value != "proposed":
            failures.append(f"{workflow.workflow_id}: status is not proposed")
        if not workflow.triggers:
            failures.append(f"{workflow.workflow_id}: missing trigger")
        if not workflow.sources:
            failures.append(f"{workflow.workflow_id}: missing source")
        if not workflow.outputs:
            failures.append(f"{workflow.workflow_id}: missing output")
        if not workflow.success_criteria:
            failures.append(f"{workflow.workflow_id}: missing success criteria")
        if len(workflow.steps) < 3:
            failures.append(f"{workflow.workflow_id}: too few steps")
    return failures


def _probe_blocker(new_proposals: list[Any], quality_failures: list[str]) -> str:
    if not new_proposals:
        return "agent did not create a new pending skill proposal"
    if quality_failures:
        return "proposal quality failed: " + "; ".join(quality_failures)
    return ""


def _proposal_quality_failures(proposals: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    required_labels = (
        "trigger",
        "interview",
        "discovery",
        "proposal",
        "approval",
        "recording",
        "evolution",
    )
    for proposal in proposals:
        proposal_id = str(proposal.get("proposal_id") or "<unknown>")
        body = str(proposal.get("proposal_body") or "")
        bullet_labels = _proposal_bullet_labels(body)
        if len(body.strip()) < 220:
            failures.append(f"{proposal_id}: proposal_body too short")
        if body.rstrip().endswith(("Pro", "Spec", "Appro", "Reco", "Evo", "the")):
            failures.append(f"{proposal_id}: proposal_body appears truncated")
        for label in required_labels:
            if label not in bullet_labels:
                failures.append(f"{proposal_id}: missing {label}")
    return failures


def _proposal_bullet_labels(body: str) -> set[str]:
    labels: set[str] = set()
    expected_labels = (
        "trigger",
        "interview",
        "discovery",
        "proposal",
        "approval",
        "recording",
        "evolution",
    )
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("-", "*")):
            continue
        label_text = _bullet_label_text(stripped)
        for label in expected_labels:
            if label_text == label or label_text.startswith(label + " "):
                labels.add(label)
    return labels


def _bullet_label_text(stripped_line: str) -> str:
    label_text = stripped_line[1:].strip().lower()
    label_text = label_text.lstrip("*`_ ").split(":", 1)[0]
    return label_text.strip("*`_ ")
