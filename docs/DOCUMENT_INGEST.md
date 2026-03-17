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
6. Extract top phrases heuristically into memes.
7. Add bounded auto-derived relation edges inside each chunk when explicit surface rules fire (`AUTHOR_OF`, `INFLUENCES`, `REFERENCES` today), then add `CO_OCCURS_WITH` fallback edges across the chunk-local meme set.
8. Materialize a memode when a chunk yields at least two memes and persist explicit `MEMODE_HAS_MEMBER` membership edges from the memode to its member memes.
9. Mark the document `ingested` on success or `failed` with error and extraction-quality metadata if extraction/ingest aborts.

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
