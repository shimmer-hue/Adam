# Measurement Event Model

Measurement events are the persistence bridge between browser-side observation and graph mutation.

## Event fields

- `id`
- `experiment_id`
- `session_id`
- `turn_id`
- `action_type`
- `target_ids_json`
- `before_state_json`
- `proposed_state_json`
- `committed_state_json`
- `rationale`
- `operator_label`
- `evidence_label`
- `measurement_method`
- `confidence`
- `created_at`
- `reverted_from_event_id`

For `motif_annotation` targeting a derived cluster instance, `committed_state_json.annotation` carries:

- `target.kind = "cluster"`
- `cluster_signature`
- `source_graph_hash`
- `algorithm_version`
- `manual_label`
- `manual_summary`
- `transfer_policy`

## Action types

Supported in v1.2:

- `edge_add`
- `edge_update`
- `edge_remove`
- `memode_assert`
- `memode_update_membership`
- `motif_annotation`
- `geometry_measurement_run`
- `ablation_measurement_run`
- `revert`

## Semantics

- Preview computes a candidate change and its metric deltas but does not persist an event.
- Preview responses may expose `compare_selection` and `preview_graph_patch` so the browser can render baseline vs modified state without committing.
- Commit persists the event and, when applicable, mutates the graph.
- Revert persists a new `revert` event. Reversion is itself part of the measurement ledger.
- Commits and reverts also emit runtime trace events whose payloads link back to the committed `measurement_event_id`.
- Browser view presets are never measurement events. They stay in browser-local state.
- Browser-local layouts, appearance controls, filter presets, layout snapshots, and Data Lab table state are never measurement events. They stay in browser-local state.
- Tanakh tool-surface runs are not measurement events in v1.2. They persist as Tanakh sidecar artifacts (`tanakh_surface.json`, `tanakh_measurements.json`, scene/passsage/validation sidecars) until a first-class schema extension is specified and proved.

## Runtime trace linkage

- `GET /api/sessions/<session_id>/trace` exposes the browser-visible runtime bridge for observatory work.
- The trace payload carries:
  - `latest_turn_trace`
  - `trace_events`
  - `membrane_events`
- These trace surfaces are evidence of runtime causality and attribution. They are not additional mutation paths.

## Evidence handling

- `OBSERVED`, `DERIVED`, and `SPECULATIVE` remain geometry evidence labels.
- `OPERATOR_ASSERTED`, `OPERATOR_REFINED`, and `AUTO_DERIVED` describe graph-fact provenance.
- A measurement event may use either family where appropriate, but the UI keeps the distinction visible.
