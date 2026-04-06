||| Session management: profile overrides, conversation archiving,
||| markdown log export, and session state snapshots.
|||
||| Mirrors the Python runtime session_profile_request,
||| update_conversation_archive, conversation_archive_records,
||| conversation_archive_preview, write_conversation_log, and
||| session_state_snapshot operations.
module Eden.Session

import Data.IORef
import Data.List
import Data.Maybe
import Data.String
import System.File
import Eden.Types
import Eden.Config
import Eden.Inference
import Eden.Store.InMemory
import Eden.Monad

------------------------------------------------------------------------
-- Session profile (inference settings per session)
------------------------------------------------------------------------

||| Per-session inference profile overrides.
||| Mirrors Python InferenceProfileRequest stored in session metadata.
public export
record SessionProfile where
  constructor MkSessionProfile
  spMode        : InferenceMode
  spTemp        : Double
  spMaxOutput   : Nat
  spTopP        : Double
  spRepPen      : Double
  spRetrDepth   : Nat
  spMaxCtx      : Nat
  spHistTurns   : Nat
  spRespCap     : Nat
  spLowMotion   : Bool
  spDebug       : Bool
  spBudget      : BudgetMode
  spTitle       : String

||| Build a SessionProfile from the default ProfileRequest.
public export
defaultSessionProfile : SessionProfile
defaultSessionProfile =
  let req = defaultProfileRequest
  in MkSessionProfile
       req.prMode req.prTemp req.prMaxOutput req.prTopP req.prRepPen
       req.prRetrDepth req.prMaxCtx req.prHistTurns req.prRespCap
       req.prLowMotion req.prDebug req.prBudget req.prTitle

------------------------------------------------------------------------
-- Archive record
------------------------------------------------------------------------

||| Metadata attached to an archived session.
public export
record ArchiveRecord where
  constructor MkArchiveRecord
  arSessionId : SessionId
  arTitle     : String
  arFolder    : String
  arTags      : List String
  arTurnCount : Nat
  arCreatedAt : Eden.Types.Timestamp

------------------------------------------------------------------------
-- Session metadata store (archive info + profile overrides)
------------------------------------------------------------------------

||| Per-session mutable metadata: archive info and profile overrides.
public export
record SessionMeta where
  constructor MkSessionMeta
  smFolder  : String
  smTags    : List String
  smProfile : SessionProfile

||| Global session metadata map, stored as a flat list of (SessionId, SessionMeta).
public export
record SessionMetaStore where
  constructor MkSessionMetaStore
  entries : IORef (List (SessionId, SessionMeta))

||| Create a fresh metadata store.
export
newSessionMetaStore : IO SessionMetaStore
newSessionMetaStore = do
  ref <- newIORef []
  pure (MkSessionMetaStore ref)

||| Look up metadata for a session.
export
lookupMeta : SessionMetaStore -> SessionId -> IO (Maybe SessionMeta)
lookupMeta sms sid = do
  xs <- readIORef sms.entries
  pure (map snd (find (\pair => fst pair == sid) xs))

||| Upsert metadata for a session.
export
upsertMeta : SessionMetaStore -> SessionId -> SessionMeta -> IO ()
upsertMeta sms sid meta = do
  xs <- readIORef sms.entries
  let others = filter (\pair => fst pair /= sid) xs
  writeIORef sms.entries ((sid, meta) :: others)

||| Get the profile for a session, falling back to defaults.
export
getSessionProfile : SessionMetaStore -> SessionId -> IO SessionProfile
getSessionProfile sms sid = do
  mmeta <- lookupMeta sms sid
  pure (case mmeta of
    Just m  => m.smProfile
    Nothing => defaultSessionProfile)

------------------------------------------------------------------------
-- JSON helpers (local, matching Export.idr patterns)
------------------------------------------------------------------------

escJsonChar : Char -> List Char
escJsonChar '"'  = ['\\', '"']
escJsonChar '\\' = ['\\', '\\']
escJsonChar '\n' = ['\\', 'n']
escJsonChar '\t' = ['\\', 't']
escJsonChar c    = [c]

escJson : String -> String
escJson = pack . concatMap escJsonChar . unpack

jStr : String -> String
jStr s = "\"" ++ escJson s ++ "\""

jNum : Double -> String
jNum d =
  let i = cast {to=Integer} (d * 1000.0)
  in show (cast {to=Double} i / 1000.0)

jNat : Nat -> String
jNat = show

jBool : Bool -> String
jBool True  = "true"
jBool False = "false"

jObj : List (String, String) -> String
jObj fields =
  "{" ++ joinBy ", " (map (\kv => jStr (fst kv) ++ ": " ++ snd kv) fields) ++ "}"

jArr : List String -> String
jArr items = "[" ++ joinBy ", " items ++ "]"

------------------------------------------------------------------------
-- Parse helpers for updateSessionProfile
------------------------------------------------------------------------

parseInfMode : String -> Maybe InferenceMode
parseInfMode s =
  if s == "manual" then Just Manual
  else if s == "runtime_auto" then Just RuntimeAuto
  else if s == "adam_auto" then Just AdamAuto
  else Nothing

parseBudMode : String -> Maybe BudgetMode
parseBudMode s =
  if s == "tight" then Just Tight
  else if s == "balanced" then Just Balanced
  else if s == "wide" then Just Wide
  else Nothing

parseBoolField : String -> Maybe Bool
parseBoolField s =
  if s == "true" then Just True
  else if s == "false" then Just False
  else Nothing

parseNatField : String -> Maybe Nat
parseNatField s = case parsePositive {a=Integer} s of
  Just n  => Just (cast n)
  Nothing => Nothing

parseDoubleField : String -> Maybe Double
parseDoubleField = parseDouble

------------------------------------------------------------------------
-- Profile update by field name
------------------------------------------------------------------------

||| Update a single field of a SessionProfile by name and string value.
||| Returns the updated profile, or the original if the field/value is invalid.
export
updateProfileField : SessionProfile -> (field : String) -> (value : String) -> SessionProfile
updateProfileField sp field v =
  if field == "mode" then
    case parseInfMode v of
      Just m  => { spMode := m } sp
      Nothing => sp
  else if field == "temperature" then
    case parseDoubleField v of
      Just d  => { spTemp := d } sp
      Nothing => sp
  else if field == "max_output" then
    case parseNatField v of
      Just n  => { spMaxOutput := n } sp
      Nothing => sp
  else if field == "top_p" then
    case parseDoubleField v of
      Just d  => { spTopP := d } sp
      Nothing => sp
  else if field == "repetition_penalty" then
    case parseDoubleField v of
      Just d  => { spRepPen := d } sp
      Nothing => sp
  else if field == "retrieval_depth" then
    case parseNatField v of
      Just n  => { spRetrDepth := n } sp
      Nothing => sp
  else if field == "max_context" then
    case parseNatField v of
      Just n  => { spMaxCtx := n } sp
      Nothing => sp
  else if field == "history_turns" then
    case parseNatField v of
      Just n  => { spHistTurns := n } sp
      Nothing => sp
  else if field == "response_cap" then
    case parseNatField v of
      Just n  => { spRespCap := n } sp
      Nothing => sp
  else if field == "low_motion" then
    case parseBoolField v of
      Just b  => { spLowMotion := b } sp
      Nothing => sp
  else if field == "debug" then
    case parseBoolField v of
      Just b  => { spDebug := b } sp
      Nothing => sp
  else if field == "budget_mode" then
    case parseBudMode v of
      Just m  => { spBudget := m } sp
      Nothing => sp
  else if field == "title" then
    { spTitle := v } sp
  else sp

------------------------------------------------------------------------
-- Update session profile
------------------------------------------------------------------------

||| Update a single inference setting for a session.
||| Creates default metadata if the session has none yet.
export
updateSessionProfile : SessionMetaStore -> SessionId -> (field : String) -> (value : String) -> IO ()
updateSessionProfile sms sid field value = do
  mmeta <- lookupMeta sms sid
  let meta = fromMaybe (MkSessionMeta "inbox" [] defaultSessionProfile) mmeta
      newProf = updateProfileField meta.smProfile field value
  upsertMeta sms sid ({ smProfile := newProf } meta)

------------------------------------------------------------------------
-- Conversation archive
------------------------------------------------------------------------

||| Normalize a folder name: trim, lowercase, replace spaces with hyphens.
normFolder : String -> String
normFolder s =
  let trimmed = trim s
      lower   = toLower trimmed
  in pack (map (\c => if c == ' ' then '-' else c) (unpack lower))

||| Normalize tags: trim each, lowercase, filter blanks.
normTags : List String -> List String
normTags ts = filter (\t => length t > 0) (map (\t => toLower (trim t)) ts)

||| Archive a session with folder and tag metadata.
export
archiveSession : SessionMetaStore -> SessionId -> (folder : String) -> (tags : List String) -> IO ()
archiveSession sms sid folder tags = do
  mmeta <- lookupMeta sms sid
  let meta = fromMaybe (MkSessionMeta "inbox" [] defaultSessionProfile) mmeta
  upsertMeta sms sid ({ smFolder := normFolder folder, smTags := normTags tags } meta)

||| List all sessions that have archive metadata.
export
listArchives : SessionMetaStore -> StoreState -> IO (List ArchiveRecord)
listArchives sms st = do
  allMeta <- readIORef sms.entries
  sessions <- readIORef st.sessions
  allTurns <- readIORef st.turns
  let go : List (SessionId, SessionMeta) -> List ArchiveRecord
      go [] = []
      go ((sid, meta) :: rest) =
        let mSess = find (\s => s.id == sid) sessions
            tcount = length (filter (\t => t.sessionId == sid) allTurns)
        in case mSess of
          Just sess =>
            MkArchiveRecord sid sess.title meta.smFolder meta.smTags tcount sess.createdAt
              :: go rest
          Nothing => go rest
  pure (go allMeta)

------------------------------------------------------------------------
-- Archive preview
------------------------------------------------------------------------

fmtPreviewTurn : Turn -> String
fmtPreviewTurn t = "## Turn " ++ show t.turnIndex ++ "\n"
               ++ "**You:** " ++ substr 0 200 t.userText ++ "\n"
               ++ "**Adam:** " ++ substr 0 300 t.membraneText ++ "\n"

||| Preview an archived session: return the last N turns formatted as text.
export
previewArchive : StoreState -> SessionId -> (turnLimit : Nat) -> IO String
previewArchive st sid turnLimit = do
  allTurns <- getSessionTurns st sid
  let sorted = sortBy (\x, y => compare x.turnIndex y.turnIndex) allTurns
      n = length sorted
  let recent = if n <= turnLimit then sorted else drop (minus n turnLimit) sorted
  pure (case recent of
    [] => "(no turns yet)"
    _  => unlines (map fmtPreviewTurn recent))

------------------------------------------------------------------------
-- Conversation log export (markdown)
------------------------------------------------------------------------

fmtLogTurn : List FeedbackRecord -> Turn -> String
fmtLogTurn sessionFb t =
  let turnFb = filter (\fb => fb.frTurnId == t.id) sessionFb
      fbLine = case turnFb of
        []       => ""
        (fb :: _) => "*Feedback: " ++ show fb.frVerdict ++ "*\n\n"
  in "## Turn " ++ show t.turnIndex ++ "\n\n"
  ++ "**You:** " ++ t.userText ++ "\n\n"
  ++ "**Adam:** " ++ t.membraneText ++ "\n\n"
  ++ fbLine

||| Export a session as a markdown conversation log.
||| Returns Right path on success, Left error on failure.
export
writeConversationLog : StoreState -> SessionMetaStore -> SessionId -> (outPath : String) -> IO (Either String String)
writeConversationLog st sms sid outPath = do
  mSess <- getSession st sid
  case mSess of
    Nothing => pure (Left ("Session not found: " ++ show sid))
    Just sess => do
      allTurns <- getSessionTurns st sid
      let sorted = sortBy (\a, b => compare a.turnIndex b.turnIndex) allTurns
      profile <- getSessionProfile sms sid
      allFb <- readIORef st.feedbackEvents
      let sessionFb = filter (\fb => fb.frSessionId == sid) allFb
          header = "# Conversation Log -- Session " ++ show sid ++ "\n\n"
                ++ "- session: " ++ sess.title ++ " (" ++ show sid ++ ")\n"
                ++ "- experiment: " ++ show sess.experimentId ++ "\n"
                ++ "- mode: " ++ show profile.spMode ++ "\n"
                ++ "- budget: " ++ show profile.spBudget ++ "\n\n"
          body = case sorted of
            [] => "_No turns yet._\n"
            _  => concatMap (fmtLogTurn sessionFb) sorted
          content = header ++ body
      Right () <- writeFile outPath content
        | Left err => pure (Left ("Write failed: " ++ show err))
      pure (Right outPath)

------------------------------------------------------------------------
-- Session state snapshot (JSON)
------------------------------------------------------------------------

||| Serialize a SessionProfile to JSON.
profileToJson : SessionProfile -> String
profileToJson sp = jObj
  [ ("mode",              jStr (show sp.spMode))
  , ("temperature",       jNum sp.spTemp)
  , ("max_output",        jNat sp.spMaxOutput)
  , ("top_p",             jNum sp.spTopP)
  , ("repetition_penalty", jNum sp.spRepPen)
  , ("retrieval_depth",   jNat sp.spRetrDepth)
  , ("max_context",       jNat sp.spMaxCtx)
  , ("history_turns",     jNat sp.spHistTurns)
  , ("response_cap",      jNat sp.spRespCap)
  , ("low_motion",        jBool sp.spLowMotion)
  , ("debug",             jBool sp.spDebug)
  , ("budget_mode",       jStr (show sp.spBudget))
  , ("title",             jStr sp.spTitle)
  ]

||| Serialize a Turn to JSON.
turnToJson : Turn -> String
turnToJson t = jObj
  [ ("id",         jStr (show t.id))
  , ("turn_index", jNat t.turnIndex)
  , ("user_text",  jStr (substr 0 500 t.userText))
  , ("response",   jStr (substr 0 500 t.membraneText))
  , ("created_at", jStr (show t.createdAt))
  ]

||| Serialize an ArchiveRecord to JSON.
export
archiveToJson : ArchiveRecord -> String
archiveToJson ar = jObj
  [ ("session_id", jStr (show ar.arSessionId))
  , ("title",      jStr ar.arTitle)
  , ("folder",     jStr ar.arFolder)
  , ("tags",       jArr (map jStr ar.arTags))
  , ("turn_count", jNat ar.arTurnCount)
  , ("created_at", jStr (show ar.arCreatedAt))
  ]

||| Full serialization of session state for debugging/export.
||| Returns a JSON string with session metadata, profile, recent turns, and graph counts.
export
sessionSnapshot : StoreState -> SessionMetaStore -> SessionId -> IO String
sessionSnapshot st sms sid = do
  mSess <- getSession st sid
  case mSess of
    Nothing => pure (jObj [("error", jStr ("Session not found: " ++ show sid))])
    Just sess => do
      profile <- getSessionProfile sms sid
      allTurns <- getSessionTurns st sid
      let sorted = sortBy (\a, b => compare a.turnIndex b.turnIndex) allTurns
      counts <- graphCounts st
      mmeta <- lookupMeta sms sid
      let folder = case mmeta of
                     Just m => m.smFolder
                     Nothing => "inbox"
          tags = case mmeta of
                   Just m => m.smTags
                   Nothing => the (List String) []
          lastTurn = case reverse sorted of
            []       => jObj [("present", jBool False)]
            (t :: _) => jObj
              [ ("present",    jBool True)
              , ("turn_id",    jStr (show t.id))
              , ("turn_index", jNat t.turnIndex)
              , ("user_text",  jStr (substr 0 300 t.userText))
              , ("response",   jStr (substr 0 300 t.membraneText))
              ]
      pure (jObj
        [ ("session_id",      jStr (show sid))
        , ("session_title",   jStr sess.title)
        , ("experiment_id",   jStr (show sess.experimentId))
        , ("created_at",      jStr (show sess.createdAt))
        , ("folder",          jStr folder)
        , ("tags",            jArr (map jStr tags))
        , ("turn_count",      jNat (length sorted))
        , ("profile",         profileToJson profile)
        , ("last_turn",       lastTurn)
        , ("graph_counts",    jObj
            [ ("memes",     jNat counts.memeCount)
            , ("memodes",   jNat counts.memodeCount)
            , ("edges",     jNat counts.edgeCount)
            , ("turns",     jNat counts.turnCount)
            , ("feedback",  jNat counts.feedbackCount)
            ])
        ])

------------------------------------------------------------------------
-- EdenM wrappers (monadic convenience)
------------------------------------------------------------------------

||| Get session profile in EdenM.
export
mGetSessionProfile : SessionMetaStore -> EdenM SessionProfile
mGetSessionProfile sms = do
  sid <- getSessId
  liftIO (getSessionProfile sms sid)

||| Update session profile in EdenM.
export
mUpdateSessionProfile : SessionMetaStore -> (field : String) -> (value : String) -> EdenM ()
mUpdateSessionProfile sms field value = do
  sid <- getSessId
  liftIO (updateSessionProfile sms sid field value)

||| Archive current session in EdenM.
export
mArchiveSession : SessionMetaStore -> (folder : String) -> (tags : List String) -> EdenM ()
mArchiveSession sms folder tags = do
  sid <- getSessId
  liftIO (archiveSession sms sid folder tags)

||| List all archives in EdenM.
export
mListArchives : SessionMetaStore -> EdenM (List ArchiveRecord)
mListArchives sms = do
  st <- getStore
  liftIO (listArchives sms st)

||| Preview an archived session in EdenM.
export
mPreviewArchive : SessionId -> (turnLimit : Nat) -> EdenM String
mPreviewArchive sid turnLimit = do
  st <- getStore
  liftIO (previewArchive st sid turnLimit)

||| Write conversation log in EdenM.
export
mWriteConversationLog : SessionMetaStore -> (outPath : String) -> EdenM (Either String String)
mWriteConversationLog sms outPath = do
  st <- getStore
  sid <- getSessId
  liftIO (writeConversationLog st sms sid outPath)

||| Session state snapshot in EdenM.
export
mSessionSnapshot : SessionMetaStore -> EdenM String
mSessionSnapshot sms = do
  st <- getStore
  sid <- getSessId
  liftIO (sessionSnapshot st sms sid)
