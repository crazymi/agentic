# Milestone 3 Status

Status: implemented.

Completed:

- SQLite durable task store at `traces/state/agentic.sqlite3`
- Durable task state machine and event log
- Bounded thread-pool task execution
- Worker completion/failure persistence
- Heartbeat and stale-task watchdog
- Pause/resume/cancel task control
- Durable channel loop that enqueues `chat_turn` tasks
- FastAPI task routes and task status UI
- Startup recovery for interrupted running tasks
- Milestone 3 eval coverage

Verification:

```bash
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
timeout 5s .venv/bin/python -m agentic.app.cli serve --host 127.0.0.1 --port 8876
```

Latest result:

- 103 evals passing, 2 skipped
- `config-check` passing

Manual checks still expected:

- Start `serve` outside the sandbox and inspect `http://127.0.0.1:8876`.
- Submit `1+1은 뭐지?`.
- Confirm task appears immediately and later completes with result `2`.
- Restart server and confirm task list persists.

Notes:

- M3 keeps real model execution single-worker by default to avoid VRAM contention.
- M2 approval JSONL storage remains unchanged.
- There is still no scheduler daemon, MCP connector, browser tool, Gmail connector, or public auth.
