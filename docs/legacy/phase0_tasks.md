# Phase 0 Task Breakdown

Status: complete.

## 0.1 Project scaffold

Create package directories, module boundaries, and a minimal test runner.

Acceptance:

- package imports cleanly
- `.venv/bin/python -m unittest discover -s evals` runs
- project is configured as a `uv` Python project

## 0.2 LocalGGUFProvider

Create one local provider that can execute a configured GGUF command.

Acceptance:

- provider accepts a prompt and returns captured text
- command execution is traced
- real model calls can be enabled later by model config

## 0.3 Master model smoke test

Create a smoke test path for the master model.

Acceptance:

- test can run with a lightweight fake command in CI/dev
- real command can be swapped through config/env without changing harness code
- `master-gemma-q4` and `master-gemma-iq2` can be selected independently

## 0.4 Subagent model smoke test

Create a smoke test path for the subagent model.

Acceptance:

- same `LocalGGUFProvider` supports the subagent role
- subagent config is separate from master config
- `subagent-diffusiongemma-q4` can be selected independently

## 0.5 Prompt builder

Build role prompts and inject tool schemas.

Acceptance:

- subagent prompt includes available tools
- builder is deterministic

## 0.6 Tool schema + add tool

Create a tiny tool registry with one `add(a, b)` tool.

Acceptance:

- schema serializes to JSON-compatible dict
- `add(1, 1)` returns `2`

## 0.7 Tool-call parser

Parse strict JSON tool-call objects.

Acceptance:

- valid JSON parses
- missing fields fail clearly
- malformed JSON fails clearly

## 0.8 SubAgentTask model

Represent subagent work as a stateful task object.

Acceptance:

- task id is generated
- state transitions are explicit
- invalid transitions fail

## 0.9 Trace logger

Record JSONL events for model calls, tool calls, task creation, and results.

Acceptance:

- trace file is append-only JSONL
- event records include timestamp, type, and payload

## 0.10 Module eval suite

Create programmatic tests for each Phase 0 part.

Acceptance:

- all Phase 0 module tests pass locally

Additional closeout:

- local CUDA runners are configured for all three GGUF files
- all three local models pass opt-in real-model smoke evals
- response sanitizing is in place for raw channel/timing output
