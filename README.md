# agentic

Personal 24/7 agent harness for a single local RTX 4090 machine.

This project intentionally starts small:

- one local GGUF runtime path
- one master agent
- one subagent
- simple tools
- JSONL traces
- programmatic evals

It is not trying to become a general provider gateway, plugin marketplace, or multi-backend framework.

See [docs/user_requirements.md](docs/user_requirements.md) for the current grill-session requirements and use cases.
See [docs/roadmap.md](docs/roadmap.md) for the active milestone plan.
See [docs/architecture.md](docs/architecture.md) for the module map and Mermaid diagrams.
See [docs/legacy/](docs/legacy/) for completed Phase 0 and Phase 1 implementation notes.

## Core Commands

This project uses `uv`. The current `.venv` is already prepared, so use the venv Python directly:

Run the module eval suite:

```bash
.venv/bin/python -m unittest discover -s evals
```

Check the CLI scaffold:

```bash
.venv/bin/python -m agentic.app.cli --version
```

Run one full-loop agent turn:

```bash
.venv/bin/python -m agentic.app.cli ask "1+1은 뭐지?"
```

Start the simple full-loop REPL:

```bash
.venv/bin/python -m agentic.app.cli chat
```

Start the local web channel:

```bash
.venv/bin/python -m agentic.app.cli serve --host 127.0.0.1 --port 8765
```

The web channel uses the Milestone 3 durable runtime. Chat requests are stored as
SQLite-backed tasks and executed by a bounded background worker. The default
state database is:

```bash
traces/state/agentic.sqlite3
```

Check config, prompt files, and local GGUF model paths:

```bash
.venv/bin/python -m agentic.app.cli config-check
```

List configured model candidates:

```bash
.venv/bin/python -m agentic.app.cli list-models
```

Check local runner prerequisites:

```bash
.venv/bin/python -m agentic.app.cli runner-check
```

Run a fake smoke call through the same provider path:

```bash
.venv/bin/python -m agentic.app.cli smoke --model master-gemma-q4 --fake --prompt "hello"
.venv/bin/python -m agentic.app.cli smoke --model subagent-diffusiongemma-q4 --fake --prompt "add 1 and 1"
```

If `uv` is installed on the machine, the same commands can be run as:

```bash
uv run python -m unittest discover -s evals
uv run python -m agentic.app.cli config-check
uv run python -m agentic.app.cli serve --host 127.0.0.1 --port 8765
```

## Local Model Smoke Path

Phase 0 uses `LocalGGUFProvider` for both master and subagent. When no local model command is configured, tests use a tiny fake command so the harness modules can be verified quickly.

The real GGUF paths and CUDA runner commands are wired through:

```bash
config/config.toml
```

Configured model candidates:

- `master-gemma-q4`: `models/gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf`
- `master-gemma-iq2`: `models/gemma-4-26B-A4B-it-UD-IQ2_XXS.gguf`
- `subagent-diffusiongemma-q4`: `models/diffusiongemma-26B-A4B-it-Q4_K_M.gguf`

Configured runner binaries:

- Gemma master models: `runtimes/llama.cpp/build-cuda/bin/llama-completion`
- DiffusionGemma subagent: DiffusionGemma PR runner `llama-diffusion-cli`

Master Gemma models are configured with `--jinja --single-turn` and `prompts/master_phase1.md` as the system prompt. DiffusionGemma is run through the diffusion CLI with `prompts/subagent_phase1.md` as the system prompt and entropy-bound decoding.

Build or refresh the CUDA runners with conservative parallelism:

```bash
MAX_JOBS=2 CMAKE_BUILD_PARALLEL_LEVEL=2 MAKEFLAGS="-j2" bash scripts/build_llama_cuda.sh
```

On this machine, the first CUDA build is slow because `nvcc` compiles many attention and quantization kernels. Incremental builds are much faster.

Run real GPU smoke checks:

```bash
.venv/bin/python -m agentic.app.cli smoke --model master-gemma-q4 --max-tokens 256 --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."
.venv/bin/python -m agentic.app.cli smoke --model master-gemma-iq2 --max-tokens 384 --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."
.venv/bin/python -m agentic.app.cli smoke --model subagent-diffusiongemma-q4 --max-tokens 256 --prompt "한국의 수도는 어디야? 답변만 한 문장으로 말해."
```

If running inside a sandboxed tool context, GPU access may be blocked. In that case, run smoke checks in a normal WSL shell.

Raw model output can include channel markers such as `<|channel>thought`. `LocalGGUFProvider` returns sanitized `response.text` and keeps the original stdout in `response.raw_text`.

Run the opt-in real-model eval suite:

```bash
AGENTIC_RUN_REAL_MODELS=1 .venv/bin/python -m unittest evals.test_real_models
```

Run the opt-in real Phase 1 full-loop eval:

```bash
AGENTIC_RUN_REAL_PHASE1=1 .venv/bin/python -m unittest evals.test_phase1_real_full_loop
```

The default eval command skips real model execution so normal development stays fast:

```bash
.venv/bin/python -m unittest discover -s evals
```

## WSL Memory

Recommended WSL allocation for this project on a 32GB RAM / 24GB VRAM RTX 4090 machine:

- minimum usable: 24GB RAM with swap enabled
- preferred for 24/7 harness work: 24GB RAM, 32GB swap, build parallelism capped at `-j2` or `-j4`
- avoid: 16GB RAM for CUDA builds or simultaneous model experimentation

Do not run master Q4 and subagent Q4 concurrently on a 24GB GPU unless the runtime is explicitly designed to unload one before loading the other.
