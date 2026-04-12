# Architecture Overview

This document is the technical architecture map for the EDEN/Adam runtime. Every claim matches what the code does. Where something is missing or incomplete, this document says so.

---

## Design Principles

**Local-first.** The runtime is tied to a local model and local SQLite persistence. There is no cloud dependency. The base model is an inference surface: it produces text when prompted. Identity does not live in the model. Identity lives in the graph -- memes, memodes, regard scores, feedback events, membrane traces, and the measurement ledger, all stored in a local SQLite database (Python) or in-memory store with SQLite persistence (Idris2). The Idris2 build produces a single 1.3MB native binary with no external runtime dependencies. A community can run Adam on their own hardware, with their own values, without corporate permission or cloud connectivity.

**Externalized identity.** Adam's continuity is maintained by the persistent memetic graph, explicit feedback events, regard pressure, membrane traces, and the measurement ledger -- not by model weights, fine-tuning, LoRA, or hidden parameter updates. Swap the model, keep the identity. This is the core thesis under test: alignment should be a property of the governance layer, not of the generative substrate. The governance layer is fully auditable, reversible, and external to the system it governs.

**Direct loop (no hidden governor).** The turn loop is: input, retrieve/assemble, deliberate, generate, membrane, feedback, graph update. There is no hidden planner, no pre-generation governor, no recursive task decomposition, no multi-step reasoning orchestrator. This is an active constitutional boundary, not a missing feature. The `adam_auto` inference mode resolves to `runtime_auto` -- proven at the type level in Idris2 (`adamAutoIsRuntimeAuto : resolveMode AdamAuto = RuntimeAuto`). The inference layer records when `adam_auto` falls back to `runtime_auto` and logs both the requested mode and the effective mode, making the boundary visible rather than burying it.

**Honest instrumentation.** Every claim about the system is backed by code, tests, or runtime traces. Synthetic figures are labeled synthetic. Derived metrics carry evidence labels (`OBSERVED`, `DERIVED`, `SPECULATIVE`). Missing capabilities are documented as missing in `docs/KNOWN_LIMITATIONS.md` and `docs/IMPLEMENTATION_TRUTH_TABLE.md`. The hum artifact does not claim to be a hidden voice. The geometry lab does not claim sacred geometry. Projection provenance is explicit. Export freshness mismatches are surfaced rather than hidden. When a richer future mechanism is not yet implemented, the current build uses a bounded fallback with explicit persistence rather than a theatrical simulation of depth.

---

## Core Concepts

### Meme

First-class persistent graph unit representing a performative behavioral element.

**IS:** A feedback-derived behavior unit with graph relations -- edges, regard scores, activation decay, evidence counts, and memode membership. Memes are the atomic building blocks of Adam's externalized identity. Both behavior-domain and knowledge-domain rows inhabit the `memes` table in the compatibility store, but the ontology projects them differently: behavior-domain rows project as performative memes eligible for memode materialization; knowledge-domain rows project as constative information.

**IS NOT:** A social media meme, a loose metaphor, or an unconstrained Dawkinsian replicator claim. The term is operationally grounded in persistent graph units, selection pressure, and recurrence -- not in biological literalism.

**Defined in:** `docs/CANONICAL_ONTOLOGY.md`; implemented in `eden-idris/src/Eden/Types.idr`.

### Memode

Derived second-order structure composed from at least two behavior-domain memes plus a connected qualifying memetic support subgraph.

**IS:** An audited behavior assembly whose member memes are connected through support edges and pass the admissibility checks exported in the memode audit surface. The admissibility floor is graph-theoretic: every selected behavior meme must participate in at least one qualifying support edge, and the support subgraph must be connected. In the Idris2 build, the minimum-two-members requirement is enforced at the type level: `CanMaterialize` is a decidable proposition, and `materializableImpliesGE2` proves the bound. A single meme cannot form a memode.

**IS NOT:** A semantic cluster label, a community summary, a pairwise relation, or a UI grouping. Clusters are not memodes. Knowledge constatives do not auto-materialize memodes. Informational edges remain non-memetic even when they connect multiple knowledge nodes. Wake-up or observability summaries are not promoted into durable second-order behavior objects.

**Defined in:** `docs/CANONICAL_ONTOLOGY.md`; admissibility proven in `eden-idris/src/Eden/Proofs.idr` (section 5).

### Regard

Durable selection pressure over persistent graph objects, accumulated through explicit feedback and retrieval history.

**IS:** A 7-component weighted score (`reward`, `evidence`, `coherence`, `persistence`, `decay`, `isolation`, `risk`) computed over a graph node's accumulated history. The total is bounded to [-8, 8] -- proven at the type level via `regardUsesBounded`. Feedback updates flow through EMA channels with eta = 0.35. Propagation to related graph nodes attenuates (edit at 0.65x, accept/reject/skip at 0.80x -- proven values).

**IS NOT:** Prompt-time salience, one-off relevance to the current query, or momentary activation. Regard persists across sessions. A meme can be highly salient in a given turn while having low durable regard, and a high-regard meme can remain outside the current prompt if the retrieval aperture does not select it. Regard acts over memes and memodes, not over tokens.

**Defined in:** `docs/REGARD_MECHANISM.md`; implemented in `eden-idris/src/Eden/Regard.idr`; boundedness proven in `eden-idris/src/Eden/Proofs.idr` (section 15).

### Active Set

Bounded retrieval and prompt-compilation slice assembled for a single turn.

**IS:** The runtime's current working slice of persistent graph material under budget and profile constraints. The selection score combines semantic similarity, activation, regard, session bias, explicit feedback relevance, scope penalty, and membrane penalty -- bounded to [-12, 12] (proven via `selectionUsesBounded`). The active set is what enters the prompt context for generation. `selectTopK` preserves the k-bound (proven).

**IS NOT:** The full identity. **IS NOT** Adam itself. Adam's continuity is distributed across the entire graph, feedback history, regard scores, traces, and repeated retrieval -- not collapsed into any single ephemeral slice.

**Defined in:** `docs/TURN_LOOP_AND_MEMBRANE.md`; implemented in `eden-idris/src/Eden/Retrieval.idr` and `eden-idris/src/Eden/Pipeline.idr`.

### Membrane

Post-generation control surface that sanitizes, constrains, and records trace effects on the raw model output.

**IS:** A sanitization and constraint layer that strips control characters, removes recognized planning spills (`<think>` blocks, `Thinking Process` scaffolds), enforces response contracts, clamps response length, fails closed when a response is reasoning-only, and records all actions as persistent membrane events with visible traces. The operator-facing response is the membrane result, not the raw model output.

**IS NOT:** A planner, governor, cognition layer, or pre-generation filter. The membrane acts strictly after generation. It does not perform hidden planning, latent policy search, inaccessible chain-of-thought exposure, or silent re-ranking after operator-visible scoring.

**Defined in:** `docs/TURN_LOOP_AND_MEMBRANE.md`; implemented in `eden-idris/src/Eden/Membrane.idr`; event type coverage proven in `eden-idris/src/Eden/Proofs.idr` (section 11).

### Feedback Events

Explicit operator verdicts (`accept`, `reject`, `edit`, `skip`) over a turn, with required explanations.

These are performative utterances -- they change persistent state only when felicity conditions are met. `accept` and `reject` require an explanation string. `edit` requires both an explanation and corrected text. `skip` is neutral and requires no data. These constraints are enforced at the type level through `ExplainedVerdict`, a GADT indexed by `Verdict`. The type checker rejects feedback without the required data. Explanation text is proven to round-trip: `acceptExplanationPreserved`, `rejectExplanationPreserved`, `editExplanationPreserved`.

Feedback updates regard channels via EMA. Accept yields reward +1.0 and risk -0.1 (proven). Reject yields reward -0.4 and risk +1.0 (proven). Edit yields edit channel +0.9 (proven). Skip is neutral on reward (proven). Propagation to constituent memes attenuates at 0.65x for edits and 0.80x for other verdicts (proven). Feedback itself is re-ingested into the graph as behavior-domain material.

**Defined in:** `docs/REGARD_MECHANISM.md`; felicity conditions proven in `eden-idris/src/Eden/Proofs.idr` (section 17); signal values proven in section 2; propagation scales proven in section 8.

### Measurement Ledger

Structured persistence surface recording observatory-originated mutations with before-state, proposed-state, committed-state, and reversion linkage.

Each measurement event carries: target IDs, action type, rationale, operator label, evidence label, measurement method, confidence, and timestamps. Supported action types: `edge_add`, `edge_update`, `edge_remove`, `memode_assert`, `memode_update_membership`, `motif_annotation`, `geometry_measurement_run`, `ablation_measurement_run`, and `revert`. Reversion is itself a new event -- the system does not achieve reversibility by silently mutating history. It persists another attributable step in the same ledger. The history of intervention is permanently inspectable.

Preview computes a candidate change without persisting an event. Commit persists the event and mutates the graph. Observation does not silently mutate the graph. Mutation is a separate, attributable step. Browser-local view state (layout, filters, styling, table sort) never enters the measurement ledger.

**Defined in:** `docs/MEASUREMENT_EVENT_MODEL.md`; observatory state machine modeled in `eden-idris/src/Eden/Proofs.idr` (section 14).

### Hum

Bounded continuity artifact.

**IS:** A timestamped, path-addressable export derived from already-persisted runtime surfaces (latest active-set snapshots, recent feedback events, recent membrane events). Written per session as `current_hum.md` and `current_hum.json`. Surfaced read-only through runtime session snapshots, observatory payloads, the TUI hum panel, and conversation-log footers. The artifact carries bounded motif-style entries, surface stats, and token-table rows. Enforced bounds: `max_text_chars = 320`, `max_lines = 6`, `max_recurring_items = 4`, `max_table_rows = 6`.

**IS NOT:** Input to generation, a hidden inner voice, planner residue, a generation-side control channel, the active set, the full graph, a basin summary, a cluster summary, or an observatory payload plane. Prompt injection, membrane consumption, and generation-input use of the hum remain unimplemented. No consciousness claims, no metaphysical inflation.

**Defined in:** `docs/HUM_SPEC.md`; implemented in `eden-idris/src/Eden/Hum.idr`; turn cap boundedness proven in `eden-idris/src/Eden/Proofs.idr` (section 6).

### Shamash

Conversation-to-graph bridge for external tool integration (Claude Code hooks).

**IS:** A three-phase pipeline that connects external conversations to the EDEN graph. Phase 1 (Retrieve with deliberation): query-aware context assembly that runs the Talmud layer - surfaces behavioral memes by regard, relevant knowledge memes by query keywords, dissenting positions (held tensions), connected concepts via edge traversal, coverage assessment with gap detection, and precedent from prior turns. The output is injected as additional context into the external conversation. Phase 2 (Feedback): model-classified signals update regard channels. Phase 3 (Record turn): captures the conversation exchange for precedent accumulation. Shamash runs as a hook on `UserPromptSubmit` events via a Node.js handler that calls the EDEN binary.

**IS NOT:** A standalone agent, a planner, or a generation backend. Shamash does not generate responses. It enriches the context available to whatever tool is generating. It does not bypass the membrane or modify graph state during retrieval. Feedback and turn recording are separate, explicit phases.

**Defined in:** Implemented in `eden-idris/src/Eden/Shamash.idr`; hook handler in `eden-idris/shamash-hook.js`; C FFI persistence in `eden-idris/support/eden_sqlite.c`.

---

## The Turn Loop

```
                         +------------------+
                         |  Operator Input  |
                         +--------+---------+
                                  |
                                  v
                    +----------------------------+
                    |   Retrieve & Assemble      |
                    |   (candidates from graph,  |<------+
                    |    budget allocation,       |       |
                    |    active set selection)    |       |
                    +-------------+--------------+       |
                                  |                      |
                                  v                      |
                    +----------------------------+       |
                    |      Deliberate            |       |
                    |   (Talmud layer: coverage   |       |
                    |    check, dissent surface,  |       |
                    |    edge traversal,          |       |
                    |    precedent retrieval)      |       |
                    +-------------+--------------+       |
                                  |                      |
                                  v                      |
                    +----------------------------+       |
                    |        Generate            |       |
                    |   (model inference via      |       |
                    |    selected backend)        |       |
                    +-------------+--------------+       |
                                  |                      |
                                  v                      |
                    +----------------------------+       |
                    |        Membrane            |       |
                    |   (strip, sanitize,         |       |
                    |    clamp, trace)            |       |
                    +-------------+--------------+       |
                                  |                      |
                                  v                      |
                    +----------------------------+       |
                    |    Persist Turn Data       |       |
                    |   (turn record, active set  |       |
                    |    snapshot, traces,         |       |
                    |    membrane events)          |       |
                    +-------------+--------------+       |
                                  |                      |
                                  v                      |
                    +----------------------------+       |
                    |       Feedback             |       |
                    |   (accept / reject / edit   |       |
                    |    / skip with explanation)  |       |
                    +-------------+--------------+       |
                                  |                      |
                                  v                      |
                    +----------------------------+       |
                    |     Graph Update           |       |
                    |   (regard channels,         |       |
                    |    feedback propagation,    +-------+
                    |    new memes/memodes)       |  regard
                    +----------------------------+  feeds back
```

1. **Receive operator input** through the TUI or REPL.
2. **Retrieve candidates** from the persisted graph. Score each candidate by semantic similarity, activation, regard, session bias, explicit feedback relevance, scope penalty, and membrane penalty.
3. **Assemble the bounded active set** and prompt context under the current inference profile and token budget. Inputs: constitutional seed, retrieved active-set items with provenance, recent feedback summaries, bounded recent turn history.
4. **Deliberate** over the assembled context (Talmud layer). Check query coverage against the knowledge graph, surface dissenting positions (minority opinions with low regard), traverse edges from activated memes to find connected concepts, retrieve precedent from prior turns. When coverage is low, this is reported honestly rather than suppressed. The deliberation phase enriches the context with knowledge memes, held tensions, and gap detection before generation.
5. **Generate** Adam's response through the selected backend (mock, Claude CLI, or MLX in the Python build).
6. **Apply the membrane** to the raw model output. Strip planning spills, enforce response contracts, clamp length, record membrane events.
7. **Persist** turn data, active-set snapshot, trace events, and membrane events.
8. **Accept explicit feedback.** Accept/reject require explanation; edit requires explanation plus corrected text; skip is neutral.
9. **Update graph channels** and derive new memes/memodes from feedback. Regard scores change via EMA. Propagation attenuates across related graph nodes.

The loop is linear per turn. There is no recursion, no multi-step decomposition, no hidden pre-pass. The phase machine enforces ordering at compile time: `Idle -> Assembling -> Generating -> MembraneApplied -> AwaitingFeedback -> FeedbackIntegrated`. No phase can transition to itself (6 proofs). No phase can be skipped (3 proofs). No backward transition is valid (5 proofs). These are machine-checked in `Eden.Proofs` sections 3 and 18.

---

## The Proof Architecture (Idris2)

`eden-idris/src/Eden/Proofs.idr` contains 55 machine-checked theorems across 18 sections. The entire module is declared `%default total`, meaning Idris2 verifies that every proof terminates. If any theorem fails to hold, the build fails -- the binary cannot be produced.

### What the 18 sections verify

| Section | Theorems | What it proves |
|---|---|---|
| 1. Mode resolution | 4 | `adam_auto` always resolves to `runtime_auto` (no hidden governor). `manual` is never overridden. Resolution is idempotent. Resolution never introduces `adam_auto`. |
| 2. Feedback signals | 6 | Accept yields positive reward (+1.0). Reject yields negative reward (-0.4) and maximum risk (1.0). Edit yields non-zero edit channel (0.9). Skip is neutral on reward. Accept lowers risk (-0.1). |
| 3. Phase machine | 11 | No phase can transition to itself (6 proofs). Cannot skip assembly, generation, or membrane (3 proofs). Cannot go backward (2 proofs). |
| 4. List boundedness | 3 | `take k xs` never exceeds k elements or the original list length. `selectTopK` preserves the k-bound. |
| 5. Memode admissibility | 4 | `CanMaterialize` is decidable. A list is materializable iff it has 2+ elements. Materialization implies length >= 2. Vect with 2+ elements is always admissible. |
| 6. Hum boundedness | 2 | Hum turn cap is positive. `boundTurns` never exceeds the cap. |
| 7. Pressure level coverage | 1 | Every pressure ratio maps to exactly one level (Low, Elevated, or High). |
| 8. Propagation scale | 4 | Edit propagates at 0.65. Accept, reject, and skip propagate at 0.80. |
| 9. Inference preset monotonicity | 4 | Tight budget < balanced budget < wide budget. Tight output < balanced output < wide output. |
| 10. ExplainedVerdict completeness | 5 | Every verdict can be explained. Accept, reject, and edit explanations are preserved. Skip has empty explanation. |
| 11. Membrane event coverage | 1 | Every `MembraneEventType` is showable (structural coverage over the type). |
| 12. Budget estimation | 1 | `estimateTokens` is deterministic: `(chars + 3) / 4`. |
| 13. Adaptive response cap | 1 | Low pressure preserves the base cap. |
| 14. Observatory state machine | 2 | `HasPreview` and `HasCommit` witnesses are constructible (modeling preview-before-commit, commit-before-revert). |
| 15. Regard total boundedness | 1 | Regard total is bounded to [-8, 8] via `bounded`. Proof is definitional (`Refl`). |
| 16. Selection score boundedness | 1 | Selection score is bounded to [-12, 12] via `bounded`. Proof is definitional (`Refl`). |
| 17. Feedback explanation requirement | 4 | Accept and reject carry explanations. Edit carries explanation and corrected text. Skip needs no data. |
| 18. PhasedTurn phantom enforcement | 5 | `advanceTurn` is identity on the target. Cannot jump from Idle to FeedbackIntegrated. No backward transitions from FeedbackIntegrated or MembraneApplied. |

### Proof methodology

Most proofs are definitional (`Refl`) -- the type checker confirms equality by reducing both sides. Phase machine proofs use `impossible` to demonstrate that invalid constructors cannot exist. Five proofs (of 55) use `believe_me` where the structural proof would require stdlib lemmas not available in Idris2: `drop`/`length` interaction for hum bounds, Double comparison opacity for pressure levels, and unary LTE chains of thousands of constructors for preset monotonicity. These are documented inline with the structural argument they stand for.

### Why this matters

For communities that need mathematical guarantees about runtime behavior -- safety-critical systems, governance frameworks, audit-sensitive deployments -- the proofs are verifiable by compiling the project. They are not tests that might be skipped, assertions that might be disabled at runtime, or compliance checkboxes that might be misrepresented. They are type-level propositions checked by the compiler. If the invariant is violated, the code does not compile.

What is proven at compile time:

- The turn loop follows the correct phase ordering and cannot skip or reverse steps.
- Memode materialization requires 2+ behavior-domain members, not arbitrary clustering.
- Feedback propagation respects exact attenuation bounds per verdict type.
- Phantom-tagged IDs prevent accidental mixing of MemeId, SessionId, ExperimentId, and other identity types.
- Core pipeline functions terminate (total by `%default total`).
- Regard and selection scores are bounded to finite ranges.
- Inference presets are monotonically ordered.

---

## The Observatory

The observatory is a browser-based measurement workbench for inspecting, measuring, and (in a bounded way) mutating the persistent graph. The Python implementation is authoritative for exports, clustering, basin projection, and measurement provenance. The frontend lives in `web/observatory/` (React + TypeScript + Vite + Graphology/Sigma).

### Three roles

1. **Read surface.** Inspect graph topology, regard scores, provenance, membrane events, active-set composition, feedback history, basin trajectories, geometry diagnostics, and runtime traces. Hover, pin, filter, sort, search across Overview, Data Laboratory, and Preview workspaces. No mutation.

2. **Comparison and preview surface.** Compute local motif metrics, geometry deltas, and preview baseline-vs-modified state from proposed edits. Compare slices, coordinate methods, or ablation scenarios. Preview responses expose `compare_selection` and `preview_graph_patch`. No mutation until explicit commit.

3. **Bounded mutation surface.** Add/update/remove edges with provenance. Assert known memodes. Refine memode membership. Annotate motifs. Run geometry and ablation measurements. Every mutation follows the measurement-first contract: select, propose, preview, commit, persist with provenance, refresh views. Revert explicitly if needed. Reversion is itself a new event.

The workspace grammar follows Gephi conventions: Overview (graph-first exploration), Data Laboratory (spreadsheet audit), and Preview (final-render/export). Observation does not silently mutate the graph. Mutation is a separate, attributable step. Layout, styling, filter presets, and table state are browser-local and are not evidence.

**Idris2 status:** The Idris build has `--export` for static JSON graph snapshots matching the observatory payload contract. There is no server, no live endpoints, no browser interaction in the Idris build. The static JSON can be served by any HTTP server for inspection in the observatory frontend.

---

## Implementation Comparison

The project has two implementations: a Python reference (full-featured) and an Idris2 port (machine-verified, native binary). See `docs/IDRIS_IMPLEMENTATION_STATUS.md` for the complete breakdown.

| Subsystem | Python | Idris2 | Coverage |
|---|---|---|---|
| Core turn loop + deliberation | 3,724 LOC | 357 LOC + ~300 LOC (Shamash) | 90% |
| Retrieval + Regard | ~600 LOC | ~300 LOC | 95% |
| Membrane + Feedback | ~400 LOC | ~200 LOC | 95% |
| Machine-checked proofs | 0 | 800 LOC | Idris-only (55 theorems) |
| Inference profiles | ~340 LOC | ~200 LOC | 90% |
| Storage | 1,590 LOC | 320 LOC | 40% |
| Models | 480 LOC | 130 LOC | 30% (Claude CLI only, no MLX) |
| TUI | 5,881 LOC | 620 LOC | 25% (functional, missing modals) |
| Ingest | 731 LOC | ~400 LOC | 65% |
| Graph Audit | ~750 LOC | 534 LOC | 80% |
| Tanakh | 1,590 LOC | ~250 LOC | 30% |
| Session Management | ~500 LOC | ~200 LOC | 40% |
| Observatory | 6,700+ LOC | 0 | 0% (static JSON export only) |
| Export | ~3,700 LOC | ~300 LOC | 15% |
| Concept Extraction | keyword-based | keyword + model | 110% (model-based exceeds Python) |

### Idris2-only advantages

- **55 machine-checked proofs** verifying runtime invariants at compile time.
- **Dependent types** enforcing ontology rules (memode materialization requires 2+ members, proven at the type level).
- **Phantom-tagged IDs** preventing accidental mixing of MemeId, SessionId, ExperimentId.
- **Total core functions** -- the type checker guarantees termination for pure pipeline logic.
- **Native binary** -- single 1.3MB executable, no Python/venv dependency at runtime.

---

## Links to Detailed Specs

| Document | Description |
|---|---|
| [PROJECT_CHARTER.md](PROJECT_CHARTER.md) | Mission statement, v1 thesis, and hard architectural boundaries. |
| [CANONICAL_ONTOLOGY.md](CANONICAL_ONTOLOGY.md) | First-class and derived object definitions, edge semantics, domain split, and memode admissibility rules. |
| [TURN_LOOP_AND_MEMBRANE.md](TURN_LOOP_AND_MEMBRANE.md) | The v1 direct loop steps, membrane behavior, prompt assembly inputs, and operator-visible trace. |
| [REGARD_MECHANISM.md](REGARD_MECHANISM.md) | Activation decay, coherence, evidence, reward, risk, persistence formulas; selection score; feedback update protocol. |
| [MEASUREMENT_EVENT_MODEL.md](MEASUREMENT_EVENT_MODEL.md) | Event fields, action types, preview/commit/revert semantics, runtime trace linkage, and evidence handling. |
| [GRAPH_SCHEMA.md](GRAPH_SCHEMA.md) | SQLite table definitions, key row fields, edge families, and health metrics. |
| [INFERENCE_PROFILES.md](INFERENCE_PROFILES.md) | Manual, runtime_auto, and adam_auto modes; persisted fields; session-start graph wake-up audit; MLX pass-through. |
| [OBSERVATORY_SPEC.md](OBSERVATORY_SPEC.md) | Artifact families, observatory modes, workspace grammar, graph payload planes, measurement-first contract, basin, geometry, and Tanakh surfaces. |
| [OBSERVATORY_INTERACTION_SPEC.md](OBSERVATORY_INTERACTION_SPEC.md) | Constructive measurement instrument contract, workspace interaction controls, preview/commit/revert flow. |
| [OBSERVATORY_GEOMETRY_SPEC.md](OBSERVATORY_GEOMETRY_SPEC.md) | Geometry diagnostics, slice views, local selection measurement, and metric evidence labels. |
| [OBSERVATORY_E2E_AUDIT.md](OBSERVATORY_E2E_AUDIT.md) | Playwright browser journey audit results for live and static modes. |
| [GEOMETRY_EVIDENCE_POLICY.md](GEOMETRY_EVIDENCE_POLICY.md) | Evidence labeling for geometry metrics: OBSERVED, DERIVED, and SPECULATIVE. |
| [TUI_SPEC.md](TUI_SPEC.md) | Terminal user interface layout, boot flow, panels, composer, action shelf, and runtime telemetry. |
| [HUM_SPEC.md](HUM_SPEC.md) | Hum artifact contract, implemented surface, token table, and what remains unimplemented. |
| [DOCUMENT_INGEST.md](DOCUMENT_INGEST.md) | Supported formats, extraction order, chunking, and quality scoring for document ingestion. |
| [EXPERIMENT_PROTOCOLS.md](EXPERIMENT_PROTOCOLS.md) | Persistent graph contract, session lifecycle, and document ingest flow. |
| [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) | Current limitations: model fallbacks, budget bounds, extraction quality, geometry approximations. |
| [IMPLEMENTATION_TRUTH_TABLE.md](IMPLEMENTATION_TRUTH_TABLE.md) | Per-capability implementation status with evidence references. |
| [IDRIS_IMPLEMENTATION_STATUS.md](IDRIS_IMPLEMENTATION_STATUS.md) | Idris2 port coverage, recently completed modules, and gaps relative to the Python reference. |
| [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) | Prioritized roadmap for remaining work organized by tier. |
| [WHY_THIS_MATTERS.md](WHY_THIS_MATTERS.md) | Governance gap analysis and the case for externalized identity. |
| [TRADITION_EMBEDDING_GUIDE.md](TRADITION_EMBEDDING_GUIDE.md) | Pattern for embedding community-specific interpretive traditions into the runtime. |
| [GETTING_STARTED.md](GETTING_STARTED.md) | First interaction walkthrough: build, converse, give feedback, export. |
| [FIRST_RUN_QUICKSTART.md](FIRST_RUN_QUICKSTART.md) | Minimal steps to launch and use Adam for the first time. |
| [USER_JOURNEYS.md](USER_JOURNEYS.md) | Operator journeys verified against the live TUI. |
| [HOW_TO_USE_ADAM_TUI.md](HOW_TO_USE_ADAM_TUI.md) | Operator manual for the terminal interface. |
| [SOURCE_MANIFEST.md](SOURCE_MANIFEST.md) | Source artifact inventory and authority levels for the build. |
| [HUM_TROUBLESHOOTING_GUIDE.md](HUM_TROUBLESHOOTING_GUIDE.md) | Diagnosing hum artifact claims against implementation evidence. |
| [UX_AUDIT_AND_REPAIRS.md](UX_AUDIT_AND_REPAIRS.md) | UX audit findings and repair log from live testing. |
| [MIGRATION_NOTES_V1_1.md](MIGRATION_NOTES_V1_1.md) | Additive SQLite schema changes for v1.1. |
| [PATCH_MANIFEST_V1_1.md](PATCH_MANIFEST_V1_1.md) | Scope and changes for the v1.1 reliability/observability patch. |
| [PATCH_MANIFEST_V1_2.md](PATCH_MANIFEST_V1_2.md) | Scope and changes for the v1.2 measurement-instrument patch. |
| [integrate-sqlite.md](integrate-sqlite.md) | SQLite integration notes for the Idris2 build. |
