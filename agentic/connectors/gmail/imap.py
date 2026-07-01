from __future__ import annotations

import imaplib
from email.parser import BytesParser
from email.policy import default

from agentic.connectors.gmail.models import EmailMessage


class GmailImapConnector:
    connector_id = "gmail-imap"

    def __init__(
        self,
        *,
        username: str,
        app_password: str,
        host: str = "imap.gmail.com",
        mailbox: str = "INBOX",
    ):
        if not username:
            raise ValueError("username must not be empty")
        if not app_password:
            raise ValueError("app_password must not be empty")
        self.username = username
        self.app_password = app_password
        self.host = host
        self.mailbox = mailbox

    def search_newsletters(self, *, query: str = "WSJ", limit: int = 10) -> list[EmailMessage]:
        with imaplib.IMAP4_SSL(self.host, timeout=20) as client:
            client.login(self.username, self.app_password)
            client.select(self.mailbox, readonly=True)
            status, ids = client.search(None, "OR", "SUBJECT", f'"{query}"', "FROM", '"wsj"')
            if status != "OK":
                raise RuntimeError(f"gmail imap search failed: {status}")
            message_ids = ids[0].split()[-limit:]
            messages: list[EmailMessage] = []
            for message_id in message_ids:
                fetch_status, data = client.fetch(message_id, "(RFC822)")
                if fetch_status != "OK":
                    continue
                raw = next((part[1] for part in data if isinstance(part, tuple)), b"")
                if not raw:
                    continue
                messages.append(_parse_message(message_id.decode("ascii", errors="ignore"), raw))
            return messages


def _parse_message(message_id: str, raw: bytes) -> EmailMessage:
    parsed = BytesParser(policy=default).parsebytes(raw)
    sender = str(parsed.get("from", ""))
    subject = str(parsed.get("subject", ""))
    received_at = str(parsed.get("date", ""))
    body = ""
    if parsed.is_multipart():
        for part in parsed.walk():
            if part.get_content_type() == "text/plain":
                body = str(part.get_content())
                break
    else:
        body = str(parsed.get_content())
    return EmailMessage(
        message_id=message_id,
        subject=subject,
        sender=sender,
        received_at=received_at,
        body_text=body,
        labels=["gmail", "newsletter"],
        metadata={"connector": GmailImapConnector.connector_id},
    )
