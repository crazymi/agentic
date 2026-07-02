from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from urllib import request
from urllib.error import URLError

from agentic.approvals.models import ApprovalRequest


Transport = Callable[[str, bytes, dict[str, str]], int]


def _urllib_transport(url: str, data: bytes, headers: dict[str, str]) -> int:
    req = request.Request(url, data=data, headers=headers, method="POST")
    with request.urlopen(req, timeout=10) as response:
        return int(response.status)


@dataclass(frozen=True)
class NtfyConfig:
    server: str = "https://ntfy.sh"
    topic: str = ""
    title: str = "Agentic approval needed"
    enabled: bool = False
    web_url: str = "http://127.0.0.1:8765"


class NtfyChannel:
    def __init__(
        self,
        config: NtfyConfig,
        *,
        transport: Transport | None = None,
    ):
        self.config = config
        self.transport = transport or _urllib_transport

    def send_approval_request(self, approval: ApprovalRequest) -> bool:
        body = (
            f"Approval required: {approval.capability}\n"
            f"{approval.reason}\n"
            f"{self.config.web_url.rstrip('/')}/"
        )
        return self.send_text(title=self.config.title, body=body, tags="warning")

    def send_text(self, *, title: str, body: str, tags: str = "") -> bool:
        if not self.config.enabled or not self.config.topic:
            return False
        url = f"{self.config.server.rstrip('/')}/{self.config.topic}"
        headers = {"Title": title}
        if tags:
            headers["Tags"] = tags
        try:
            status = self.transport(url, body.encode("utf-8"), headers)
        except URLError:
            return False
        return 200 <= status < 300
