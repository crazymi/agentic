from __future__ import annotations

from typing import Any


def source_strategy_tuning_request(
    *,
    workflow_id: str,
    run_id: str,
    reports: list[dict[str, Any]],
) -> Any:
    from agentic.tooling import ToolingKind, ToolingRequest

    return ToolingRequest(
        workflow_id=workflow_id,
        capability="source:strategy_tuning",
        kind=ToolingKind.RUNTIME,
        action="revise_source_strategy",
        resource="source_collection",
        reason="source quality gate failed before report creation",
        suggested_module="agentic/sources/",
        priority=1,
        payload={
            "run_id": run_id,
            "quality_reports": reports,
            "candidate_actions": _candidate_actions(reports),
            "agent_review_prompt": _agent_review_prompt(reports),
            "approval_required_before_activation": False,
        },
    )


def _candidate_actions(reports: list[dict[str, Any]]) -> list[str]:
    reasons = {reason for report in reports for reason in report.get("reasons", [])}
    actions: list[str] = []
    if "navigation_like_items" in reasons:
        actions.append("revise_extraction_filters")
        actions.append("exclude_navigation_text")
    if "off_source_path_items" in reasons:
        actions.append("constrain_links_to_source_path")
    if "short_text_items" in reasons or "too_few_items" in reasons:
        actions.append("increase_min_text_chars_or_select_richer_elements")
    if "duplicate_text_items" in reasons:
        actions.append("revise_dedupe_or_collect_recent_window")
    actions.append("consider_browser_or_api_connector_if_static_html_is_insufficient")
    return _unique(actions)


def _agent_review_prompt(reports: list[dict[str, Any]]) -> str:
    examples: list[str] = []
    for report in reports:
        for example in report.get("examples", []):
            if len(examples) >= 5:
                break
            examples.append(str(example))
    reason_text = ", ".join(
        sorted({reason for report in reports for reason in report.get("reasons", [])})
    )
    example_text = "; ".join(examples) if examples else "none"
    return (
        "Source quality failed. Review the quality evidence and propose a revised "
        "source collection strategy, not a bespoke crawler. Preserve the WorkflowSpec "
        f"shape. Reasons: {reason_text or 'unknown'}. Examples: {example_text}"
    )


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
