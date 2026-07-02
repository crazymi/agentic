from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib import request
from urllib.parse import unquote, urljoin, urlparse

from agentic.resources.store import ResourceKind, ResourceRecord, ResourceStore
from agentic.sources.models import SourceCollector, SourceDefinition, SourceItem, SourceKind
from agentic.sources.quality import SourceQualityReport, evaluate_source_quality, quality_thresholds
from agentic.sources.store import SourceStore


@dataclass(frozen=True)
class SourceCollectionResult:
    source_id: str
    collected_count: int
    new_count: int
    resource_ids: list[str]
    recent_resource_ids: list[str]
    quality: SourceQualityReport


class LocalFileSourceCollector:
    def collect(self, source: SourceDefinition) -> list[SourceItem]:
        path = _locator_to_path(source.locator)
        if not path.exists():
            raise FileNotFoundError(f"source file does not exist: {path}")
        if path.is_dir():
            raise IsADirectoryError(f"source locator must be a file: {path}")
        if path.suffix.lower() == ".jsonl":
            return self._collect_jsonl(source, path)
        text = path.read_text(encoding="utf-8")
        return [
            SourceItem(
                source_id=source.source_id,
                uri=path.as_uri(),
                title=source.name,
                content_text=text,
                metadata={"collector": "local_file", "path": str(path)},
            )
        ]

    def _collect_jsonl(self, source: SourceDefinition, path: Path) -> list[SourceItem]:
        items: list[SourceItem] = []
        with path.open("r", encoding="utf-8") as handle:
            for index, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                record = json.loads(stripped)
                if not isinstance(record, dict):
                    raise ValueError(f"jsonl source line must be an object: {path}:{index}")
                uri = str(
                    record.get("uri")
                    or record.get("url")
                    or record.get("message_id")
                    or f"{path.as_uri()}#{index}"
                )
                title = str(record.get("title") or record.get("subject") or source.name)
                content_text = str(
                    record.get("content_text")
                    or record.get("body_text")
                    or record.get("text")
                    or record.get("body")
                    or ""
                )
                metadata = {
                    key: value
                    for key, value in record.items()
                    if key not in {"content_text", "body_text", "text", "body"}
                }
                metadata["collector"] = "local_file"
                metadata["path"] = str(path)
                items.append(
                    SourceItem(
                        source_id=source.source_id,
                        uri=uri,
                        title=title,
                        content_text=content_text,
                        metadata=metadata,
                    )
                )
        return items


class RepoStateSourceCollector:
    def collect(self, source: SourceDefinition) -> list[SourceItem]:
        root = _locator_to_path(source.locator)
        if not root.exists():
            raise FileNotFoundError(f"repo source path does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"repo source must be a directory: {root}")
        status = _run_git(root, ["status", "--short"])
        files = _run_git(root, ["ls-files"])
        content = "\n".join(
            [
                f"Repository: {root}",
                "",
                "Git status:",
                status or "(clean)",
                "",
                "Tracked files:",
                files,
            ]
        )
        return [
            SourceItem(
                source_id=source.source_id,
                uri=root.as_uri(),
                title=f"Repository state: {root.name}",
                content_text=content,
                metadata={"collector": "repo_state", "path": str(root)},
            )
        ]


class WebPageSourceCollector:
    def collect(self, source: SourceDefinition) -> list[SourceItem]:
        response = _fetch_url(source.locator)
        html = response["text"]
        extraction = dict(source.metadata.get("extract") or {})
        if extraction:
            items = self._extract_items(source, html, extraction)
            if items:
                return items
        return [
            SourceItem(
                source_id=source.source_id,
                uri=response["url"],
                title=source.name,
                content_text=html,
                metadata={
                    "collector": "web_page",
                    "status": response["status"],
                    "content_type": response["content_type"],
                    "extraction": "full_page",
                },
            )
        ]

    def _extract_items(
        self,
        source: SourceDefinition,
        html: str,
        extraction: dict,
    ) -> list[SourceItem]:
        parser = _AnchorParser(base_url=source.locator)
        parser.feed(html)
        href_contains = [str(item) for item in extraction.get("href_contains") or []]
        href_contains_all = [str(item) for item in extraction.get("href_contains_all") or []]
        href_excludes = [str(item) for item in extraction.get("href_excludes") or []]
        text_excludes = [str(item) for item in extraction.get("text_excludes") or []]
        text_exclude_regexes = [re.compile(str(item)) for item in extraction.get("text_exclude_regexes") or []]
        min_text_chars = int(extraction.get("min_text_chars") or 0)
        limit = int(extraction.get("limit") or 20)
        items: list[SourceItem] = []
        seen: set[str] = set()
        for link in parser.links:
            href = link["href"]
            title = link["text"]
            if href_contains and not any(fragment in href for fragment in href_contains):
                continue
            if href_contains_all and not all(fragment in href for fragment in href_contains_all):
                continue
            if href_excludes and any(fragment in href for fragment in href_excludes):
                continue
            if text_excludes and any(fragment in title for fragment in text_excludes):
                continue
            if min_text_chars and len(title) < min_text_chars:
                continue
            if text_exclude_regexes and any(pattern.search(title) for pattern in text_exclude_regexes):
                continue
            if href in seen:
                continue
            seen.add(href)
            items.append(
                SourceItem(
                    source_id=source.source_id,
                    uri=href,
                    title=title,
                    content_text=title,
                    metadata={
                        "collector": "web_page",
                        "extraction": "links",
                        "source_url": source.locator,
                    },
                )
            )
            if len(items) >= limit:
                break
        return items


class SourceRuntime:
    def __init__(
        self,
        *,
        source_store: SourceStore,
        resource_store: ResourceStore,
        collectors: dict[SourceKind, SourceCollector] | None = None,
    ):
        self.source_store = source_store
        self.resource_store = resource_store
        self.collectors = collectors or {
            SourceKind.LOCAL_FILE: LocalFileSourceCollector(),
            SourceKind.MAIL: LocalFileSourceCollector(),
            SourceKind.FEED: LocalFileSourceCollector(),
            SourceKind.WEB_PAGE: WebPageSourceCollector(),
            SourceKind.BROWSER_PAGE: LocalFileSourceCollector(),
            SourceKind.REPO_STATE: RepoStateSourceCollector(),
        }

    def collect(self, source_id: str) -> SourceCollectionResult:
        source = self.source_store.get_source(source_id)
        if not source.enabled:
            raise ValueError(f"source is not enabled: {source_id}")
        collector = self.collectors.get(source.kind)
        if collector is None:
            raise ValueError(f"no collector registered for source kind: {source.kind}")
        items = collector.collect(source)
        min_score, min_items = quality_thresholds(source.metadata)
        quality = evaluate_source_quality(
            items,
            source_url=source.locator,
            min_score=min_score,
            min_items=min_items,
        )
        resource_ids: list[str] = []
        new_count = 0
        for item in items:
            stored, created = self.source_store.add_item_dedup(item)
            if not created:
                continue
            new_count += 1
            resource = self.resource_store.add(_resource_from_source_item(source, stored))
            resource_ids.append(resource.resource_id)
        recent_resource_ids = [
            resource.resource_id
            for resource in self.resource_store.list_by_source(
                source.source_id,
                limit=max(len(items), len(resource_ids), 20),
            )
        ]
        return SourceCollectionResult(
            source_id=source.source_id,
            collected_count=len(items),
            new_count=new_count,
            resource_ids=resource_ids,
            recent_resource_ids=recent_resource_ids,
            quality=quality,
        )


def _resource_from_source_item(source: SourceDefinition, item: SourceItem) -> ResourceRecord:
    return ResourceRecord(
        uri=item.uri,
        kind=_resource_kind(source.kind),
        title=item.title,
        content_text=item.content_text,
        source_connector=f"source:{source.kind.value}",
        metadata={
            "source_id": source.source_id,
            "source_item_id": item.item_id,
            "fingerprint": item.fingerprint,
        },
    )


def _resource_kind(kind: SourceKind) -> ResourceKind:
    if kind == SourceKind.MAIL:
        return ResourceKind.EMAIL
    if kind == SourceKind.LOCAL_FILE:
        return ResourceKind.FILE
    if kind == SourceKind.BROWSER_PAGE:
        return ResourceKind.WEBPAGE
    if kind == SourceKind.WEB_PAGE:
        return ResourceKind.WEBPAGE
    if kind == SourceKind.FEED:
        return ResourceKind.WEBPAGE
    if kind == SourceKind.REPO_STATE:
        return ResourceKind.FILE
    return ResourceKind.WEBPAGE


def _locator_to_path(locator: str) -> Path:
    parsed = urlparse(locator)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path)).expanduser().resolve()
    return Path(locator).expanduser().resolve()


def _run_git(root: Path, args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"git command timed out: {' '.join(args)}") from exc
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"git command failed: {' '.join(args)}: {message}")
    return completed.stdout.strip()


def _fetch_url(url: str) -> dict[str, str | int]:
    req = request.Request(
        url,
        headers={
            "User-Agent": "agentic-source-runtime/0.1 (+local personal agent)",
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    with request.urlopen(req, timeout=20) as response:
        status = getattr(response, "status", None) or response.getcode() or 200
        return {
            "url": response.geturl(),
            "status": int(status),
            "content_type": response.headers.get("content-type", ""),
            "text": response.read().decode("utf-8", errors="replace"),
        }


class _AnchorParser(HTMLParser):
    def __init__(self, *, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = {key: value or "" for key, value in attrs}
        href = attrs_dict.get("href")
        if not href:
            return
        self._href = urljoin(self.base_url, href)
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
