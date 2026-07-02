from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from agentic.resources.store import ResourceRecord, ResourceStore


@dataclass(frozen=True)
class ResourceTrendSummary:
    source_count: int
    top_terms: list[tuple[str, int]]
    sample_titles: list[str]

    def to_record(self) -> dict:
        return {
            "source_count": self.source_count,
            "top_terms": [{"term": term, "count": count} for term, count in self.top_terms],
            "sample_titles": self.sample_titles,
        }


def summarize_resource_trends(
    store: ResourceStore,
    *,
    query: str = "",
    limit: int = 100,
    top_n: int = 20,
) -> ResourceTrendSummary:
    resources = store.search(query, limit=limit) if query else store.list(limit=limit)
    counter: Counter[str] = Counter()
    for resource in resources:
        counter.update(_tokens(resource.title))
        counter.update(_tokens(resource.content_text))
    return ResourceTrendSummary(
        source_count=len(resources),
        top_terms=counter.most_common(top_n),
        sample_titles=[resource.title for resource in resources[:10]],
    )


def _tokens(text: str) -> list[str]:
    tokens = re.findall(r"[0-9A-Za-z가-힣]{2,}", text.lower())
    stopwords = {
        "https",
        "http",
        "www",
        "com",
        "page",
        "board",
        "view",
    }
    return [token for token in tokens if token not in stopwords]
