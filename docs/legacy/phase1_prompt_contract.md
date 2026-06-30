# Phase 1 Prompt Contract

Phase 1 uses separate prompt files so integration can switch config only after
the full loop is ready:

- `prompts/master_phase1.md`
- `prompts/subagent_phase1.md`

Do not change `config/config.toml` until the integration package.

## Master Contract

The master emits exactly one JSON object with one of these decisions.

Direct answer:

```json
{"decision":"answer","answer":"2"}
```

Delegate:

```json
{"decision":"delegate","task":"Compute 1+1 using the add tool."}
```

Final report to user after subagent completion:

```json
{"decision":"answer","answer":"The answer is 2."}
```

Required fields:

- `decision`: either `answer` or `delegate`
- `answer`: required when `decision` is `answer`
- `task`: required when `decision` is `delegate`

The master must not emit Markdown, tool calls, or multiple actions in one turn.

## Subagent Contract

The subagent emits exactly one JSON object.

Tool call for the add tool:

```json
{"tool":"add","arguments":{"a":1,"b":1}}
```

Report after a tool result:

```json
{"report":"2"}
```

Required fields for tool calls:

- `tool`: exact registered tool name
- `arguments`: JSON object matching that tool schema

Required fields for reports:

- `report`: concise string result for the master

The subagent must not wrap JSON in Markdown when responding to the runtime.

## Integration Owner Config Change

When P1-F, P1-G, and P1-H are ready, update `config/config.toml`:

```toml
[prompts]
master = "prompts/master_phase1.md"
subagent = "prompts/subagent_phase1.md"
tool_call_grammar = "prompts/tool_call_grammar.md"
```

The existing tool-call grammar remains in use for runtime prompt building.
