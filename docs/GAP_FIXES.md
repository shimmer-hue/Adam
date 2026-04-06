# EDEN Gap Fixes — Spec Compliance Punch List

Tracked gaps between normative specs and Idris2 implementation.
Each item has a status: `[ ]` pending, `[x]` done, `[-]` deferred.

---

## 1. Critical — Regard Formula Noncompliance

**Spec:** `REGARD_MECHANISM.md`
**File:** `eden-idris/src/Eden/Regard.idr`, `eden-idris/src/Eden/Types.idr`

### 1.1 NodeState missing fields
- [ ] Add `nsFeedbackCount : Nat` to NodeState
- [ ] Add `nsEditEma : Double` to NodeState
- [ ] Add `nsContradictionCount : Nat` to NodeState
- [ ] Add `nsMembraneConflicts : Nat` to NodeState
- [ ] Update all NodeState construction sites (Pipeline, TUI, Retrieval, etc.)

### 1.2 evidenceScore formula
- [ ] Change signature to `evidenceScore : Double -> Nat -> Nat -> Double`
- [ ] Implement: `log(1 + evidenceN + cast usageCount + 0.5 * cast feedbackCount)`

### 1.3 rewardScore formula
- [ ] Change signature to `rewardScore : Double -> Double -> Double`
- [ ] Implement: `bounded (-2.0) 2.0 (rewardEma + 0.35 * editEma)`

### 1.4 riskScore formula
- [ ] Change signature to `riskScore : Double -> Nat -> Nat -> Double`
- [ ] Implement: `bounded 0.0 2.0 (riskEma + 0.35 * cast contradictionCount + 0.3 * cast membraneConflicts)`

### 1.5 regardBreakdown caller updates
- [ ] Update `regardBreakdown` to pass new NodeState fields to sub-formulas
- [ ] Update all callers constructing NodeState (add zero defaults)

---

## 2. High — Core Pipeline

### 2.1 Session wakeup audit integration
**Spec:** `TURN_LOOP_AND_MEMBRANE.md` lines 14-41
**File:** `eden-idris/src/Eden/TUI.idr`, `eden-idris/src/Eden/Monad.idr`
- [ ] Call `runSessionStartAudit` at session start in TUI (already done — verify)
- [ ] Record trace events: GRAPH_NORMALIZATION, GRAPH_TAXONOMY_AUDIT, GRAPH_COHERENCE_REWEAVE
- [ ] Store session metadata fields for audit results

### 2.2 Feedback propagation to memodes
**Spec:** `REGARD_MECHANISM.md` lines 82-85
**File:** `eden-idris/src/Eden/Pipeline.idr`
- [ ] Apply feedback to memodes before memes (direct signal)
- [ ] Scale inherited signal to constituent memes
- [ ] Re-ingest feedback text as behavior-domain meme material

### 2.3 Budget-aware history trimming
**Spec:** `INFERENCE_PROFILES.md` lines 109-110
**File:** `eden-idris/src/Eden/Pipeline.idr`, `eden-idris/src/Eden/Budget.idr`
- [ ] Replace hardcoded `eGetRecentTurns 3` with profile-driven depth
- [ ] Trim history against remaining budget after active set + feedback + operator text

### 2.4 Missing edge types
**Spec:** `GRAPH_SCHEMA.md`, `CANONICAL_ONTOLOGY.md`
**File:** `eden-idris/src/Eden/Types.idr`
- [ ] Add `Reinforces` edge type
- [ ] Add `Refines` edge type
- [ ] Add `ContextualizesDocument` edge type
- [ ] Add `FedBackBy` edge type
- [ ] Add `OccursIn` edge type
- [ ] Update `Show EdgeType`, `Eq EdgeType`, `edgeTypeFromString`

### 2.5 Memode admissibility floor
**Spec:** `CANONICAL_ONTOLOGY.md` line 52
**File:** `eden-idris/src/Eden/GraphAudit.idr`
- [ ] Validate every member meme has >= 1 qualifying support edge
- [ ] Validate member support subgraph is connected
- [ ] Guard against knowledge-node memode materialization

---

## 3. High — TUI

### 3.1 Action strip Enter-to-execute
**Spec:** `TUI_SPEC.md` boot flow
**File:** `eden-idris/src/Eden/TUI.idr`
- [ ] In `handleNormalKey ui KeyEnter`, check `uiActionFocus`; if true, dispatch selected action via `handleFKey`

### 3.2 Session resume on boot
**Spec:** `TUI_SPEC.md` boot flow lines 8-11
**File:** `eden-idris/src/Eden/TUI.idr`
- [ ] On startup, check for existing sessions; resume latest instead of always creating new

### 3.3 Reasoning lens tabs
**Spec:** `TUI_SPEC.md` lines 86-91
**File:** `eden-idris/src/Eden/TUI.idr`
- [ ] Add `uiReasoningTab : IORef Nat` to UIState (0=Reasoning, 1=Chain-Like, 2=Hum Live)
- [ ] Wire tab switching (e.g., F-key or number in reasoning panel)
- [ ] Render Reasoning tab: response material, reasoning signal, runtime condition, membrane record
- [ ] Render Chain-Like tab: numbered beats from answer
- [ ] Render Hum Live tab: hum entries, stats, metrics, table

### 3.4 Action strip focus marker
**Spec:** `TUI_SPEC.md` line 183
**File:** `eden-idris/src/Eden/TUI.idr`
- [ ] Render `>>` marker on focused action in strip

### 3.5 Stored-feedback collapse
**Spec:** `TUI_SPEC.md` lines 171-176
**File:** `eden-idris/src/Eden/TUI.idr`
- [ ] After feedback is recorded, show verdict/timestamp block instead of clearing

---

## 4. High — Observatory

### 4.1 Experiment-scoped endpoints
**Spec:** `OBSERVATORY_SPEC.md` lines 314-334
**File:** `eden-idris/src/Eden/Observatory.idr`
- [ ] Add `/api/experiments` listing
- [ ] Add `/api/experiments/<id>/payload`
- [ ] Add `/api/experiments/<id>/overview`
- [ ] Scope basin, geometry, measurements under experiment ID
- [ ] Scope preview/commit/revert under experiment ID

### 4.2 Geometry lab slices
**Spec:** `OBSERVATORY_SPEC.md` lines 254-269
**File:** `eden-idris/src/Eden/Observatory.idr`
- [ ] Add `current_session` slice
- [ ] Add `current_active_set` slice
- [ ] Accept `?slice=` query parameter on geometry endpoint

### 4.3 Basin projection metadata
**Spec:** `OBSERVATORY_SPEC.md` lines 227-252
**File:** `eden-idris/src/Eden/Observatory.idr`
- [ ] Add `projection_input_hash`
- [ ] Add `source_turn_count` and `filtered_turn_count`
- [ ] Add per-turn overlay fields (dominant node, dominant memode, attractor label)

---

## 5. Medium — Data Model

### 5.1 Metadata JSON fields on records
**Spec:** `GRAPH_SCHEMA.md`
**File:** `eden-idris/src/Eden/Types.idr`
- [ ] Add `metadataJson : String` to Document record
- [ ] Add `metadataJson : String` to Chunk record
- [ ] Add `metadataJson : String` to Meme record (entity_type, relation_role, candidate_kind)
- [ ] Add `metadataJson : String` to Memode record (member_ids, supporting_edge_ids)
- [ ] Add `provenanceJson : String` to Edge record

### 5.2 Session metadata audit fields
**Spec:** `TURN_LOOP_AND_MEMBRANE.md` lines 37-41
**File:** `eden-idris/src/Eden/Session.idr`
- [ ] Add `graphNormalization`, `graphTaxonomy`, `graphCoherence`, `graphWakeup` to session metadata

### 5.3 Turn metadata missing fields
**Spec:** `INFERENCE_PROFILES.md` lines 50-59
**File:** `eden-idris/src/Eden/Types.idr`
- [ ] Add `profileName : String` to TurnMetadata
- [ ] Add `selectionSource : String` to TurnMetadata
- [ ] Add `countMethod : String` to TurnMetadata

### 5.4 Config modal missing profile fields
**Spec:** `TUI_SPEC.md` lines 55-67
**File:** `eden-idris/src/Eden/TUI.idr`, `eden-idris/src/Eden/Session.idr`
- [ ] Add `top_p`, `repetition_penalty`, `max_context_items` to SessionProfile
- [ ] Add corresponding config modal rows
- [ ] Enforce clamps: max_output 128..4096, history_turns 1..256, response_char_cap 600..12000

---

## 6. Medium — Miscellaneous

### 6.1 Conversation log markdown export
**Spec:** `TUI_SPEC.md` lines 177-178
**File:** `eden-idris/src/Eden/Export.idr`
- [ ] Write markdown transcript to `exports/conversations/<session_id>.md`

### 6.2 Environment variable gate
**Spec:** `INFERENCE_PROFILES.md` lines 84-87
**File:** `eden-idris/src/Eden/GraphAudit.idr`
- [ ] Check `EDEN_ENABLE_MLX_WAKEUP_REVIEW` before MLX calls in wakeup audit

---

## Execution Order

1. **Regard formulas** (1.1-1.5) — affects every retrieval/feedback cycle
2. **Edge types** (2.4) — needed by admissibility and audit
3. **Data model fields** (5.1-5.3) — needed by pipeline and observatory
4. **Pipeline fixes** (2.1-2.3, 2.5) — depends on updated types
5. **TUI fixes** (3.1-3.5) — user-facing
6. **Observatory fixes** (4.1-4.3) — user-facing
7. **Medium items** (5.4, 6.1-6.2) — polish
