# Document Ingest

## Supported formats

- PDF
- CSV
- TXT
- Markdown

## Extraction order

### PDF

1. `pdfplumber`
2. `pypdf`
3. `pdftotext` CLI fallback

Failure is explicit if all three fail.

### CSV

- parsed row-by-row
- normalized into pipe-delimited text chunks

### TXT / Markdown

- decoded with replacement on bad bytes
- chunked by sentence boundaries

## Pipeline

1. Create or update a `documents` record.
2. If the same document SHA is already fully ingested for the current graph, reuse that document record instead of duplicating chunks and graph artifacts.
3. Stream page-like text units from the extractor instead of materializing the full document payload before storage.
4. Chunk text into manageable blocks.
5. Store `document_chunks` with parser and page provenance as extraction progresses.
6. Extract top phrases heuristically into memes.
7. Add co-occurrence edges inside each chunk.
8. Materialize a memode when a chunk yields at least two memes.
9. Mark the document `ingested` on success or `failed` with error metadata if extraction/ingest aborts.

## Provenance kept

- source path
- document id
- chunk id
- page number where available
- parser used

## Observed validation

This build validated a real PDF ingest on:

- `assets/seed_canon/eden_whitepaper_v14.pdf`

Observed result:

- `24` page-like units
- parser: `pdfplumber`

## Current ingest status semantics

- `processing`: active ingest run in progress
- `ingested`: ingest completed and chunk/materialization work is persisted
- `failed`: ingest aborted; error and partial progress metadata are stored on the document row

Large PDFs can still take real time to process, but the pipeline now streams extraction/storage work instead of waiting for the full PDF to be read before any `document_chunks` are written.
