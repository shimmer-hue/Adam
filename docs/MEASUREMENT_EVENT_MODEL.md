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
- Commit persists the event and, when applicable, mutates the graph.
- Revert persists a new `revert` event. Reversion is itself part of the measurement ledger.

## Evidence handling

- `OBSERVED`, `DERIVED`, and `SPECULATIVE` remain geometry evidence labels.
- `OPERATOR_ASSERTED`, `OPERATOR_REFINED`, and `AUTO_DERIVED` describe graph-fact provenance.
- A measurement event may use either family where appropriate, but the UI keeps the distinction visible.
