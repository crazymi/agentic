# Milestone 2 Status

Status: implemented.

Completed:

- Event and channel core
- Approval request model, JSONL store, and service
- Deterministic policy gate
- Approval-aware tool bridge wrapper
- ntfy outbound channel with test transport
- FastAPI local web UI and HTTP routes
- Channel loop integration with existing Phase 1 full loop
- CLI `serve` command
- Milestone 2 eval coverage
- Sandbox-safe ASGI route tests for web behavior

Verification:

```bash
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
timeout 5s .venv/bin/python -m agentic.app.cli serve --host 127.0.0.1 --port 8876
```

Latest result:

- 82 evals passing, 2 skipped
- `config-check` passing
- `serve` starts successfully outside the sandbox; sandboxed socket binding can fail

The `serve` smoke requires normal local socket binding. In sandboxed tool execution, binding may fail; outside the sandbox it should run until interrupted or timed out.

Manual checks still expected:

- Start `serve` and inspect `http://127.0.0.1:8765`.
- Confirm real ntfy notification on phone with enabled topic.
- Exercise the UI against real local models only when GPU access is available.

Notes:

- Milestone 2 keeps persistence to JSONL.
- There is still no public auth, MCP integration, scheduler, or daemon.
- FastAPI and uvicorn are the first runtime dependencies.
