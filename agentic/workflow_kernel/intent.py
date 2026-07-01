from __future__ import annotations

from agentic.traces.logger import TraceLogger
from agentic.workflow_kernel.models import IntentType, RequestIntent


class IntentRouter:
    def __init__(self, trace: TraceLogger | None = None):
        self.trace = trace

    def classify(self, text: str) -> RequestIntent:
        normalized = text.strip()
        lowered = normalized.lower()
        extracted = {"text": normalized}

        if not normalized:
            return self._record(
                RequestIntent(
                    intent_type=IntentType.UNKNOWN,
                    confidence=1.0,
                    reason="empty request",
                    requires_clarification=True,
                    clarification_question="무엇을 하려는 요청인지 한 문장으로 알려주세요.",
                    extracted=extracted,
                )
            )

        if self._looks_like_simple_answer(lowered):
            return self._record(
                RequestIntent(
                    intent_type=IntentType.ANSWER_NOW,
                    confidence=0.9,
                    reason="short factual or arithmetic request",
                    extracted=extracted,
                )
            )
        if self._looks_like_coding(lowered):
            return self._record(
                RequestIntent(
                    intent_type=IntentType.CODING_WORKFLOW,
                    confidence=0.85,
                    reason="repository or code change workflow requested",
                    extracted=extracted,
                )
            )
        if self._looks_like_scheduled(lowered):
            return self._record(
                RequestIntent(
                    intent_type=IntentType.SCHEDULED_WORKFLOW,
                    confidence=0.86,
                    reason="recurring cadence or repeated report requested",
                    extracted=extracted,
                )
            )
        if self._looks_like_watcher(lowered):
            return self._record(
                RequestIntent(
                    intent_type=IntentType.WATCHER_WORKFLOW,
                    confidence=0.86,
                    reason="watch/alert condition requested",
                    extracted=extracted,
                )
            )
        if self._looks_like_research(lowered):
            return self._record(
                RequestIntent(
                    intent_type=IntentType.DEEP_RESEARCH,
                    confidence=0.78,
                    reason="research/report request",
                    extracted=extracted,
                )
            )
        if self._looks_like_workflow_design(lowered):
            return self._record(
                RequestIntent(
                    intent_type=IntentType.WORKFLOW_DESIGN,
                    confidence=0.76,
                    reason="workflow design requested",
                    extracted=extracted,
                )
            )
        if len(normalized) < 12:
            return self._record(
                RequestIntent(
                    intent_type=IntentType.UNKNOWN,
                    confidence=0.7,
                    reason="short ambiguous request",
                    requires_clarification=True,
                    clarification_question="이 요청은 즉시 답변, 조사, 반복 workflow 중 어느 쪽인가요?",
                    extracted=extracted,
                )
            )
        return self._record(
            RequestIntent(
                intent_type=IntentType.ONE_OFF_TASK,
                confidence=0.55,
                reason="bounded task request without recurring signals",
                extracted=extracted,
            )
        )

    def _record(self, intent: RequestIntent) -> RequestIntent:
        if self.trace is not None:
            self.trace.record("intent_classified", intent.to_record())
        return intent

    @staticmethod
    def _looks_like_simple_answer(text: str) -> bool:
        answer_tokens = ("뭐야", "무엇", "어디", "누구", "계산", "1+1", "수도")
        scheduling_tokens = ("매일", "주기", "마다", "알려", "보고서", "watch", "crawl")
        return any(token in text for token in answer_tokens) and not any(
            token in text for token in scheduling_tokens
        )

    @staticmethod
    def _looks_like_scheduled(text: str) -> bool:
        return any(
            token in text
            for token in (
                "매일",
                "매주",
                "주기",
                "간격",
                "마다",
                "cron",
                "schedule",
                "scheduled",
                "반복",
                "정기",
                "30분",
                "1분",
                "daily",
                "hourly",
            )
        )

    @staticmethod
    def _looks_like_watcher(text: str) -> bool:
        return any(
            token in text
            for token in (
                "watch",
                "watcher",
                "감시",
                "빈자리",
                "뜨면",
                "나면",
                "알림",
                "알려줘",
                "monitor",
                "detect",
                "ticket",
                "티켓",
            )
        )

    @staticmethod
    def _looks_like_research(text: str) -> bool:
        return any(token in text for token in ("deepresearch", "deep research", "조사", "리서치", "research"))

    @staticmethod
    def _looks_like_coding(text: str) -> bool:
        return any(
            token in text
            for token in ("repo", "repository", "코드", "리포", "구현", "수정", "테스트", "patch", "fix")
        )

    @staticmethod
    def _looks_like_workflow_design(text: str) -> bool:
        return any(token in text for token in ("workflow", "워크플로우", "자동화", "설계", "만들어줘"))
