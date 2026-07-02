from __future__ import annotations

from html.parser import HTMLParser
from urllib import request
from urllib.parse import urljoin

from agentic.tools.base import ToolSpec


DEFAULT_USER_AGENT = "agentic-harness/0.1 (+local personal agent)"


def web_fetch(url: str, *, timeout_s: float = 20.0, user_agent: str = DEFAULT_USER_AGENT) -> dict:
    req = request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    with request.urlopen(req, timeout=timeout_s) as response:
        body = response.read().decode("utf-8", errors="replace")
        return {
            "url": response.geturl(),
            "status": int(response.status),
            "content_type": response.headers.get("content-type", ""),
            "text": body,
            "text_chars": len(body),
        }


def html_extract_links(
    html: str,
    *,
    base_url: str = "",
    href_contains: str = "",
    limit: int = 20,
) -> dict:
    parser = _LinkParser(base_url=base_url)
    parser.feed(html)
    links = parser.links
    if href_contains:
        links = [link for link in links if href_contains in link["href"]]
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for link in links:
        key = (link["href"], link["text"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(link)
        if len(deduped) >= limit:
            break
    return {"links": deduped, "count": len(deduped)}


class _LinkParser(HTMLParser):
    def __init__(self, *, base_url: str = ""):
        super().__init__()
        self.base_url = base_url
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = {key: value or "" for key, value in attrs}
        href = attrs_dict.get("href", "")
        if not href:
            return
        self._href = urljoin(self.base_url, href) if self.base_url else href
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return
        text = " ".join(part.strip() for part in self._text if part.strip())
        if text:
            self.links.append({"href": self._href, "text": text})
        self._href = None
        self._text = []


WEB_FETCH_TOOL = ToolSpec(
    name="web_fetch",
    description="Fetch a real URL over HTTP(S) and return status, content type, and text.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "timeout_s": {"type": "number"},
            "user_agent": {"type": "string"},
        },
        "required": ["url"],
    },
    fn=web_fetch,
)


HTML_EXTRACT_LINKS_TOOL = ToolSpec(
    name="html_extract_links",
    description="Extract links from HTML text with optional href substring filtering.",
    parameters={
        "type": "object",
        "properties": {
            "html": {"type": "string"},
            "base_url": {"type": "string"},
            "href_contains": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["html"],
    },
    fn=html_extract_links,
)
