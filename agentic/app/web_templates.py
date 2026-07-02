from __future__ import annotations

from html import escape
from typing import Any


def render_home(
    *,
    messages: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    tasks: list[dict[str, Any]] | None = None,
    workflows: list[dict[str, Any]] | None = None,
    workflow_runs: list[dict[str, Any]] | None = None,
    planning_sessions: list[dict[str, Any]] | None = None,
    session_logs: list[dict[str, Any]] | None = None,
    tooling_requests: list[dict[str, Any]] | None = None,
    skill_proposals: list[dict[str, Any]] | None = None,
    deliveries: list[dict[str, Any]] | None = None,
    daemon: dict[str, Any] | None = None,
    health: dict[str, Any] | None = None,
    traces: list[dict[str, Any]],
) -> str:
    message_items = "\n".join(
        f"<li><strong>{escape(str(item.get('role', 'system')))}:</strong> "
        f"{escape(str(item.get('text', '')))}</li>"
        for item in messages[-20:]
    )
    approval_items = "\n".join(_approval_item(item) for item in approvals)
    task_items = "\n".join(_task_item(item) for item in (tasks or []))
    workflow_items = "\n".join(_workflow_item(item) for item in (workflows or []))
    workflow_run_items = "\n".join(_workflow_run_item(item) for item in (workflow_runs or []))
    planning_items = "\n".join(_planning_session_item(item) for item in (planning_sessions or []))
    session_log_items = "\n".join(_session_log_item(item) for item in (session_logs or []))
    tooling_items = "\n".join(_tooling_item(item) for item in (tooling_requests or []))
    skill_proposal_items = "\n".join(_skill_proposal_item(item) for item in (skill_proposals or []))
    delivery_items = "\n".join(_delivery_item(item) for item in (deliveries or []))
    health_panel = _health_panel(health)
    daemon_panel = _daemon_panel(daemon)
    trace_items = "\n".join(
        f"<li><code>{escape(str(item.get('event_type', '')))}</code></li>"
        for item in traces[-20:]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>agentic</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 0; background: #f7f7f4; color: #171717; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 20px; }}
    section {{ margin: 18px 0; padding: 16px; background: #fff; border: 1px solid #ddd; border-radius: 8px; }}
    textarea {{ width: 100%; min-height: 90px; box-sizing: border-box; font: inherit; }}
    button {{ padding: 8px 12px; margin-top: 8px; }}
    li {{ margin: 8px 0; }}
    .row {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  </style>
</head>
<body>
<main>
  <h1>agentic</h1>
  <section>
    <h2>Ops Health</h2>
    {health_panel}
  </section>
  <section>
    <h2>Runtime Daemon</h2>
    {daemon_panel}
  </section>
  <section>
    <h2>Chat</h2>
    <form action="/messages" method="post">
      <textarea name="message" placeholder="Send a message to the local harness"></textarea>
      <br>
      <button type="submit">Send</button>
    </form>
    <ul>{message_items}</ul>
  </section>
  <section>
    <h2>Pending Approvals</h2>
    <ul>{approval_items or "<li>No pending approvals</li>"}</ul>
  </section>
  <section>
    <h2>Tasks</h2>
    <ul>{task_items or "<li>No tasks yet</li>"}</ul>
  </section>
  <section>
    <h2>Workflows</h2>
    <form action="/sources/web" method="post">
      <input name="name" placeholder="Source name">
      <input name="url" placeholder="https://example.com/list">
      <input name="aliases" placeholder="aliases, comma separated">
      <button type="submit">Add Web Source</button>
    </form>
    <form action="/workflows/design" method="post">
      <textarea name="message" placeholder="Describe a workflow to design"></textarea>
      <br>
      <button type="submit">Design Workflow</button>
    </form>
    <ul>{workflow_items or "<li>No workflows yet</li>"}</ul>
  </section>
  <section>
    <h2>Harness Probe</h2>
    <form action="/probes/workflow-builder" method="post">
      <textarea name="request">반복 자동화 워크플로우 만들어줘</textarea>
      <textarea name="answers">커뮤니티 웹 페이지를 소스로 쓰고, 필요한 경우 에이전트가 HTTP/API/browser/script 중 적절한 수집 전략을 선택하게 해.
1분마다 수집하고 1시간마다 분석해서 웹 보고서와 ntfy 알림으로 알려줘.</textarea>
      <br>
      <button type="submit">Run Workflow Probe</button>
    </form>
  </section>
  <section>
    <h2>Planning Sessions</h2>
    <ul>{planning_items or "<li>No planning sessions yet</li>"}</ul>
  </section>
  <section>
    <h2>Session Logs</h2>
    <ul>{session_log_items or "<li>No session logs yet</li>"}</ul>
  </section>
  <section>
    <h2>Tooling Backlog</h2>
    <ul>{tooling_items or "<li>No tooling requests yet</li>"}</ul>
  </section>
  <section>
    <h2>Skill Proposals</h2>
    <ul>{skill_proposal_items or "<li>No skill proposals yet</li>"}</ul>
  </section>
  <section>
    <h2>Workflow Runs</h2>
    <ul>{workflow_run_items or "<li>No workflow runs yet</li>"}</ul>
  </section>
  <section>
    <h2>Deliveries</h2>
    <ul>{delivery_items or "<li>No deliveries yet</li>"}</ul>
  </section>
  <section>
    <h2>Recent Trace</h2>
    <ul>{trace_items}</ul>
  </section>
</main>
</body>
</html>"""


def _health_panel(health: dict[str, Any] | None) -> str:
    if not health:
        return "<p>Health monitor is not configured.</p>"
    status = escape(str(health.get("status", "unknown")))
    uptime = escape(str(round(float(health.get("uptime_seconds") or 0), 1)))
    warnings = health.get("warnings") or []
    failures = health.get("recent_failures") or []
    components = health.get("components") or {}
    component_items = "\n".join(
        f"<li><strong>{escape(str(name))}</strong>: {escape(str(value.get('status', 'unknown')))}</li>"
        for name, value in components.items()
        if isinstance(value, dict)
    )
    warning_items = "\n".join(f"<li>{escape(str(item))}</li>" for item in warnings)
    failure_items = "\n".join(
        f"<li><code>{escape(str(item.get('type', 'failure')))}</code> "
        f"{escape(str(item.get('id', '')))} {escape(str(item.get('status', '')))}</li>"
        for item in failures[:5]
        if isinstance(item, dict)
    )
    return f"""
<p><strong>{status}</strong> uptime: {uptime}s</p>
<ul>{component_items or "<li>No components</li>"}</ul>
<h3>Warnings</h3>
<ul>{warning_items or "<li>No warnings</li>"}</ul>
<h3>Recent Failures</h3>
<ul>{failure_items or "<li>No recent failures</li>"}</ul>
<form action="/ops/health/export" method="post">
  <button type="submit">Export Health Snapshot</button>
</form>"""


def _daemon_panel(daemon: dict[str, Any] | None) -> str:
    if not daemon:
        return "<p>Runtime daemon is not configured.</p>"
    running = escape(str(daemon.get("running", False)))
    tick_count = escape(str(daemon.get("tick_count", 0)))
    last_tick_at = escape(str(daemon.get("last_tick_at") or ""))
    last_error = daemon.get("last_error") or {}
    error_text = escape(str(last_error.get("message", ""))) if isinstance(last_error, dict) else ""
    last_result = escape(str(daemon.get("last_result") or "")[:1000])
    return f"""
<p><strong>running:</strong> {running} <strong>ticks:</strong> {tick_count}</p>
<small>last tick: {last_tick_at}</small>
<p>{error_text}</p>
<pre>{last_result}</pre>
<form action="/daemon/tick" method="post">
  <button type="submit">Run Tick</button>
</form>"""


def _approval_item(item: dict[str, Any]) -> str:
    approval_id = escape(str(item.get("approval_id", "")))
    capability = escape(str(item.get("capability", "")))
    reason = escape(str(item.get("reason", "")))
    return f"""
<li>
  <strong>{capability}</strong><br>
  {reason}<br>
  <div class="row">
    <form action="/approvals/{approval_id}/approve" method="post">
      <button type="submit">Approve</button>
    </form>
    <form action="/approvals/{approval_id}/deny" method="post">
      <button type="submit">Deny</button>
    </form>
  </div>
</li>"""


def _task_item(item: dict[str, Any]) -> str:
    task_id = escape(str(item.get("task_id", "")))
    kind = escape(str(item.get("kind", "")))
    status = escape(str(item.get("status", "")))
    result = item.get("result") or {}
    error = item.get("error") or {}
    final_answer = escape(str(result.get("final_answer", ""))) if isinstance(result, dict) else ""
    error_message = escape(str(error.get("message", ""))) if isinstance(error, dict) else ""
    heartbeat = escape(str(item.get("last_heartbeat_at") or ""))
    detail = final_answer or error_message
    return f"""
<li>
  <strong>{status}</strong> <code>{task_id}</code> {kind}<br>
  {detail}<br>
  <small>heartbeat: {heartbeat}</small>
  <div class="row">
    <form action="/tasks/{task_id}/cancel" method="post">
      <button type="submit">Cancel</button>
    </form>
    <form action="/tasks/{task_id}/pause" method="post">
      <button type="submit">Pause</button>
    </form>
    <form action="/tasks/{task_id}/resume" method="post">
      <button type="submit">Resume</button>
    </form>
  </div>
</li>"""


def _workflow_item(item: dict[str, Any]) -> str:
    workflow_id = escape(str(item.get("workflow_id", "")))
    name = escape(str(item.get("name", "")))
    status = escape(str(item.get("status", "")))
    goal = escape(str(item.get("goal", "")))
    version = escape(str(item.get("version", "")))
    return f"""
<li>
  <strong>{status}</strong> <code>{workflow_id}</code> v{version}<br>
  {name}<br>
  <small>{goal}</small>
  <div class="row">
    <form action="/workflows/{workflow_id}/approve" method="post">
      <button type="submit">Approve</button>
    </form>
    <form action="/workflows/{workflow_id}/activate" method="post">
      <button type="submit">Activate</button>
    </form>
    <form action="/workflows/{workflow_id}/pause" method="post">
      <button type="submit">Pause</button>
    </form>
    <form action="/workflows/{workflow_id}/run" method="post">
      <button type="submit">Run</button>
    </form>
  </div>
</li>"""


def _workflow_run_item(item: dict[str, Any]) -> str:
    run_id = escape(str(item.get("run_id", "")))
    workflow_id = escape(str(item.get("workflow_id", "")))
    status = escape(str(item.get("status", "")))
    result = escape(str(item.get("result") or item.get("error") or ""))
    artifacts = escape(", ".join(str(value) for value in item.get("artifacts", [])))
    return f"""
<li>
  <strong>{status}</strong> <code>{run_id}</code> for <code>{workflow_id}</code><br>
  {result}<br>
  <small>artifacts: {artifacts}</small>
</li>"""


def _planning_session_item(item: dict[str, Any]) -> str:
    session_id = escape(str(item.get("session_id", "")))
    status = escape(str(item.get("status", "")))
    intent = item.get("intent") or {}
    intent_type = escape(str(intent.get("intent_type", ""))) if isinstance(intent, dict) else ""
    question = escape(str(item.get("question") or ""))
    missing = escape(", ".join(str(value) for value in item.get("missing_slots", [])))
    return f"""
<li>
  <strong>{status}</strong> <code>{session_id}</code> {intent_type}<br>
  {question or "No open question"}<br>
  <small>missing: {missing}</small>
  <form action="/planning-sessions/{session_id}/answer" method="post">
    <textarea name="answer" placeholder="Answer the current planning question"></textarea>
    <br>
    <button type="submit">Answer</button>
  </form>
</li>"""


def _session_log_item(item: dict[str, Any]) -> str:
    session_id = escape(str(item.get("session_id", "")))
    title = escape(str(item.get("title", "")))
    status = escape(str(item.get("status", "")))
    event_count = escape(str(item.get("event_count", 0)))
    metadata = item.get("metadata") or {}
    planning_id = escape(str(metadata.get("planning_session_id", ""))) if isinstance(metadata, dict) else ""
    return f"""
<li>
  <strong>{status}</strong> <code>{session_id}</code> {title}<br>
  <small>events: {event_count} planning: {planning_id}</small>
</li>"""


def _tooling_item(item: dict[str, Any]) -> str:
    tooling_id = escape(str(item.get("tooling_id", "")))
    status = escape(str(item.get("status", "")))
    kind = escape(str(item.get("kind", "")))
    capability = escape(str(item.get("capability", "")))
    reason = escape(str(item.get("reason", "")))
    module = escape(str(item.get("suggested_module", "")))
    priority = escape(str(item.get("priority", "")))
    return f"""
<li>
  <strong>{status}</strong> <code>{tooling_id}</code> {kind} p{priority}<br>
  {capability}<br>
  <small>{reason}</small><br>
  <small>module: {module}</small>
</li>"""


def _skill_proposal_item(item: dict[str, Any]) -> str:
    proposal_id = escape(str(item.get("proposal_id", "")))
    name = escape(str(item.get("target_skill_name") or item.get("name", "")))
    status = escape(str(item.get("status", "")))
    description = escape(str(item.get("description", "")))
    body = escape(str(item.get("proposal_body", ""))[:800])
    review = item.get("review") or {}
    mode = escape(str(review.get("mode", ""))) if isinstance(review, dict) else ""
    validation = (
        "ok"
        if isinstance(review, dict) and review.get("validation_ok")
        else escape(str(review.get("validation_error", "not validated"))) if isinstance(review, dict) else ""
    )
    diff = escape(str(review.get("diff", ""))[:2000]) if isinstance(review, dict) else ""
    return f"""
<li>
  <strong>{status}</strong> <code>{proposal_id}</code> {name} {mode}<br>
  {description}<br>
  <pre>{body}</pre>
  <small>validation: {validation}</small>
  <pre>{diff}</pre>
  <div class="row">
    <form action="/skills/proposals/{proposal_id}/request-apply" method="post">
      <button type="submit">Request Apply</button>
    </form>
    <form action="/skills/proposals/{proposal_id}/apply" method="post">
      <input name="approval_id" placeholder="approved approval id">
      <button type="submit">Apply</button>
    </form>
  </div>
</li>"""


def _delivery_item(item: dict[str, Any]) -> str:
    delivery_id = escape(str(item.get("delivery_id", "")))
    artifact_id = escape(str(item.get("artifact_id", "")))
    channel = escape(str(item.get("channel", "")))
    status = escape(str(item.get("status", "")))
    attempts = escape(str(item.get("attempts", "")))
    sent_at = escape(str(item.get("sent_at") or ""))
    title = escape(str(item.get("title", "")))
    body = escape(str(item.get("body", ""))[:500])
    error = item.get("error") or {}
    error_text = escape(str(error.get("message", ""))) if isinstance(error, dict) else ""
    return f"""
<li>
  <strong>{status}</strong> <code>{delivery_id}</code> {channel}<br>
  {title}<br>
  <small>artifact: {artifact_id} attempts: {attempts} sent: {sent_at}</small>
  <pre>{body}</pre>
  <small>{error_text}</small>
</li>"""
