||| Persistence and export for graph store, hum artifacts, and observatory data.
|||
||| Graph persistence: tab-separated line format in data/graph.eden.
||| Hum persistence: human-readable markdown in data/hum/.
||| Observatory export: JSON matching the web frontend's GraphPayload contract.
module Eden.Export

import Data.IORef
import Data.List
import Data.Maybe
import Data.List1
import Data.String
import System.File
import System.Directory
import Eden.Types
import Eden.Config
import Eden.Regard
import Eden.Hum
import Eden.Store.InMemory
import Eden.OntologyProjection
import Eden.Tanakh

%hide System.File.Meta.Timestamp

------------------------------------------------------------------------
-- Field escaping for tab-separated persistence
------------------------------------------------------------------------

escField : String -> String
escField = pack . concatMap escF . unpack
  where
    escF : Char -> List Char
    escF '\t' = ['\\', 't']
    escF '\n' = ['\\', 'n']
    escF '\\' = ['\\', '\\']
    escF c    = [c]

unescField : String -> String
unescField s = pack (go (unpack s))
  where
    go : List Char -> List Char
    go []               = []
    go ('\\' :: 't' :: rest)  = '\t' :: go rest
    go ('\\' :: 'n' :: rest)  = '\n' :: go rest
    go ('\\' :: '\\' :: rest) = '\\' :: go rest
    go (c :: rest)      = c :: go rest

||| Split a string on tab characters.
export
splitTabs : String -> List String
splitTabs s = split' (unpack s) [] []
  where
    split' : List Char -> List Char -> List String -> List String
    split' []          acc fields = reverse (pack (reverse acc) :: fields)
    split' ('\t' :: rest) acc fields = split' rest [] (pack (reverse acc) :: fields)
    split' (c :: rest)    acc fields = split' rest (c :: acc) fields

------------------------------------------------------------------------
-- Enum parsers (string -> type)
------------------------------------------------------------------------

parseDomain : String -> Domain
parseDomain "behavior" = Behavior
parseDomain _          = Knowledge

parseSourceKind : String -> SourceKind
parseSourceKind "turn_user" = TurnUser
parseSourceKind "turn_adam" = TurnAdam
parseSourceKind "feedback"  = FeedbackSource
parseSourceKind "document"  = IngestSource
parseSourceKind "seed"      = SeedSource
parseSourceKind _           = ManualSource

parseScope : String -> Scope
parseScope "global" = Global
parseScope s = case isPrefixOf "session:" s of
  True  => SessionScoped (MkId (substr 8 (length s) s))
  False => Global

parseEdgeType : String -> EdgeType
parseEdgeType "SUPPORTS"        = Supports
parseEdgeType "REINFORCES"      = Reinforces
parseEdgeType "REFINES"         = Refines
parseEdgeType "CONTRADICTS"     = ContradictsEdge
parseEdgeType "CO_OCCURS_WITH"  = CoOccursWith
parseEdgeType "AUTHOR_OF"       = AuthorOf
parseEdgeType "INFLUENCES"      = Influences
parseEdgeType "DERIVED_FROM"    = DerivedFrom
parseEdgeType "RELATES_TO"      = RelatesTo
parseEdgeType "CHUNK_OF"            = ChunkOf
parseEdgeType "MEMBER_OF"           = MemberOf
parseEdgeType "SOURCE_DOCUMENT"     = SourceDocument
parseEdgeType "HAS_TURN"            = HasTurn
parseEdgeType "HAS_FEEDBACK"        = HasFeedback
parseEdgeType "BELONGS_TO_SESSION"  = BelongsToSession
parseEdgeType "BELONGS_TO_AGENT"    = BelongsToAgent
parseEdgeType "CONTEXTUALIZES_DOCUMENT" = ContextualizesDocument
parseEdgeType "FED_BACK_BY"         = FedBackBy
parseEdgeType "OCCURS_IN"           = OccursIn
parseEdgeType _                     = RelatesTo

parseNodeKind : String -> NodeKind
parseNodeKind "memode"   = MemodeNode
parseNodeKind "document" = DocumentNode
parseNodeKind "turn"     = TurnNode
parseNodeKind "chunk"    = ChunkNode
parseNodeKind "session"  = SessionNode
parseNodeKind "agent"    = AgentNode
parseNodeKind "feedback" = FeedbackNode
parseNodeKind _          = MemeNode

parseVerdict : String -> Verdict
parseVerdict "accept" = Accept
parseVerdict "reject" = Reject
parseVerdict "edit"   = Edit
parseVerdict _        = Skip

parseNat : String -> Nat
parseNat s = case parsePositive s of
  Just n  => cast n
  Nothing => 0

myParseDouble : String -> Double
myParseDouble s = case parseDouble s of
  Just d  => d
  Nothing => 0.0

------------------------------------------------------------------------
-- Meme serialization
------------------------------------------------------------------------

||| Serialize a meme as a tab-separated line.
serializeMeme : Meme -> String
serializeMeme m =
  joinBy "\t" [ "MEME", show m.id, show m.experimentId
              , escField m.label, escField m.text
              , show m.domain, show m.sourceKind, show m.scope
              , show m.evidenceN, show m.usageCount
              , show m.rewardEma, show m.riskEma, show m.editEma
              , show m.skipCount, show m.contradictionCount
              , show m.membraneConflicts, show m.feedbackCount
              , show m.activationTau
              , show m.lastActiveAt, show m.createdAt, show m.updatedAt
              , escField m.metadataJson
              ]

||| Deserialize a meme from tab-separated fields.
||| Accepts 21 fields (legacy, no metadataJson) or 22 fields (with metadataJson).
export
deserializeMeme : List String -> Maybe Meme
deserializeMeme fields =
  let n = length fields in
  if n /= 21 && n /= 22 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
        metaJ = if n == 22 then unescField (idx 21) else ""
    in Just (MkMeme (MkId (idx 1)) (MkId (idx 2))
      (unescField (idx 3)) (toLower (unescField (idx 3))) (unescField (idx 4))
      (parseDomain (idx 5)) (parseSourceKind (idx 6)) (parseScope (idx 7))
      (myParseDouble (idx 8)) (parseNat (idx 9))
      (myParseDouble (idx 10)) (myParseDouble (idx 11)) (myParseDouble (idx 12))
      (parseNat (idx 13)) (parseNat (idx 14)) (parseNat (idx 15)) (parseNat (idx 16))
      (myParseDouble (idx 17))
      (MkTimestamp (idx 18)) (MkTimestamp (idx 19)) (MkTimestamp (idx 20))
      metaJ)

------------------------------------------------------------------------
-- Edge serialization
------------------------------------------------------------------------

serializeEdge : Edge -> String
serializeEdge e =
  joinBy "\t" [ "EDGE", show e.id, show e.experimentId
              , show e.srcKind, e.srcId, show e.dstKind, e.dstId
              , show e.edgeType, show e.weight
              , escField e.provenanceJson
              , show e.createdAt, show e.updatedAt
              ]

export
deserializeEdge : List String -> Maybe Edge
deserializeEdge fields =
  if length fields /= 12 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
    in Just (MkEdge (MkId (idx 1)) (MkId (idx 2))
      (parseNodeKind (idx 3)) (idx 4) (parseNodeKind (idx 5)) (idx 6)
      (parseEdgeType (idx 7)) (myParseDouble (idx 8))
      (unescField (idx 9))
      (MkTimestamp (idx 10)) (MkTimestamp (idx 11)))

------------------------------------------------------------------------
-- Turn serialization
------------------------------------------------------------------------

serializeTurn : Turn -> String
serializeTurn t =
  joinBy "\t" [ "TURN", show t.id, show t.experimentId, show t.sessionId
              , show t.turnIndex
              , escField t.userText, escField t.promptContext
              , escField t.responseText, escField t.membraneText
              , show t.createdAt
              ]

export
deserializeTurn : List String -> Maybe Turn
deserializeTurn fields =
  if length fields /= 10 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
    in Just (MkTurn (MkId (idx 1)) (MkId (idx 2)) (MkId (idx 3))
      (parseNat (idx 4)) (unescField (idx 5)) (unescField (idx 6))
      (unescField (idx 7)) (unescField (idx 8)) (MkTimestamp (idx 9)))

------------------------------------------------------------------------
-- Feedback serialization
------------------------------------------------------------------------

serializeFeedback : FeedbackRecord -> String
serializeFeedback fb =
  joinBy "\t" [ "FB", show fb.frId, show fb.frExperimentId
              , show fb.frSessionId, show fb.frTurnId
              , show fb.frVerdict, escField fb.frExplanation
              , escField fb.frCorrected
              , show fb.frSignal.reward, show fb.frSignal.risk, show fb.frSignal.edit
              ]

export
deserializeFeedback : List String -> Maybe FeedbackRecord
deserializeFeedback fields =
  if length fields /= 11 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
    in Just (MkFeedbackRecord (MkId (idx 1)) (MkId (idx 2)) (MkId (idx 3)) (MkId (idx 4))
      (parseVerdict (idx 5)) (unescField (idx 6)) (unescField (idx 7))
      (MkFeedbackSignal (myParseDouble (idx 8)) (myParseDouble (idx 9)) (myParseDouble (idx 10))))

------------------------------------------------------------------------
-- Experiment serialization
------------------------------------------------------------------------

parseExperimentMode : String -> ExperimentMode
parseExperimentMode "seeded"  = Seeded
parseExperimentMode "resumed" = Resumed
parseExperimentMode _         = Blank

parseExperimentStatus : String -> ExperimentStatus
parseExperimentStatus "completed" = Completed
parseExperimentStatus "archived"  = Archived
parseExperimentStatus _           = Active

||| Deserialize an experiment from tab-separated fields.
||| Format: EXP id name slug mode status createdAt updatedAt (8 fields)
export
deserializeExperiment : List String -> Maybe Experiment
deserializeExperiment fields =
  if length fields /= 8 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
    in Just (MkExperiment (MkId (idx 1)) (unescField (idx 2)) (unescField (idx 3))
      (parseExperimentMode (idx 4)) (parseExperimentStatus (idx 5))
      (MkTimestamp (idx 6)) (MkTimestamp (idx 7)))

------------------------------------------------------------------------
-- Session serialization
------------------------------------------------------------------------

||| Deserialize a session from tab-separated fields.
||| Format: SESS id experimentId agentId title createdAt updatedAt endedAt (8 fields)
export
deserializeSession : List String -> Maybe Session
deserializeSession fields =
  if length fields /= 8 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
        ea = let s = idx 7 in
             if length s == 0 then Nothing else Just (MkTimestamp s)
    in Just (MkSession (MkId (idx 1)) (MkId (idx 2)) (MkId (idx 3))
      (unescField (idx 4)) (MkTimestamp (idx 5)) (MkTimestamp (idx 6)) ea)

------------------------------------------------------------------------
-- Memode serialization
------------------------------------------------------------------------

||| Deserialize a memode from tab-separated fields.
||| Format: MEMODE id experimentId label memberHash summary domain scope
|||   evidenceN usageCount rewardEma riskEma editEma feedbackCount
|||   activationTau lastActiveAt createdAt updatedAt [metadataJson] (18 or 19 fields)
export
deserializeMemode : List String -> Maybe Memode
deserializeMemode fields =
  let n = length fields in
  if n /= 18 && n /= 19 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
        metaJ = if n == 19 then unescField (idx 18) else ""
    in Just (MkMemode (MkId (idx 1)) (MkId (idx 2))
      (unescField (idx 3)) (unescField (idx 4)) (unescField (idx 5))
      (parseDomain (idx 6)) (parseScope (idx 7))
      (myParseDouble (idx 8)) (parseNat (idx 9))
      (myParseDouble (idx 10)) (myParseDouble (idx 11)) (myParseDouble (idx 12))
      (parseNat (idx 13)) (myParseDouble (idx 14))
      (MkTimestamp (idx 15)) (MkTimestamp (idx 16)) (MkTimestamp (idx 17))
      metaJ)

------------------------------------------------------------------------
-- Agent serialization
------------------------------------------------------------------------

||| Deserialize an agent from tab-separated fields.
||| Format: AGENT id experimentId name persona createdAt (6 fields)
export
deserializeAgent : List String -> Maybe Agent
deserializeAgent fields =
  if length fields /= 6 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
    in Just (MkAgent (MkId (idx 1)) (MkId (idx 2))
      (unescField (idx 3)) (unescField (idx 4))
      (MkTimestamp (idx 5)))

------------------------------------------------------------------------
-- ActiveSetEntry serialization
------------------------------------------------------------------------

||| Deserialize an active set entry from tab-separated fields.
||| Format: ASET id experimentId sessionId turnId nodeKind nodeId label
|||   domain selectionScore semanticSim activationVal regardVal createdAt (14 fields)
export
deserializeActiveSetEntry : List String -> Maybe ActiveSetEntry
deserializeActiveSetEntry fields =
  if length fields /= 14 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
    in Just (MkActiveSetEntry (idx 1) (MkId (idx 2)) (MkId (idx 3)) (MkId (idx 4))
      (parseNodeKind (idx 5)) (idx 6) (unescField (idx 7)) (parseDomain (idx 8))
      (myParseDouble (idx 9)) (myParseDouble (idx 10)) (myParseDouble (idx 11))
      (myParseDouble (idx 12)) (MkTimestamp (idx 13)))

------------------------------------------------------------------------
-- TurnMetadata serialization
------------------------------------------------------------------------

||| Deserialize turn metadata from tab-separated fields.
||| Format: TMETA turnId inferenceModeReq inferenceModeEff budgetMode
|||   budgetPressure budgetUsedTokens budgetRemainingTokens activeSetSize
|||   reasoningText temperature maxOutput responseCap
|||   profileName selectionSource countMethod createdAt (17 fields)
export
deserializeTurnMetadata : List String -> Maybe TurnMetadata
deserializeTurnMetadata fields =
  if length fields /= 17 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
    in Just (MkTurnMetadata (MkId (idx 1))
      (idx 2) (idx 3) (idx 4) (idx 5)
      (parseNat (idx 6)) (parseNat (idx 7)) (parseNat (idx 8))
      (unescField (idx 9))
      (myParseDouble (idx 10)) (parseNat (idx 11)) (parseNat (idx 12))
      (idx 13) (idx 14) (idx 15)
      (MkTimestamp (idx 16)))

------------------------------------------------------------------------
-- Chunk / Document / MeasurementEvent deserializers
------------------------------------------------------------------------

parseDocKind : String -> DocKind
parseDocKind "pdf"      = PDF
parseDocKind "markdown" = Markdown
parseDocKind "csv"      = CSV
parseDocKind _          = PlainText

parseDocStatus : String -> DocStatus
parseDocStatus "processing" = Processing
parseDocStatus "ingested"   = Ingested
parseDocStatus "failed"     = Failed
parseDocStatus _            = Processing

parseMeasurementAction : String -> MeasurementAction
parseMeasurementAction "edge_add"                 = EdgeAdd
parseMeasurementAction "edge_update"              = EdgeUpdate
parseMeasurementAction "edge_remove"              = EdgeRemove
parseMeasurementAction "memode_assert"            = MemodeAssert
parseMeasurementAction "memode_update_membership" = MemodeUpdateMembership
parseMeasurementAction "node_edit"                = NodeEdit
parseMeasurementAction "motif_annotation"         = MotifAnnotation
parseMeasurementAction "geometry_measurement_run" = GeometryMeasurementRun
parseMeasurementAction "ablation_measurement_run" = AblationMeasurementRun
parseMeasurementAction _                          = MeasurementRevert

parseMeasurementState : String -> MeasurementState
parseMeasurementState "committed" = Committed
parseMeasurementState "reverted"  = Reverted
parseMeasurementState _           = Previewed

export
deserializeChunk : List String -> Maybe Chunk
deserializeChunk fields =
  if length fields < 8 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
        mpg = let s = idx 4 in if s == "" then Nothing else Just (parseNat s)
    in Just (MkChunk (MkId (idx 0)) (MkId (idx 1)) (MkId (idx 2))
             (parseNat (idx 3)) mpg (unescField (idx 5)) (unescField (idx 6))
             (MkTimestamp (idx 7)))

export
deserializeDocument : List String -> Maybe Document
deserializeDocument fields =
  if length fields < 9 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
    in Just (MkDocument (MkId (idx 0)) (MkId (idx 1)) (idx 2)
             (parseDocKind (idx 3)) (unescField (idx 4)) (idx 5)
             (parseDocStatus (idx 6)) (unescField (idx 7))
             (MkTimestamp (idx 8)))

export
deserializeMeasurementEvent : List String -> Maybe MeasurementEvent
deserializeMeasurementEvent fields =
  if length fields < 12 then Nothing
  else
    let idx : Nat -> String
        idx i = fromMaybe "" (head' (drop i fields))
        n = length fields
        -- New fields: turnId, targetIdsJson, rationale, operatorLabel, measurementMethod, confidence
        -- Legacy format (12 fields): these default to "" / 1.0
        mTurnId  = if n >= 18 then idx 11 else ""
        mTargets = if n >= 18 then idx 12 else ""
        mRationale = if n >= 18 then unescField (idx 13) else ""
        mOpLabel = if n >= 18 then idx 14 else ""
        mMethod  = if n >= 18 then idx 15 else ""
        mConf    = if n >= 18 then myParseDouble (idx 16) else 1.0
        mCreated = if n >= 18 then MkTimestamp (idx 17) else MkTimestamp (idx 11)
        mRevertOf = if n >= 18 then idx 10 else idx 10
    in Just (MkMeasurementEvent (idx 0) (MkId (idx 1)) (MkId (idx 2))
             (parseMeasurementAction (idx 3)) (parseMeasurementState (idx 4))
             (idx 5) (idx 6) (unescField (idx 7)) (unescField (idx 8))
             (unescField (idx 9)) mRevertOf
             mTurnId mTargets mRationale mOpLabel mMethod mConf mCreated)

------------------------------------------------------------------------
-- Full graph save/load
------------------------------------------------------------------------

||| Save the full graph store to data/graph.eden.
export
saveGraph : StoreState -> IO ()
saveGraph st = do
  _ <- createDir "data"
  memes <- readIORef st.memes
  edges <- readIORef st.edges
  turns <- readIORef st.turns
  fbs   <- readIORef st.feedbackEvents
  let memeLines = map serializeMeme memes
      edgeLines = map serializeEdge edges
      turnLines = map serializeTurn turns
      fbLines   = map serializeFeedback fbs
      content   = unlines (memeLines ++ edgeLines ++ turnLines ++ fbLines)
  Right () <- writeFile "data/graph.eden" content
    | Left err => putStrLn ("  (graph save failed: " ++ show err ++ ")")
  pure ()

||| Load the graph store from data/graph.eden into the given StoreState.
||| Returns the highest ID seen (for nextId continuation).
export
loadGraph : StoreState -> IO Nat
loadGraph st = do
  Right content <- readFile "data/graph.eden"
    | Left _ => pure 0  -- no saved graph, start fresh
  let ls = filter (\l => length l > 0) (lines content)
  maxId <- processLines st ls 0
  pure maxId
  where
    extractId : String -> Nat
    extractId s =
      let parts = split (== '-') s
      in case last' (forget parts) of
           Just n  => parseNat n
           Nothing => 0

    processLines : StoreState -> List String -> Nat -> IO Nat
    processLines _  []        mx = pure mx
    processLines st (l :: ls) mx = do
      let fields = splitTabs l
          lineMax = case fields of
            (_ :: idField :: _) => max mx (extractId idField)
            _ => mx
      case head' fields of
        Just "MEME" => case deserializeMeme fields of
          Just m  => do modifyIORef st.memes (m ::); processLines st ls lineMax
          Nothing => processLines st ls lineMax
        Just "EDGE" => case deserializeEdge fields of
          Just e  => do modifyIORef st.edges (e ::); processLines st ls lineMax
          Nothing => processLines st ls lineMax
        Just "TURN" => case deserializeTurn fields of
          Just t  => do modifyIORef st.turns (t ::); processLines st ls lineMax
          Nothing => processLines st ls lineMax
        Just "FB"   => case deserializeFeedback fields of
          Just fb => do modifyIORef st.feedbackEvents (fb ::); processLines st ls lineMax
          Nothing => processLines st ls lineMax
        _ => processLines st ls lineMax

------------------------------------------------------------------------
-- JSON helpers (minimal, no external dependency)
------------------------------------------------------------------------

escChar : Char -> List Char
escChar '"'  = ['\\', '"']
escChar '\\' = ['\\', '\\']
escChar '\n' = ['\\', 'n']
escChar '\t' = ['\\', 't']
escChar c    = [c]

escapeStr : String -> String
escapeStr = pack . concatMap escChar . unpack

jsonStr : String -> String
jsonStr s = "\"" ++ escapeStr s ++ "\""

jsonNum : Double -> String
jsonNum d =
  let i = cast {to=Integer} (d * 1000.0)
  in show (cast {to=Double} i / 1000.0)

jsonNat : Nat -> String
jsonNat = show

jsonObj : List (String, String) -> String
jsonObj fields =
  "{" ++ joinBy ", " (map (\kv => jsonStr (fst kv) ++ ": " ++ snd kv) fields) ++ "}"

jsonArr : List String -> String
jsonArr items = "[" ++ joinBy ", " items ++ "]"

jsonBool : Bool -> String
jsonBool True  = "true"
jsonBool False = "false"

jsonNull : String
jsonNull = "null"

jsonMaybeStr : Maybe String -> String
jsonMaybeStr (Just s) = jsonStr s
jsonMaybeStr Nothing  = jsonNull

------------------------------------------------------------------------
-- Meme -> JSON
------------------------------------------------------------------------

export
memeToJson : Meme -> String
memeToJson m = jsonObj
  [ ("id",       jsonStr (show m.id))
  , ("label",    jsonStr m.label)
  , ("kind",     jsonStr "meme")
  , ("domain",   jsonStr (show m.domain))
  , ("scope",    jsonStr (show m.scope))
  , ("source",   jsonStr (show m.sourceKind))
  , ("text",     jsonStr (substr 0 500 m.text))
  , ("rewardEma", jsonNum m.rewardEma)
  , ("riskEma",   jsonNum m.riskEma)
  , ("editEma",   jsonNum m.editEma)
  , ("evidenceN", jsonNum m.evidenceN)
  , ("usageCount", jsonNat m.usageCount)
  , ("feedbackCount", jsonNat m.feedbackCount)
  , ("speech_act_mode", jsonStr (show (projectMeme m).mpSpeechAct))
  , ("ontology_role",   jsonStr (show (projectMeme m).mpRole))
  ]

------------------------------------------------------------------------
-- Edge -> JSON
------------------------------------------------------------------------

export
edgeToJson : Edge -> String
edgeToJson e = jsonObj
  [ ("id",     jsonStr (show e.id))
  , ("source", jsonStr e.srcId)
  , ("target", jsonStr e.dstId)
  , ("type",   jsonStr (show e.edgeType))
  , ("weight", jsonNum e.weight)
  , ("source_kind", jsonStr (show e.srcKind))
  , ("target_kind", jsonStr (show e.dstKind))
  ]

------------------------------------------------------------------------
-- Memode -> JSON (as assembly for observatory)
------------------------------------------------------------------------

||| Format a memode as an observatory assembly entry.
||| The memberHash encodes member IDs; we parse them back out.
extractMemberId : String -> Maybe String
extractMemberId s =
  let trimmed = pack (filter (\c => c /= '"' && c /= '[' && c /= ']' && c /= ' ') (unpack s))
  in if length trimmed > 0 then Just trimmed else Nothing

parseMemberHash : String -> List String
parseMemberHash h =
  let parts = forget (split (== ':') h)
  in case drop 1 parts of
       (rest :: _) => mapMaybe extractMemberId (forget (split (== ',') rest))
       _           => []

export
memodeToAssembly : Memode -> String
memodeToAssembly md =
  let memberIds = parseMemberHash md.memberHash
  in jsonObj
    [ ("id",       jsonStr (show md.id))
    , ("label",    jsonStr md.label)
    , ("summary",  jsonStr md.summary)
    , ("domain",   jsonStr (show md.domain))
    , ("member_meme_ids", jsonArr (map jsonStr memberIds))
    , ("supporting_edge_ids", jsonArr [])
    , ("member_order", jsonArr [])
    , ("invariance_summary", jsonStr "")
    , ("measurement_history", jsonArr [])
    ]

||| Legacy memode-as-node format (kept for backward compat).
export
memodeToJson : Memode -> String
memodeToJson md = jsonObj
  [ ("id",       jsonStr (show md.id))
  , ("label",    jsonStr md.label)
  , ("kind",     jsonStr "memode")
  , ("domain",   jsonStr (show md.domain))
  , ("summary",  jsonStr md.summary)
  , ("memberHash", jsonStr md.memberHash)
  ]

------------------------------------------------------------------------
-- Runtime plane: sessions, agents, turns, feedback as graph nodes
------------------------------------------------------------------------

sessionToRuntimeNode : Session -> String
sessionToRuntimeNode s = jsonObj
  [ ("id",         jsonStr (show s.id))
  , ("label",      jsonStr s.title)
  , ("kind",       jsonStr "session")
  , ("created_at", jsonStr (show s.createdAt))
  ]

agentToRuntimeNode : Agent -> String
agentToRuntimeNode a = jsonObj
  [ ("id",         jsonStr (show a.id))
  , ("label",      jsonStr a.name)
  , ("kind",       jsonStr "agent")
  , ("persona",    jsonStr a.persona)
  , ("created_at", jsonStr (show a.createdAt))
  ]

turnToRuntimeNode : Turn -> String
turnToRuntimeNode t = jsonObj
  [ ("id",         jsonStr (show t.id))
  , ("label",      jsonStr ("Turn " ++ show t.turnIndex))
  , ("kind",       jsonStr "turn")
  , ("session_id", jsonStr (show t.sessionId))
  , ("created_at", jsonStr (show t.createdAt))
  ]

feedbackToRuntimeNode : FeedbackRecord -> String
feedbackToRuntimeNode fb = jsonObj
  [ ("id",       jsonStr (show fb.frId))
  , ("label",    jsonStr ("Feedback: " ++ show fb.frVerdict))
  , ("kind",     jsonStr "feedback")
  , ("turn_id",  jsonStr (show fb.frTurnId))
  , ("verdict",  jsonStr (show fb.frVerdict))
  ]

------------------------------------------------------------------------
-- Runtime edges (session-turn, turn-feedback, agent-session)
------------------------------------------------------------------------

sessionTurnEdges : List Turn -> List String
sessionTurnEdges turns = map (\t => jsonObj
  [ ("source", jsonStr (show t.sessionId))
  , ("target", jsonStr (show t.id))
  , ("type",   jsonStr "HAS_TURN")
  , ("weight", jsonNum 1.0)
  ]) turns

turnFeedbackEdges : List FeedbackRecord -> List String
turnFeedbackEdges fbs = map (\fb => jsonObj
  [ ("source", jsonStr (show fb.frTurnId))
  , ("target", jsonStr (show fb.frId))
  , ("type",   jsonStr "HAS_FEEDBACK")
  , ("weight", jsonNum 1.0)
  ]) fbs

agentSessionEdges : List Agent -> List Session -> List String
agentSessionEdges agents sessions =
  concatMap (\a =>
    map (\s => jsonObj
      [ ("source", jsonStr (show a.id))
      , ("target", jsonStr (show s.id))
      , ("type",   jsonStr "BELONGS_TO_AGENT")
      , ("weight", jsonNum 1.0)
      ]) (filter (\s => s.experimentId == a.experimentId) sessions)
  ) agents

------------------------------------------------------------------------
-- Active set slices
------------------------------------------------------------------------

activeSetEntryToJson : ActiveSetEntry -> String
activeSetEntryToJson e = jsonObj
  [ ("node_id",         jsonStr e.nodeId)
  , ("label",           jsonStr e.label)
  , ("domain",          jsonStr (show e.domain))
  , ("selection_score", jsonNum e.selectionScore)
  , ("semantic_sim",    jsonNum e.semanticSim)
  , ("activation_val",  jsonNum e.activationVal)
  , ("regard_val",      jsonNum e.regardVal)
  ]

buildActiveSetSlices : List ActiveSetEntry -> List String
buildActiveSetSlices entries =
  let turnIdStrs = nub (map (\e => show e.turnId) entries)
  in map (\tidStr => jsonObj
    [ ("turn_id", jsonStr tidStr)
    , ("entries", jsonArr (map activeSetEntryToJson
        (filter (\e => show e.turnId == tidStr) entries)))
    ]) turnIdStrs

------------------------------------------------------------------------
-- Cluster summaries
------------------------------------------------------------------------

buildClusterSummaries : List Meme -> List String
buildClusterSummaries memes =
  let knCount = length (filter (\m => m.domain == Knowledge) memes)
      bhCount = length (filter (\m => m.domain == Behavior) memes)
  in [ jsonObj [("domain", jsonStr "knowledge"), ("count", jsonNat knCount)]
     , jsonObj [("domain", jsonStr "behavior"),  ("count", jsonNat bhCount)]
     ]

------------------------------------------------------------------------
-- Session summaries
------------------------------------------------------------------------

buildSessionSummary : List Turn -> List FeedbackRecord -> Session -> String
buildSessionSummary allTurns allFb s =
  let sessTurns = filter (\t => t.sessionId == s.id) allTurns
      sessFb    = filter (\fb => fb.frSessionId == s.id) allFb
  in jsonObj
    [ ("session_id",     jsonStr (show s.id))
    , ("title",          jsonStr s.title)
    , ("agent_id",       jsonStr (show s.agentId))
    , ("started_at",     jsonStr (show s.createdAt))
    , ("ended_at",       jsonMaybeStr (map show s.endedAt))
    , ("turn_count",     jsonNat (length sessTurns))
    , ("feedback_count", jsonNat (length sessFb))
    ]

------------------------------------------------------------------------
-- Membrane event summaries
------------------------------------------------------------------------

membraneEventToJson : (MembraneEventType, String, Eden.Types.Timestamp) -> String
membraneEventToJson (evt, detail, ts) = jsonObj
  [ ("type",        jsonStr (show evt))
  , ("description", jsonStr (substr 0 500 detail))
  , ("timestamp",   jsonStr (show ts))
  ]

------------------------------------------------------------------------
-- Measurement event summaries
------------------------------------------------------------------------

measurementEventToJson : MeasurementEvent -> String
measurementEventToJson m = jsonObj
  [ ("id",        jsonStr m.id)
  , ("action",    jsonStr (show m.action))
  , ("state",     jsonStr (show m.state))
  , ("operator",  jsonStr m.operator)
  , ("evidence",  jsonStr (substr 0 300 m.evidence))
  , ("timestamp", jsonStr (show m.createdAt))
  ]

------------------------------------------------------------------------
-- Hum artifact JSON
------------------------------------------------------------------------

humMotifToJson : HumTokenRow -> String
humMotifToJson r = jsonObj
  [ ("token",     jsonStr r.htToken)
  , ("frequency", jsonNat r.htFrequency)
  , ("source",    jsonStr r.htSource)
  ]

humToJson : HumPayload -> String
humToJson hp = jsonObj
  [ ("artifact_version", jsonStr hp.artifactVersion)
  , ("generated_at",     jsonStr (show hp.generatedAt))
  , ("experiment_id",    jsonStr (show hp.hpExperimentId))
  , ("session_id",       jsonStr (show hp.hpSessionId))
  , ("latest_turn_id",   case hp.latestTurnId of
                            Nothing => jsonStr ""
                            Just tid => jsonStr (show tid))
  , ("turn_ids",         jsonArr (map (\tid => jsonStr (show tid)) hp.turnIds))
  , ("turn_indices",     jsonArr (map (\i => jsonNat i) hp.turnIndices))
  , ("derived_from",     jsonArr (map jsonStr hp.derivedFrom))
  , ("boundedness",      jsonStr hp.boundedness)
  , ("status",           jsonStr (show hp.hpStatus))
  , ("continuity",       jsonStr hp.continuity)
  , ("metrics", jsonObj
      [ ("turns_covered",    jsonNat hp.metrics.turnsCovered)
      , ("feedback_events",  jsonNat hp.metrics.hmFeedbackEvts)
      , ("membrane_events",  jsonNat hp.metrics.hmMembraneEvts)
      , ("recurring_motifs", jsonNat hp.metrics.recurringItems)
      , ("unique_motifs",    jsonNat hp.metrics.uniqueMotifs)
      ])
  , ("text_surface",     jsonStr hp.textSurface)
  , ("surface_lines",    jsonArr (map jsonStr hp.surfaceLines))
  , ("surface_stats", jsonObj
      [ ("line_count", jsonNat hp.surfaceStats.lineCount)
      , ("char_count", jsonNat hp.surfaceStats.charCount)
      , ("word_count", jsonNat hp.surfaceStats.wordCount)
      ])
  , ("token_table",      jsonArr (map humMotifToJson hp.tokenTable))
  ]

------------------------------------------------------------------------
-- Regard history (per-meme regard breakdown snapshot)
------------------------------------------------------------------------

memeRegardToJson : Meme -> String
memeRegardToJson m =
  let ns = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau 0.0 m.feedbackCount m.editEma m.contradictionCount m.membraneConflicts
      gm = MkGraphMetrics 0.5 0.4 0.3
      rb = regardBreakdown defaultRegardWeights ns gm
  in jsonObj
    [ ("meme_id",     jsonStr (show m.id))
    , ("label",       jsonStr m.label)
    , ("reward",      jsonNum rb.reward)
    , ("evidence",    jsonNum rb.evidence)
    , ("coherence",   jsonNum rb.coherence)
    , ("persistence", jsonNum rb.persistence)
    , ("decay",       jsonNum rb.decay)
    , ("isolation",   jsonNum rb.isolationPenalty)
    , ("risk",        jsonNum rb.risk)
    , ("activation",  jsonNum rb.activation)
    , ("total",       jsonNum rb.totalRegard)
    ]

------------------------------------------------------------------------
-- Export schema version
------------------------------------------------------------------------

||| Current export schema version.
exportSchemaVersion : String
exportSchemaVersion = "2.0.0"

------------------------------------------------------------------------
-- Full graph export (observatory payload)
------------------------------------------------------------------------

||| Export the full graph as a JSON string matching the observatory
||| GraphPayload contract (semantic_nodes, semantic_edges, assemblies, etc.).
||| Enhanced with metadata header, session summaries, membrane events,
||| measurement events, hum data, regard history, and ontology projection.
export
exportGraphJson : StoreState -> ExperimentId -> IO String
exportGraphJson st eid = do
  allMemes   <- readIORef st.memes
  allEdges   <- readIORef st.edges
  allMemodes <- readIORef st.memodes
  allTurns   <- readIORef st.turns
  allFb      <- readIORef st.feedbackEvents
  allAgents  <- readIORef st.agents
  allSess    <- readIORef st.sessions
  allAsets   <- readIORef st.activeSetSnaps
  allMbe     <- readIORef st.membraneEvts
  allMeas    <- readIORef st.measurements
  let memes    = filter (\m => m.experimentId == eid) allMemes
      edges    = filter (\e => e.experimentId == eid) allEdges
      memodes  = filter (\m => m.experimentId == eid) allMemodes
      turns    = filter (\t => t.experimentId == eid) allTurns
      fbs      = filter (\fb => fb.frExperimentId == eid) allFb
      agents   = filter (\a => a.experimentId == eid) allAgents
      sessions = filter (\s => s.experimentId == eid) allSess
      asets    = filter (\a => a.experimentId == eid) allAsets
      mbes     = allMbe  -- membrane events are not experiment-scoped in store
      meas     = filter (\m => m.experimentId == eid) allMeas
      -- Semantic plane: memes as nodes
      semanticNodes = map memeToJson memes
      semanticEdges = map edgeToJson edges
      -- Assemblies: memodes in observatory format
      assemblies = map memodeToAssembly memodes
      -- Runtime plane: sessions, agents, turns, feedback as nodes
      rtNodes = map sessionToRuntimeNode sessions
             ++ map agentToRuntimeNode agents
             ++ map turnToRuntimeNode turns
             ++ map feedbackToRuntimeNode fbs
      rtEdges = sessionTurnEdges turns
             ++ turnFeedbackEdges fbs
             ++ agentSessionEdges agents sessions
      -- Active set slices
      slices = buildActiveSetSlices asets
      -- Cluster summaries
      clusters = buildClusterSummaries memes
      -- Counts
      counts = jsonObj
        [ ("nodes",    jsonNat (length memes))
        , ("edges",    jsonNat (length edges))
        , ("memes",    jsonNat (length memes))
        , ("memodes",  jsonNat (length memodes))
        , ("turns",    jsonNat (length turns))
        , ("feedback", jsonNat (length fbs))
        , ("agents",   jsonNat (length agents))
        , ("sessions", jsonNat (length sessions))
        ]
      -- Ontology stats
      roles = countByRole memes
      (constatives, performatives, runtimes) = partitionBySpeechAct memes
      ontology = jsonObj
        [ ("constative",   jsonNat (length constatives))
        , ("performative", jsonNat (length performatives))
        , ("runtime",      jsonNat (length runtimes))
        , ("core",         jsonNat roles.coreCount)
        , ("active",       jsonNat roles.activeCount)
        , ("peripheral",   jsonNat roles.peripheralCount)
        , ("emergent",     jsonNat roles.emergentCount)
        ]
      -- Export metadata header
      metadata = jsonObj
        [ ("schema_version",  jsonStr exportSchemaVersion)
        , ("export_source",   jsonStr "idris2-refc")
        , ("meme_count",      jsonNat (length memes))
        , ("edge_count",      jsonNat (length edges))
        , ("memode_count",    jsonNat (length memodes))
        , ("turn_count",      jsonNat (length turns))
        , ("feedback_count",  jsonNat (length fbs))
        , ("session_count",   jsonNat (length sessions))
        , ("agent_count",     jsonNat (length agents))
        ]
      -- Provenance
      agentName = case agents of
        (a :: _) => a.name
        []       => "unknown"
      provenance = jsonObj
        [ ("experiment_id",  jsonStr (show eid))
        , ("agent",          jsonStr agentName)
        , ("session_ids",    jsonArr (map (\s => jsonStr (show s.id)) sessions))
        ]
      -- Session summaries
      sessSummaries = map (buildSessionSummary turns fbs) sessions
      -- Membrane events
      mbeJson = map membraneEventToJson mbes
      -- Measurement events
      measJson = map measurementEventToJson meas
      -- Regard history (current snapshot for each meme)
      regardHist = map memeRegardToJson memes
      -- Assembly planes (§4.2): assembly_nodes and assembly_edges
      -- Nodes: memes + memodes projected into assembly space
      assemblyNodes = jsonArr (
        map (\m => jsonObj
          [ ("id",          jsonStr (show m.id))
          , ("label",       jsonStr m.label)
          , ("domain",      jsonStr (show m.domain))
          , ("source_kind", jsonStr (show m.sourceKind))
          , ("kind",        jsonStr "meme")
          ]) memes
        ++ map (\md => jsonObj
          [ ("id",          jsonStr (show md.id))
          , ("label",       jsonStr md.label)
          , ("domain",      jsonStr (show md.domain))
          , ("kind",        jsonStr "memode")
          ]) memodes)
      -- Edges: only assembly-relevant types
      isAssemblyEdge : Edge -> Bool
      isAssemblyEdge e = case e.edgeType of
        MemberOf               => True
        Supports               => True
        Reinforces             => True
        CoOccursWith           => True
        AuthorOf               => True
        Influences             => True
        DerivedFrom            => True
        ContextualizesDocument => True
        _                      => False
      assemblyEdges = jsonArr (map (\e => jsonObj
        [ ("id",        jsonStr (show e.id))
        , ("source",    jsonStr e.srcId)
        , ("target",    jsonStr e.dstId)
        , ("edge_type", jsonStr (show e.edgeType))
        , ("weight",    jsonNum e.weight)
        ]) (filter isAssemblyEdge edges))
      -- Memode audit plane (§4.2): id, label, member_count, admissible
      memodeAudit = map (\md =>
        let memberIds = parseMemberHash md.memberHash
            memberCount = length memberIds
            admissible = memberCount >= 2
        in jsonObj
          [ ("id",           jsonStr (show md.id))
          , ("label",        jsonStr md.label)
          , ("member_count", jsonNat memberCount)
          , ("admissible",   jsonBool admissible)
          ]) memodes
      -- Graph metadata (§4.2)
      layoutFamilies = jsonArr (map jsonStr ["force", "spectral", "circular"])
      layoutCatalog = jsonObj []
      layoutDefaults = jsonObj [("default", jsonStr "force")]
      appearanceDims = jsonArr (map jsonStr ["domain", "source_kind", "scope"])
      filterDims = jsonArr (map jsonStr ["domain", "source_kind"])
      statsCaps = jsonArr (map jsonStr ["clustering", "degree_distribution", "modularity"])
      exportFormats = jsonArr (map jsonStr ["json", "graphml", "csv"])
  pure (jsonObj
    [ ("experiment_id",       jsonStr (show eid))
    , ("export_manifest_id",  jsonStr ("idris-" ++ show eid))
    , ("source_graph_hash",   jsonStr "")
    , ("metadata",            metadata)
    , ("provenance",          provenance)
    , ("graph_modes",         jsonArr (map jsonStr ["Semantic Map", "Assemblies", "Runtime", "Active Set", "Compare"]))
    , ("assembly_render_modes", jsonArr (map jsonStr ["hulls", "collapsed-meta-node", "hidden"]))
    , ("semantic_nodes",      jsonArr semanticNodes)
    , ("semantic_edges",      jsonArr semanticEdges)
    , ("assembly_nodes",      assemblyNodes)
    , ("assembly_edges",      assemblyEdges)
    , ("runtime_nodes",       jsonArr rtNodes)
    , ("runtime_edges",       jsonArr rtEdges)
    , ("assemblies",          jsonArr assemblies)
    , ("memode_audit",        jsonArr memodeAudit)
    , ("cluster_summaries",   jsonArr clusters)
    , ("active_set_slices",   jsonArr slices)
    , ("session_summaries",   jsonArr sessSummaries)
    , ("membrane_events",     jsonArr mbeJson)
    , ("measurement_events",  jsonArr measJson)
    , ("regard_history",      jsonArr regardHist)
    , ("counts",              counts)
    , ("ontology",            ontology)
    , ("layout_families",          layoutFamilies)
    , ("layout_catalog",           layoutCatalog)
    , ("layout_defaults",          layoutDefaults)
    , ("appearance_dimensions",    appearanceDims)
    , ("filter_dimensions",        filterDims)
    , ("statistics_capabilities",  statsCaps)
    , ("export_formats",           exportFormats)
    ])

------------------------------------------------------------------------
-- Hum -> file persistence
------------------------------------------------------------------------

||| Format a HumPayload as a human-readable text artifact.
export
formatHumArtifact : HumPayload -> String
formatHumArtifact hp =
  unlines
    [ "# Hum Artifact (" ++ hp.artifactVersion ++ ")"
    , ""
    , "Generated: " ++ show hp.generatedAt
    , "Experiment: " ++ show hp.hpExperimentId
    , "Session: " ++ show hp.hpSessionId
    , "Status: " ++ show hp.hpStatus
    , ""
    , "[HUM_STATS]"
    , "Lines: " ++ show hp.surfaceStats.lineCount
        ++ " | Words: " ++ show hp.surfaceStats.wordCount
        ++ " | Chars: " ++ show hp.surfaceStats.charCount
    , ""
    , "[HUM_METRICS]"
    , "- Turns covered: " ++ show hp.metrics.turnsCovered
    , "- Feedback events: " ++ show hp.metrics.hmFeedbackEvts
    , "- Membrane events: " ++ show hp.metrics.hmMembraneEvts
    , "- Recurring motifs: " ++ show hp.metrics.recurringItems
    , "- Unique motifs: " ++ show hp.metrics.uniqueMotifs
    , ""
    , hp.textSurface
    , ""
    , "[HUM_TABLE]"
    , unlines (map (\r => "  " ++ r.htToken ++ " x" ++ show r.htFrequency
                       ++ " (" ++ r.htSource ++ ")") hp.tokenTable)
    ]

||| Write a hum artifact to disk at data/hum/<session-id>.md.
export
writeHumFile : HumPayload -> IO ()
writeHumFile hp = do
  -- Ensure directory exists
  _ <- createDir "data"
  _ <- createDir "data/hum"
  let path = "data/hum/" ++ show hp.hpSessionId ++ ".md"
      content = formatHumArtifact hp
  Right () <- writeFile path content
    | Left err => putStrLn ("  (hum write failed: " ++ show err ++ ")")
  pure ()

||| Export graph JSON to data/export/<experiment-id>.json.
export
writeGraphExport : StoreState -> ExperimentId -> IO String
writeGraphExport st eid = do
  _ <- createDir "data"
  _ <- createDir "data/export"
  json <- exportGraphJson st eid
  let path = "data/export/" ++ show eid ++ ".json"
  Right () <- writeFile path json
    | Left err => do putStrLn ("  (export write failed: " ++ show err ++ ")")
                     pure path
  pure path

------------------------------------------------------------------------
-- Session log export (markdown conversation log)
------------------------------------------------------------------------

||| Format a turn for a session log with full detail.
fmtSessionLogTurn : List FeedbackRecord -> Turn -> String
fmtSessionLogTurn sessionFb t =
  let turnFb = filter (\fb => fb.frTurnId == t.id) sessionFb
      fbSection = case turnFb of
        []       => ""
        (fb :: _) =>
          "\n**Feedback:** " ++ show fb.frVerdict
          ++ (if length fb.frExplanation > 0
                then " -- " ++ fb.frExplanation
                else "")
          ++ "\n"
  in "## Turn " ++ show t.turnIndex ++ "\n\n"
  ++ "**User:** " ++ t.userText ++ "\n\n"
  ++ "**Adam:** " ++ t.membraneText ++ "\n"
  ++ fbSection ++ "\n---\n\n"

||| Export a session as a detailed markdown conversation log.
||| Includes session metadata, all turns with feedback, and a summary.
export
exportSessionLog : StoreState -> ExperimentId -> SessionId -> IO String
exportSessionLog st eid sid = do
  _ <- createDir "data"
  _ <- createDir "data/export"
  allTurns <- readIORef st.turns
  allFb    <- readIORef st.feedbackEvents
  allSess  <- readIORef st.sessions
  allAg    <- readIORef st.agents
  let turns    = sortBy (\a, b => compare a.turnIndex b.turnIndex)
                   (filter (\t => t.sessionId == sid && t.experimentId == eid) allTurns)
      fbs      = filter (\fb => fb.frSessionId == sid) allFb
      mSess    = find (\s => s.id == sid) allSess
      sessTitle = case mSess of
        Just s  => s.title
        Nothing => "Unknown Session"
      sessCreated = case mSess of
        Just s  => show s.createdAt
        Nothing => "unknown"
      agentName = case allAg of
        (a :: _) => a.name
        []       => "Adam"
      acceptCount = length (filter (\fb => fb.frVerdict == Accept) fbs)
      rejectCount = length (filter (\fb => fb.frVerdict == Reject) fbs)
      editCount   = length (filter (\fb => fb.frVerdict == Edit) fbs)
      header = "# Session Log: " ++ sessTitle ++ "\n\n"
            ++ "- **Session ID:** " ++ show sid ++ "\n"
            ++ "- **Experiment:** " ++ show eid ++ "\n"
            ++ "- **Agent:** " ++ agentName ++ "\n"
            ++ "- **Started:** " ++ sessCreated ++ "\n"
            ++ "- **Turns:** " ++ show (length turns) ++ "\n"
            ++ "- **Feedback:** " ++ show (length fbs)
               ++ " (accept=" ++ show acceptCount
               ++ ", reject=" ++ show rejectCount
               ++ ", edit=" ++ show editCount ++ ")\n"
            ++ "\n---\n\n"
      body = case turns of
        [] => "_No turns recorded._\n"
        _  => concatMap (fmtSessionLogTurn fbs) turns
      content = header ++ body
      path = "data/export/" ++ show sid ++ "-log.md"
  Right () <- writeFile path content
    | Left err => do putStrLn ("  (session log write failed: " ++ show err ++ ")")
                     pure path
  pure path

------------------------------------------------------------------------
-- Regard timeline export (CSV)
------------------------------------------------------------------------

||| Compute current regard for a meme and format as a CSV row.
memeRegardCsvRow : Meme -> String
memeRegardCsvRow m =
  let ns = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau 0.0 m.feedbackCount m.editEma m.contradictionCount m.membraneConflicts
      gm = MkGraphMetrics 0.5 0.4 0.3
      rb = regardBreakdown defaultRegardWeights ns gm
  in show m.id ++ ","
  ++ "\"" ++ escapeStr m.label ++ "\","
  ++ show m.domain ++ ","
  ++ jsonNum rb.reward ++ ","
  ++ jsonNum rb.evidence ++ ","
  ++ jsonNum rb.coherence ++ ","
  ++ jsonNum rb.persistence ++ ","
  ++ jsonNum rb.decay ++ ","
  ++ jsonNum rb.isolationPenalty ++ ","
  ++ jsonNum rb.risk ++ ","
  ++ jsonNum rb.activation ++ ","
  ++ jsonNum rb.totalRegard ++ ","
  ++ show m.usageCount ++ ","
  ++ show m.feedbackCount ++ ","
  ++ show m.updatedAt

||| Export regard scores as CSV for all memes in an experiment.
||| Columns: meme_id, label, domain, reward, evidence, coherence,
||| persistence, decay, isolation, risk, activation, total_regard,
||| usage_count, feedback_count, updated_at
export
exportRegardTimeline : StoreState -> ExperimentId -> IO String
exportRegardTimeline st eid = do
  _ <- createDir "data"
  _ <- createDir "data/export"
  allMemes <- readIORef st.memes
  let memes = filter (\m => m.experimentId == eid) allMemes
      header = "meme_id,label,domain,reward,evidence,coherence,persistence,decay,isolation,risk,activation,total_regard,usage_count,feedback_count,updated_at"
      rows   = map memeRegardCsvRow memes
      content = unlines (header :: rows)
      path = "data/export/" ++ show eid ++ "-regard.csv"
  Right () <- writeFile path content
    | Left err => do putStrLn ("  (regard timeline write failed: " ++ show err ++ ")")
                     pure path
  pure path

------------------------------------------------------------------------
-- Meme index export (text)
------------------------------------------------------------------------

||| Format a single meme for the text index.
fmtMemeIndexEntry : Meme -> String
fmtMemeIndexEntry m =
  let proj = projectMeme m
  in show m.id ++ "  " ++ m.label
  ++ "  [" ++ show m.domain ++ "/" ++ show proj.mpRole ++ "]"
  ++ "  usage=" ++ show m.usageCount
  ++ "  feedback=" ++ show m.feedbackCount
  ++ "  source=" ++ show m.sourceKind

||| Export a simple text index of all memes with labels, domains, and roles.
export
exportMemeIndex : StoreState -> ExperimentId -> IO String
exportMemeIndex st eid = do
  _ <- createDir "data"
  _ <- createDir "data/export"
  allMemes <- readIORef st.memes
  let memes = sortBy (\a, b => compare (show a.domain) (show b.domain))
                (filter (\m => m.experimentId == eid) allMemes)
      roles = countByRole memes
      (constatives, performatives, runtimes) = partitionBySpeechAct memes
      header = "EDEN Meme Index -- Experiment " ++ show eid ++ "\n"
            ++ "Total: " ++ show (length memes) ++ " memes\n"
            ++ "  Knowledge: " ++ show (length (filter (\m => m.domain == Knowledge) memes)) ++ "\n"
            ++ "  Behavior:  " ++ show (length (filter (\m => m.domain == Behavior) memes)) ++ "\n"
            ++ "Roles: core=" ++ show roles.coreCount
               ++ " active=" ++ show roles.activeCount
               ++ " peripheral=" ++ show roles.peripheralCount
               ++ " emergent=" ++ show roles.emergentCount ++ "\n"
            ++ "Speech acts: constative=" ++ show (length constatives)
               ++ " performative=" ++ show (length performatives)
               ++ " runtime=" ++ show (length runtimes) ++ "\n"
            ++ "\n"
      entries = map fmtMemeIndexEntry memes
      content = header ++ unlines entries
      path = "data/export/" ++ show eid ++ "-meme-index.txt"
  Right () <- writeFile path content
    | Left err => do putStrLn ("  (meme index write failed: " ++ show err ++ ")")
                     pure path
  pure path

------------------------------------------------------------------------
-- Basin projection export
------------------------------------------------------------------------

||| Compute regard for a meme (reused helper).
memeRegard : Meme -> Double
memeRegard m =
  let ns = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau 0.0 m.feedbackCount m.editEma m.contradictionCount m.membraneConflicts
      gm = MkGraphMetrics 0.5 0.4 0.3
      rb = regardBreakdown defaultRegardWeights ns gm
  in rb.totalRegard

||| Build a basin summary for memes in a single domain.
basinSummary : String -> List Meme -> String
basinSummary domainLabel memes =
  let count = length memes
      regards = map memeRegard memes
      sumRegard = foldl (+) 0.0 regards
      centroid = if count == 0 then 0.0
                 else sumRegard / cast count
      -- Variance: sum of (r - centroid)^2 / n
      variance = if count == 0 then 0.0
                 else let sumSqDiff = foldl (\acc, r => acc + (r - centroid) * (r - centroid)) 0.0 regards
                      in sumSqDiff / cast count
      -- Top-k members by regard (descending), k=5
      sorted = sortBy (\a, b => compare (memeRegard b) (memeRegard a)) memes
      topK = take 5 sorted
      topKJson = map (\m => jsonObj
        [ ("id",     jsonStr (show m.id))
        , ("label",  jsonStr m.label)
        , ("regard", jsonNum (memeRegard m))
        ]) topK
  in jsonObj
    [ ("domain",    jsonStr domainLabel)
    , ("count",     jsonNat count)
    , ("centroid",  jsonNum centroid)
    , ("radius",    jsonNum variance)
    , ("top_members", jsonArr topKJson)
    ]

||| Export basin projection: groups memes by domain, computes centroid,
||| radius (variance), count, and top-k members per basin.
export
exportBasinProjection : StoreState -> ExperimentId -> IO String
exportBasinProjection st eid = do
  _ <- createDir "data"
  _ <- createDir "data/export"
  allMemes <- readIORef st.memes
  let memes = filter (\m => m.experimentId == eid) allMemes
      knowledge = filter (\m => m.domain == Knowledge) memes
      behavior  = filter (\m => m.domain == Behavior) memes
      basins = [ basinSummary "knowledge" knowledge
               , basinSummary "behavior"  behavior
               ]
      content = jsonObj
        [ ("experiment_id", jsonStr (show eid))
        , ("total_memes",   jsonNat (length memes))
        , ("basins",        jsonArr basins)
        ]
      path = "data/export/" ++ show eid ++ "-basins.json"
  Right () <- writeFile path content
    | Left err => do putStrLn ("  (basin projection write failed: " ++ show err ++ ")")
                     pure path
  pure path

------------------------------------------------------------------------
-- Geometry diagnostics export
------------------------------------------------------------------------

||| Compute graph density: edges / (nodes * (nodes - 1) / 2).
||| Returns 0.0 for graphs with fewer than 2 nodes.
graphDensity : List Meme -> List Edge -> Double
graphDensity memes edges =
  let n = length memes
      e = length edges
  in if n < 2 then 0.0
     else let maxEdges = (cast n * (cast n - 1.0)) / 2.0
          in cast e / maxEdges

||| Compute average degree: 2 * edges / nodes.
||| Returns 0.0 for empty graphs.
averageDegree : List Meme -> List Edge -> Double
averageDegree memes edges =
  let n = length memes
      e = length edges
  in if n == 0 then 0.0
     else (2.0 * cast e) / cast n

||| Get the degree of a single node by counting edges incident to it.
nodeDegree : String -> List Edge -> Nat
nodeDegree nid edges =
  length (filter (\e => e.srcId == nid || e.dstId == nid) edges)

||| Find isolated nodes: nodes with degree 0.
isolatedNodes : List Meme -> List Edge -> List Meme
isolatedNodes memes edges =
  filter (\m => nodeDegree (show m.id) edges == 0) memes

||| BFS to find all nodes reachable from a start node.
||| Returns set of visited node IDs.
bfsComponent : List Edge -> List String -> List String -> List String
bfsComponent _ [] visited = visited
bfsComponent edges queue visited =
  let newVisited = nub (visited ++ queue)
      neighbors = concatMap (\nid =>
        let outgoing = map (\e => e.dstId) (filter (\e => e.srcId == nid) edges)
            incoming = map (\e => e.srcId) (filter (\e => e.dstId == nid) edges)
        in outgoing ++ incoming) queue
      unvisited = filter (\n => not (elem n newVisited)) (nub neighbors)
  in case unvisited of
    [] => newVisited
    _  => bfsComponent edges unvisited newVisited

||| Count connected components using BFS.
connectedComponents : List Meme -> List Edge -> Nat
connectedComponents memes edges =
  let allIds = map (\m => show m.id) memes
  in countComps allIds 0
  where
    countComps : List String -> Nat -> Nat
    countComps [] acc = acc
    countComps (n :: rest) acc =
      let component = bfsComponent edges [n] []
          remaining = filter (\x => not (elem x component)) rest
      in countComps remaining (acc + 1)

||| BFS shortest path lengths from src to all reachable nodes.
||| Returns list of (nodeId, distance) pairs.
bfsDistances : String -> List Edge -> List (String, Nat)
bfsDistances start edges = go [start] [] 0 []
  where
    go : List String -> List String -> Nat -> List (String, Nat) -> List (String, Nat)
    go [] _ _ acc = acc
    go queue visited dist acc =
      let newAcc = acc ++ map (\n => (n, dist)) queue
          allVisited = nub (visited ++ queue)
          neighbors = concatMap (\nid =>
            let outgoing = map (\e => e.dstId) (filter (\e => e.srcId == nid) edges)
                incoming = map (\e => e.srcId) (filter (\e => e.dstId == nid) edges)
            in outgoing ++ incoming) queue
          nextQueue = filter (\n => not (elem n allVisited)) (nub neighbors)
      in go nextQueue allVisited (dist + 1) newAcc

||| Compute graph diameter: longest shortest path between any pair.
||| Bounded to 100 nodes to avoid excessive computation.
graphDiameter : List Meme -> List Edge -> Nat
graphDiameter memes edges =
  let nodeIds = take 100 (map (\m => show m.id) memes)
  in foldl (\acc, nid =>
       let dists = bfsDistances nid edges
           maxDist = foldl (\mx, pair => max mx (snd pair)) 0 dists
       in max acc maxDist) 0 nodeIds

||| Generate all unordered pairs from a list.
allPairs : List String -> List (String, String)
allPairs [] = []
allPairs (x :: xs) = map (\y => (x, y)) xs ++ allPairs xs

||| Compute local clustering coefficient for a single node.
||| C(v) = 2 * triangles(v) / (deg(v) * (deg(v) - 1))
localClustering : String -> List Edge -> Double
localClustering nid edges =
  let neighborIds = nub (map (\e => e.dstId) (filter (\e => e.srcId == nid) edges)
                      ++ map (\e => e.srcId) (filter (\e => e.dstId == nid) edges))
      deg = length neighborIds
  in if deg < 2 then 0.0
     else let pairs = allPairs neighborIds
              triangles = foldl (\acc, pair =>
                let (a, b) = pair
                in if any (\e => (e.srcId == a && e.dstId == b) || (e.srcId == b && e.dstId == a)) edges
                   then acc + 1
                   else acc) 0 pairs
              maxTriangles = (cast deg * (cast deg - 1.0)) / 2.0
          in if maxTriangles == 0.0 then 0.0
             else cast triangles / maxTriangles

||| Compute average clustering coefficient across all nodes.
||| Bounded to 100 nodes for performance.
clusteringCoefficient : List Meme -> List Edge -> Double
clusteringCoefficient memes edges =
  let nodeIds = take 100 (map (\m => show m.id) memes)
      n = length nodeIds
  in if n == 0 then 0.0
     else let sumCC = foldl (\acc, nid => acc + localClustering nid edges) 0.0 nodeIds
          in sumCC / cast n

||| Export geometry diagnostics as JSON.
export
exportGeometryDiagnostics : StoreState -> ExperimentId -> IO String
exportGeometryDiagnostics st eid = do
  _ <- createDir "data"
  _ <- createDir "data/export"
  allMemes <- readIORef st.memes
  allEdges <- readIORef st.edges
  let memes = filter (\m => m.experimentId == eid) allMemes
      edges = filter (\e => e.experimentId == eid) allEdges
      iso   = isolatedNodes memes edges
      content = jsonObj
        [ ("experiment_id",         jsonStr (show eid))
        , ("node_count",            jsonNat (length memes))
        , ("edge_count",            jsonNat (length edges))
        , ("density",               jsonNum (graphDensity memes edges))
        , ("average_degree",        jsonNum (averageDegree memes edges))
        , ("connected_components",  jsonNat (connectedComponents memes edges))
        , ("isolated_node_count",   jsonNat (length iso))
        , ("isolated_nodes",        jsonArr (map (\m => jsonStr (show m.id)) iso))
        , ("diameter",              jsonNat (graphDiameter memes edges))
        , ("clustering_coefficient", jsonNum (clusteringCoefficient memes edges))
        ]
      path = "data/export/" ++ show eid ++ "-geometry.json"
  Right () <- writeFile path content
    | Left err => do putStrLn ("  (geometry diagnostics write failed: " ++ show err ++ ")")
                     pure path
  pure path

------------------------------------------------------------------------
-- Tanakh surface bundle export
------------------------------------------------------------------------

||| Check if any memes contain Hebrew text.
hasHebrewContent : List Meme -> Bool
hasHebrewContent memes = any (\m => any isHebrew (unpack m.text)) memes

||| Render a letter breakdown entry to JSON.
letterEntryToJson : (Char, String, Int) -> String
letterEntryToJson entry =
  let c    = fst entry
      name = fst (snd entry)
      val  = snd (snd entry)
  in jsonObj
    [ ("letter", jsonStr (singleton c))
    , ("name",   jsonStr name)
    , ("value",  jsonNat (cast val))
    ]

||| Analyze a single meme's Hebrew text and produce a JSON bundle.
memeHebrewBundle : Meme -> String
memeHebrewBundle m =
  let analysis = analyzeHebrewExt m.text
      base = analysis.haeBase
  in jsonObj
    [ ("meme_id",       jsonStr (show m.id))
    , ("label",         jsonStr m.label)
    , ("passage_text",  jsonStr (substr 0 500 m.text))
    , ("stripped_text",  jsonStr (substr 0 500 base.strippedText))
    , ("letter_count",  jsonNat base.letterCount)
    , ("gematria_standard", jsonNat (cast base.gematriaValue))
    , ("gematria_gadol",    jsonNat (cast analysis.haeGadol))
    , ("gematria_katan",    jsonNat (cast analysis.haeKatan))
    , ("gematria_ordinal",  jsonNat (cast analysis.haeOrdinal))
    , ("roshei_teivot",  jsonStr base.rosheiResult)
    , ("sofei_teivot",   jsonStr base.sofeiResult)
    , ("atbash",         jsonStr base.atBashResult)
    , ("letter_breakdown", jsonArr (map letterEntryToJson analysis.haeLetters))
    ]

||| Export Tanakh surface bundle for all Hebrew-containing memes.
||| Returns empty string if no Hebrew content exists.
export
exportTanakhBundle : StoreState -> ExperimentId -> IO String
exportTanakhBundle st eid = do
  _ <- createDir "data"
  _ <- createDir "data/export"
  allMemes <- readIORef st.memes
  let memes = filter (\m => m.experimentId == eid) allMemes
      hebrewMemes = filter (\m => any isHebrew (unpack m.text)) memes
  case hebrewMemes of
    [] => pure ""
    _  => do
      let bundles = map memeHebrewBundle hebrewMemes
          content = jsonObj
            [ ("experiment_id",    jsonStr (show eid))
            , ("hebrew_meme_count", jsonNat (length hebrewMemes))
            , ("passages",         jsonArr bundles)
            ]
          path = "data/export/" ++ show eid ++ "-tanakh.json"
      Right () <- writeFile path content
        | Left err => do putStrLn ("  (tanakh bundle write failed: " ++ show err ++ ")")
                         pure path
      pure path

------------------------------------------------------------------------
-- Full artifact family export (manifest)
------------------------------------------------------------------------

||| Export manifest: describes all artifacts produced in a single export run.
export
exportManifest : ExperimentId -> List (String, String) -> IO String
exportManifest eid artifacts = do
  _ <- createDir "data"
  _ <- createDir "data/export"
  let entries = map (\pair =>
        jsonObj [ ("path",  jsonStr (fst pair))
                , ("type",  jsonStr (snd pair))
                ]) artifacts
      content = jsonObj
        [ ("experiment_id",    jsonStr (show eid))
        , ("artifact_count",   jsonNat (length artifacts))
        , ("artifacts",        jsonArr entries)
        ]
      path = "data/export/" ++ show eid ++ "-manifest.json"
  Right () <- writeFile path content
    | Left err => do putStrLn ("  (manifest write failed: " ++ show err ++ ")")
                     pure path
  pure path

------------------------------------------------------------------------
-- Membrane trace export (CSV)
------------------------------------------------------------------------

||| Format a membrane event as a CSV row.
||| Columns: event_index, event_type, detail, timestamp
membraneTraceCsvRow : Nat -> MembraneEventType -> String -> Eden.Types.Timestamp -> String
membraneTraceCsvRow idx evt detail ts =
  show idx ++ ","
  ++ show evt ++ ","
  ++ "\"" ++ escapeStr (substr 0 500 detail) ++ "\","
  ++ show ts

||| Export membrane trace as CSV for all membrane events.
export
exportMembraneTrace : StoreState -> ExperimentId -> IO String
exportMembraneTrace st eid = do
  _ <- createDir "data"
  _ <- createDir "data/export"
  allMbe <- readIORef st.membraneEvts
  let header = "event_index,event_type,detail,timestamp"
      rows   = zipIndex 0 allMbe
      content = unlines (header :: rows)
      path = "data/export/" ++ show eid ++ "-membrane-trace.csv"
  Right () <- writeFile path content
    | Left err => do putStrLn ("  (membrane trace write failed: " ++ show err ++ ")")
                     pure path
  pure path
  where
    zipIndex : Nat -> List (MembraneEventType, String, Eden.Types.Timestamp) -> List String
    zipIndex _ [] = []
    zipIndex n ((evt, detail, ts) :: xs) = membraneTraceCsvRow n evt detail ts :: zipIndex (S n) xs

------------------------------------------------------------------------
-- Combined export (all formats)
------------------------------------------------------------------------

||| Run all export formats for an experiment and return paths.
export
exportAll : StoreState -> ExperimentId -> IO (List String)
exportAll st eid = do
  p1 <- writeGraphExport st eid
  p2 <- exportRegardTimeline st eid
  p3 <- exportMemeIndex st eid
  p4 <- exportBasinProjection st eid
  p5 <- exportGeometryDiagnostics st eid
  p6 <- exportMembraneTrace st eid
  -- Tanakh bundle: only if Hebrew content exists
  allMemes <- readIORef st.memes
  let memes = filter (\m => m.experimentId == eid) allMemes
  p7 <- if hasHebrewContent memes
        then exportTanakhBundle st eid
        else pure ""
  let basePaths = [p1, p2, p3, p4, p5, p6]
      allPaths  = if p7 == "" then basePaths else basePaths ++ [p7]
      artifacts = map (\p => (p, "json")) allPaths
  p8 <- exportManifest eid artifacts
  pure (allPaths ++ [p8])
