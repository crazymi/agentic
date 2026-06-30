from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from agentic.connectors.gmail.models import EmailMessage
from agentic.memory.models import MemoryKind
from agentic.memory.store import MemoryStore
from agentic.resources.store import ResourceKind, ResourceRecord, ResourceStore


@dataclass(frozen=True)
class NewsletterAnalysisGoal:
    name: str
    description: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NewsletterFinding:
    kind: str
    title: str
    summary: str
    evidence: str
    confidence: str
    source_resource_id: str
    source_uri: str


@dataclass(frozen=True)
class NewsletterReport:
    goal: NewsletterAnalysisGoal
    resource_ids: list[str]
    findings: list[NewsletterFinding]
    followups: list[str]

    def to_markdown(self) -> str:
        lines = [f"# Newsletter Report: {self.goal.name}", "", self.goal.description, ""]
        for finding in self.findings:
            lines.extend(
                [
                    f"## {finding.title}",
                    f"- kind: {finding.kind}",
                    f"- confidence: {finding.confidence}",
                    f"- summary: {finding.summary}",
                    f"- evidence: {finding.evidence}",
                    f"- source: {finding.source_uri}",
                    "",
                ]
            )
        if self.followups:
            lines.append("## Follow-ups")
            lines.extend(f"- {item}" for item in self.followups)
        return "\n".join(lines).strip()


class NewsletterIngestor:
    def __init__(self, resources: ResourceStore):
        self.resources = resources

    def ingest(self, messages: Iterable[EmailMessage]) -> list[ResourceRecord]:
        records = []
        for message in messages:
            records.append(
                self.resources.add(
                    ResourceRecord(
                        uri=message.uri,
                        kind=ResourceKind.EMAIL,
                        title=message.subject,
                        content_text=message.body_text,
                        source_connector="gmail",
                        metadata={
                            "message_id": message.message_id,
                            "sender": message.sender,
                            "received_at": message.received_at,
                            "labels": message.labels,
                            **message.metadata,
                        },
                    )
                )
            )
        return records


class NewsletterAnalyzer:
    def analyze(
        self,
        resources: list[ResourceRecord],
        goal: NewsletterAnalysisGoal,
    ) -> NewsletterReport:
        findings: list[NewsletterFinding] = []
        for resource in resources:
            sentences = _sentences(resource.content_text)
            for sentence in sentences:
                finding = self._finding_from_sentence(sentence, resource, goal)
                if finding is not None:
                    findings.append(finding)
        followups = [
            f"Review {finding.title} from {finding.source_uri}"
            for finding in findings[:3]
        ]
        return NewsletterReport(
            goal=goal,
            resource_ids=[resource.resource_id for resource in resources],
            findings=findings,
            followups=followups,
        )

    def _finding_from_sentence(
        self,
        sentence: str,
        resource: ResourceRecord,
        goal: NewsletterAnalysisGoal,
    ) -> NewsletterFinding | None:
        lowered = sentence.lower()
        goal_text = f"{goal.name} {goal.description} {' '.join(goal.tags)}".lower()
        if any(token in lowered for token in ("startup", "founder", "new company", "venture")):
            return NewsletterFinding(
                kind="startup_idea",
                title="Startup signal",
                summary=sentence,
                evidence=sentence,
                confidence="medium",
                source_resource_id=resource.resource_id,
                source_uri=resource.uri,
            )
        if any(token in goal_text for token in ("portfolio", "stock", "주식")) and any(
            token in lowered for token in ("stock", "shares", "market", "earnings", "guidance")
        ):
            return NewsletterFinding(
                kind="portfolio_relevance",
                title="Portfolio relevance",
                summary=sentence,
                evidence=sentence,
                confidence="medium",
                source_resource_id=resource.resource_id,
                source_uri=resource.uri,
            )
        if any(token in lowered for token in ("ai", "agent", "automation", "semiconductor")):
            return NewsletterFinding(
                kind="technology_signal",
                title="Technology signal",
                summary=sentence,
                evidence=sentence,
                confidence="low",
                source_resource_id=resource.resource_id,
                source_uri=resource.uri,
            )
        return None


class NewsletterWorkflow:
    def __init__(self, *, resources: ResourceStore, memory: MemoryStore):
        self.resources = resources
        self.memory = memory
        self.ingestor = NewsletterIngestor(resources)
        self.analyzer = NewsletterAnalyzer()

    def run(self, messages: list[EmailMessage], goal: NewsletterAnalysisGoal) -> NewsletterReport:
        records = self.ingestor.ingest(messages)
        report = self.analyzer.analyze(records, goal)
        self.memory.add(
            kind=MemoryKind.INSIGHT,
            text=report.to_markdown(),
            tags=["newsletter", *goal.tags],
            source="newsletter_workflow",
            links=report.resource_ids,
            metadata={"goal": goal.name, "finding_count": len(report.findings)},
        )
        return report


def _sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]
