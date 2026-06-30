Tool calls must be strict JSON:

```json
{"tool":"add","arguments":{"a":1,"b":1}}
```

Rules:
- `tool` must be the exact registered tool name.
- `arguments` must be a JSON object.
- Do not wrap the JSON in Markdown when emitting an actual tool call.
