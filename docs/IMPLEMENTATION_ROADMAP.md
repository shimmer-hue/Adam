# Implementation Roadmap

This roadmap tracks what needs to happen, organized by priority tier. Each item references what exists now and what the target state looks like.

---

## Tier 1 — Ship Blockers

These must be complete before public announcement.

| Item | Status | Notes |
|------|--------|-------|
| README rewrite | Done | Public-facing, three quick-start paths |
| Getting Started guide | Done | Step-by-step first ten minutes |
| Why This Matters document | Done | Philosophical bridge with evidence |
| Architecture Overview | Done | Technical map with diagrams |
| Tradition Embedding Guide | Done | Replication pattern using Tanakh as worked example |
| License selection | Done | GPL-3.0 (copyleft, protects community use) |
| Verify first-run experience | Done | Mock REPL, export, demo, REPL commands all verified; guide updated to match |
| Remove machine-specific paths | Partial | Public-facing docs clean; historical audit docs still reference `/Users/brianray/` |

---

## Tier 2 — High-Impact Gaps (first month)

| Item | Python | Idris2 | Complexity | Files |
|------|--------|--------|------------|-------|
| TUI session config modal | Full modal with 8+ params | Missing | Medium | `Eden/TUI.idr` |
| TUI conversation atlas | Archive browser with sort/filter | Missing | Medium | `Eden/TUI.idr`, `Eden/Session.idr` |
| Schema migrations | Versioned additive migrations | Missing | Medium | `Eden/SQLite.idr` |
| FTS indexing for chunks | Full-text search in retrieval | Missing | Medium | `Eden/Store/InMemory.idr` |
| Document SHA deduplication | Prevents duplicate ingestion | Missing | Small | `Eden/Store/InMemory.idr` |
| Second tradition module | N/A | Skeleton only | Medium | New module |
| Wire Session module into TUI | N/A | Module exists, not wired | Small | `Eden/TUI.idr`, `Main.idr` |
| Wire GraphAudit into session start | N/A | Module exists, not wired | Small | `Main.idr`, `Eden/Pipeline.idr` |

---

## Tier 3 — Full Parity (first quarter)

| Item | Python | Idris2 | Complexity | Notes |
|------|--------|--------|------------|-------|
| Observatory web server | Flask + WebSocket, 20+ endpoints | `--export` JSON only | Large | At minimum: read-only HTTP serving export JSON |
| MLX local model backend | Full adapter with streaming | Claude CLI only | Large | Full sovereignty without cloud dependency |
| Embedding-based retrieval | Embedding backends | Jaccard word-overlap | Large | Critical for Hebrew and cross-lingual queries |
| Full TUI modals | Help, feedback, review editing | Basic composer | Medium | Modals, paste handling, mouse support |
| Measurement event tracking | Full ledger | Missing | Medium | `Eden/Store/InMemory.idr` |
| Tanakh scene compiler | Merkavah 3D visualization | Core hermeneutics only | Medium | `Eden/Tanakh.idr` |

---

## Tier 4 — Expansion

| Item | Complexity | Impact |
|------|------------|--------|
| Pre-built binaries for Linux ARM (Raspberry Pi) | Medium | Critical for Global South deployment |
| Android terminal support (Termux) | Medium | Mobile-first access |
| Multiple tradition modules from communities | Ongoing | Proves the architecture is general |
| Multi-language concept extraction | Medium | Beyond English/Hebrew |
| Federation between Adam instances | Large | Share graph material with provenance |
| Offline model quantization guide | Small | Which open models work on which hardware |
| CI/CD pipeline | Medium | Build verification on push |

---

## Dependency Map

```
License selection ──┐
                    ├──> Public announcement
First-run verify ───┘

Session config modal ──> Conversation atlas (needs profile access)

Schema migrations ──> FTS indexing (needs schema changes)

Observatory server ──> Live measurement (needs HTTP layer)

MLX backend ──> Embedding retrieval (needs local model for embeddings)
```

---

## How to Pick Up Work

1. Check [IDRIS_IMPLEMENTATION_STATUS.md](IDRIS_IMPLEMENTATION_STATUS.md) for the current state
2. Read the Python implementation of the feature you're porting
3. Read the relevant normative spec in `docs/`
4. Follow the patterns in existing Idris2 modules
5. Build with `cd eden-idris && ./build.sh` — it must pass
6. Update IDRIS_IMPLEMENTATION_STATUS.md with your changes
