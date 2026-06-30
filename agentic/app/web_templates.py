from __future__ import annotations

from html import escape
from typing import Any


def render_home(
    *,
    messages: list[dict[str, Any]],
    approvals: list[dict[str, Any]],
    tasks: list[dict[str, Any]] | None = None,
    traces: list[dict[str, Any]],
) -> str:
    message_items = "\n".join(
        f"<li><strong>{escape(str(item.get('role', 'system')))}:</strong> "
        f"{escape(str(item.get('text', '')))}</li>"
        for item in messages[-20:]
    )
    approval_items = "\n".join(_approval_item(item) for item in approvals)
    task_items = "\n".join(_task_item(item) for item in (tasks or []))
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
    <h2>Recent Trace</h2>
    <ul>{trace_items}</ul>
  </section>
</main>
</body>
</html>"""


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
