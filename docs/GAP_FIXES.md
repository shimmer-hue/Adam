# EDEN Gap Fixes — Spec Compliance Punch List

Tracked gaps between normative specs and Idris2 implementation.
Each item has a status: `[ ]` pending, `[x]` done, `[-]` deferred.

Last audited: 2026-04-07 (branch `david`, post gap-fix session).

---

## 1. Regard Formula Compliance

**Spec:** `REGARD_MECHANISM.md`
**File:** `eden-idris/src/Eden/Regard.idr`, `eden-idris/src/Eden/Types.idr`

### 1.1 NodeState fields
- [x] `nsFeedbackCount : Nat`
- [x] `nsEditEma : Double`
- [x] `nsContradictionCount : Nat`
- [x] `nsMembraneConflicts : Nat`
- [x] All construction sites updated (12 files)

### 1.2 evidenceScore formula
- [x] Signature: `Double -> Nat -> Nat -> Double`
- [x] Body: `log(1 + evidenceN + cast usageCount + 0.5 * cast feedbackCount)`

### 1.3 rewardScore formula
- [x] Signature: `Double -> Double -> Double`
- [x] Body: `bounded (-2.0) 2.0 (rewardEma + 0.35 * editEma)`

### 1.4 riskScore formula
- [x] Signature: `Double -> Nat -> Nat -> Double`
- [x] Body: `bounded 0.0 2.0 (riskEma + 0.35 * cast cc + 0.3 * cast mc)`

### 1.5 regardBreakdown + Proofs
- [x] `regardBreakdown` passes new NodeState fields
- [x] `regardUsesBounded` proof updated for new signatures

### 1.6 Graph metrics from real topology
- [x] `computeGraphMetrics` in `Store/InMemory.idr` computes clustering coefficient, normalized degree, triangle participation from edge store
- [x] `mRetrieve` in `Pipeline.idr` calls `computeGraphMetrics` instead of hardcoded `MkGraphMetrics 0.5 0.4 0.3`
- [x] TUI `/regard` command uses real graph metrics

---

## 2. Core Pipeline

### 2.1 Profile-driven history depth + generation params
**Spec:** `INFERENCE_PROFILES.md`
**File:** `eden-idris/src/Eden/Pipeline.idr`
- [x] `mExecuteTurnWith` takes `historyDepth : Nat` parameter, used for `mAssembleWith`
- [x] TUI passes `prof'.spHistTurns` from session profile
- [x] `top_p` and `repetition_penalty` from `ResolvedProfile` wired into `mGenerateWith`

### 2.2 Feedback propagation to memodes
**Spec:** `REGARD_MECHANISM.md` §feedback-propagation
**File:** `eden-idris/src/Eden/Pipeline.idr`
- [x] Memodes read and logged in feedback propagation
- [x] Constituent memes (via MemberOf edges) get 0.85 attenuation; non-constituent get 0.5
- [-] Direct memode-first signal deferred (memode channels not yet per-memode)
- [-] Re-ingest feedback text as behavior meme material deferred

### 2.3 Budget-aware history trimming
**Spec:** `INFERENCE_PROFILES.md` §budget-envelope
**File:** `eden-idris/src/Eden/Pipeline.idr`, `eden-idris/src/Eden/Budget.idr`
- [-] Deferred: after active set + feedback + operator text, trim history against remaining budget

### 2.4 Edge types
- [x] `Reinforces`, `Refines`, `ContextualizesDocument`, `FedBackBy`, `OccursIn`
- [x] `Show`, `Eq`, `edgeTypeFromString` updated

### 2.5 Memode admissibility floor
**Spec:** `CANONICAL_ONTOLOGY.md` §memode-admissibility
**File:** `eden-idris/src/Eden/GraphAudit.idr`
- [x] `findInadmissible` validates member memes have >= 1 qualifying support edge
- [x] Support edge types: Supports, Reinforces, CoOccursWith, RelatesTo, Influences, DerivedFrom
- [x] Memodes with inadmissible members skipped during audit
- [-] Connected subgraph validation deferred

### 2.6 Session wakeup audit trace events
**Spec:** `TURN_LOOP_AND_MEMBRANE.md` §wake-up
**File:** `eden-idris/src/Eden/GraphAudit.idr`
- [x] `emitAuditTrace` and `formatReportSummary` emit TraceGraphNormalization, TraceGraphTaxonomy, TraceGraphCoherence
- [x] `runSessionStartAudit` gated by `EDEN_ENABLE_MLX_WAKEUP_REVIEW` env var

### 2.7 Membrane: fail closed on reasoning-only response
**Spec:** `TURN_LOOP_AND_MEMBRANE.md` §membrane
**File:** `eden-idris/src/Eden/Membrane.idr`
- [x] `splitReasoning` handles both `<think>...</think>` and `reasoning</think>body` formats
- [x] Fail-closed: if body is empty after all processing, returns fallback message

### 2.8 Document chunks retrieval
**Spec:** `TURN_LOOP_AND_MEMBRANE.md` §retrieve, `DOCUMENT_INGEST.md`
**File:** `eden-idris/src/Eden/Retrieval.idr`, `eden-idris/src/Eden/Pipeline.idr`
- [x] `scoreChunkCandidate` scores chunks as retrieval candidates with `nodeKind=ChunkNode`
- [x] `mRetrieve` merges chunk candidates with meme candidates via `selectTopK`

---

## 3. TUI

### 3.1 Action strip Enter-to-execute
- [x] `handleNormalKey ui KeyEnter` checks `uiActionFocus` and dispatches

### 3.2 Session resume on boot
- [x] Checks for existing sessions; resumes latest

### 3.3 Reasoning lens tabs
- [x] `uiReasoningTab` with 3 tabs (Reasoning/Chain-Like/Hum Live)
- [x] Ctrl+R cycles tabs
- [x] Tab bar rendering

### 3.4 Action strip focus marker
- [x] `>>` marker rendered on focused action

### 3.5 Stored-feedback collapse
**File:** `eden-idris/src/Eden/TUI.idr`
- [x] After feedback recorded, shows "feedback: <verdict> @ <timestamp>" block

### 3.6 F7 inline review — verdict flow
**File:** `eden-idris/src/Eden/TUI.idr`
- [x] F7 presents accept/edit/reject/skip verdict prompt
- [x] Edit opens EditModal with response buffer
- [x] Verdict records feedback, updates hum, shows confirmation

### 3.7 F5 proper new session
**File:** `eden-idris/src/Eden/TUI.idr`
- [x] F5 creates new session object via `createSession`
- [x] Opens ConfigModal after session creation

### 3.8 Conversation log export wiring
**File:** `eden-idris/src/Eden/TUI.idr`
- [x] F2 calls `writeConversationLog` from Session module
- [x] Output path: `data/export/<sid>-conversation.md`

### 3.9 Digit-to-action jump
**File:** `eden-idris/src/Eden/TUI.idr`
- [x] When action strip focused, digits 0-9 jump to that action selection index

### 3.10 Compact budget strip in topbar
**File:** `eden-idris/src/Eden/TUI.idr`
- [x] Context budget panel shows pressure, used/remaining tokens, item count, budget mode
- [x] Runtime status line shows budget=pressure + used tokens inline

### 3.11 Live turn-status strip
**File:** `eden-idris/src/Eden/TUI.idr`
- [x] `uiTurnPhase` set to "assembling" / "generating" / "idle" during turn execution
- [x] Phase indicator rendered in runtime status line when not idle

### 3.12 Reasoning panel scroll
**File:** `eden-idris/src/Eden/TUI.idr`
- [x] `uiReasoningScroll : IORef Int` tracks scroll offset
- [x] Ctrl+U scrolls up, Ctrl+D scrolls down (3 lines)
- [x] Chain-Like tab applies scroll offset to beat list

### 3.13 Config modal clamps
**File:** `eden-idris/src/Eden/TUI.idr`
- [x] max_output: `max 128 (min 4096 raw)` — bounds 128..4096
- [x] response_cap: `max 600 (min 12000 raw)` — bounds 600..12000
- [x] history_turns: `max 1 (min 256 raw)` — bounds 1..256

---

## 4. Observatory

### 4.1 Experiment-scoped endpoints
**Spec:** `OBSERVATORY_SPEC.md` §api-routes
**File:** `eden-idris/src/Eden/Observatory.idr`
- [x] `GET /api/experiments` listing
- [x] `GET /api/experiments/<id>/memes`
- [x] `GET /api/experiments/<id>/sessions`
- [x] `GET /api/experiments/<id>/graph`
- [-] `GET /api/experiments/<id>/payload` deferred
- [-] `GET /api/experiments/<id>/overview` deferred
- [-] Scope basin, geometry, measurements under experiment ID deferred

### 4.2 Export payload planes
**Spec:** `OBSERVATORY_SPEC.md` §graph-payload
**File:** `eden-idris/src/Eden/Export.idr`
- [x] `assembly_nodes` and `assembly_edges` planes (empty placeholder)
- [x] `memode_audit` plane with id, label, member_count, admissible
- [x] Graph metadata: `layout_families`, `layout_catalog`, `layout_defaults`, `appearance_dimensions`, `filter_dimensions`, `statistics_capabilities`, `export_formats`
- [-] Actual assembly data population deferred

### 4.3 Geometry lab
**Spec:** `OBSERVATORY_SPEC.md` §geometry, `OBSERVATORY_GEOMETRY_SPEC.md`
- [-] Deferred: projection methods, symmetry diagnostics, ablation support require non-trivial math libraries

### 4.4 Basin projection
**Spec:** `OBSERVATORY_SPEC.md` §basin
- [-] Deferred: real turn-trajectory projection, per-turn overlays

### 4.5 Missing measurement action types
**Spec:** `OBSERVATORY_INTERACTION_SPEC.md`, `MEASUREMENT_EVENT_MODEL.md`
**File:** `eden-idris/src/Eden/Types.idr`
- [x] `MemodeUpdateMembership`, `MotifAnnotation`, `GeometryMeasurementRun`, `AblationMeasurementRun` added to enum
- [x] `Show` instance updated
- [-] Observatory commit flow handlers deferred

---

## 5. Data Model

### 5.1 Metadata JSON fields
**Spec:** `GRAPH_SCHEMA.md`
**File:** `eden-idris/src/Eden/Types.idr`
- [x] `metadataJson` on Document
- [x] `metadataJson` on Chunk
- [x] `provenanceJson` on Edge
- [x] `metadataJson` on Meme
- [x] `metadataJson` on Memode

### 5.2 Session metadata audit fields
**Spec:** `TURN_LOOP_AND_MEMBRANE.md` §wake-up
**File:** `eden-idris/src/Eden/Session.idr`
- [x] `smAuditNormalization`, `smAuditTaxonomy`, `smAuditCoherence`, `smAuditWakeup` fields added
- [x] `updateAuditFields` function implemented

### 5.3 Turn metadata fields
- [x] `profileName`, `selectionSource`, `countMethod` added

### 5.4 Config modal profile fields
- [x] `top_p`, `repetition_penalty`, `max_context_items` added to `SessionProfile`
- [x] Config modal rows for these fields

### 5.5 MeasurementEvent spec fields
**Spec:** `MEASUREMENT_EVENT_MODEL.md`
**File:** `eden-idris/src/Eden/Types.idr`
- [x] `turnId`, `targetIdsJson`, `rationale`, `operatorLabel`, `measurementMethod`, `confidence` added
- [x] Deserialization handles legacy (12-field) and new (18-field) formats

### 5.6 Evidence and provenance labels
**Spec:** `MEASUREMENT_EVENT_MODEL.md` §evidence-labels
**File:** `eden-idris/src/Eden/Types.idr`
- [x] `EvidenceLabel` enum: Observed, Derived, Speculative with Show/Eq
- [x] `ProvenanceLabel` enum: OperatorAsserted, OperatorRefined, AutoDerived with Show/Eq

### 5.7 Graph health metrics
**Spec:** `GRAPH_SCHEMA.md` §health-metrics
**File:** `eden-idris/src/Eden/Store/InMemory.idr`
- [x] `GraphHealthReport` record: isolated count, dyad ratio, feedback coverage, avg edges, totals
- [x] `getGraphHealth` computes metrics from edge store

### 5.8 FTS for memodes and chunks
**Spec:** `GRAPH_SCHEMA.md` §fts
**File:** `eden-idris/src/Eden/Store/InMemory.idr`
- [x] `ftsSearchMemodes` tokenizes query, matches against memode label+summary, ranks by hit count
- [x] `ftsSearchChunks` tokenizes query, matches against chunk text, ranks by hit count

---

## 6. Miscellaneous

### 6.1 Environment variable gate
**Spec:** `INFERENCE_PROFILES.md` §mlx-gate
**File:** `eden-idris/src/Eden/GraphAudit.idr`
- [x] `runSessionStartAudit` checks `EDEN_ENABLE_MLX_WAKEUP_REVIEW` — skips audit if not set to "1" or "true"

### 6.2 MLX contextualization pass
**Spec:** `DOCUMENT_INGEST.md` §contextualization
**File:** `eden-idris/src/Eden/Ingest/Pipeline.idr`
- [-] Deferred: Adam-identity MLX contextualization pass during ingest

### 6.3 Hum derivedFrom format
**Spec:** `HUM_SPEC.md`
**File:** `eden-idris/src/Eden/Hum.idr`
- [x] Uses canonical source names: `turns.active_set_json`, `feedback_events`, `membrane_events`

### 6.4 Hum markdown markers
**Spec:** `HUM_SPEC.md`
**File:** `eden-idris/src/Eden/Export.idr`
- [x] Uses exact `[HUM_STATS]`, `[HUM_METRICS]`, `[HUM_TABLE]` markers

### 6.5 Typewriter Light theme
**Spec:** `TUI_SPEC.md` §themes
**File:** `eden-idris/src/Eden/Term.idr`
- [x] `typewriterLight` theme defined with light background/ink-on-paper colors
- [x] Added to `allThemes`, `nextThemeName`, `lookupTheme`

### 6.6 Operator turn prefix
**Spec:** `TUI_SPEC.md` §dialogue-tape
**File:** `eden-idris/src/Eden/TUI.idr`
- [x] User messages prefixed with "[operator T..." in dialogue tape

### 6.7 Printable key routing to composer
**Spec:** `TUI_SPEC.md` §input-routing
**File:** `eden-idris/src/Eden/TUI.idr`
- [x] When action strip focused: digits route to action index, other printable keys route to composer

### 6.8 Memode default tau
**Spec:** `REGARD_MECHANISM.md` §activation-decay
**File:** `eden-idris/src/Eden/Regard.idr`
- [x] `memodeDefaultTau = 172800.0` (2 days) and `memeDefaultTau = 86400.0` (1 day) exported

---

## Priority Order

1. **CRITICAL** (2 items): §1.6 ✅, §2.1 ✅
2. **HIGH** (12 items): §2.2 ✅, §2.5 ✅, §2.6 ✅, §2.7 ✅, §2.8 ✅, §3.6 ✅, §3.7 ✅, §3.8 ✅, §4.1 partial, §4.2 partial, §5.1 ✅, §5.2 ✅
3. **MEDIUM** (14 items): §2.3 deferred, §3.5 ✅, §3.9 ✅, §3.10 ✅, §3.11 ✅, §3.12 ✅, §3.13 ✅, §4.3 deferred, §4.4 deferred, §4.5 partial, §5.5 ✅, §5.6 ✅, §5.7 ✅, §5.8 ✅
4. **LOW** (6 items): §6.1 ✅, §6.2 deferred, §6.3 ✅, §6.4 ✅, §6.5 ✅, §6.6 ✅, §6.7 ✅, §6.8 ✅

Total: 45 done, 7 deferred.
