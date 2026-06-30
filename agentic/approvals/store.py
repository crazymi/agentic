from __future__ import annotations

import json
from pathlib import Path

from agentic.approvals.models import ApprovalRequest, ApprovalStatus


class ApprovalStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, request: ApprovalRequest) -> ApprovalRequest:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(request.to_record(), ensure_ascii=False) + "\n")
        return request

    def list_all(self) -> list[ApprovalRequest]:
        if not self.path.exists():
            return []
        approvals: dict[str, ApprovalRequest] = {}
        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                request = ApprovalRequest.from_record(json.loads(line))
                approvals[request.approval_id] = request
        return list(approvals.values())

    def get(self, approval_id: str) -> ApprovalRequest:
        for request in self.list_all():
            if request.approval_id == approval_id:
                return request
        raise KeyError(f"unknown approval: {approval_id}")

    def pending(self) -> list[ApprovalRequest]:
        return [
            request
            for request in self.list_all()
            if request.status == ApprovalStatus.PENDING
        ]

    def update(self, request: ApprovalRequest) -> ApprovalRequest:
        self.get(request.approval_id)
        return self.append(request)
