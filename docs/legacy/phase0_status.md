# Phase 0 Status

## Completed

- Project documentation: `README.md`, `docs/roadmap.md`, `docs/legacy/phase0_tasks.md`
- Python package scaffold under `agentic/`
- `LocalGGUFProvider` with fake-command smoke path
- Master and subagent wrappers
- Prompt builder with tool schema injection
- `add(a, b)` tool and simple registry
- Strict JSON tool-call parser
- `SubAgentTask` with explicit state transitions
- Simulated subagent spawn
- JSONL trace logger
- Programmatic module evals
- `config/config.toml` for local model candidates and runtime paths
- Prompt files under `prompts/`
- CLI config/model inspection commands
- Fake provider smoke for selected configured models
- Runner preflight checks for local build/runtime readiness
- External `llama.cpp` runtime kept under ignored `runtimes/llama.cpp/`
- CUDA build configured for RTX 4090 (`CMAKE_CUDA_ARCHITECTURES=89`)
- CUDA runners built:
  - `runtimes/llama.cpp/build-cuda/bin/llama-completion`
  - `runtimes/llama.cpp/build-cuda/bin/llama-diffusion-cli`
- `config/config.toml` wired to CUDA runners with `-ngl 99`
- Master Gemma models run through `llama-completion --jinja --single-turn`
- DiffusionGemma uses `llama-diffusion-cli` with `prompts/subagent.md` as the system prompt and entropy-bound max steps set to `16`
- Architecture diagrams documented in `docs/architecture.md`
- Response sanitizer extracts final channel text and drops diffusion timing lines
- Opt-in real-model evals are available via `AGENTIC_RUN_REAL_MODELS=1`

## Verified

```bash
.venv/bin/python -m unittest discover -s evals
```

Result:

```text
Ran 20 tests
OK (skipped=1)
```

Also verified:

```bash
.venv/bin/python -m agentic.app.cli config-check
.venv/bin/python -m agentic.app.cli list-models
.venv/bin/python -m agentic.app.cli runner-check
.venv/bin/python -m agentic.app.cli smoke --model master-gemma-q4 --fake --prompt "1+1은 뭐지?"
.venv/bin/python -m agentic.app.cli smoke --model subagent-diffusiongemma-q4 --fake --prompt "add로 1+1 계산"
```

Real GPU smoke checks:

```bash
timeout 120s .venv/bin/python -m agentic.app.cli smoke \
  --model master-gemma-q4 \
  --max-tokens 16 \
  --prompt "Reply with the single word OK."

timeout 180s .venv/bin/python -m agentic.app.cli smoke \
  --model subagent-diffusiongemma-q4 \
  --max-tokens 16 \
  --prompt "Call add with a=1 and b=1."
```

Results:

- `master-gemma-q4` loaded through CUDA `llama-completion` and emitted text.
- `master-gemma-iq2` loaded through CUDA `llama-completion` and emitted text.
- `subagent-diffusiongemma-q4` loaded through CUDA `llama-diffusion-cli` and emitted text.
- `nvidia-smi` confirmed the Q4 master runner as a GPU compute process with about 18.5GB VRAM in use during load.

Three-model sanity prompt:

```bash
.venv/bin/python -m agentic.app.cli smoke \
  --model master-gemma-q4 \
  --max-tokens 256 \
  --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."

.venv/bin/python -m agentic.app.cli smoke \
  --model master-gemma-iq2 \
  --max-tokens 384 \
  --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."

.venv/bin/python -m agentic.app.cli smoke \
  --model subagent-diffusiongemma-q4 \
  --max-tokens 256 \
  --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."
```

All three models reached the expected answer: `한국의 수도는 서울입니다.`

Opt-in real-model eval:

```bash
AGENTIC_RUN_REAL_MODELS=1 .venv/bin/python -m unittest evals.test_real_models
```

Result:

```text
Ran 1 test in 51.357s
OK
```

Current output handling:

- Raw stdout can include `<|channel>thought` / `<channel|>` markers and diffusion timing lines.
- `LocalGGUFProvider` now returns sanitized `response.text` and preserves the original stdout in `response.raw_text`.

The configured GGUF symlinks are visible:

- `models/gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf`
- `models/gemma-4-26B-A4B-it-UD-IQ2_XXS.gguf`
- `models/diffusiongemma-26B-A4B-it-Q4_K_M.gguf`

## Current runner preflight

Passing:

- `git`
- `g++`
- `cmake`
- all three configured GGUF model paths
- all configured CUDA runner executables

Known caveat:

- In the Codex sandbox, `nvidia-smi` can report `GPU access blocked by the operating system`.
  Real model smoke checks must run outside the sandbox with GPU access.

## Phase 0 Closeout

Phase 0 is complete. The core modules are independently alive, configured, tested, and verified against the three local GGUF model files.

Carry into Phase 1:

1. Keep CLI subprocess calls for the first minimal loop; defer persistent runner/wrapper work until model reload overhead becomes a measured blocker.
2. Tighten tool-call grammar and malformed-output recovery as part of the Phase 1 full-loop eval.
3. Build the minimal runtime path: master delegation, task creation, subagent tool call, tool result, subagent report, master final.
