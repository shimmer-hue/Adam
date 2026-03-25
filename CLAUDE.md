# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EDEN is a local-first experimental memetic persona runtime. ADAM is the first agent/persona instance. Identity persists in an explicit graph (memes, memodes, regard scores), not in model weights. The primary interface is a Textual TUI; the browser observatory is for observability and graph editing.

## Commands

```bash
# Setup (Python 3.12, repo-local venv)
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,mlx]'

# Run TUI
.venv/bin/python app.py

# Run tests
.venv/bin/pytest -q

# Run a single test
.venv/bin/pytest tests/test_budget.py -q
.venv/bin/pytest tests/test_budget.py::test_name -q

# One-turn demo (mock backend, no GPU needed)
.venv/bin/python -m eden demo --backend mock --mode blank --prompt 'test prompt' --feedback accept --feedback-explanation 'reason'

# Ingest a document
.venv/bin/python -m eden ingest <experiment_id> /path/to/file.pdf

# Export observability artifacts
.venv/bin/python -m eden export <experiment_id> --session-id <session_id>

# Serve observatory
.venv/bin/python -m eden observatory --host 127.0.0.1 --port 8741 --open
```

No linter is configured. Tests use `pytest` with `asyncio_mode = "auto"`.

## Architecture

**Core loop (v1 invariant):** `input -> retrieve/assemble -> Adam response -> membrane -> feedback -> graph update`

### Key modules in `eden/`

- **runtime.py** — `EdenRuntime`: central orchestrator. Manages the turn loop, session lifecycle, inference dispatch, feedback integration, and all subsystem coordination.
- **storage/graph_store.py** — `GraphStore`: SQLite persistence (WAL mode) for the entire graph, sessions, turns, feedback, documents, measurement events.
- **retrieval.py** — `RetrievalService`: candidate scoring using semantic similarity, activation, regard, and session bias signals.
- **regard.py** — `HumService`: persistent regard valuation with EMA decay and feedback-driven selection pressure.
- **config.py** — `RuntimeSettings`, `RegardWeights`, `SelectionWeights`, paths.
- **inference.py** — Inference profile system: modes (`manual`, `runtime_auto`, `adam_auto`) and presets (`tight`, `balanced`, `wide`).
- **budget.py** — Token budgeting and prompt-size estimation.
- **hum.py** — Human-understandable summary generation.
- **models/mlx_backend.py** — `MLXModelAdapter` for local Qwen 3.5 35B inference via `mlx-lm`.
- **models/mock.py** — `MockModelAdapter` for testing without a GPU.
- **ingest/pipeline.py** — Document ingestion (PDF, MD, TXT, CSV) into the memgraph.
- **tui/app.py** — `TUIApp`: Textual-based terminal interface (~6600 lines).
- **observatory/** — Browser-based graph inspection, measurement, editing, ablation, comparison. Server + exporters + geometry.

### Ontology

- **Memes** are first-class graph nodes (knowledge or behavior units).
- **Memodes** are derived structures composed from multiple memes plus relations.
- **Regard** is a persistent valuation signal over memes/memodes, updated by feedback.
- **Membrane** is the visible record of what was selected, trimmed, or rejected each turn.

### Data paths

- `data/eden.db` — SQLite database (runtime-generated)
- `logs/runtime.jsonl` — JSONL event log (runtime-generated)
- `exports/` — Observatory artifacts per experiment (runtime-generated, not committed)
- `models/` — Local MLX model cache (not committed)
- `eden/agents/adam/profile.json` — Agent identity and system principles
- `eden/agents/adam/seed_constitution.md` — Constitutional guidelines

## Spec-Driven Development

The `docs/` directory contains natural-language contract specs that govern code behavior. **Read the relevant spec before editing code.** If code and spec disagree, either fix the code or update the spec in the same change.

Key normative specs: `PROJECT_CHARTER.md`, `CANONICAL_ONTOLOGY.md`, `TURN_LOOP_AND_MEMBRANE.md`, `REGARD_MECHANISM.md`, `GRAPH_SCHEMA.md`, `TUI_SPEC.md`, `INFERENCE_PROFILES.md`, `OBSERVATORY_SPEC.md`.

When feature status changes, update `docs/IMPLEMENTATION_TRUTH_TABLE.md` and `docs/KNOWN_LIMITATIONS.md`.

## Runtime Invariants

- Keep inference on MLX. Do not introduce Ollama, vLLM, llama.cpp, or remote inference as the core path.
- The TUI is the primary interface; browser work is observability/export.
- Preserve ontology: memes are first-class; memodes are derived.
- Feedback is explicit and structured: `accept`/`reject` require explanation; `edit` requires explanation + corrected text.
- Preserve exact repository vocabulary (meme, memode, regard, membrane, active set, observatory, measurement event). Do not introduce sloppy synonyms.

## Testing

Tests live in `tests/`. The `runtime` fixture creates a temporary `EdenRuntime` with mock backend and temp SQLite — no GPU or persistent state needed. The `sample_files` fixture provides test PDFs/TXTs/CSVs. All tests run with `asyncio_mode = "auto"`.

## Web Observatory

The React/TypeScript frontend lives in `web/observatory/` (Vite + Graphology/Sigma). It has its own `package.json` and Playwright E2E tests. This is a separate build from the Python package.
