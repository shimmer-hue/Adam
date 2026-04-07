||| SQLite3 FFI bindings for graph persistence.
|||
||| Lifecycle (open/close/schema), bulk load at startup,
||| schema migration framework, and write-through helpers
||| called from Store.InMemory.
module Eden.SQLite

import Data.IORef
import Data.List
import Data.String
import System.File
import System.Directory
import Eden.Types
import Eden.Store.InMemory
import Eden.Export

------------------------------------------------------------------------
-- C FFI declarations
------------------------------------------------------------------------

%foreign "C:eden_db_open,eden_sqlite"
prim__dbOpen : String -> PrimIO AnyPtr

%foreign "C:eden_db_close,eden_sqlite"
prim__dbClose : AnyPtr -> PrimIO Int

%foreign "C:eden_db_init_schema,eden_sqlite"
prim__dbInitSchema : AnyPtr -> PrimIO Int

%foreign "C:eden_db_is_null,eden_sqlite"
prim__dbIsNull : AnyPtr -> PrimIO Int

-- Save functions
%foreign "C:eden_db_save_experiment,eden_sqlite"
prim__dbSaveExperiment : AnyPtr -> String -> String -> String
  -> String -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_session,eden_sqlite"
prim__dbSaveSession : AnyPtr -> String -> String -> String
  -> String -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_turn,eden_sqlite"
prim__dbSaveTurn : AnyPtr -> String -> String -> String
  -> Int -> String -> String -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_document,eden_sqlite"
prim__dbSaveDocument : AnyPtr -> String -> String
  -> String -> String -> String
  -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_chunk,eden_sqlite"
prim__dbSaveChunk : AnyPtr -> String -> String -> String
  -> Int -> Int -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_edge,eden_sqlite"
prim__dbSaveEdge : AnyPtr -> String -> String
  -> String -> String -> String -> String
  -> String -> Double -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_feedback,eden_sqlite"
prim__dbSaveFeedback : AnyPtr -> String -> String
  -> String -> String
  -> String -> String -> String
  -> Double -> Double -> Double -> String -> PrimIO Int

%foreign "C:eden_db_save_membrane_event,eden_sqlite"
prim__dbSaveMembraneEvent : AnyPtr -> String -> String -> String
  -> String -> PrimIO Int

%foreign "C:eden_db_save_trace_event,eden_sqlite"
prim__dbSaveTraceEvent : AnyPtr -> String -> String -> String
  -> String -> String -> PrimIO Int

-- Targeted updates
%foreign "C:eden_db_update_meme_channels,eden_sqlite"
prim__dbUpdateMemeChannels : AnyPtr -> String -> Double -> Double -> Double -> PrimIO Int

%foreign "C:eden_db_update_meme_usage,eden_sqlite"
prim__dbUpdateMemeUsage : AnyPtr -> String -> Int -> String -> PrimIO Int

%foreign "C:eden_db_end_session,eden_sqlite"
prim__dbEndSession : AnyPtr -> String -> String -> PrimIO Int

-- Load functions (return tab-separated strings)
%foreign "C:eden_db_load_experiments,eden_sqlite"
prim__dbLoadExperiments : AnyPtr -> PrimIO String

%foreign "C:eden_db_load_sessions,eden_sqlite"
prim__dbLoadSessions : AnyPtr -> PrimIO String

%foreign "C:eden_db_load_turns,eden_sqlite"
prim__dbLoadTurns : AnyPtr -> PrimIO String

%foreign "C:eden_db_load_memes,eden_sqlite"
prim__dbLoadMemes : AnyPtr -> PrimIO String

%foreign "C:eden_db_load_memodes,eden_sqlite"
prim__dbLoadMemodes : AnyPtr -> PrimIO String

%foreign "C:eden_db_load_edges,eden_sqlite"
prim__dbLoadEdges : AnyPtr -> PrimIO String

%foreign "C:eden_db_load_feedback,eden_sqlite"
prim__dbLoadFeedback : AnyPtr -> PrimIO String

-- New entity loads
%foreign "C:eden_db_load_agents,eden_sqlite"
prim__dbLoadAgents : AnyPtr -> PrimIO String

%foreign "C:eden_db_load_active_sets,eden_sqlite"
prim__dbLoadActiveSets : AnyPtr -> PrimIO String

%foreign "C:eden_db_load_turn_metadata,eden_sqlite"
prim__dbLoadTurnMetadata : AnyPtr -> PrimIO String

-- Config store
%foreign "C:eden_db_set_config,eden_sqlite"
prim__dbSetConfig : AnyPtr -> String -> String -> PrimIO Int

%foreign "C:eden_db_get_config,eden_sqlite"
prim__dbGetConfig : AnyPtr -> String -> PrimIO String

-- Transactions
%foreign "C:eden_db_begin,eden_sqlite"
prim__dbBegin : AnyPtr -> PrimIO Int

%foreign "C:eden_db_commit,eden_sqlite"
prim__dbCommit : AnyPtr -> PrimIO Int

-- Schema migration support
%foreign "C:eden_db_exec_sql,eden_sqlite"
prim__dbExecSql : AnyPtr -> String -> PrimIO Int

-- Document SHA lookup
%foreign "C:eden_db_document_exists_sha,eden_sqlite"
prim__dbDocExistsSha : AnyPtr -> String -> String -> PrimIO Int

-- Chunk loading
%foreign "C:eden_db_load_chunks,eden_sqlite"
prim__dbLoadChunks : AnyPtr -> PrimIO String

-- Document loading
%foreign "C:eden_db_load_documents,eden_sqlite"
prim__dbLoadDocuments : AnyPtr -> PrimIO String

-- Measurement event loading
%foreign "C:eden_db_load_measurement_events,eden_sqlite"
prim__dbLoadMeasurementEvents : AnyPtr -> PrimIO String

------------------------------------------------------------------------
-- Schema migration framework
------------------------------------------------------------------------

||| A single migration step: version number, description, SQL to execute.
record Migration where
  constructor MkMigration
  mgVersion     : Int
  mgDescription : String
  mgSql         : String

||| The ordered list of schema migrations.
||| Migration 1 = baseline schema (created by eden_db_init_schema).
||| Migration 2 = add schema_version tracking + ensure chunks/measurements tables.
migrations : List Migration
migrations =
  [ MkMigration 2 "add schema_version tracking and ensure new tables"
      (  "CREATE TABLE IF NOT EXISTS schema_version "
      ++ "(version INTEGER PRIMARY KEY, description TEXT, applied_at TEXT);"
      ++ "INSERT OR IGNORE INTO schema_version (version, description, applied_at) "
      ++ "VALUES (1, 'baseline schema', datetime('now'));"
      ++ "CREATE TABLE IF NOT EXISTS chunks "
      ++ "(id TEXT PRIMARY KEY, experiment_id TEXT, document_id TEXT, "
      ++ "chunk_index INTEGER, page_number INTEGER, text TEXT, created_at TEXT);"
      ++ "CREATE TABLE IF NOT EXISTS measurement_events "
      ++ "(id TEXT PRIMARY KEY, experiment_id TEXT, session_id TEXT, "
      ++ "action_type TEXT, state TEXT, operator TEXT, evidence TEXT, "
      ++ "before_state TEXT, proposed_state TEXT, committed_state TEXT, "
      ++ "revert_of TEXT, created_at TEXT);"
      ++ "CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);"
      ++ "CREATE INDEX IF NOT EXISTS idx_chunks_experiment ON chunks(experiment_id);"
      ++ "CREATE INDEX IF NOT EXISTS idx_meas_experiment ON measurement_events(experiment_id);"
      ++ "CREATE INDEX IF NOT EXISTS idx_docs_sha ON documents(sha256);")
  , MkMigration 3 "add document and chunk FTS indexes"
      (  "CREATE INDEX IF NOT EXISTS idx_docs_experiment ON documents(experiment_id);"
      ++ "CREATE INDEX IF NOT EXISTS idx_memes_canonical ON memes(experiment_id, canonical_label, domain);"
      ++ "CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(experiment_id, src_id);"
      ++ "CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(experiment_id, dst_id);")
  ]

||| Get the current schema version from the database.
||| Returns 1 if no schema_version table exists (baseline).
export
getCurrentVersion : HasIO io => AnyPtr -> io Int
getCurrentVersion db = do
  verStr <- liftIO $ primIO (prim__dbGetConfig db "schema_version")
  case the (Maybe Integer) (parsePositive verStr) of
    Just v  => pure (cast v)
    Nothing => pure 1  -- baseline: no version tracked yet

||| Apply a single migration.
applyMigration : AnyPtr -> Migration -> IO Bool
applyMigration db mig = do
  rc <- primIO (prim__dbExecSql db mig.mgSql)
  if rc == 0
    then do
      _ <- primIO (prim__dbExecSql db
        (  "INSERT OR REPLACE INTO schema_version "
        ++ "(version, description, applied_at) VALUES ("
        ++ show mig.mgVersion ++ ", '"
        ++ mig.mgDescription ++ "', datetime('now'))"))
      _ <- primIO (prim__dbSetConfig db "schema_version" (show mig.mgVersion))
      putStrLn ("  [db] migration " ++ show mig.mgVersion
             ++ ": " ++ mig.mgDescription)
      pure True
    else do
      putStrLn ("  [db] migration " ++ show mig.mgVersion
             ++ " FAILED")
      pure False

||| Run all pending migrations against the database.
||| Checks current version and applies any migrations with higher version numbers.
export
runMigrations : HasIO io => AnyPtr -> io ()
runMigrations db = liftIO $ do
  currentVer <- getCurrentVersion db
  let pending = filter (\m => m.mgVersion > currentVer) migrations
      sorted  = sortBy (\a, b => compare a.mgVersion b.mgVersion) pending
  case sorted of
    [] => pure ()
    _  => do
      putStrLn ("  [db] running " ++ show (length sorted)
             ++ " migration(s) from v" ++ show currentVer ++ "...")
      _ <- primIO (prim__dbBegin db)
      results <- traverse (applyMigration db) sorted
      _ <- primIO (prim__dbCommit db)
      pure ()

------------------------------------------------------------------------
-- High-level lifecycle
------------------------------------------------------------------------

||| Open the database, initialize schema, run migrations, return handle.
export
openDB : String -> IO (Maybe AnyPtr)
openDB path = do
  _ <- createDir "data"
  db <- primIO (prim__dbOpen path)
  isNull <- primIO (prim__dbIsNull db)
  if isNull == 1
    then pure Nothing
    else do
      rc <- primIO (prim__dbInitSchema db)
      if rc /= 0
        then do _ <- primIO (prim__dbClose db)
                pure Nothing
        else do
          runMigrations db
          pure (Just db)

||| Close database handle.
export
closeDB : AnyPtr -> IO ()
closeDB db = do
  _ <- primIO (prim__dbClose db)
  pure ()

------------------------------------------------------------------------
-- Write-through helpers (called after in-memory mutation)
------------------------------------------------------------------------

export
dbSaveExperiment : AnyPtr -> Experiment -> IO ()
dbSaveExperiment db e = do
  _ <- primIO (prim__dbSaveExperiment db
    (show e.id) e.name e.slug
    (show e.mode) (show e.status)
    (show e.createdAt) (show e.updatedAt))
  pure ()

export
dbSaveSession : AnyPtr -> Session -> IO ()
dbSaveSession db s = do
  let ea = case s.endedAt of
              Just ts => show ts
              Nothing => ""
  _ <- primIO (prim__dbSaveSession db
    (show s.id) (show s.experimentId) (show s.agentId)
    s.title (show s.createdAt) (show s.updatedAt) ea)
  pure ()

export
dbSaveTurn : AnyPtr -> Turn -> IO ()
dbSaveTurn db t = do
  _ <- primIO (prim__dbSaveTurn db
    (show t.id) (show t.experimentId) (show t.sessionId)
    (cast t.turnIndex) t.userText t.promptContext
    t.responseText t.membraneText (show t.createdAt))
  pure ()

export
dbSaveDocument : AnyPtr -> Document -> IO ()
dbSaveDocument db d = do
  _ <- primIO (prim__dbSaveDocument db
    (show d.id) (show d.experimentId)
    d.path (show d.kind) d.title d.sha256
    (show d.status) (show d.createdAt))
  pure ()

export
dbSaveChunk : AnyPtr -> Chunk -> IO ()
dbSaveChunk db c = do
  _ <- primIO (prim__dbSaveChunk db
    (show c.id) (show c.experimentId) (show c.documentId)
    (cast c.chunkIndex) (the Int (case c.pageNumber of Just p => cast p; Nothing => 0))
    c.text (show c.createdAt))
  pure ()

export
dbSaveEdge : AnyPtr -> Edge -> IO ()
dbSaveEdge db e = do
  _ <- primIO (prim__dbSaveEdge db
    (show e.id) (show e.experimentId)
    (show e.srcKind) e.srcId (show e.dstKind) e.dstId
    (show e.edgeType) e.weight
    (show e.createdAt) (show e.updatedAt))
  pure ()

export
dbSaveFeedback : AnyPtr -> FeedbackRecord -> Eden.Types.Timestamp -> IO ()
dbSaveFeedback db fb now = do
  _ <- primIO (prim__dbSaveFeedback db
    (show fb.frId) (show fb.frExperimentId)
    (show fb.frSessionId) (show fb.frTurnId)
    (show fb.frVerdict) fb.frExplanation fb.frCorrected
    fb.frSignal.reward fb.frSignal.risk fb.frSignal.edit
    (show now))
  pure ()

export
dbUpdateMemeChannels : AnyPtr -> MemeId -> Double -> Double -> Double -> IO ()
dbUpdateMemeChannels db mid rw rk ed = do
  _ <- primIO (prim__dbUpdateMemeChannels db (show mid) rw rk ed)
  pure ()

export
dbSaveNextId : AnyPtr -> Nat -> IO ()
dbSaveNextId db n = do
  _ <- primIO (prim__dbSetConfig db "next_id" (show n))
  pure ()

------------------------------------------------------------------------
-- Bulk load from SQLite into StoreState
------------------------------------------------------------------------

||| Load all graph data from SQLite into the in-memory store.
||| Returns the next_id value for ID generation continuity.
export
loadFromDB : AnyPtr -> StoreState -> IO Nat
loadFromDB db st = do
  -- Load memes (reuse existing deserializer from Export)
  memeStr <- primIO (prim__dbLoadMemes db)
  let memeLines = filter (\l => length l > 0) (lines memeStr)
  memes <- pure $ mapMaybe (\l => deserializeMeme (splitTabs l)) memeLines
  writeIORef st.memes memes

  -- Load edges
  edgeStr <- primIO (prim__dbLoadEdges db)
  let edgeLines = filter (\l => length l > 0) (lines edgeStr)
  edges <- pure $ mapMaybe (\l => deserializeEdge (splitTabs l)) edgeLines
  writeIORef st.edges edges

  -- Load turns
  turnStr <- primIO (prim__dbLoadTurns db)
  let turnLines = filter (\l => length l > 0) (lines turnStr)
  turns <- pure $ mapMaybe (\l => deserializeTurn (splitTabs l)) turnLines
  writeIORef st.turns turns

  -- Load feedback
  fbStr <- primIO (prim__dbLoadFeedback db)
  let fbLines = filter (\l => length l > 0) (lines fbStr)
  fbs <- pure $ mapMaybe (\l => deserializeFeedback (splitTabs l)) fbLines
  writeIORef st.feedbackEvents fbs

  -- Load experiments
  expStr <- primIO (prim__dbLoadExperiments db)
  let expLines = filter (\l => length l > 0) (lines expStr)
  exps <- pure $ mapMaybe (\l => deserializeExperiment (splitTabs l)) expLines
  writeIORef st.experiments exps

  -- Load sessions
  sessStr <- primIO (prim__dbLoadSessions db)
  let sessLines = filter (\l => length l > 0) (lines sessStr)
  sessions <- pure $ mapMaybe (\l => deserializeSession (splitTabs l)) sessLines
  writeIORef st.sessions sessions

  -- Load memodes
  mdStr <- primIO (prim__dbLoadMemodes db)
  let mdLines = filter (\l => length l > 0) (lines mdStr)
  memodes <- pure $ mapMaybe (\l => deserializeMemode (splitTabs l)) mdLines
  writeIORef st.memodes memodes

  -- Load agents
  agentStr <- primIO (prim__dbLoadAgents db)
  let agentLines = filter (\l => length l > 0) (lines agentStr)
  agents <- pure $ mapMaybe (\l => deserializeAgent (splitTabs l)) agentLines
  writeIORef st.agents agents

  -- Load active sets
  asetStr <- primIO (prim__dbLoadActiveSets db)
  let asetLines = filter (\l => length l > 0) (lines asetStr)
  asets <- pure $ mapMaybe (\l => deserializeActiveSetEntry (splitTabs l)) asetLines
  writeIORef st.activeSetSnaps asets

  -- Load turn metadata
  tmetaStr <- primIO (prim__dbLoadTurnMetadata db)
  let tmetaLines = filter (\l => length l > 0) (lines tmetaStr)
  tmetas <- pure $ mapMaybe (\l => deserializeTurnMetadata (splitTabs l)) tmetaLines
  writeIORef st.turnMetadata tmetas

  -- Load chunks
  chunkStr <- primIO (prim__dbLoadChunks db)
  let chunkLines = filter (\l => length l > 0) (lines chunkStr)
  chunks <- pure $ mapMaybe (\l => deserializeChunk (splitTabs l)) chunkLines
  writeIORef st.chunks chunks

  -- Load documents
  docStr <- primIO (prim__dbLoadDocuments db)
  let docLines = filter (\l => length l > 0) (lines docStr)
  docs <- pure $ mapMaybe (\l => deserializeDocument (splitTabs l)) docLines
  writeIORef st.documents docs

  -- Load measurement events
  measStr <- primIO (prim__dbLoadMeasurementEvents db)
  let measLines = filter (\l => length l > 0) (lines measStr)
  meass <- pure $ mapMaybe (\l => deserializeMeasurementEvent (splitTabs l)) measLines
  writeIORef st.measurements meass

  -- Restore next_id from config
  nidStr <- primIO (prim__dbGetConfig db "next_id")
  let nid = case the (Maybe Integer) (parsePositive nidStr) of
              Just n  => the Nat (cast n)
              Nothing => 1
  writeIORef st.nextId nid

  -- Rebuild FTS index from loaded memes
  rebuildFtsIndex st

  putStrLn ("  [db] loaded: " ++ show (length memes) ++ " memes, "
         ++ show (length edges) ++ " edges, "
         ++ show (length turns) ++ " turns, "
         ++ show (length fbs) ++ " feedback, "
         ++ show (length agents) ++ " agents, "
         ++ show (length chunks) ++ " chunks, "
         ++ show (length docs) ++ " documents")
  pure nid

------------------------------------------------------------------------
-- Document SHA deduplication (SQLite-backed)
------------------------------------------------------------------------

||| Check if a document with the given SHA256 exists in the database.
export
dbDocumentExistsBySha : AnyPtr -> ExperimentId -> String -> IO Bool
dbDocumentExistsBySha db eid sha = do
  rc <- primIO (prim__dbDocExistsSha db (show eid) sha)
  pure (rc > 0)
