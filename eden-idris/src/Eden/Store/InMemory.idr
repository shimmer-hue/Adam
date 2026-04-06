||| In-memory graph store backed by mutable IORef lists.
||| When dbHandle is Just, every mutation writes through to SQLite.
module Eden.Store.InMemory

import Data.IORef
import Data.List
import Data.String
import Eden.Types
import Eden.Config
import Eden.Storage

------------------------------------------------------------------------
-- SQLite FFI (inline declarations to avoid circular import)
------------------------------------------------------------------------

%foreign "C:eden_db_save_experiment,eden_sqlite"
prim__wt_exp : AnyPtr -> String -> String -> String -> String -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_session,eden_sqlite"
prim__wt_sess : AnyPtr -> String -> String -> String -> String -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_turn,eden_sqlite"
prim__wt_turn : AnyPtr -> String -> String -> String -> Int -> String -> String -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_meme_tsv,eden_sqlite"
prim__wt_meme_tsv : AnyPtr -> String -> PrimIO Int

%foreign "C:eden_db_save_memode_tsv,eden_sqlite"
prim__wt_memode_tsv : AnyPtr -> String -> PrimIO Int

%foreign "C:eden_db_save_edge,eden_sqlite"
prim__wt_edge : AnyPtr -> String -> String -> String -> String -> String -> String -> String -> Double -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_feedback,eden_sqlite"
prim__wt_fb : AnyPtr -> String -> String -> String -> String -> String -> String -> String -> Double -> Double -> Double -> String -> PrimIO Int

%foreign "C:eden_db_save_membrane_event,eden_sqlite"
prim__wt_mbe : AnyPtr -> String -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_trace_event,eden_sqlite"
prim__wt_tre : AnyPtr -> String -> String -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_update_meme_channels,eden_sqlite"
prim__wt_memech : AnyPtr -> String -> Double -> Double -> Double -> PrimIO Int

%foreign "C:eden_db_set_config,eden_sqlite"
prim__wt_config : AnyPtr -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_document,eden_sqlite"
prim__wt_doc : AnyPtr -> String -> String -> String -> String -> String -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_chunk,eden_sqlite"
prim__wt_chunk : AnyPtr -> String -> String -> String -> Int -> Int -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_agent,eden_sqlite"
prim__wt_agent : AnyPtr -> String -> String -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_active_set_tsv,eden_sqlite"
prim__wt_aset_tsv : AnyPtr -> String -> PrimIO Int

%foreign "C:eden_db_save_measurement_event_tsv,eden_sqlite"
prim__wt_meas_tsv : AnyPtr -> String -> PrimIO Int

%foreign "C:eden_db_save_export_artifact,eden_sqlite"
prim__wt_export : AnyPtr -> String -> String -> String -> String -> String -> String -> PrimIO Int

%foreign "C:eden_db_save_turn_metadata_tsv,eden_sqlite"
prim__wt_tmeta_tsv : AnyPtr -> String -> PrimIO Int

------------------------------------------------------------------------
-- Feedback record (cleaner than 8-tuple, which also hits Idris2 parse limit)
------------------------------------------------------------------------

public export
record FeedbackRecord where
  constructor MkFeedbackRecord
  frId           : FeedbackId
  frExperimentId : ExperimentId
  frSessionId    : SessionId
  frTurnId       : TurnId
  frVerdict      : Verdict
  frExplanation  : String
  frCorrected    : String
  frSignal       : FeedbackSignal

------------------------------------------------------------------------
-- Inverted index for FTS
------------------------------------------------------------------------

||| A single posting: a meme ID that contains a given term.
public export
record Posting where
  constructor MkPosting
  postingMemeId : MemeId
  postingField  : String  -- "label" or "text"

||| Inverted index: maps lowercased terms to lists of postings.
||| Backed by a flat association list (sufficient for in-memory use).
public export
record InvertedIndex where
  constructor MkInvertedIndex
  iiEntries : IORef (List (String, List Posting))

||| Create a fresh empty inverted index.
export
newInvertedIndex : IO InvertedIndex
newInvertedIndex = do
  ref <- newIORef []
  pure (MkInvertedIndex ref)

------------------------------------------------------------------------
-- Store state
------------------------------------------------------------------------

||| Mutable in-memory store state.
||| When dbHandle holds a Just ptr, mutations write through to SQLite.
public export
record StoreState where
  constructor MkStoreState
  experiments    : IORef (List Experiment)
  sessions       : IORef (List Session)
  turns          : IORef (List Turn)
  memes          : IORef (List Meme)
  memodes        : IORef (List Memode)
  edges          : IORef (List Edge)
  feedbackEvents : IORef (List FeedbackRecord)
  membraneEvts   : IORef (List (MembraneEventType, String, Timestamp))
  traceEvts      : IORef (List (TraceEventType, TraceLevel, String, Timestamp))
  nextId         : IORef Nat
  dbHandle       : IORef (Maybe AnyPtr)
  agents         : IORef (List Agent)
  activeSetSnaps : IORef (List ActiveSetEntry)
  measurements   : IORef (List MeasurementEvent)
  exportArtifacts: IORef (List ExportArtifact)
  turnMetadata   : IORef (List TurnMetadata)
  chunks         : IORef (List Chunk)
  documents      : IORef (List Document)
  ftsIndex       : InvertedIndex

------------------------------------------------------------------------
-- Create a fresh store
------------------------------------------------------------------------

export
newStore : IO StoreState
newStore = do
  exps  <- newIORef []
  sess  <- newIORef []
  trns  <- newIORef []
  mms   <- newIORef []
  mds   <- newIORef []
  eds   <- newIORef []
  fbs   <- newIORef []
  mbes  <- newIORef []
  tres  <- newIORef []
  nid   <- newIORef 1
  dbh   <- newIORef Nothing
  ags   <- newIORef []
  asets <- newIORef []
  msev  <- newIORef []
  exart <- newIORef []
  tmeta <- newIORef []
  chnks <- newIORef []
  docs  <- newIORef []
  fts   <- newInvertedIndex
  pure (MkStoreState exps sess trns mms mds eds fbs mbes tres nid dbh ags asets msev exart tmeta chnks docs fts)

------------------------------------------------------------------------
-- FTS tokenization helpers
------------------------------------------------------------------------

||| Check if a character is a word boundary (not alphanumeric).
isWordChar : Char -> Bool
isWordChar c = isAlphaNum c || c == '_'

||| Tokenize a string into lowercased terms, splitting on non-word chars.
||| Filters out terms shorter than 2 characters.
tokenize : String -> List String
tokenize s = filter (\t => length t >= 2) (go (unpack (toLower s)) [] [])
  where
    go : List Char -> List Char -> List String -> List String
    go []          acc toks = reverse (if acc == [] then toks else pack (reverse acc) :: toks)
    go (c :: rest) acc toks =
      if isWordChar c
        then go rest (c :: acc) toks
        else go rest [] (if acc == [] then toks else pack (reverse acc) :: toks)

||| Add postings for a meme to the inverted index.
indexMemeTerms : InvertedIndex -> MemeId -> String -> String -> IO ()
indexMemeTerms idx mid label text = do
  let labelTerms = map (\t => (t, MkPosting mid "label")) (tokenize label)
      textTerms  = map (\t => (t, MkPosting mid "text"))  (tokenize text)
      allTerms   = labelTerms ++ textTerms
  entries <- readIORef idx.iiEntries
  let updated = foldl addPosting entries allTerms
  writeIORef idx.iiEntries updated
  where
    addPosting : List (String, List Posting) -> (String, Posting) -> List (String, List Posting)
    addPosting [] (term, posting) = [(term, [posting])]
    addPosting ((k, ps) :: rest) (term, posting) =
      if k == term
        then (k, posting :: ps) :: rest
        else (k, ps) :: addPosting rest (term, posting)

------------------------------------------------------------------------
-- Write-through helpers
------------------------------------------------------------------------

||| Discard PrimIO Int result.
wt_ : IO Int -> IO ()
wt_ act = do _ <- act; pure ()

||| Call f(db) if SQLite handle is open, else no-op.
withDB : StoreState -> (AnyPtr -> IO ()) -> IO ()
withDB st f = do
  mdb <- readIORef st.dbHandle
  case mdb of
    Nothing => pure ()
    Just db => f db

||| Join strings with tab separator.
joinTSV : List String -> String
joinTSV [] = ""
joinTSV [x] = x
joinTSV (x :: xs) = x ++ "\t" ++ joinTSV xs

wtMeme : StoreState -> Meme -> IO ()
wtMeme st m =
  let tsv = joinTSV [ show m.id, show m.experimentId
                    , m.label, m.canonicalLabel, m.text
                    , show m.domain, show m.sourceKind, show m.scope
                    , show m.evidenceN, show m.usageCount
                    , show m.rewardEma, show m.riskEma, show m.editEma
                    , show m.skipCount, show m.contradictionCount
                    , show m.membraneConflicts, show m.feedbackCount
                    , show m.activationTau
                    , show m.lastActiveAt, show m.createdAt, show m.updatedAt ]
  in withDB st (\db => wt_ (primIO (prim__wt_meme_tsv db tsv)))

------------------------------------------------------------------------
-- ID generation
------------------------------------------------------------------------

export
genId : StoreState -> String -> IO String
genId st pfx = do
  n <- readIORef st.nextId
  let next = n + 1
  writeIORef st.nextId next
  withDB st (\db => wt_ (primIO (prim__wt_config db "next_id" (show next))))
  pure (pfx ++ "-" ++ show n)

------------------------------------------------------------------------
-- Experiment operations
------------------------------------------------------------------------

export
createExperiment : StoreState -> String -> String -> ExperimentMode -> Timestamp -> IO Experiment
createExperiment st name slug mode now = do
  eid <- genId st "exp"
  let exp = MkExperiment (MkId eid) name slug mode Active now now
  modifyIORef st.experiments (exp ::)
  withDB st (\db => wt_ (primIO (prim__wt_exp db eid name slug (show mode) (show Active) (show now) (show now))))
  pure exp

export
getExperiment : StoreState -> ExperimentId -> IO (Maybe Experiment)
getExperiment st eid = do
  exps <- readIORef st.experiments
  pure (find (\e => e.id == eid) exps)

------------------------------------------------------------------------
-- Session operations
------------------------------------------------------------------------

export
createSession : StoreState -> ExperimentId -> AgentId -> String -> Timestamp -> IO Session
createSession st eid aid title now = do
  sid <- genId st "sess"
  let sess = MkSession (MkId sid) eid aid title now now Nothing
  modifyIORef st.sessions (sess ::)
  withDB st (\db => wt_ (primIO (prim__wt_sess db sid (show eid) (show aid) title (show now) (show now) "")))
  pure sess

export
getSession : StoreState -> SessionId -> IO (Maybe Session)
getSession st sid = do
  sessions <- readIORef st.sessions
  pure (find (\s => s.id == sid) sessions)

------------------------------------------------------------------------
-- Turn operations
------------------------------------------------------------------------

export
recordTurn : StoreState -> ExperimentId -> SessionId -> Nat -> String
          -> String -> String -> String -> Timestamp -> IO Turn
recordTurn st eid sid idx userText promptCtx respText membText now = do
  tid <- genId st "turn"
  let turn = MkTurn (MkId tid) eid sid idx userText promptCtx respText membText now
  modifyIORef st.turns (turn ::)
  withDB st (\db => wt_ (primIO (prim__wt_turn db tid (show eid) (show sid)
    (cast idx) userText promptCtx respText membText (show now))))
  pure turn

export
getSessionTurns : StoreState -> SessionId -> IO (List Turn)
getSessionTurns st sid = do
  allTurns <- readIORef st.turns
  pure (filter (\t => t.sessionId == sid) allTurns)

export
getRecentTurns : StoreState -> SessionId -> Nat -> IO (List Turn)
getRecentTurns st sid n = do
  allTurns <- getSessionTurns st sid
  let sorted = sortBy (\a, b => compare a.turnIndex b.turnIndex) allTurns
      l = length sorted
  pure (if l <= n then sorted else drop (minus l n) sorted)

------------------------------------------------------------------------
-- Meme operations
------------------------------------------------------------------------

export
upsertMeme : StoreState -> ExperimentId -> String -> String -> Domain
          -> SourceKind -> Scope -> Timestamp -> IO Meme
upsertMeme st eid label text domain sk scope now = do
  allMemes <- readIORef st.memes
  let canonical = toLower label
      existing = find (\m => m.experimentId == eid
                          && m.canonicalLabel == canonical
                          && m.domain == domain) allMemes
  case existing of
    Just m => do
      -- Update existing: bump usage, update timestamp
      let updated = { usageCount := m.usageCount + 1
                    , updatedAt := now } m
          others = filter (\x => x.id /= m.id) allMemes
      writeIORef st.memes (updated :: others)
      wtMeme st updated
      pure updated
    Nothing => do
      mid <- genId st "meme"
      let meme = MkMeme (MkId mid) eid label canonical text domain sk scope
                        0.0 1 0.0 0.0 0.0 0 0 0 0 86400.0 now now now
      modifyIORef st.memes (meme ::)
      wtMeme st meme
      indexMemeTerms st.ftsIndex (MkId mid) label text
      pure meme

export
getMeme : StoreState -> MemeId -> IO (Maybe Meme)
getMeme st mid = do
  allMemes <- readIORef st.memes
  pure (find (\m => m.id == mid) allMemes)

export
searchMemes : StoreState -> ExperimentId -> String -> Nat -> IO (List Meme)
searchMemes st eid query limit = do
  allMemes <- readIORef st.memes
  let q = toLower query
      matches = filter (\m => m.experimentId == eid
                           && (isInfixOf q (toLower m.label)
                            || isInfixOf q (toLower m.text))) allMemes
  pure (take limit matches)

------------------------------------------------------------------------
-- Memode operations
------------------------------------------------------------------------

export
upsertMemode : StoreState -> ExperimentId -> String -> String -> Domain
            -> List MemeId -> Timestamp -> IO Memode
upsertMemode st eid lbl summary dom memberIds now = do
  mid <- genId st "memode"
  let hash = show (length memberIds) ++ ":" ++ show (map show memberIds)
      md = MkMemode (MkId mid) eid lbl hash summary dom Global
                    0.0 1 0.0 0.0 0.0 0 86400.0 now now now
  modifyIORef st.memodes (md ::)
  let tsv = joinTSV [ mid, show eid, lbl, hash, summary
                    , show dom, show Global
                    , "0.0", "1", "0.0", "0.0", "0.0"
                    , "0", "86400.0"
                    , show now, show now, show now ]
  withDB st (\db => wt_ (primIO (prim__wt_memode_tsv db tsv)))
  pure md

export
getMemode : StoreState -> MemodeId -> IO (Maybe Memode)
getMemode st mid = do
  allMemodes <- readIORef st.memodes
  pure (find (\m => m.id == mid) allMemodes)

||| Materialize memodes from behavior memes with support edges.
||| Finds clusters of 2+ behavior memes connected by support edges
||| and creates memode records for them.
export
materializeMemodes : StoreState -> ExperimentId -> Timestamp -> IO (List Memode)
materializeMemodes st eid now = do
  allMemes <- readIORef st.memes
  allEdges <- readIORef st.edges
  let behaviorMemes = filter (\m => m.experimentId == eid && m.domain == Behavior) allMemes
      expEdges = filter (\e => e.experimentId == eid) allEdges
  -- Find pairs connected by support edges
  let connected = mapMaybe (\e =>
        case e.edgeType of
          Supports => Just (e.srcId, e.dstId)
          _ => Nothing) expEdges
  -- Build memode from each connected pair (simplified: one memode per edge)
  results <- traverse (\pair => do
    let (src, dst) = pair
        lbl = "memode:" ++ src ++ "+" ++ dst
    upsertMemode st eid lbl "auto-materialized" Behavior
      [MkId src, MkId dst] now) connected
  pure results

------------------------------------------------------------------------
-- Edge operations
------------------------------------------------------------------------

export
createEdge : StoreState -> ExperimentId -> NodeKind -> String -> NodeKind -> String
          -> EdgeType -> Double -> Timestamp -> IO Edge
createEdge st eid sk sid dk did et w now = do
  edgeId <- genId st "edge"
  let edge = MkEdge (MkId edgeId) eid sk sid dk did et w now now
  modifyIORef st.edges (edge ::)
  withDB st (\db => wt_ (primIO (prim__wt_edge db edgeId (show eid)
    (show sk) sid (show dk) did (show et) w (show now) (show now))))
  pure edge

export
getEdges : StoreState -> ExperimentId -> NodeKind -> String -> IO (List Edge)
getEdges st eid nk nid = do
  allEdges <- readIORef st.edges
  pure (filter (\e => e.experimentId == eid
                   && e.srcKind == nk
                   && e.srcId == nid) allEdges)

export
getExperimentMemes : StoreState -> ExperimentId -> IO (List Meme)
getExperimentMemes st eid = do
  allMemes <- readIORef st.memes
  pure (filter (\m => m.experimentId == eid) allMemes)

------------------------------------------------------------------------
-- Feedback operations
------------------------------------------------------------------------

export
recordFeedback : StoreState -> ExperimentId -> SessionId -> TurnId -> Verdict
              -> String -> String -> FeedbackSignal -> Timestamp -> IO FeedbackId
recordFeedback st eid sid tid v expl corr sig now = do
  fid <- genId st "fb"
  let fbid = MkId {a=FeedbackTag} fid
      rec  = MkFeedbackRecord fbid eid sid tid v expl corr sig
  modifyIORef st.feedbackEvents (rec ::)
  withDB st (\db => wt_ (primIO (prim__wt_fb db fid (show eid) (show sid) (show tid)
    (show v) expl corr sig.reward sig.risk sig.edit (show now))))
  pure fbid

------------------------------------------------------------------------
-- Membrane + trace event recording
------------------------------------------------------------------------

export
recordMembraneEvent : StoreState -> MembraneEventType -> String -> Timestamp -> IO ()
recordMembraneEvent st evt detail now = do
  modifyIORef st.membraneEvts ((evt, detail, now) ::)
  nid <- readIORef st.nextId
  let mid = "mbe-" ++ show nid
  withDB st (\db => wt_ (primIO (prim__wt_mbe db mid (show evt) detail (show now))))

export
recordTraceEvent : StoreState -> TraceEventType -> TraceLevel -> String -> Timestamp -> IO ()
recordTraceEvent st evt lvl msg now = do
  modifyIORef st.traceEvts ((evt, lvl, msg, now) ::)
  nid <- readIORef st.nextId
  let tid = "tre-" ++ show nid
  withDB st (\db => wt_ (primIO (prim__wt_tre db tid (show evt) (show lvl) msg (show now))))

------------------------------------------------------------------------
-- Document operations
------------------------------------------------------------------------

export
createDocument : StoreState -> ExperimentId -> String -> DocKind -> String -> String -> Timestamp -> IO Document
createDocument st eid path kind title sha now = do
  did <- genId st "doc"
  let doc = MkDocument (MkId did) eid path kind title sha Processing now
  modifyIORef st.documents (doc ::)
  withDB st (\db => wt_ (primIO (prim__wt_doc db did (show eid) path (show kind) title sha (show Processing) (show now))))
  pure doc

export
createChunk : StoreState -> ExperimentId -> DocumentId -> Nat -> Maybe Nat -> String -> Timestamp -> IO Chunk
createChunk st eid did idx pageNum text now = do
  cid <- genId st "chunk"
  let chunk = MkChunk (MkId cid) eid did idx pageNum text now
      pn : Int = case pageNum of Just p => cast p; Nothing => 0
  modifyIORef st.chunks (chunk ::)
  withDB st (\db => wt_ (primIO (prim__wt_chunk db cid (show eid) (show did) (cast idx) pn text (show now))))
  pure chunk

------------------------------------------------------------------------
-- Graph counts
------------------------------------------------------------------------

export
graphCounts : StoreState -> IO GraphCounts
graphCounts st = do
  ms  <- readIORef st.memes
  mds <- readIORef st.memodes
  es  <- readIORef st.edges
  ts  <- readIORef st.turns
  fs  <- readIORef st.feedbackEvents
  mev <- readIORef st.measurements
  mbe <- readIORef st.membraneEvts
  tre <- readIORef st.traceEvts
  pure (MkGraphCounts (length ms) (length mds) (length es) (length ts)
                      (length fs) (length mev) (length mbe) (length tre))

------------------------------------------------------------------------
-- Update feedback channels on a meme
------------------------------------------------------------------------

export
updateMemeChannels : StoreState -> MemeId -> Double -> Double -> Double -> IO ()
updateMemeChannels st mid newRw newRk newEd = do
  allMemes <- readIORef st.memes
  let updated = map (\m => if m.id == mid
                           then { rewardEma := newRw, riskEma := newRk, editEma := newEd } m
                           else m) allMemes
  writeIORef st.memes updated
  withDB st (\db => wt_ (primIO (prim__wt_memech db (show mid) newRw newRk newEd)))

------------------------------------------------------------------------
-- Agent operations
------------------------------------------------------------------------

export
createAgent : StoreState -> ExperimentId -> String -> String -> Timestamp -> IO Agent
createAgent st eid name persona now = do
  aid <- genId st "agent"
  let agent = MkAgent (MkId aid) eid name persona now
  modifyIORef st.agents (agent ::)
  withDB st (\db => wt_ (primIO (prim__wt_agent db aid (show eid) name persona (show now))))
  pure agent

------------------------------------------------------------------------
-- Active set snapshot operations
------------------------------------------------------------------------

export
recordActiveSetEntry : StoreState -> ExperimentId -> SessionId -> TurnId
                    -> String -> String -> Domain -> Double -> Double -> Double -> Double
                    -> Timestamp -> IO ()
recordActiveSetEntry st eid sid tid nid label dom sel sem act reg now = do
  asid <- genId st "aset"
  let entry = MkActiveSetEntry asid eid sid tid MemeNode nid label dom sel sem act reg now
  modifyIORef st.activeSetSnaps (entry ::)
  let tsv = joinTSV [ asid, show eid, show sid, show tid
                    , show MemeNode, nid, label, show dom
                    , show sel, show sem, show act, show reg
                    , show now ]
  withDB st (\db => wt_ (primIO (prim__wt_aset_tsv db tsv)))

------------------------------------------------------------------------
-- Measurement event operations
------------------------------------------------------------------------

export
recordMeasurementEvent : StoreState -> ExperimentId -> SessionId
                      -> MeasurementAction -> MeasurementState
                      -> String -> String -> String -> String -> String -> String
                      -> Timestamp -> IO MeasurementEvent
recordMeasurementEvent st eid sid action state operator evidence
                       before proposed committed revertOf now = do
  mid <- genId st "meas"
  let evt = MkMeasurementEvent mid eid sid action state operator evidence
                               before proposed committed revertOf now
  modifyIORef st.measurements (evt ::)
  let tsv = joinTSV [ mid, show eid, show sid, show action, show state
                    , operator, evidence, before, proposed, committed
                    , revertOf, show now ]
  withDB st (\db => wt_ (primIO (prim__wt_meas_tsv db tsv)))
  pure evt

------------------------------------------------------------------------
-- Export artifact operations
------------------------------------------------------------------------

export
recordExportArtifact : StoreState -> ExperimentId -> String -> String -> String
                    -> Timestamp -> IO ExportArtifact
recordExportArtifact st eid artType path graphHash now = do
  aid <- genId st "expart"
  let art = MkExportArtifact aid eid artType path graphHash now
  modifyIORef st.exportArtifacts (art ::)
  withDB st (\db => wt_ (primIO (prim__wt_export db aid (show eid) artType path graphHash (show now))))
  pure art

------------------------------------------------------------------------
-- Turn metadata operations
------------------------------------------------------------------------

export
recordTurnMetadata : StoreState -> TurnMetadata -> IO ()
recordTurnMetadata st meta = do
  modifyIORef st.turnMetadata (meta ::)
  let tsv = joinTSV [ show meta.turnId
                    , meta.inferenceModeReq, meta.inferenceModeEff
                    , meta.budgetMode, meta.budgetPressure
                    , show meta.budgetUsedTokens, show meta.budgetRemainingTokens
                    , show meta.activeSetSize, meta.reasoningText
                    , show meta.temperature, show meta.maxOutput
                    , show meta.responseCap, show meta.createdAt ]
  withDB st (\db => wt_ (primIO (prim__wt_tmeta_tsv db tsv)))

------------------------------------------------------------------------
-- Chunk CRUD operations
------------------------------------------------------------------------

||| Get a chunk by ID.
export
getChunk : StoreState -> ChunkId -> IO (Maybe Chunk)
getChunk st cid = do
  allChunks <- readIORef st.chunks
  pure (find (\c => c.id == cid) allChunks)

||| Get all chunks (filtered by experiment).
export
getChunks : StoreState -> ExperimentId -> IO (List Chunk)
getChunks st eid = do
  allChunks <- readIORef st.chunks
  pure (filter (\c => c.experimentId == eid) allChunks)

||| Get chunks belonging to a specific document.
export
getChunksByDocument : StoreState -> DocumentId -> IO (List Chunk)
getChunksByDocument st did = do
  allChunks <- readIORef st.chunks
  pure (sortBy (\a, b => compare a.chunkIndex b.chunkIndex)
    (filter (\c => c.documentId == did) allChunks))

------------------------------------------------------------------------
-- Document read operations
------------------------------------------------------------------------

||| Get a document by ID.
export
getDocument : StoreState -> DocumentId -> IO (Maybe Document)
getDocument st did = do
  allDocs <- readIORef st.documents
  pure (find (\d => d.id == did) allDocs)

||| Get all documents for an experiment.
export
getDocuments : StoreState -> ExperimentId -> IO (List Document)
getDocuments st eid = do
  allDocs <- readIORef st.documents
  pure (filter (\d => d.experimentId == eid) allDocs)

------------------------------------------------------------------------
-- Document SHA deduplication
------------------------------------------------------------------------

||| Check whether a document with the given SHA256 hash already exists
||| in the experiment. Prevents duplicate ingestion of the same content.
export
documentExistsBySha : StoreState -> ExperimentId -> String -> IO Bool
documentExistsBySha st eid sha = do
  allDocs <- readIORef st.documents
  pure (any (\d => d.experimentId == eid && d.sha256 == sha) allDocs)

------------------------------------------------------------------------
-- FTS search
------------------------------------------------------------------------

||| Search memes using the inverted index.
||| Tokenizes the query, looks up each term in the index,
||| and returns memes that match any query term, ranked by hit count.
export
ftsSearchMemes : StoreState -> ExperimentId -> String -> IO (List Meme)
ftsSearchMemes st eid query = do
  let queryTerms = tokenize query
  entries <- readIORef st.ftsIndex.iiEntries
  allMemes <- readIORef st.memes
  -- Collect all matching meme IDs with hit counts
  let matchedPostings = concatMap (\qt =>
        case lookup qt entries of
          Nothing => []
          Just ps => map (\p => p.postingMemeId) ps) queryTerms
      -- Count occurrences per meme ID
      memeIdStrs = map show matchedPostings
      uniqueIds  = nub memeIdStrs
      -- Sort by hit count (descending)
      ranked = sortBy (\a, b => compare (countHits b memeIdStrs) (countHits a memeIdStrs)) uniqueIds
      -- Resolve to actual memes in this experiment
      results = mapMaybe (\idStr =>
        find (\m => show m.id == idStr && m.experimentId == eid) allMemes) ranked
  pure results
  where
    countHits : String -> List String -> Nat
    countHits target xs = length (filter (== target) xs)

||| Rebuild the FTS index from all memes currently in the store.
||| Called after bulk loading from SQLite.
export
rebuildFtsIndex : StoreState -> IO ()
rebuildFtsIndex st = do
  writeIORef st.ftsIndex.iiEntries []
  allMemes <- readIORef st.memes
  traverse_ (\m => indexMemeTerms st.ftsIndex m.id m.label m.text) allMemes

------------------------------------------------------------------------
-- Measurement event queries
------------------------------------------------------------------------

||| Get all measurement events for an experiment.
export
getMeasurementEvents : StoreState -> ExperimentId -> IO (List MeasurementEvent)
getMeasurementEvents st eid = do
  allEvts <- readIORef st.measurements
  pure (filter (\e => e.experimentId == eid) allEvts)

||| Get measurement events targeting specific node IDs.
||| Checks the beforeState and proposedState fields for the target ID string.
export
getMeasurementEventsByTarget : StoreState -> ExperimentId -> String -> IO (List MeasurementEvent)
getMeasurementEventsByTarget st eid targetId = do
  allEvts <- readIORef st.measurements
  pure (filter (\e => e.experimentId == eid
                   && (isInfixOf targetId e.beforeState
                    || isInfixOf targetId e.proposedState
                    || isInfixOf targetId e.committedState)) allEvts)

||| Revert a measurement event by creating a new revert event.
||| Reversion is itself part of the measurement ledger — history is never
||| silently mutated.
export
revertMeasurementEvent : StoreState -> ExperimentId -> SessionId
                      -> String -> Timestamp -> IO (Maybe MeasurementEvent)
revertMeasurementEvent st eid sid originalEventId now = do
  allEvts <- readIORef st.measurements
  case find (\e => e.id == originalEventId && e.experimentId == eid) allEvts of
    Nothing => pure Nothing
    Just orig => do
      -- Create a revert event that references the original
      revEvt <- recordMeasurementEvent st eid sid
                  MeasurementRevert Committed
                  orig.operator orig.evidence
                  orig.committedState orig.beforeState orig.beforeState
                  originalEventId now
      pure (Just revEvt)
