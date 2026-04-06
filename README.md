# EDEN / Adam

Adam is an AI runtime that keeps its values in a graph you control, not in weights trained by a corporation. It runs on your hardware. Every decision it makes is recorded, reversible, and yours.

## Why This Exists

AI governance frameworks have no shared theory of flourishing. Arrow's impossibility theorem extends to fairness: no single aggregation of preferences can satisfy all reasonable ethical constraints simultaneously. Corporate ethics boards collapse under commercial pressure, and the 470+ published AI ethics documents overwhelmingly reflect Global North institutional perspectives, with Global South voices structurally absent. Meanwhile, the cost of running capable models locally has collapsed -- the hardware barrier that once justified centralized control is gone. What remains missing is value architecture that communities can own, inspect, and modify without permission from a platform vendor. EDEN is an attempt to build that missing piece: a runtime where identity, values, and behavioral constraints live in an explicit graph that the operator controls, not in opaque model weights that a corporation updates on its own schedule.

## What It Does

- **Runs a complete AI conversation loop locally.** No cloud dependency required. The primary interface is a terminal TUI; a browser observatory provides graph inspection.
- **Stores identity in a persistent graph, not weights.** Swap the underlying model and keep Adam's values, knowledge, and behavioral patterns intact.
- **Post-generation membrane enforces community-defined constraints.** Every model response passes through a membrane that strips authority claims, normalizes formatting, and enforces response contracts before the operator sees it.
- **Regard -- durable selection pressure through feedback.** Operator feedback (accept, reject, edit with explanation) propagates through the graph as persistent regard scores, shaping which memes surface in future turns.
- **Attributable measurement ledger.** Every graph mutation, feedback event, and membrane action is recorded with provenance. Inspectable, reversible, permanent.
- **Tradition-specific modules.** A worked example with Tanakh/Hebrew hermeneutics (gematria, notarikon, temurah, at-bash) demonstrates how domain-specific interpretive traditions can be embedded as first-class graph operations.
- **Idris2 verifies 55 runtime invariants at compile time.** Machine-checked proofs guarantee properties like "AdamAuto mode always resolves to RuntimeAuto (no hidden governor)" and "membrane never silently drops content without recording an event."

## Two Implementations

| | Python (reference) | Idris2 (machine-verified) |
|---|---|---|
| Purpose | Full-featured reference implementation | Dependently-typed verified core |
| Runtime | Python 3.12, Textual TUI, Flask observatory | 1.3 MB native binary, no runtime dependencies |
| Model backends | MLX (local Qwen), Claude CLI, mock | Claude CLI, mock |
| TUI | Full modal interface (5,881 LOC) | Functional two-panel layout (620 LOC) |
| Observatory | Live server with 20+ endpoints, React frontend | Static JSON export |
| Proofs | 0 | 55 machine-checked theorems across 18 sections |
| Storage | SQLite with migrations, FTS indexing | SQLite via C FFI, in-memory store |
| Status | Production-ready for single operator | Core loop at functional parity, TUI and observatory in progress |

Both implementations share the same ontology, turn loop, and graph schema. The Idris2 build compiles to a single native executable via the RefC backend.

## Quick Start

**Path A: Idris2 with mock backend (no API key needed)**

```bash
cd eden-idris && ./build.sh
./build/exec/eden.exe --repl --backend mock
```

**Path B: Idris2 with Claude backend**

```bash
cd eden-idris && ./build.sh
./build/exec/eden.exe --tui --backend claude
```

**Path C: Python**

```bash
pip install -r requirements.txt
python -m eden app
```

The Idris2 build requires a custom Idris2 fork (branch `progressive-stage1`) with the RefC backend, plus GCC and GMP. See `eden-idris/build.sh` for the full toolchain invocation.

## Architecture in One Diagram

```
Input --> Retrieve/Assemble --> Generate --> Membrane --> Feedback --> Graph Update
  ^                                                                      |
  +------------------ Regard (durable selection pressure) ----------------+
```

The core loop is direct and auditable. There is no hidden governor, no latent policy search, no inaccessible chain-of-thought. The membrane operates on the raw model output and records every action it takes. Feedback is explicit and structured: accept and reject require explanation; edit requires explanation plus corrected text.

## For Builders From Other Traditions

The `Eden.Tanakh` module (`eden-idris/src/Eden/Tanakh.idr`) is a worked example of embedding a specific interpretive tradition into EDEN's graph operations. It implements standard Hebrew hermeneutic methods (gematria, notarikon, temurah) as pure, total Idris2 functions. If you want to embed a different tradition -- Islamic jurisprudence, Buddhist epistemology, Indigenous knowledge systems -- this module demonstrates the pattern: define your interpretive operations as pure functions over graph nodes, wire them into retrieval and indexing, and let the type system enforce your invariants. See [docs/TRADITION_EMBEDDING_GUIDE.md](docs/TRADITION_EMBEDDING_GUIDE.md) for the full replication guide.

## Project Structure

```
eden/                  Python reference implementation
  agents/adam/         Agent profile, seed constitution
  models/              Model adapters (MLX, Claude, mock)
  storage/             SQLite persistence, migrations
  observatory/         Flask server, live graph API
  ingest/              Document extraction pipeline
eden-idris/            Idris2 verified implementation
  src/Eden/            All Idris2 modules
  support/             C FFI (terminal I/O)
  build/exec/          Compiled native binary
web/observatory/       React/TypeScript browser observatory (Vite, Graphology/Sigma)
docs/                  Normative specs and status tracking
tests/                 Python test suite
```

## Documentation

**Guides:**
- `docs/GETTING_STARTED.md` -- Step-by-step first interaction walkthrough
- `docs/ARCHITECTURE_OVERVIEW.md` -- Technical map: design principles, core concepts, proof architecture
- `docs/WHY_THIS_MATTERS.md` -- The governance gap and the case for externalized identity
- `docs/TRADITION_EMBEDDING_GUIDE.md` -- How to embed your community's tradition into the runtime
- `CONTRIBUTING.md` -- How to contribute: tradition modules, ports, proofs, documentation

**Architecture and ontology:**
- `docs/PROJECT_CHARTER.md` -- Mission, hard boundaries, success conditions
- `docs/CANONICAL_ONTOLOGY.md` -- First-class and derived objects, edge semantics, domain split
- `docs/GRAPH_SCHEMA.md` -- Graph storage schema

**Runtime behavior:**
- `docs/TURN_LOOP_AND_MEMBRANE.md` -- Turn loop stages, membrane behavior, prompt assembly
- `docs/REGARD_MECHANISM.md` -- Regard breakdown, weighted signals, EMA decay
- `docs/INFERENCE_PROFILES.md` -- Manual, RuntimeAuto, AdamAuto modes
- `docs/HUM_SPEC.md` -- Bounded continuity artifact

**Interfaces:**
- `docs/TUI_SPEC.md` -- Terminal UI specification
- `docs/OBSERVATORY_SPEC.md` -- Browser observatory contract
- `docs/OBSERVATORY_INTERACTION_SPEC.md` -- Observatory editing semantics
- `docs/MEASUREMENT_EVENT_MODEL.md` -- Measurement event provenance model

**Status tracking:**
- `docs/IDRIS_IMPLEMENTATION_STATUS.md` -- Idris2 port coverage vs Python reference
- `docs/IMPLEMENTATION_ROADMAP.md` -- Prioritized roadmap for remaining work
- `docs/IMPLEMENTATION_TRUTH_TABLE.md` -- Feature-by-feature implementation state
- `docs/KNOWN_LIMITATIONS.md` -- What does not work yet

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
