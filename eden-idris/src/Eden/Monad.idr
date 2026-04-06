||| EdenM: a reader+IO monad that threads environment through the pipeline.
|||
||| Eliminates the manual parameter threading of StoreState, ExperimentId,
||| SessionId, and Timestamp through every function call.
|||
||| Usage:
|||   executeTurn : String -> EdenM TurnResult
|||   instead of:
|||   executeTurn : StoreState -> ExperimentId -> SessionId -> Timestamp -> String -> IO TurnResult
module Eden.Monad

import Data.IORef
import System
import Eden.Types
import Eden.Store.InMemory
import Eden.Trace

------------------------------------------------------------------------
-- Environment
------------------------------------------------------------------------

||| Immutable environment threaded through the EDEN pipeline.
public export
record EdenEnv where
  constructor MkEdenEnv
  store      : StoreState
  eid        : ExperimentId
  sid        : SessionId
  ts         : Timestamp
  trace      : TraceLog
  principles : String

------------------------------------------------------------------------
-- The EdenM monad (ReaderT EdenEnv IO)
------------------------------------------------------------------------

||| Eden computation: a function from environment to IO action.
public export
record EdenM (a : Type) where
  constructor MkEdenM
  runEdenM : EdenEnv -> IO a

||| Execute an Eden computation with a given environment.
public export
runEden : EdenEnv -> EdenM a -> IO a
runEden env act = act.runEdenM env

------------------------------------------------------------------------
-- Functor
------------------------------------------------------------------------

public export
Functor EdenM where
  map f (MkEdenM act) = MkEdenM (\env => map f (act env))

------------------------------------------------------------------------
-- Applicative
------------------------------------------------------------------------

public export
Applicative EdenM where
  pure x = MkEdenM (\_ => pure x)
  (MkEdenM f) <*> (MkEdenM x) = MkEdenM (\env => f env <*> x env)

------------------------------------------------------------------------
-- Monad
------------------------------------------------------------------------

public export
Monad EdenM where
  (MkEdenM act) >>= f = MkEdenM (\env => do
    a <- act env
    (f a).runEdenM env)

------------------------------------------------------------------------
-- HasIO (lift raw IO into EdenM)
------------------------------------------------------------------------

public export
HasIO EdenM where
  liftIO act = MkEdenM (\_ => act)

------------------------------------------------------------------------
-- Environment access
------------------------------------------------------------------------

||| Get the full environment.
public export
ask : EdenM EdenEnv
ask = MkEdenM (\env => pure env)

||| Project a field from the environment.
public export
asks : (EdenEnv -> a) -> EdenM a
asks f = MkEdenM (\env => pure (f env))

||| Get the store.
public export
getStore : EdenM StoreState
getStore = asks store

||| Get the experiment ID.
public export
getExpId : EdenM ExperimentId
getExpId = asks eid

||| Get the session ID.
public export
getSessId : EdenM SessionId
getSessId = asks sid

||| Get the timestamp.
public export
getTimestamp : EdenM Timestamp
getTimestamp = asks ts

||| Get the trace log.
public export
getTraceLog : EdenM TraceLog
getTraceLog = asks trace

------------------------------------------------------------------------
-- System clock integration
------------------------------------------------------------------------

||| Get the current time as an EDEN Timestamp.
||| Produces an ISO 8601 string from epoch seconds (Hinnant civil_from_days).
export
currentTimestamp : HasIO io => io Timestamp
currentTimestamp = do
  t <- time
  let remSec   = t `mod` 86400
      h        = remSec `div` 3600
      mn       = (remSec `mod` 3600) `div` 60
      s        = remSec `mod` 60
      -- Hinnant civil_from_days algorithm (days since 1970-01-01 -> y/m/d)
      z        = t `div` 86400 + 719468
      era      = z `div` 146097
      doe      = z - era * 146097
      yoe      = (doe - doe `div` 1461 + doe `div` 36524 - doe `div` 146096) `div` 365
      y        = yoe + era * 400
      doy      = doe - (365 * yoe + yoe `div` 4 - yoe `div` 100)
      mp       = (5 * doy + 2) `div` 153
      d        = doy - (153 * mp + 2) `div` 5 + 1
      m        = if mp < 10 then mp + 3 else mp - 9
      year     = if m <= 2 then y + 1 else y
      pad2     : Integer -> String
      pad2 n   = if n < 10 then "0" ++ show n else show n
  pure (MkTimestamp (show year ++ "-" ++ pad2 m ++ "-" ++ pad2 d
                  ++ "T" ++ pad2 h ++ ":" ++ pad2 mn ++ ":" ++ pad2 s ++ "Z"))

------------------------------------------------------------------------
-- Convenience: lifted store operations
------------------------------------------------------------------------

||| Upsert a meme in EdenM.
public export
eUpsertMeme : String -> String -> Domain -> SourceKind -> Scope -> EdenM Meme
eUpsertMeme label text domain sk scope = do
  env <- ask
  liftIO (upsertMeme env.store env.eid label text domain sk scope env.ts)

||| Create an edge in EdenM.
public export
eCreateEdge : NodeKind -> String -> NodeKind -> String
           -> EdgeType -> Double -> EdenM Edge
eCreateEdge sk sid dk did et w = do
  env <- ask
  liftIO (createEdge env.store env.eid sk sid dk did et w env.ts)

||| Get experiment memes in EdenM.
public export
eGetMemes : EdenM (List Meme)
eGetMemes = do
  env <- ask
  liftIO (getExperimentMemes env.store env.eid)

||| Record a turn in EdenM.
public export
eRecordTurn : Nat -> String -> String -> String -> String -> EdenM Turn
eRecordTurn idx userText convPrompt rawResp membraneText = do
  env <- ask
  liftIO (recordTurn env.store env.eid env.sid idx userText convPrompt
            rawResp membraneText env.ts)

||| Get recent turns in EdenM.
public export
eGetRecentTurns : Nat -> EdenM (List Turn)
eGetRecentTurns n = do
  env <- ask
  liftIO (getRecentTurns env.store env.sid n)

||| Record feedback in EdenM.
public export
eRecordFeedback : TurnId -> Verdict -> String -> String
               -> FeedbackSignal -> EdenM FeedbackId
eRecordFeedback tid v expl corr sig = do
  env <- ask
  liftIO (recordFeedback env.store env.eid env.sid tid v expl corr sig env.ts)

||| Get graph counts in EdenM.
public export
eGraphCounts : EdenM GraphCounts
eGraphCounts = do
  st <- getStore
  liftIO (graphCounts st)

||| Materialize memodes in EdenM.
public export
eMaterializeMemodes : EdenM (List Memode)
eMaterializeMemodes = do
  env <- ask
  liftIO (materializeMemodes env.store env.eid env.ts)

||| Update meme channels in EdenM.
public export
eUpdateMemeChannels : MemeId -> Double -> Double -> Double -> EdenM ()
eUpdateMemeChannels mid rw rk ed = do
  st <- getStore
  liftIO (updateMemeChannels st mid rw rk ed)

||| Get session turns in EdenM.
public export
eGetSessionTurns : EdenM (List Turn)
eGetSessionTurns = do
  env <- ask
  liftIO (getSessionTurns env.store env.sid)

||| Create an agent in EdenM.
public export
eCreateAgent : String -> String -> EdenM Agent
eCreateAgent name persona = do
  env <- ask
  liftIO (createAgent env.store env.eid name persona env.ts)

||| Record an active set entry in EdenM.
public export
eRecordActiveSetEntry : TurnId -> String -> String -> Domain
                     -> Double -> Double -> Double -> Double -> EdenM ()
eRecordActiveSetEntry tid nid label dom sel sem act reg = do
  env <- ask
  liftIO (recordActiveSetEntry env.store env.eid env.sid tid nid label dom
            sel sem act reg env.ts)

||| Record turn metadata in EdenM.
public export
eRecordTurnMetadata : TurnMetadata -> EdenM ()
eRecordTurnMetadata meta = do
  st <- getStore
  liftIO (recordTurnMetadata st meta)

||| Record a measurement event in EdenM.
public export
eRecordMeasurementEvent : MeasurementAction -> MeasurementState
                       -> String -> String -> String -> String -> String -> String
                       -> EdenM MeasurementEvent
eRecordMeasurementEvent action state operator evidence before proposed committed revertOf = do
  env <- ask
  liftIO (recordMeasurementEvent env.store env.eid env.sid action state
            operator evidence before proposed committed revertOf env.ts)

||| Record an export artifact in EdenM.
public export
eRecordExportArtifact : String -> String -> String -> EdenM ExportArtifact
eRecordExportArtifact artType path graphHash = do
  env <- ask
  liftIO (recordExportArtifact env.store env.eid artType path graphHash env.ts)

------------------------------------------------------------------------
-- Convenience: chunk operations
------------------------------------------------------------------------

||| Get all chunks for the current experiment.
public export
eGetChunks : EdenM (List Chunk)
eGetChunks = do
  env <- ask
  liftIO (getChunks env.store env.eid)

||| Get chunks belonging to a specific document.
public export
eGetChunksByDocument : DocumentId -> EdenM (List Chunk)
eGetChunksByDocument did = do
  st <- getStore
  liftIO (getChunksByDocument st did)

||| Create a chunk in EdenM.
public export
eCreateChunk : DocumentId -> Nat -> Maybe Nat -> String -> EdenM Chunk
eCreateChunk did idx pageNum text = do
  env <- ask
  liftIO (createChunk env.store env.eid did idx pageNum text env.ts)

------------------------------------------------------------------------
-- Convenience: document operations
------------------------------------------------------------------------

||| Get all documents for the current experiment.
public export
eGetDocuments : EdenM (List Document)
eGetDocuments = do
  env <- ask
  liftIO (getDocuments env.store env.eid)

||| Check whether a document with the given SHA256 already exists.
public export
eDocumentExistsBySha : String -> EdenM Bool
eDocumentExistsBySha sha = do
  env <- ask
  liftIO (documentExistsBySha env.store env.eid sha)

------------------------------------------------------------------------
-- Convenience: FTS search
------------------------------------------------------------------------

||| Search memes using the inverted full-text index.
public export
eFtsSearchMemes : String -> EdenM (List Meme)
eFtsSearchMemes query = do
  env <- ask
  liftIO (ftsSearchMemes env.store env.eid query)

------------------------------------------------------------------------
-- Convenience: measurement event queries
------------------------------------------------------------------------

||| Get all measurement events for the current experiment.
public export
eGetMeasurementEvents : EdenM (List MeasurementEvent)
eGetMeasurementEvents = do
  env <- ask
  liftIO (getMeasurementEvents env.store env.eid)

||| Get measurement events targeting a specific node ID.
public export
eGetMeasurementEventsByTarget : String -> EdenM (List MeasurementEvent)
eGetMeasurementEventsByTarget targetId = do
  env <- ask
  liftIO (getMeasurementEventsByTarget env.store env.eid targetId)

||| Revert a measurement event by creating a new revert event.
public export
eRevertMeasurementEvent : String -> EdenM (Maybe MeasurementEvent)
eRevertMeasurementEvent originalEventId = do
  env <- ask
  liftIO (revertMeasurementEvent env.store env.eid env.sid originalEventId env.ts)

------------------------------------------------------------------------
-- Convenience: lifted trace operations
------------------------------------------------------------------------

||| Trace a turn event in EdenM.
public export
eTraceTurn : TurnId -> String -> EdenM ()
eTraceTurn tid msg = do
  env <- ask
  liftIO (traceTurnInfo env.trace env.eid env.sid tid msg env.ts)

||| Trace a feedback event in EdenM.
public export
eTraceFeedback : TurnId -> String -> EdenM ()
eTraceFeedback tid msg = do
  env <- ask
  liftIO (traceFeedbackEvent env.trace env.eid env.sid tid msg env.ts)

------------------------------------------------------------------------
-- Create environment
------------------------------------------------------------------------

||| Create a fresh EdenEnv from a store and session setup.
export
newEdenEnv : StoreState -> ExperimentId -> SessionId -> Timestamp -> String -> IO EdenEnv
newEdenEnv st eid sid ts princ = do
  tlog <- newTraceLog
  pure (MkEdenEnv st eid sid ts tlog princ)
