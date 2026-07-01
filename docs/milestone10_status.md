# Milestone 10 Status

Status: started.

Completed in step 1:

- Removed runtime `FakeConnector` from the product connector surface.
- Removed `ModelConfig.fake()` and the CLI `smoke --fake` path.
- Removed `SourceKind.FAKE` and the default fake source collector.
- Added real local collectors for:
  - local files
  - mail-like JSONL files
  - feed-like JSONL files
  - browser-page local files
  - current repository state
- Changed workflow `COLLECT` execution to require `SourceRuntime` and `ResourceStore`.
- Changed workflow probes to use checked-in local source files or current repository state.
- Added a real local-source E2E test that collects, aggregates, analyzes, and writes a report artifact.

Completed in step 2:

- Added `agentic/ops/` with `HealthMonitor` and JSON-compatible `HealthSnapshot`.
- Health snapshots cover:
  - durable task counts and recent task failures
  - workflow spec/run counts and recent workflow failures
  - source counts and missing enabled local source warnings
  - artifact counts, including review-required artifacts
  - pending approvals
  - task-pool max/running worker state when available
- Added `GET /ops/health`.
- Added `POST /ops/health/export`.
- Added an Ops Health panel to the local web UI.
- Added CLI `ops-status`.
- Added operational health evals.

Completed during browser/API smoke:

- Added checked-in local source binding for workflow designs.
- A designed social trend workflow now binds `community_web` to `examples/sources/market_community_posts.jsonl`.
- Web/API flow now completes: design -> approve -> activate -> run -> collect resources -> create report artifact.
- Verified `/ops/health/export` writes `traces/state/health_snapshot.json`.

Completed in step 3:

- Added CLI `ops-smoke`.
- `ops-smoke` verifies workflow design, checked-in source binding, workflow run completion, report artifact creation, and health snapshot creation.
- Added `ops-smoke --include-model` for opt-in real configured model smoke.
- Added `--model-max-tokens` for real model smoke stability.
- Fixed model output sanitization so complete master decision JSON is preserved while partial JSON fragments are still hidden.
- Added explicit fallback extraction for direct answers generated inside internal model text without leaking the full internal text.

Real GPU smoke results:

- `master-gemma-iq2` with `--max-tokens 192` answered: `한국의 수도는 서울입니다.`
- `master-gemma-q4` with `--max-tokens 256` produced: `{"decision":"answer","answer":"한국의 수도는 서울입니다."}`
- `subagent-diffusiongemma-q4` produced tool-call JSON: `{"tool":"add","arguments":{"a":7,"b":5}}`
- Full loop `ask '7+5는 뭐지?'` returned `12`.
- Trace confirmed: master delegate -> subagent task -> `tool_called:add` -> `tool_result:add` -> final answer.

Current boundary:

- Unit tests may still use local in-process/subprocess test doubles where needed to isolate code.
- Product runtime paths must not silently generate fake source data.
- Workflow proposals without real source binding should fail clearly rather than complete with invented data.
- External production integrations remain explicit future work, not simulated success paths.

Verification:

```bash
.venv/bin/python -m unittest discover -s evals
.venv/bin/python -m agentic.app.cli config-check
```

Next:

- M10 step 4 should add service lifecycle hardening: graceful shutdown timing, restart smoke script, health-based exit checks, manual long-running serve/worker smoke checklist, and Chrome bridge recovery notes.
