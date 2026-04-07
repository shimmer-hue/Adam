# Idris2 Implementation Status

**Date:** 2026-04-06
**Branch:** david
**Compiler:** Custom Idris2 fork (progressive-stage1), RefC backend
**Binary:** 1.7MB native executable (37 modules)

This document tracks the Idris2 port of the EDEN/Adam runtime against the Python reference implementation.

---

## Core Architecture (Implemented)

These subsystems are fully operational in the Idris2 build.

| Subsystem | Module(s) | Notes |
|---|---|---|
| Core types & ontology | `Eden.Types` | Meme, Memode, Chunk, Document, MeasurementEvent, CandidateScore, TurnRecord, FeedbackEntry, phantom-tagged Id, all domain types |
| Turn loop pipeline | `Eden.Pipeline` | retrieve -> assemble -> generate -> membrane -> index. Full v1 invariant. |
| Retrieval & scoring | `Eden.Retrieval` | TF-IDF similarity, character bigrams, Jaccard fallback, stopword filtering, suffix stemming, activation, regard, session bias |
| Regard mechanism | `Eden.Regard` | 7-component weighted breakdown, EMA decay, feedback integration |
| Membrane | `Eden.Membrane` | Authority stripping, prefix normalization, newline cleanup |
| Feedback processing | `Eden.Runtime` | accept/reject/edit with graph-wide propagation (0.85x attenuation per rank) |
| Inference profiles | `Eden.Inference` | Manual, RuntimeAuto, AdamAuto modes. AdamAuto -> RuntimeAuto proven. |
| Token budgeting | `Eden.Budget` | Pressure estimation, budget allocation |
| Hum artifact | `Eden.Hum` | Bounded continuity artifact with token table, surface lines, status tracking |
| In-memory graph store | `Eden.Store.InMemory` | Memes, edges, memodes, turns, feedback, sessions, experiments, chunks, documents, FTS inverted index, measurement events |
| SQLite persistence | `Eden.SQLite` | Full C FFI to sqlite3. Load/save for all graph entities. Schema migration framework. |
| Machine-checked proofs | `Eden.Proofs` | 55 theorems across 18 sections verifying runtime invariants |
| Agent profile loading | `Main` | `seed_constitution.md` read at startup, injected into system prompt |
| Observatory JSON export | `Eden.Export` | `--export` CLI. Enhanced graph JSON with metadata, provenance, sessions, membrane events, regard history. Plus session log (markdown), regard timeline (CSV), meme index (text). |
| Observatory HTTP server | `Eden.Observatory` | Read-only HTTP server with 11 REST endpoints. `--observatory [port]` CLI flag. |
| Hum file persistence | `Eden.Export` | Written to `data/hum/<session-id>.md` after every hum build |
| System clock timestamps | `Eden.Runtime` | `currentTimestamp` via `System.time` + Hinnant civil-from-days |
| Turn trace enrichment | `Eden.Pipeline` | 6 events per turn: candidates, profile/budget, backend/tokens, membrane, indexing, completion |
| ANSI terminal rendering | `Eden.Term` | Pure escape sequences, EDEN Amber Dark palette |
| C FFI terminal I/O | `Eden.TermIO` | Win32 console API + POSIX termios, cell-buffer compositor, paste detection |
| TUI | `Eden.TUI` | Two-column layout with dialogue tape, aperture panel, hum panel, composer, memgraph bus, feedback phase, help/config/atlas modals, 10+ slash commands, session wiring, GraphAudit at startup |
| REPL | `Eden.Loop` | Interactive loop with optional backend selection |
| Claude CLI backend | `Eden.Models.Base` | Writes prompt to temp file, pipes through `claude --model sonnet` |
| MLX adapter | `Eden.Models.MLX` | Subprocess-based MLX adapter with graceful fallback to mock |
| Mock backend | `Eden.Models.Mock` | Deterministic test responses |
| Browser automation | `Eden.Browser` | Platform-aware URL opener (start/open/xdg-open). `--open` flag for export and observatory. |
| Graph audit pipelines | `Eden.GraphAudit` | Graph normalization, behavior taxonomy, coherence reweave, document contextualization |
| Tanakh/Hebrew | `Eden.Tanakh` | 4 gematria schemes, notarikon, temurah, equivalence search, word/letter breakdowns, scene compiler skeleton |
| Session management | `Eden.Session` | Session profiles, archiving, markdown export, state snapshots, wired into TUI |
| Document extraction | `Eden.Ingest.Extractors` | PDF, CSV, plaintext/markdown extraction with quality scoring |
| Concept extraction | `Eden.Indexer` | Model-based (Claude) + keyword fallback. English and Hebrew. |

## Recently Completed (2026-04-06)

### Storage Enhancements (`Eden.Store.InMemory`, `Eden.SQLite`)
- **Chunk management** — `Chunk` record with CRUD, document association, position tracking
- **Document SHA deduplication** — Hash-based duplicate detection on ingest
- **FTS inverted index** — Pure Idris tokenizer, inverted index, `ftsSearchMemes` with term-based search, auto-rebuild on meme creation
- **Measurement event tracking** — Full `MeasurementEvent` lifecycle with reversion (reversion creates a new event, never silently mutates history)
- **Schema migration framework** — Version table, `runMigrations` on database open, migrations v2 (chunks table) and v3 (measurement_events table)
- **9 new EdenM wrappers** in `Eden.Monad` for chunks, FTS, documents, measurement events

### TUI Enhancements (`Eden.TUI`, `Eden.TermIO`, `eden_term.c`)
- **Help modal** (`?`/`F1`/`/help`) — Full keybinding reference with box-drawn overlay
- **Config modal** (`Ctrl+S`/`/config`) — 10 settings: backend, inference mode, token budget, retrieval depth, etc. Navigate with arrows, Enter to cycle values
- **Atlas/archive modal** (`/atlas`/`/archive`) — Scrollable session list from database with ID, title, turn count, date
- **Paste handling** — C FFI `eden_term_drain_paste` detects rapid input bursts, converts newlines to spaces
- **Session wiring** — Loads `SessionProfile` at startup, displays in status panels
- **GraphAudit wiring** — Runs `runSessionStartAudit` (normalization + taxonomy + reweave) at TUI startup
- **10+ slash commands** — /quit, /help, /config, /atlas, /archive, /stats, /memes, /regard, /hum, /export

### Observatory HTTP Server (`Eden.Observatory`, `eden_http.c`)
- **Minimal C HTTP server** — Platform sockets (Winsock2 on Windows/MSYS2, POSIX on Linux/macOS), single-threaded, CORS headers
- **11 REST endpoints** — `/api/graph`, `/api/memes`, `/api/memes/:id`, `/api/edges`, `/api/memodes`, `/api/regard`, `/api/feedback`, `/api/sessions`, `/api/turns`, `/api/health`, plus styled HTML index page
- **CLI integration** — `--observatory [port]` flag (default 8420)

### Export Enhancements (`Eden.Export`)
- **Richer graph JSON** — Metadata header (schema version, counts), provenance (experiment, agent, sessions), session summaries, membrane events, measurement events, regard history with full breakdown
- **Session log export** — Markdown conversation log with turns, feedback, and summary statistics
- **Regard timeline** — CSV export of regard scores per meme (all 7 components + activation + total)
- **Meme index** — Plain text index with label, domain, role, usage/feedback counts, aggregate statistics
- **`exportAll`** — Runs all export formats and returns output paths
- **Chunk/document/measurement event deserializers** for SQLite loading

### Tanakh Enhancements (`Eden.Tanakh`)
- **4 gematria schemes** — Standard (mispar hechrachi), Gadol (final forms at full value), Katan (single digit), Ordinal (positional)
- **`GematriaScheme` enum** with `gematriaWith` generic function
- **Equivalence search** — `areGematriaEqual`, `findEquivalent` across any scheme
- **Word/letter breakdowns** — `wordGematria` (per-word values), `letterBreakdown` (per-letter name and value)
- **Extended analysis** — `HebrewAnalysisExt` record with all-scheme values, `analyzeHebrewExt`
- **Scene compiler skeleton** — `Vec3`, `AnalyzedPassage`, `SceneElement`, `Scene` records, `compileScene`, `sceneToJSON`

### Retrieval Enhancements (`Eden.Retrieval`)
- **TF-IDF similarity** — Term frequency, inverse document frequency, cosine similarity over TF-IDF vectors
- **Character bigrams** — `bigramSimilarity` using Jaccard over character pairs (script-agnostic, works for Hebrew)
- **`SimilarityMethod` enum** — `Jaccard | TFIDF | Bigram` with configurable dispatch
- **Stopword filtering** — 70-word English stopword list
- **Suffix stemming** — 20-suffix stemmer (-tion, -sion, -ment, -ness, -able, -ible, -ing, -ous, -ive, -ful, -ity, -ly, -ed, -er, -al, etc.)
- **Default changed to TF-IDF** — `assembleActiveSet` uses TF-IDF by default, Jaccard available as fallback

### MLX Adapter (`Eden.Models.MLX`)
- **`MLXConfig` record** — modelPath, maxTokens, temperature, topP, repetitionPenalty
- **Subprocess invocation** — Calls `mlx_lm.generate` via Python subprocess
- **Graceful fallback** — Falls back to mock backend if MLX is unavailable
- **`--backend mlx` CLI option**

### Browser Automation (`Eden.Browser`)
- **`openBrowser`** — Platform fallback: `start` (Windows) -> `open` (macOS) -> `xdg-open` (Linux) -> prints URL
- **`--open` flag** — Opens export JSON or observatory URL in system browser

---

## Remaining Gaps

### Observatory (read-only only)
**Python:** 6,700+ LOC. Full Flask/WebSocket server with SSE invalidation, graph/basin/geometry payloads, mutation endpoints (preview/commit/revert). React/TypeScript frontend.
**Idris:** 288 LOC. Read-only HTTP server with 11 GET endpoints. No mutation, no WebSocket, no SSE, no frontend.
**Remaining:** Mutation endpoints, preview/commit/revert flow, SSE invalidation, basin/geometry payloads, frontend integration.

### TUI (modals done, advanced features remaining)
**Python:** 5,881 LOC. Full Textual framework with review text editing, mouse support, themes, accessibility modes.
**Idris:** ~1,500 LOC. Help/config/atlas modals, paste handling, session wiring, 10+ commands.
**Remaining:** Review text editing modal, mouse support, themes, accessibility modes.

### Embedding-Based Retrieval
**Python:** Supports embedding backends for true semantic similarity.
**Idris:** TF-IDF + bigrams (lexical, not semantic). Significant improvement over Jaccard but still not embedding-based.
**Remaining:** Integration with an embedding model (local or via API) for vector similarity.

### Storage (most features done)
**Python:** 79 methods with full metadata support.
**Idris:** Core CRUD + chunks + FTS + SHA dedup + measurement events.
**Remaining:** Some metadata fields, advanced query patterns.

### Tanakh Scene Compiler
**Python:** Full Merkavah 3D visualization with passage positioning, camera paths, lighting.
**Idris:** Skeleton with data types and linear layout.
**Remaining:** 3D positioning algorithms, camera paths, full scene graph.

---

## Coverage Summary

| Subsystem | Python | Idris | Coverage |
|---|---|---|---|
| Core turn loop | 3,724 LOC | 357 LOC | **90%** (functional parity, less code due to types) |
| Retrieval + Regard | ~600 LOC | ~600 LOC | **95%** (TF-IDF, bigrams, stemming, stopwords) |
| Membrane + Feedback | ~400 LOC | ~200 LOC | **95%** |
| Proofs | 0 | 800 LOC | **Idris-only** (55 machine-checked theorems) |
| Inference profiles | ~340 LOC | ~200 LOC | **90%** |
| Storage | 1,590 LOC | ~535 LOC | **75%** (chunks, FTS, SHA dedup, measurement events, migrations) |
| Models | 480 LOC | ~275 LOC | **45%** (Claude CLI + MLX adapter + mock) |
| TUI | 5,881 LOC | ~1,500 LOC | **55%** (modals, commands, paste, session wiring) |
| Ingest | 731 LOC | ~400 LOC | **65%** (multi-format extractors) |
| Graph Audit | ~750 LOC | 534 LOC | **80%** |
| Tanakh | 1,590 LOC | ~730 LOC | **55%** (4 gematria schemes, equivalence search, scene skeleton) |
| Session Management | ~500 LOC | ~200 LOC | **50%** (wired into TUI) |
| Observatory | 6,700+ LOC | ~540 LOC | **20%** (read-only HTTP server, 11 endpoints) |
| Export | ~3,700 LOC | ~680 LOC | **45%** (4 formats, richer JSON, provenance) |
| Concept Extraction | keyword-based | keyword + model | **110%** (model-based exceeds Python) |
| Browser | ~50 LOC | ~45 LOC | **90%** |

## Idris-Only Advantages

These exist in the Idris build but not in Python:

- **55 machine-checked proofs** verifying runtime invariants at compile time
- **Dependent types** enforcing ontology rules (e.g., memode materialization requires 2+ members, proven at the type level)
- **Phantom-tagged IDs** preventing accidental mixing of MemeId, SessionId, ExperimentId, etc.
- **Total core functions** — the type checker guarantees termination for pure pipeline logic
- **Native binary** — single 1.7MB executable, no Python/venv dependency at runtime
- **Model-based concept extraction** — Claude-powered extraction exceeds Python's keyword-only indexer

---

## Build & Run

```bash
cd eden-idris && ./build.sh        # Type-check + RefC codegen + GCC link (37 modules)
./build/exec/eden.exe --tui        # Primary interface
./build/exec/eden.exe --repl --backend claude   # REPL with Claude
./build/exec/eden.exe --export     # Observatory JSON + session log + regard CSV + meme index
./build/exec/eden.exe --export --open           # Export and open in browser
./build/exec/eden.exe --observatory             # HTTP server on port 8420
./build/exec/eden.exe --observatory 9000        # Custom port
./build/exec/eden.exe --ingest ~/docs --backend claude  # Model-based ingest
```
