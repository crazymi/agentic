from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from html import unescape
import base64
from pathlib import Path
from typing import Any
from urllib import parse, request

from agentic.config.settings import load_dotenv
from agentic.tools.base import ToolSpec


DEFAULT_PROVIDER = "duckduckgo_html"
DEFAULT_COUNT = 5
MAX_COUNT = 10


@dataclass(frozen=True)
class SearchProviderConfig:
    provider: str
    api_key: str = ""
    base_url: str = ""


def web_search(
    query: str,
    *,
    provider: str = "",
    count: int = DEFAULT_COUNT,
    country: str = "",
    language: str = "",
    freshness: str = "",
    include_domains: list[str] | None = None,
) -> dict[str, Any]:
    selected = _provider_config(provider)
    normalized_count = max(1, min(int(count or DEFAULT_COUNT), MAX_COUNT))
    actual_provider = selected.provider
    if selected.provider == "brave":
        payload = _brave_search(selected, query, normalized_count, country, language, freshness)
    elif selected.provider == "tavily":
        payload = _tavily_search(selected, query, normalized_count, include_domains or [])
    elif selected.provider == "exa":
        payload = _exa_search(selected, query, normalized_count, include_domains or [])
    elif selected.provider == "serper":
        payload = _serper_search(selected, query, normalized_count, country, language)
    elif selected.provider == "searxng":
        payload = _searxng_search(selected, query, normalized_count, language)
    elif selected.provider == "duckduckgo_html":
        payload = _duckduckgo_html_search(selected, query, normalized_count)
        if not payload:
            actual_provider = "bing_html"
            payload = _bing_html_search(SearchProviderConfig("bing_html", base_url="https://www.bing.com/search"), query, normalized_count)
    elif selected.provider == "bing_html":
        payload = _bing_html_search(selected, query, normalized_count)
    else:
        raise ValueError(f"unsupported web_search provider: {selected.provider}")
    return {
        "provider": actual_provider,
        "query": query,
        "results": payload,
        "count": len(payload),
    }


def _provider_config(provider: str) -> SearchProviderConfig:
    load_dotenv(Path.cwd() / ".env")
    selected = (provider or os.environ.get("AGENTIC_WEB_SEARCH_PROVIDER") or DEFAULT_PROVIDER).lower()
    if selected == "brave":
        return SearchProviderConfig(selected, _require_env("BRAVE_API_KEY", selected))
    if selected == "tavily":
        return SearchProviderConfig(selected, _require_env("TAVILY_API_KEY", selected))
    if selected == "exa":
        return SearchProviderConfig(selected, _require_env("EXA_API_KEY", selected))
    if selected == "serper":
        return SearchProviderConfig(selected, _require_env("SERPER_API_KEY", selected))
    if selected == "searxng":
        return SearchProviderConfig(
            selected,
            base_url=os.environ.get("SEARXNG_BASE_URL", "http://127.0.0.1:8080"),
        )
    if selected in {"duckduckgo_html", "ddg_html", "ddg"}:
        return SearchProviderConfig("duckduckgo_html", base_url="https://duckduckgo.com/html/")
    if selected in {"bing_html", "bing"}:
        return SearchProviderConfig("bing_html", base_url="https://www.bing.com/search")
    return SearchProviderConfig(selected)


def _require_env(name: str, provider: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing_api_key: set {name} to use web_search provider '{provider}'")
    return value


def _brave_search(
    config: SearchProviderConfig,
    query: str,
    count: int,
    country: str,
    language: str,
    freshness: str,
) -> list[dict[str, Any]]:
    params = {"q": query, "count": str(count)}
    if country:
        params["country"] = country
    if language:
        params["search_lang"] = language
    if freshness:
        params["freshness"] = _brave_freshness(freshness)
    url = "https://api.search.brave.com/res/v1/web/search?" + parse.urlencode(params)
    data = _get_json(url, {"X-Subscription-Token": config.api_key, "Accept": "application/json"})
    return [
        _result(
            title=item.get("title"),
            url=item.get("url"),
            snippet=item.get("description"),
            source="brave",
            published_at=item.get("age"),
        )
        for item in (data.get("web", {}) or {}).get("results", [])[:count]
    ]


def _tavily_search(
    config: SearchProviderConfig,
    query: str,
    count: int,
    include_domains: list[str],
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "api_key": config.api_key,
        "query": query,
        "max_results": count,
        "search_depth": "basic",
    }
    if include_domains:
        body["include_domains"] = include_domains
    data = _post_json("https://api.tavily.com/search", body, {})
    return [
        _result(
            title=item.get("title"),
            url=item.get("url"),
            snippet=item.get("content"),
            source="tavily",
            score=item.get("score"),
        )
        for item in data.get("results", [])[:count]
    ]


def _exa_search(
    config: SearchProviderConfig,
    query: str,
    count: int,
    include_domains: list[str],
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"query": query, "numResults": count}
    if include_domains:
        body["includeDomains"] = include_domains
    data = _post_json("https://api.exa.ai/search", body, {"x-api-key": config.api_key})
    return [
        _result(
            title=item.get("title"),
            url=item.get("url"),
            snippet=item.get("text") or item.get("summary"),
            source="exa",
            published_at=item.get("publishedDate"),
            score=item.get("score"),
        )
        for item in data.get("results", [])[:count]
    ]


def _serper_search(
    config: SearchProviderConfig,
    query: str,
    count: int,
    country: str,
    language: str,
) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"q": query, "num": count}
    if country:
        body["gl"] = country.lower()
    if language:
        body["hl"] = language.lower()
    data = _post_json("https://google.serper.dev/search", body, {"X-API-KEY": config.api_key})
    return [
        _result(
            title=item.get("title"),
            url=item.get("link"),
            snippet=item.get("snippet"),
            source="serper",
            published_at=item.get("date"),
        )
        for item in data.get("organic", [])[:count]
    ]


def _searxng_search(
    config: SearchProviderConfig,
    query: str,
    count: int,
    language: str,
) -> list[dict[str, Any]]:
    params = {"q": query, "format": "json"}
    if language:
        params["language"] = language
    url = config.base_url.rstrip("/") + "/search?" + parse.urlencode(params)
    data = _get_json(url, {"Accept": "application/json"})
    return [
        _result(
            title=item.get("title"),
            url=item.get("url"),
            snippet=item.get("content"),
            source="searxng",
            score=item.get("score"),
        )
        for item in data.get("results", [])[:count]
    ]


def _duckduckgo_html_search(
    config: SearchProviderConfig,
    query: str,
    count: int,
) -> list[dict[str, Any]]:
    params = {"q": query}
    url = config.base_url + "?" + parse.urlencode(params)
    html = _get_text(
        url,
        {
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Mozilla/5.0 AgenticHarness/1.0",
        },
    )
    return _parse_duckduckgo_html(html, count)


def _bing_html_search(
    config: SearchProviderConfig,
    query: str,
    count: int,
) -> list[dict[str, Any]]:
    params = {"q": query}
    url = config.base_url + "?" + parse.urlencode(params)
    html = _get_text(
        url,
        {
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "Mozilla/5.0 AgenticHarness/1.0",
        },
    )
    return _parse_bing_html(html, count)


def _parse_duckduckgo_html(html: str, count: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    blocks = re.split(r'<div[^>]+class="(?=[^"]*\bresult\b)[^"]*"[^>]*>', html)
    for block in blocks:
        match = re.search(
            r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            continue
        raw_url = unescape(match.group(1))
        title = _strip_tags(match.group(2))
        snippet_match = re.search(
            r'<[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</[^>]+>',
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        snippet = ""
        if snippet_match:
            snippet = _strip_tags(snippet_match.group(1) or "")
        parsed = parse.urlparse(raw_url)
        if parsed.path.startswith("/l/"):
            qs = parse.parse_qs(parsed.query)
            raw_url = qs.get("uddg", [raw_url])[0]
        if raw_url and title:
            results.append(_result(title=title, url=raw_url, snippet=snippet, source="duckduckgo_html"))
        if len(results) >= count:
            break
    return results


def _parse_bing_html(html: str, count: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    blocks = re.split(r'<li[^>]+class="[^"]*\bb_algo\b[^"]*"[^>]*>', html)
    for block in blocks:
        match = re.search(
            r"<h2[^>]*>\s*<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>\s*</h2>",
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            continue
        raw_url = _decode_bing_url(unescape(match.group(1)))
        title = _strip_tags(match.group(2))
        snippet = ""
        snippet_match = re.search(
            r'<p[^>]*>(.*?)</p>',
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if snippet_match:
            snippet = _strip_tags(snippet_match.group(1) or "")
        if raw_url and title and raw_url.startswith(("http://", "https://")):
            results.append(_result(title=title, url=raw_url, snippet=snippet, source="bing_html"))
        if len(results) >= count:
            break
    return results


def _decode_bing_url(raw_url: str) -> str:
    parsed = parse.urlparse(raw_url)
    if parsed.netloc.endswith("bing.com") and parsed.path.startswith("/ck/"):
        encoded = parse.parse_qs(parsed.query).get("u", [""])[0]
        if encoded.startswith("a1"):
            token = encoded[2:]
            padding = "=" * (-len(token) % 4)
            try:
                return base64.urlsafe_b64decode((token + padding).encode("ascii")).decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                return raw_url
    return raw_url


def _strip_tags(value: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescape(no_tags).split())


def _brave_freshness(value: str) -> str:
    mapping = {"day": "pd", "week": "pw", "month": "pm", "year": "py"}
    return mapping.get(value.lower(), value)


def _result(
    *,
    title: Any,
    url: Any,
    snippet: Any,
    source: str,
    published_at: Any = None,
    score: Any = None,
) -> dict[str, Any]:
    result = {
        "title": str(title or ""),
        "url": str(url or ""),
        "snippet": str(snippet or ""),
        "source": source,
    }
    if published_at:
        result["published_at"] = str(published_at)
    if score is not None:
        result["score"] = score
    return result


def _get_json(url: str, headers: dict[str, str], *, timeout_s: float = 20.0) -> dict[str, Any]:
    req = request.Request(url, headers=headers, method="GET")
    with request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _get_text(url: str, headers: dict[str, str], *, timeout_s: float = 20.0) -> str:
    req = request.Request(url, headers=headers, method="GET")
    with request.urlopen(req, timeout=timeout_s) as response:
        return response.read().decode("utf-8", errors="replace")


def _post_json(
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    *,
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json", **headers},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


WEB_SEARCH_TOOL = ToolSpec(
    name="web_search",
    description=(
        "Search the web through an external provider. Supports providers: brave, tavily, exa, "
        "serper, searxng, duckduckgo_html, and bing_html."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "provider": {
                "type": "string",
                "enum": ["brave", "tavily", "exa", "serper", "searxng", "duckduckgo_html", "bing_html"],
            },
            "count": {"type": "integer"},
            "country": {"type": "string"},
            "language": {"type": "string"},
            "freshness": {"type": "string"},
            "include_domains": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["query"],
    },
    fn=web_search,
)
