# Milestone 2 Plan: Channel And Approval Core

Milestone 2 makes the local harness reachable from desktop/mobile through a simple FastAPI web UI and adds a deterministic approval gate before sensitive tool execution.

Decisions:

- Web stack: FastAPI plus uvicorn
- Mobile path: local web page for chat/approvals, ntfy for push notifications
- Persistence: JSONL-backed approval store
- Scope: no public auth, no multi-user deployment, no marketplace, no MCP implementation
- Existing Phase 1 CLI/full-loop behavior must continue to pass

## Acceptance

- User can open a local web page and send a message to the harness.
- Runtime records inbound channel events in trace.
- Sensitive tool requests create approval requests instead of executing immediately.
- User can approve or deny from the web UI.
- Denied approval blocks tool execution.
- Approved approval allows execution of the original stored tool call.
- Pending approvals survive process restart through JSONL rebuild.
- ntfy can send mobile push notifications when approval is needed.

## Parallel Work Packages

### M2-A: Event And Channel Core

Owned files:

```text
agentic/runtime/events.py
agentic/channels/base.py
agentic/channels/__init__.py
evals/test_milestone2_events.py
```

Review criteria:

- Event IDs and message IDs are non-empty and stable.
- Payload validation rejects non-JSON-compatible data.
- Trace records `channel_message_received`.
- No FastAPI dependency is introduced here.

### M2-B: Approval Domain And Store

Owned files:

```text
agentic/approvals/models.py
agentic/approvals/store.py
agentic/approvals/service.py
agentic/approvals/__init__.py
evals/test_milestone2_approvals.py
```

Review criteria:

- Approval statuses are `pending`, `approved`, `denied`, `expired`.
- Invalid transitions fail clearly.
- JSONL rebuild returns latest state per approval ID.
- Approval request and decision events are traced.

### M2-C: Policy Gate

Owned files:

```text
agentic/policy/rules.py
agentic/policy/engine.py
agentic/policy/__init__.py
evals/test_milestone2_policy.py
```

Review criteria:

- Policy is deterministic Python code.
- `tool:add` is allowed.
- known sensitive tools require approval.
- denied capabilities are blocked.
- unknown tool capabilities require approval.

### M2-D: Tool Bridge Approval Integration

Owned files:

```text
agentic/runtime/approval_bridge.py
evals/test_milestone2_tool_approval_bridge.py
```

Review criteria:

- Existing `ToolBridge` behavior remains unchanged.
- Allowed tools execute immediately.
- Approval-required tools create an approval and do not execute.
- Denied policy blocks without creating an approval.
- Approved stored tool calls can execute later.

### M2-E: ntfy Channel

Owned files:

```text
agentic/channels/ntfy.py
evals/test_milestone2_ntfy_channel.py
```

Review criteria:

- Tests use injected fake transport and do not hit the network.
- Disabled or missing topic means no-op.
- Notification body includes capability, reason, and local web URL.
- No secrets are logged or traced.

### M2-F: FastAPI Web Server

Owned files:

```text
agentic/app/server.py
agentic/app/web_templates.py
evals/test_milestone2_web_server.py
pyproject.toml
```

Review criteria:

- Routes exist: `GET /`, `POST /messages`, `GET /approvals`, approval approve/deny routes, `GET /health`.
- UI is plain HTML and usable on mobile.
- ASGI route tests cover the routes without requiring a live socket.
- No frontend build tool is required.

### M2-G: Channel Runtime Integration

Owned files:

```text
agentic/runtime/channel_loop.py
agentic/app/channel_app.py
evals/test_milestone2_channel_loop.py
agentic/app/cli.py
```

Review criteria:

- `ChannelLoop` converts inbound messages into existing `FullLoopRuntime` calls.
- `serve` starts the local web app from `config/config.toml`.
- `ask` and `chat` still work.
- Empty messages and runtime failures return readable responses.

### M2-H: End-To-End Eval And Status Docs

Owned files:

```text
evals/test_milestone2_full_flow.py
docs/milestone2_status.md
README.md
```

Review criteria:

- Full-flow test uses fake runtime and fake ntfy transport.
- Trace contains channel, approval, and blocked-tool events.
- README documents `serve`.
- Status doc records completed checks and remaining manual ntfy verification.

## Verification

Default verification should not require GPU:

```bash
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
.venv/bin/python -m agentic.app.cli serve --host 127.0.0.1 --port 8765
```

Manual verification:

- Open `http://127.0.0.1:8765`.
- Send a test chat message.
- Trigger an approval-required action.
- Confirm an approval card appears.
- Confirm deny blocks execution.
- Confirm approve permits execution.
- Confirm ntfy arrives on phone when real ntfy config is enabled.
