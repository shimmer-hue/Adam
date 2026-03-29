# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EDEN is a local-first experimental memetic persona runtime. ADAM is the first agent/persona instance. Identity persists in an explicit graph (memes, memodes, regard scores), not in model weights. The implementation is in **Idris2** with dependent-type verification, compiled to native code via the RefC backend.

## Commands

```bash
# Build (Idris2 type-check + RefC codegen + GCC link)
cd eden-idris && ./build.sh

# Run invariant demo (default)
./build/exec/eden.exe

# Run store + pipeline demo
./build/exec/eden.exe --demo

# Run TUI
./build/exec/eden.exe --tui

# Run REPL (with optional backend)
./build/exec/eden.exe --repl
./build/exec/eden.exe --repl --backend claude

# Export graph JSON for observatory
./build/exec/eden.exe --export

# Ingest articles into knowledge graph
./build/exec/eden.exe --ingest ~/docs/the-verge-of-redemption

# Type-check a single module
PATH="/ucrt64/bin:/usr/bin:$PATH" /home/natanh/Idris2/build/exec/idris2.exe --no-banner --check --source-dir src src/Eden/Types.idr

# Full build (manual, equivalent to build.sh)
CC=gcc PATH="/ucrt64/bin:/usr/bin:$PATH" /home/natanh/Idris2/build/exec/idris2.exe --no-banner --cg refc --build eden.ipkg
gcc -o build/exec/eden.exe build/exec/eden.c support/eden_term.c \
    -include support/eden_term.h \
    -I /home/natanh/Idris2/support/c -I /home/natanh/Idris2/support/refc \
    -L /home/natanh/Idris2/support/refc -L /home/natanh/Idris2/support/c \
    -lidris2_refc -lidris2_support -lgmp -lm -lpthread -lws2_32 \
    -Wno-error=implicit-function-declaration
```

## Architecture

**Core loop (v1 invariant):** `input -> retrieve/assemble -> Adam response -> membrane -> feedback -> graph update`

### Key modules in `eden-idris/src/Eden/`

- **Types.idr** — Core ontology types: `Meme`, `Memode`, `CandidateScore`, `TurnRecord`, `FeedbackEntry`, `MemeProjection`, `HumPayload`, `BudgetEstimate`, phantom-tagged `Id`.
- **Runtime.idr** — `EdenEnv` environment, graph operations, meme CRUD, edge management, memode materialization, turn recording, feedback processing.
- **Monad.idr** — `EdenM` monad (`ReaderT EdenEnv IO`), monadic pipeline wrappers.
- **Pipeline.idr** — Turn execution pipeline: retrieve → assemble → generate → membrane → index.
- **Retrieval.idr** — Candidate scoring with semantic similarity, activation, regard, session bias.
- **Regard.idr** — Regard breakdown computation with weighted signals, EMA decay, feedback integration.
- **Inference.idr** — Inference modes (`Manual`, `RuntimeAuto`, `AdamAuto`), presets, profile resolution. `resolveMode AdamAuto = RuntimeAuto` proven.
- **Budget.idr** — Token budgeting and pressure estimation.
- **Membrane.idr** — Post-generation control: authority stripping, prefix normalization, newline cleanup.
- **Hum.idr** — Bounded continuity artifact with token table, surface lines, status tracking.
- **Ingest.idr** / **Ingest/Pipeline.idr** — Document concept extraction and meme seeding.
- **Indexer.idr** — Turn response indexing, concept extraction, edge creation.
- **Storage.idr** / **Store/InMemory.idr** — In-memory graph store (experiments, sessions, memes, edges, memodes, turns, feedback).
- **Models/Base.idr** / **Models/Mock.idr** — Model adapter interface and mock implementation.
- **Proofs.idr** — 55 machine-checked theorems across 18 sections proving runtime invariants.
- **Term.idr** — Pure ANSI escape sequences, EDEN palette (Amber Dark theme), styled text helpers.
- **TermIO.idr** — C FFI bindings for raw terminal I/O via `support/eden_term.c`.
- **TUI.idr** — Two-column TUI application: dialogue tape, aperture panel, hum panel, composer.
- **Export.idr** — Hum file persistence (`data/hum/`), observatory JSON export (`data/export/`), minimal JSON serializer.
- **Loop.idr** — REPL implementation.

### C FFI Support

- **support/eden_term.c** — Platform-aware terminal control (Win32 console API on Windows/MinGW, POSIX termios on macOS/Linux).
- **support/eden_term.h** — Header for FFI function declarations.

### Ontology

- **Memes** are first-class graph nodes (knowledge or behavior units).
- **Memodes** are derived structures composed from multiple memes plus relations.
- **Regard** is a persistent valuation signal over memes/memodes, updated by feedback.
- **Membrane** is the visible record of what was selected, trimmed, or rejected each turn.

### Data paths

- `eden/agents/adam/profile.json` — Agent identity and system principles
- `eden/agents/adam/seed_constitution.md` — Constitutional guidelines
- `data/` — Runtime-generated data (not committed)

## Spec-Driven Development

The `docs/` directory contains natural-language contract specs that govern code behavior. **Read the relevant spec before editing code.** If code and spec disagree, either fix the code or update the spec in the same change.

Key normative specs: `PROJECT_CHARTER.md`, `CANONICAL_ONTOLOGY.md`, `TURN_LOOP_AND_MEMBRANE.md`, `REGARD_MECHANISM.md`, `GRAPH_SCHEMA.md`, `TUI_SPEC.md`, `INFERENCE_PROFILES.md`, `OBSERVATORY_SPEC.md`.

When feature status changes, update `docs/IMPLEMENTATION_TRUTH_TABLE.md` and `docs/KNOWN_LIMITATIONS.md`.

## Runtime Invariants

- The TUI is the primary interface.
- Preserve ontology: memes are first-class; memodes are derived.
- Feedback is explicit and structured: `accept`/`reject` require explanation; `edit` requires explanation + corrected text.
- Preserve exact repository vocabulary (meme, memode, regard, membrane, active set, observatory, measurement event). Do not introduce sloppy synonyms.
- Machine-checked proofs in `Eden.Proofs` verify key invariants at compile time.

## Idris2 Toolchain

The user (natanh/david-hoze) develops a custom Idris2 fork at `/home/natanh/Idris2/` (branch `progressive-stage1`). When encountering compiler bugs or unexpected behavior in Idris2, report them clearly so they can be fixed upstream — do not silently work around them.

The RefC backend generates a monolithic C file (`build/exec/eden.c`). Because it doesn't include FFI headers, the build script uses `-include support/eden_term.h` and `-Wno-error=implicit-function-declaration` to resolve forward declarations.

## Web Observatory

The React/TypeScript frontend lives in `web/observatory/` (Vite + Graphology/Sigma). It has its own `package.json` and Playwright E2E tests.
