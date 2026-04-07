# Claude Code Prompt: Integrate idris2-sqlite3 into the Adam Idris2 Port

## Context you must read first

This is an Idris2 port of Adam v1 — a local-first graph-conditioned runtime. The original Python
codebase already uses SQLite at `data/eden.db`. The whitepaper (`article.md` in this project) is the
authoritative architectural reference. Read it before writing any code.

The Python store at scale: 82,196 memes, 18,383 memodes, 447,516 edges, 75 turns, 53 feedback events,
2 measurement events, 75 membrane events, 240 trace events. The Idris2 port must be schema-compatible
enough to eventually read the Python DB, and must support a new Substack commenting pipeline.

---

## Prompt (paste into Claude Code)

```
I am porting Adam v1 from Python to Idris2. The Python codebase already has a working SQLite
persistence layer at data/eden.db. I need to build the equivalent in Idris2 using the
stefan-hoeck/idris2-sqlite3 library (https://github.com/stefan-hoeck/idris2-sqlite3).

## Step 0: Read before writing

1. Read my .ipkg file for current deps and module structure.
2. Read ALL my Idris2 record types — especially Meme, Edge, Turn, Feedback, MembraneEvent,
   TraceEvent, MeasurementEvent, Memode, Session, Experiment, and StoreState (with its IORefs).
3. Read the idris2-sqlite3 README and tutorial:
   - https://github.com/stefan-hoeck/idris2-sqlite3/blob/main/README.md
   - https://github.com/stefan-hoeck/idris2-sqlite3/blob/main/docs/src/Tutorial.md
4. Read article.md in this project — it is the canonical architectural reference.
   Key sections: §3 (Canonical Terms), §4 (Direct-Loop Architecture), §6 (Observed Evidence).

Do NOT write any code until you have read all four sources above.

## The architecture you must respect

The direct v1 loop:
  input → retrieve/assemble → Adam response → membrane → feedback → graph update

Core ontology (from article.md §3, non-collapse rules):
- MEME: First-class persistent graph unit. Has domain (behavior | knowledge).
  Knowledge-domain memes project outward as "information."
  Behavior-domain memes are eligible for memode materialization.
- MEMODE: Derived second-order structure. Requires ≥2 behavior-domain memes
  plus a connected qualifying support subgraph. NOT a cluster label.
  NOT auto-promoted from semantic similarity.
- EDGE: Typed relation between memes. Support edges (qualifying for memodes)
  vs informational edges are distinct categories.
- REGARD: Durable selection pressure over persistent graph objects.
  NOT identical to prompt-time salience or active-set membership.
- ACTIVE SET: Bounded retrieval/prompt-compilation slice for a turn.
  NOT the full identity. Budget-limited, profile-constrained.
- MEMBRANE: Post-generation control surface. Sanitizes raw model output,
  enforces response form, records membrane events. NOT a planner.
- FEEDBACK: Explicit operator verdicts — Accept, Edit, Reject, Skip.
  Accept/Reject require explanations. Edit requires explanation + corrected text.
- HUM: Bounded continuity artifact. Not injected back into prompt assembly.

Event family (all must persist):
- Feedback events (verdict + explanation + optional corrected text)
- Membrane events (sanitization record per turn)
- Trace events (runtime action binding to observable surfaces)
- Measurement events (observatory: preview/commit/revert with provenance)

Inference modes: manual, runtime_auto, adam_auto
  (adam_auto currently falls back to runtime_auto on MLX — log both requested and effective)

## Step 1: Add the dependency

Add `sqlite3` to `depends` in my .ipkg. If using the RIO/Async effect layer,
also add `sqlite3-rio`. Confirm it builds with `pack build`.

If pack doesn't resolve it, add to pack.toml:
[custom.all.idris2-sqlite3]
type   = "github"
url    = "https://github.com/stefan-hoeck/idris2-sqlite3"
commit = "latest"
ipkg   = "sqlite3.ipkg"

## Step 2: Define table schemas

Create module `Adam.Persist.Schema`. Mirror the Python eden.db schema:

### Core graph tables

MEMES table:
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  body          TEXT NOT NULL        -- meme content, newlines/tabs handled natively by SQLite
  domain        INTEGER NOT NULL     -- 0 = behavior, 1 = knowledge
  regard        REAL DEFAULT 0.0     -- durable selection pressure
  created_at    TEXT                 -- ISO timestamp
  experiment_id TEXT                 -- scoped to experiment

EDGES table:
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  source_id     INTEGER NOT NULL     -- FK → memes
  target_id     INTEGER NOT NULL     -- FK → memes
  edge_type     INTEGER NOT NULL     -- 0 = support (qualifying for memodes), 1 = informational
  weight        REAL DEFAULT 1.0
  experiment_id TEXT
  FOREIGN KEY (source_id) REFERENCES memes(id)
  FOREIGN KEY (target_id) REFERENCES memes(id)

MEMODES table:
  id              INTEGER PRIMARY KEY AUTOINCREMENT
  label           TEXT
  admissible      INTEGER DEFAULT 1  -- 0 = flagged, 1 = admissible
  member_count    INTEGER            -- count of constituent behavior memes
  support_edges   INTEGER            -- count of qualifying support edges
  experiment_id   TEXT

MEMODE_MEMBERS table:
  memode_id     INTEGER NOT NULL     -- FK → memodes
  meme_id       INTEGER NOT NULL     -- FK → memes
  PRIMARY KEY (memode_id, meme_id)

### Runtime tables

EXPERIMENTS table:
  id            TEXT PRIMARY KEY     -- UUID
  name          TEXT
  created_at    TEXT

SESSIONS table:
  id            TEXT PRIMARY KEY     -- UUID
  experiment_id TEXT NOT NULL        -- FK → experiments
  created_at    TEXT
  ended_at      TEXT

TURNS table:
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  session_id    TEXT NOT NULL        -- FK → sessions
  turn_index    INTEGER NOT NULL
  user_input    TEXT
  raw_response  TEXT                 -- pre-membrane model output
  membrane_text TEXT                 -- post-membrane operator-facing response
  active_set_size INTEGER
  requested_mode  INTEGER            -- 0=manual, 1=runtime_auto, 2=adam_auto
  effective_mode  INTEGER            -- what actually ran (adam_auto may fall back)
  created_at    TEXT

FEEDBACK table:
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  turn_id       INTEGER NOT NULL     -- FK → turns
  verdict       INTEGER NOT NULL     -- 0=accept, 1=edit, 2=reject, 3=skip
  explanation   TEXT                 -- required for accept/reject/edit
  corrected_text TEXT                -- required for edit, NULL otherwise
  created_at    TEXT

MEMBRANE_EVENTS table:
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  turn_id       INTEGER NOT NULL     -- FK → turns
  raw_text      TEXT
  sanitized_text TEXT
  headings_removed TEXT              -- comma-separated list of removed scaffold headings
  created_at    TEXT

TRACE_EVENTS table:
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  session_id    TEXT NOT NULL        -- FK → sessions
  event_type    TEXT NOT NULL        -- e.g. "generation_start", "generation_complete", "hum_refreshed"
  payload       TEXT                 -- JSON blob
  created_at    TEXT

MEASUREMENT_EVENTS table:
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  session_id    TEXT NOT NULL        -- FK → sessions
  action_type   TEXT NOT NULL        -- e.g. "edge_add", "revert", "memode_assert"
  operator      TEXT
  evidence      TEXT
  before_state  TEXT                 -- JSON
  proposed_state TEXT                -- JSON
  committed_state TEXT               -- JSON
  revert_of     INTEGER              -- FK → measurement_events (NULL if not a revert)
  created_at    TEXT

### New: Substack commenting pipeline tables

SOURCES table:
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  url           TEXT UNIQUE NOT NULL
  author        TEXT
  title         TEXT
  summary       TEXT                 -- Adam's compressed reading of the post
  ingested_at   TEXT

DRAFTS table:
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  source_id     INTEGER NOT NULL     -- FK → sources
  body          TEXT NOT NULL         -- Adam's drafted comment
  status        INTEGER DEFAULT 0    -- 0=pending, 1=approved, 2=edited, 3=rejected, 4=posted
  operator_note TEXT                 -- review feedback from operator
  topic_tags    TEXT                 -- comma-separated, for per-domain graduation tracking
  regard_delta  REAL DEFAULT 0.0     -- regard impact from this interaction
  created_at    TEXT
  reviewed_at   TEXT
  posted_at     TEXT

META table:
  key           TEXT PRIMARY KEY
  value         TEXT
  -- Stores: schema_version, last_session_id, next_id, graduation thresholds

## Step 3: Derive marshallers

For each record type:
- Derive `ToRow` and `FromRow` using `%runElab derive`.
- For enum-like fields (domain, verdict, edge_type, status, mode), write manual
  `ToCell`/`FromCell` instances that marshal to/from INTEGER.
- Use `WithID` from `Data.WithID` for query results that include the primary key.

If a record has a field that is `Maybe Text` (like corrected_text), ensure the
marshaller handles SQL NULL correctly.

## Step 4: Write the persistence module

Create `Adam.Persist.Sqlite` with these function families:

### Initialization

-- Create all tables IF NOT EXISTS, check schema version in Meta
initDB : (path : String) -> IO (Either SqlError DB)

### Graph persistence (mirrors current StoreState IORefs)

-- Write full store to DB in a single transaction (INSERT OR REPLACE)
saveGraph : DB -> StoreState -> IO (Either SqlError ())

-- Read all tables into StoreState IORefs, return max ID across all tables
loadGraph : DB -> StoreState -> IO (Either SqlError Nat)

### Turn-level operations (called during the direct loop)

-- Persist a completed turn (called after membrane, before feedback)
saveTurn : DB -> Turn -> IO (Either SqlError Bits32)

-- Record feedback event and update regard on affected memes
saveFeedback : DB -> FeedbackEvent -> IO (Either SqlError ())

-- Record membrane event
saveMembrane : DB -> MembraneEvent -> IO (Either SqlError ())

-- Record trace event
saveTrace : DB -> TraceEvent -> IO (Either SqlError ())

-- Record measurement event (observatory mutations)
saveMeasurement : DB -> MeasurementEvent -> IO (Either SqlError ())

### Substack pipeline operations (new)

-- Save an ingested Substack post
saveSource : DB -> Source -> IO (Either SqlError Bits32)

-- Check if URL already ingested
sourceExists : DB -> (url : String) -> IO (Either SqlError Bool)

-- Save Adam's draft comment
saveDraft : DB -> Draft -> IO (Either SqlError Bits32)

-- Get all drafts pending review
getPending : DB -> IO (Either SqlError (List (WithID Draft)))

-- Update draft status after review
updateDraftStatus : DB -> (draftId : Bits32) -> DraftStatus -> IO (Either SqlError ())

-- Get drafts by topic for graduation analysis
getDraftsByTopic : DB -> (tag : String) -> IO (Either SqlError (List (WithID Draft)))

-- Graduation query: consecutive accepts without edits for a topic
consecutiveAccepts : DB -> (tag : String) -> IO (Either SqlError Nat)

### Rules
- All writes use TRANSACTIONS. Group related writes (e.g., saveTurn + saveMembrane).
- saveGraph uses INSERT OR REPLACE for upsert semantics.
- loadGraph populates IORefs and returns max ID so nextId can continue without collision.
- All table creation uses IF NOT EXISTS.
- Store schema version "1" in Meta on first init. Check on load — warn but don't crash on mismatch.

## Step 5: Wire into startup

Modify main/startup:
1. Create newStore (empty IORefs as before)
2. initDB "data/eden.db" → get DB handle
3. loadGraph db store → returns maxId, populates all IORefs
4. Set nextId to maxId + 1
5. Seed memes ONLY if loadGraph returned 0 (empty DB, first run)
6. Create experiment + session as before
7. During direct loop: saveTurn/saveMembrane/saveFeedback/saveTrace at appropriate points
8. On quit: saveGraph for any unsaved state, close DB

## Step 6: Draft queue REPL commands

Add to TUI/REPL:
- `:ingest <url>`  — fetch post content, save Source, draft comment via LLM, save Draft as pending
- `:review`        — show next pending Draft with source context, prompt for accept/edit/reject
- `:queue`         — list all pending Drafts (id, source author, first line, status)
- `:posted`        — list recently posted Drafts
- `:graduation`    — show per-topic consecutive-accept counts (how close to autonomous)

## Step 7: Migration from flat file

Write a one-time `migrateFromFlatFile`:
- Read data/graph.eden if it exists
- Parse each MEME/EDGE/TURN/FB line
- Insert into corresponding SQLite tables
- Print migration summary (counts per table)
- This is a safety net — run once, then the flat file becomes archival.

## Constraints

- Pure Idris2 + idris2-sqlite3. No Python FFI. No subprocess calls to Python.
- Do NOT change the StoreState interface or how the rest of the system reads from IORefs.
  The persistence layer is behind that interface — the rest of Adam doesn't know it's SQLite.
- Do NOT delete the flat-file code yet. Keep it as a fallback module.
- If the Async effect stack from idris2-sqlite3 doesn't match my IO-based code,
  prefer using the lower-level Sqlite3.Prim module (raw IO) over restructuring my
  entire effect system. Wrap at the boundary, don't propagate.
- Use `pack` for dependency management.
- Target the `main` branch of stefan-hoeck/idris2-sqlite3.
- Respect the non-collapse rules from article.md §3:
  * Memes are NOT memodes. Memodes are derived.
  * Regard is NOT salience. They are separate temporal scales.
  * Active set is NOT identity. It's a bounded slice.
  * Membrane is NOT a planner. It's post-generation.
  * The hum is NOT prompt-injected. It's a separate artifact.
```

---

## To run

```bash
cd ~/path/to/adam
claude
# paste the prompt above

# or one-shot:
claude -p "$(cat integrate-sqlite.md)"
```

## What to watch for

1. **Effect stack mismatch.** idris2-sqlite3 uses Stefan Hoeck's `Async` effect system.
   If your Adam code is plain IO + IORefs, push Claude Code toward `Sqlite3.Prim` (raw FFI)
   rather than letting it restructure your whole codebase around `Async`.

2. **pack resolution.** Stefan Hoeck's libs are generally in the pack collection already.
   Run `pack typecheck` after adding the dependency. If it fails, you need the `[custom]`
   entry in pack.toml shown above.

3. **Enum marshalling.** The trickiest part is getting `ToCell`/`FromCell` right for your
   ADTs (Verdict, Domain, EdgeType, DraftStatus, InferenceMode). These need to round-trip
   through INTEGER cleanly. Write a test for each one.

4. **Schema compatibility with Python.** The Idris2 tables should be structurally compatible
   with the Python eden.db so that eventually you can point the Idris2 runtime at the
   existing 82K-meme database. Column names and types matter — match the Python schema.
