# Graph Schema

EDEN v1 uses SQLite for local reliability, with graph semantics implemented in domain tables plus a generalized `edges` table.

## Persistence choice

- Storage engine: SQLite with WAL mode
- Search layer: SQLite FTS5 for memes, memodes, and document chunks
- Graph analytics: NetworkX over persisted rows at query/export time

## Core tables

- `experiments`
- `agents`
- `sessions`
- `turns`
- `feedback_events`
- `documents`
- `document_chunks`
- `memes`
- `memodes`
- `edges`
- `active_sets`
- `trace_events`
- `membrane_events`
- `export_artifacts`
- `config_store`

## Key row fields

### `experiments`

- Internal graph namespace anchor retained for runtime compatibility
- current operator contract collapses to one persistent primary graph
- `metadata_json.graph_role = "primary"` marks the active graph identity

### `sessions`

- `title`, `created_at`, `updated_at`
- `metadata_json.requested_inference_profile`
- `metadata_json.archive.folder`
- `metadata_json.archive.tags`

### `documents`

- `path`, `kind`, `title`, `sha256`, `status`
- canonical identity now enforced at `(experiment_id, sha256)`
- `metadata_json.source_kind`, `metadata_json.source_path`
- `metadata_json.parser_strategy`
- `metadata_json.quality_score`, `metadata_json.quality_state`, `metadata_json.quality_flags`
- `metadata_json.selected_parser_counts`

### `document_chunks`

- `chunk_index`, `page_number`, `text`
- `metadata_json.parser`, `metadata_json.page_number`
- `metadata_json.quality_score`, `metadata_json.quality_flags`

### `memes`

- `label`, `canonical_label`, `text`, `domain`, `source_kind`, `scope`
- `evidence_n`, `usage_count`, `reward_ema`, `risk_ema`, `edit_ema`
- `feedback_count`, `skip_count`, `contradiction_count`, `membrane_conflicts`
- `activation_tau`, `last_active_at`

### `memodes`

- `label`, `member_hash`, `summary`, `domain`, `scope`
- `metadata_json.member_ids`
- `evidence_n`, `usage_count`, `reward_ema`, `risk_ema`, `edit_ema`
- `feedback_count`, `activation_tau`, `last_active_at`

### `edges`

- `src_kind`, `src_id`, `dst_kind`, `dst_id`
- `edge_type`, `weight`
- `provenance_json`
- current persisted relation families include support edges (`CO_OCCURS_WITH`, `SUPPORTS`, `REINFORCES`, `REFINES`, `CONTRADICTS`), informational knowledge edges (`AUTHOR_OF`, `INFLUENCES`, `REFERENCES`), document/runtime edges, and explicit memode materialization / membership edges (`MATERIALIZES_AS_MEMODE`, `MEMODE_HAS_MEMBER`)

## Health metrics derived on demand

- isolated meme count
- dyad ratio
- triadic closure / transitivity
- memode coverage
- per-meme degree, clustering, triangle count, component size, memode participation

## Why this shape

- Graph semantics remain explicit and inspectable.
- Local bootstrap stays reliable on Apple Silicon without adding an external graph server.
- Operator-facing runtime now treats the store as one persistent Adam graph even though the compatibility table name remains `experiments`.
- Retrieval and exports can still operate over a real, persistent graph abstraction.
