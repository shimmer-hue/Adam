# Document Ingest

## Supported formats

- PDF
- CSV
- TXT
- Markdown

## Extraction order

### PDF

EDEN now evaluates page candidates from:

1. `pdfplumber`
2. `pypdf`
3. `pdftotext -layout` when available

The extractor normalizes ligatures and line-wrap artifacts, scores each parser candidate per page, then selects the best page-level text before chunking. Failure is explicit if no parser yields usable text or if the scored document quality falls below the minimum usable threshold.

### CSV

- parsed row-by-row
- normalized into pipe-delimited text chunks

### TXT / Markdown

- decoded with replacement on bad bytes
- chunked by sentence boundaries

## Pipeline

1. Create or update a `documents` record.
2. Canonicalize document identity by `(experiment_id, sha256)` so repeated ingest attempts update one persistent document row instead of accumulating duplicate `documents` rows.
3. Stream page-like text units from the extractor instead of materializing the full document payload before storage.
4. Chunk text into manageable blocks.
5. Store `document_chunks` with parser, page provenance, and extraction-quality metadata as chunk materialization progresses.
6. Use persisted `document_chunks` as a direct retrieval substrate, so prompt assembly can surface source-grounded evidence even when heuristic meme labels are noisy or conversational graph chatter is semantically closer to the current query.
7. Extract top phrases heuristically into compatibility-table semantic units. Behavior-domain material projects outward as performative `meme`; knowledge-domain material projects outward as constative `information`.
8. Add bounded auto-derived relation edges inside each chunk when explicit surface rules fire (`AUTHOR_OF`, `INFLUENCES`, `REFERENCES` today), then add `CO_OCCURS_WITH` fallback edges across the chunk-local member set.
9. Materialize a memode only when a behavior-domain chunk yields at least two behavior memes plus at least one qualifying support edge, and persist explicit `MEMODE_HAS_MEMBER` membership edges from the memode to its member memes together with `supporting_edge_ids`.
10. When the live backend is MLX and the local model is ready, run a bounded Adam-identity contextualization pass over sampled document chunks plus related existing graph experience:
   - the model does not rewrite the document's constative knowledge ingest
   - instead it proposes behavior-domain contextualization memes and, when grounded, one behavior memode describing how the document should live in Adam's graph
   - contextualization output is persisted as `CONTEXTUALIZES_DOCUMENT` edges plus ordinary behavior memes/memodes with explicit `contextualization_origin` and confidence metadata
   - when MLX is unavailable, abstains, or produces invalid JSON, ingest falls back to the deterministic knowledge path without inventing machine-authored behavior context
11. Mark the document `ingested` on success or `failed` with error and extraction-quality metadata if extraction/ingest aborts.
12. If a document or turn-attached behavior bundle predates the newer audit logic, session-start graph wake-up can later:
    - upgrade persisted knowledge rows by materializing missing `information` entities plus typed informational edges from the already-stored text
    - derive bounded behavior memodes from already-persisted behavior bundles when qualifying support edges exist
    without forcing a full re-ingest.

## Domain defaults

- `constitution` and `feedback` source kinds ingest into `behavior`
- ordinary external documents ingest into `knowledge`
- the whitepaper sample is validated as a document extractor fixture, not silently promoted to `behavior` merely because of its filename

## Provenance kept

- source path
- document id
- chunk id
- page number where available
- parser used
- extraction quality score / flags
- selected parser counts

## Observed validation

This build validated a real PDF ingest on:

- `assets/seed_canon/eden_whitepaper_v14.pdf`

Observed result:

- `24` page-like units
- parser strategy: `page_scored_pdf_extract_v1`
- selected parser counts favored `pdfplumber` on the validated whitepaper sample

## Current ingest status semantics

- `processing`: active ingest run in progress
- `ingested`: ingest completed and chunk/materialization work is persisted; `metadata_json` records parser strategy, quality score, quality state, quality flags, and selected parser counts
- `failed`: ingest aborted; error and partial progress metadata are stored on the document row, including extraction diagnostics when available

Legacy document rows that predate scored extraction are backfilled as `quality_state = "legacy_unscored"` with explicit `legacy_unscored_*` flags rather than being silently promoted to `clean`.

Large PDFs can still take real time to process, but the pipeline still streams extraction/storage work into chunk persistence after parser selection rather than waiting for graph artifact materialization to finish before any `document_chunks` are written.
