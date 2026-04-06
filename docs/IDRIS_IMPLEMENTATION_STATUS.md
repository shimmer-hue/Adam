# Idris2 Implementation Status

**Date:** 2026-04-06
**Branch:** david
**Compiler:** Custom Idris2 fork (progressive-stage1), RefC backend

This document tracks the Idris2 port of the EDEN/Adam runtime against the Python reference implementation.

---

## Core Architecture (Implemented)

These subsystems are fully operational in the Idris2 build.

| Subsystem | Module(s) | Notes |
|---|---|---|
| Core types & ontology | `Eden.Types` | Meme, Memode, CandidateScore, TurnRecord, FeedbackEntry, phantom-tagged Id, all domain types |
| Turn loop pipeline | `Eden.Pipeline` | retrieve -> assemble -> generate -> membrane -> index. Full v1 invariant. |
| Retrieval & scoring | `Eden.Retrieval` | Jaccard word-overlap similarity, activation, regard, session bias |
| Regard mechanism | `Eden.Regard` | 7-component weighted breakdown, EMA decay, feedback integration |
| Membrane | `Eden.Membrane` | Authority stripping, prefix normalization, newline cleanup |
| Feedback processing | `Eden.Runtime` | accept/reject/edit with graph-wide propagation (0.85x attenuation per rank) |
| Inference profiles | `Eden.Inference` | Manual, RuntimeAuto, AdamAuto modes. AdamAuto -> RuntimeAuto proven. |
| Token budgeting | `Eden.Budget` | Pressure estimation, budget allocation |
| Hum artifact | `Eden.Hum` | Bounded continuity artifact with token table, surface lines, status tracking |
| In-memory graph store | `Eden.Store.InMemory` | Memes, edges, memodes, turns, feedback, sessions, experiments |
| SQLite persistence | `Eden.SQLite` | Full C FFI to sqlite3. Load/save for all graph entities. |
| Machine-checked proofs | `Eden.Proofs` | 55 theorems across 18 sections verifying runtime invariants |
| Agent profile loading | `Main` | `seed_constitution.md` read at startup, injected into system prompt |
| Observatory JSON export | `Eden.Export` | `--export` CLI. Graph state as JSON matching observatory contract. |
| Hum file persistence | `Eden.Export` | Written to `data/hum/<session-id>.md` after every hum build |
| System clock timestamps | `Eden.Runtime` | `currentTimestamp` via `System.time` + Hinnant civil-from-days |
| Turn trace enrichment | `Eden.Pipeline` | 6 events per turn: candidates, profile/budget, backend/tokens, membrane, indexing, completion |
| ANSI terminal rendering | `Eden.Term` | Pure escape sequences, EDEN Amber Dark palette |
| C FFI terminal I/O | `Eden.TermIO` | Win32 console API + POSIX termios, cell-buffer compositor |
| TUI | `Eden.TUI` | Two-column layout: dialogue tape, aperture panel, hum panel, composer, memgraph bus, feedback phase |
| REPL | `Eden.Loop` | Interactive loop with optional backend selection |
| Claude CLI backend | `Eden.Models.Base` | Writes prompt to temp file, pipes through `claude --model sonnet` |
| Mock backend | `Eden.Models.Mock` | Deterministic test responses |

## Recently Completed (2026-04-06)

### Reader Thread Fix (`eden_term.c`)
Replaced `_read` (CRT) with `PeekNamedPipe`+`ReadFile` (Win32 API) in the reader thread. The CRT version held internal locks that caused deadlocks on the second subprocess call. The pipe path now polls non-blockingly (exits within 2ms); the console path uses `ReadFile` cancellable via `CancelSynchronousIo`.

### Feedback Phase Fix (`TUI.idr`)
After the feedback verdict (accept/reject/skip), `uiFeedback` is now cleared after a 1.5s display pause. Previously it stayed set, blocking the composer from accepting new input.

### Model-Based Concept Extraction (`Indexer.idr`, `Pipeline.idr`, `Main.idr`)
Concept extraction can now use Claude instead of the hardcoded keyword list. The `extractConceptsViaModel` function writes text to a temp file, calls `claude --model sonnet`, and parses `label|domain` output. Falls back to keyword matching on failure. Works for English and Hebrew text. Activated when `--backend claude` is set. Wired into both turn indexing and document ingestion.

### Graph Audit Pipelines (`Eden.GraphAudit` — in worktree, pending merge)
Four model-in-the-loop pipelines ported from Python `eden/runtime.py`:

- **Graph Normalization** — Groups similar memes, asks Claude to MERGE/KEEP, creates DERIVED_FROM edges for merged items.
- **Behavior Taxonomy** — Collects behavior-domain memes, Claude groups them into memodes, materializes with MemberOf edges.
- **Coherence Reweave** — Finds structurally weak memes (< 2 edges), Claude suggests new edges with relation types and weights.
- **Document Contextualization** — After ingestion, cross-references new content with existing graph via Claude.

Convenience wrappers: `runSessionStartAudit`, `runPostIngestAudit`.

### Tanakh/Hebrew Service (`Eden.Tanakh` — in worktree, pending merge)
Pure Idris2 module implementing Hebrew text processing:

- **Gematria** — Standard mispar hechrachi. Explicit 22-letter lookup table with final-form normalization.
- **Notarikon** — Roshei teivot (first letters) and sofei teivot (last letters).
- **Temurah** — At-Bash cipher with 11-pair substitution table.
- **Text utilities** — `isHebrew`, `isNikkud`, `isFinalForm`, `stripNikkud`, `normalizeFinal`, `hebrewLetterName`.
- **Combined analysis** — `analyzeHebrew` runs all operations; `showAnalysis` formats results.

All functions are pure and total.

### Document Extraction (`Eden.Ingest.Extractors` — in worktree, pending merge)
Multi-format document extraction:

- **PDF** — Calls `pdftotext` via `runCommand`, with `-layout` fallback.
- **CSV** — Parses rows with quoted field support, formats as readable text.
- **Plaintext/Markdown** — Direct file read.
- **Format detection** — From file extension.
- **PDF quality scoring** — Penalties for garbled text, sparse/fragmented output. Matches Python scoring logic.
- **`ingestFile`** — Unified entry point wired into `Ingest/Pipeline.idr`.

### Session/Archive Management (`Eden.Session` — in worktree, in progress)
Session profile management, conversation archiving, markdown log export, session state snapshots.

---

## Not Yet Implemented

### Observatory Web Server & API
**Python:** 6,700+ lines across 6 modules. Flask/WebSocket server with 20+ REST endpoints, SSE invalidation, graph/basin/geometry payloads. React/TypeScript frontend with Graphology/Sigma.
**Status:** The Idris build has `--export` for static JSON. No server, no live endpoints, no browser interaction.
**Priority:** Medium. The static export covers observability for single-operator use. Live server matters when the observatory needs to preview/commit/revert mutations.

### Full TUI Feature Set
**Python:** 5,881 lines (Textual framework). Modal dialogs (help, session config, feedback, conversation atlas), review text editing, paste handling, mouse support, themes, conversation archive browser, accessibility modes.
**Idris:** 620 lines. Basic two-panel layout with keyboard-driven composer.
**Status:** Functional for dialogue and feedback. Missing modals, session tuning, archive browsing, and advanced input handling.
**Priority:** High. Session configuration and conversation atlas are the most impactful gaps.

### MLX Local Model Backend
**Python:** 216 lines. Full MLX adapter with streaming, token counting, sampler configuration, repetition penalty.
**Idris:** Claude CLI wrapper only. No local model support.
**Status:** The Idris build relies on `claude --model sonnet` via subprocess.
**Priority:** Low for now. Claude CLI works. MLX matters when local-only operation is required.

### Schema Migrations
**Python:** 254 lines. Versioned additive migrations, column additions, data deduplication, backfill operations.
**Idris:** Has SQLite FFI but no migration framework. Schema changes require manual database recreation.
**Priority:** Medium. Becomes critical as the schema evolves.

### Full Storage CRUD
**Python:** 79 methods covering all entity types with metadata, FTS indexing, SHA deduplication, measurement event tracking.
**Idris:** Core CRUD for memes, edges, memodes, turns, feedback, sessions, experiments. Missing: chunk management, FTS indexing, document SHA dedup, measurement events.
**Priority:** Medium. Current coverage handles the v1 loop.

### Embedding-Based Retrieval
**Python:** Supports embedding backends for semantic similarity.
**Idris:** Jaccard word-overlap only (lexical, not semantic).
**Priority:** Medium. Jaccard works for English but degrades on Hebrew and cross-lingual queries.

### Browser Automation
**Python:** 50 lines. Opens observatory URL via system browser.
**Idris:** Not implemented.
**Priority:** Low. `--export` writes JSON; operator can open files manually.

---

## Coverage Summary

| Subsystem | Python | Idris | Coverage |
|---|---|---|---|
| Core turn loop | 3,724 LOC | 357 LOC | **90%** (functional parity, less code due to types) |
| Retrieval + Regard | ~600 LOC | ~300 LOC | **95%** |
| Membrane + Feedback | ~400 LOC | ~200 LOC | **95%** |
| Proofs | 0 | 800 LOC | **Idris-only** (55 machine-checked theorems) |
| Inference profiles | ~340 LOC | ~200 LOC | **90%** |
| Storage | 1,590 LOC | 320 LOC | **40%** |
| Models | 480 LOC | 130 LOC | **30%** (Claude CLI only, no MLX) |
| TUI | 5,881 LOC | 620 LOC | **25%** (functional, missing modals/config) |
| Ingest | 731 LOC | ~400 LOC | **65%** (with new extractors) |
| Graph Audit | ~750 LOC | 534 LOC | **80%** (pending merge) |
| Tanakh | 1,590 LOC | ~250 LOC | **30%** (core hermeneutics, no scene compiler) |
| Session Management | ~500 LOC | ~200 LOC | **40%** (in progress) |
| Observatory | 6,700+ LOC | 0 | **0%** |
| Export | ~3,700 LOC | ~300 LOC | **15%** (JSON export only) |
| Concept Extraction | keyword-based | keyword + model | **110%** (model-based exceeds Python's keyword-only indexer) |

## Idris-Only Advantages

These exist in the Idris build but not in Python:

- **55 machine-checked proofs** verifying runtime invariants at compile time
- **Dependent types** enforcing ontology rules (e.g., memode materialization requires 2+ members, proven at the type level)
- **Phantom-tagged IDs** preventing accidental mixing of MemeId, SessionId, ExperimentId, etc.
- **Total core functions** — the type checker guarantees termination for pure pipeline logic
- **Native binary** — single 1.3MB executable, no Python/venv dependency at runtime

---

## Build & Run

```bash
cd eden-idris && ./build.sh        # Type-check + RefC codegen + GCC link
./build/exec/eden.exe --tui        # Primary interface
./build/exec/eden.exe --repl --backend claude   # REPL with Claude
./build/exec/eden.exe --export     # Observatory JSON
./build/exec/eden.exe --ingest ~/docs --backend claude  # Model-based ingest
```
