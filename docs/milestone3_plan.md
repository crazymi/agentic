# Milestone 3 Plan: Durable Runtime And Background Task Pool

Milestone 3 turns the harness from a blocking request/response chat loop into a durable local runtime.

Decisions:

- Task persistence: SQLite
- Worker model: bounded thread pool
- Web behavior: enqueue task immediately, then poll/view task status
- State path: `traces/state/agentic.sqlite3`
- Scope: no scheduler daemon, MCP, browser/Gmail tools, or multi-user auth yet

## Acceptance

- Web messages create durable `chat_turn` tasks and return quickly.
- Background workers execute queued tasks.
- Task state survives restart through SQLite.
- Running/interrupted tasks become `unhealthy` during recovery.
- Running tasks heartbeat.
- Queued/running tasks can be cancelled through control APIs.
- Paused tasks do not run until resumed.
- Web UI shows recent task state, result/error, and task controls.
- Phase 1 `ask` and `chat` remain available.

## Parallel Packages

### M3-A: SQLite Task Store And State Model

Owned files:

```text
agentic/tasks/state_machine.py
agentic/tasks/store.py
evals/test_milestone3_task_store.py
```

Review criteria:

- SQLite schema initializes with stdlib `sqlite3`.
- `TaskRecord` persists input/result/error/timestamps/heartbeat.
- Invalid state transitions fail clearly.
- Task events are durable and ordered.

### M3-B: Task Pool And Worker Lifecycle

Owned files:

```text
agentic/runtime/task_pool.py
agentic/runtime/worker.py
evals/test_milestone3_task_pool.py
```

Review criteria:

- Worker claims queued tasks atomically.
- Bounded concurrency is respected.
- Completion and failure are stored structurally.
- Duplicate workers cannot claim the same queued task.

### M3-C: Heartbeat And Watchdog

Owned files:

```text
agentic/runtime/heartbeat.py
evals/test_milestone3_heartbeat.py
```

Review criteria:

- Heartbeats update running tasks.
- Stale running/cancel-requested tasks become `unhealthy`.
- Terminal tasks are ignored.

### M3-D: Pause, Resume, And Cancellation

Owned files:

```text
agentic/runtime/task_control.py
evals/test_milestone3_task_control.py
```

Review criteria:

- Queued tasks can be cancelled immediately.
- Running tasks become `cancel_requested`.
- Fake worker observes cooperative cancellation checkpoint.
- Paused tasks resume to `queued`.

### M3-E: Durable Channel Loop Integration

Owned files:

```text
agentic/runtime/durable_channel_loop.py
evals/test_milestone3_durable_channel_loop.py
```

Review criteria:

- Inbound messages create durable `chat_turn` tasks.
- Worker executor adapts existing `FullLoopRuntime`.
- Trace records channel message and task enqueue.
- Existing `ChannelLoop` remains available for compatibility.

### M3-F: Web Task UI And API

Owned files:

```text
agentic/app/server.py
agentic/app/web_templates.py
evals/test_milestone3_web_tasks.py
```

Review criteria:

- Routes exist: `GET /tasks`, `GET /tasks/{task_id}`, cancel/pause/resume posts.
- Homepage shows tasks, result/error, heartbeat, and controls.
- Route tests avoid live socket binding.

### M3-G: Daemon/Serve Startup Recovery

Owned files:

```text
agentic/runtime/daemon.py
evals/test_milestone3_recovery.py
agentic/app/channel_app.py
```

Review criteria:

- `serve` initializes SQLite task store and task pool.
- Startup recovery marks interrupted tasks unhealthy.
- Shutdown stops accepting new worker submissions.

### M3-H: Milestone Eval, Docs, And Handoff

Owned files:

```text
evals/test_milestone3_full_flow.py
docs/milestone3_plan.md
docs/milestone3_status.md
README.md
```

Review criteria:

- Full fake flow verifies enqueue, worker completion, UI result, and recovery.
- README documents SQLite state path and `serve`.
- Default eval suite passes without GPU.

## Verification

```bash
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
timeout 5s .venv/bin/python -m agentic.app.cli serve --host 127.0.0.1 --port 8876
```

Manual smoke:

- Open `http://127.0.0.1:8876`.
- Submit `1+1은 뭐지?`.
- Confirm a task appears immediately.
- Confirm task progresses to `completed`.
- Confirm result is `2`.
- Restart server and confirm task list survives.
