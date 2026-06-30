# Phase 1 Status

Status: complete.

Phase 1 proves the smallest end-to-end local agentic loop:

```text
User
 -> Master Agent
 -> SubAgentTask
 -> Sub Agent
 -> add tool
 -> final answer
```

## Implemented

- `FullLoopRuntime`
- one-turn `ask` CLI command
- simple `chat` REPL command
- task ledger integration
- master delegation decision integration
- subagent loop integration
- tool bridge integration
- trace replay assertions
- Phase 1 prompt files wired through `config/config.toml`
- default fake/deterministic full-loop tests
- opt-in real full-loop smoke test

## Commands

Default test suite:

```bash
.venv/bin/python -m unittest discover -s evals
```

Real Phase 1 full-loop smoke:

```bash
AGENTIC_RUN_REAL_PHASE1=1 .venv/bin/python -m unittest evals.test_phase1_real_full_loop
```

User-facing command:

```bash
.venv/bin/python -m agentic.app.cli ask "1+1은 뭐지?"
```

Interactive REPL:

```bash
.venv/bin/python -m agentic.app.cli chat
```

## Verified

Default tests:

```text
Ran 56 tests
OK (skipped=2)
```

Real Phase 1 full-loop eval:

```text
Ran 1 test in 25.914s
OK
```

CLI smoke:

```bash
.venv/bin/python -m agentic.app.cli ask "1+1은 뭐지?"
```

Result:

```text
2
```

## Accepted Trace

The real CLI smoke recorded this ordered trace in `traces/phase1.jsonl`:

```text
user_message_received
master_model_called
master_delegation_decision
subagent_task_created
subagent_model_called
tool_called:add
tool_result:add
subagent_reported
master_final_answer
```

## Current Limitations

- Model calls still use one subprocess per call.
- Phase 1 supports only the `add(a, b)` tool.
- The master final answer is assembled by the runtime from the subagent report for delegated tasks.
- Retry/recovery is intentionally minimal.
- Real model execution must not be run in parallel on the 24GB GPU.

## Carry Into Phase 2

- Tighten prompt/tool grammar.
- Add malformed output retry prompts.
- Decide whether persistent model runners are worth the complexity after measuring reload overhead.
- Expand full-loop eval cases beyond `1+1`.
