||| HTTP observatory server for EDEN graph inspection and mutation.
|||
||| Serves the graph store as JSON over HTTP.  Read endpoints match the
||| observatory payload contract.  Mutation endpoints follow the
||| preview/commit/revert flow with measurement event provenance.
||| SSE endpoint for live invalidation notifications.
||| Single-threaded blocking server using C FFI sockets.
module Eden.Observatory

import Data.IORef
import Data.List
import Data.String
import Eden.Types
import Eden.Config
import Eden.Regard
import Eden.Store.InMemory
import Eden.Export
import Eden.Monad
import Eden.OntologyProjection
import Eden.Models.MLX
import Eden.Tanakh
import Eden.Trace

------------------------------------------------------------------------
-- C FFI declarations
------------------------------------------------------------------------

%foreign "C:eden_http_start,eden_http"
prim__httpStart : Int -> PrimIO Int

%foreign "C:eden_http_accept,eden_http"
prim__httpAccept : Int -> PrimIO Int

%foreign "C:eden_http_read_request,eden_http"
prim__httpReadRequest : Int -> PrimIO String

%foreign "C:eden_http_get_method,eden_http"
prim__httpGetMethod : Int -> PrimIO String

%foreign "C:eden_http_get_content_length,eden_http"
prim__httpGetContentLength : Int -> PrimIO Int

%foreign "C:eden_http_read_body,eden_http"
prim__httpReadBody : Int -> Int -> PrimIO String

%foreign "C:eden_http_send_response,eden_http"
prim__httpSendResponse : Int -> String -> String -> PrimIO ()

%foreign "C:eden_http_send_sse_headers,eden_http"
prim__httpSendSseHeaders : Int -> PrimIO Int

%foreign "C:eden_http_send_sse,eden_http"
prim__httpSendSse : String -> String -> PrimIO ()

%foreign "C:eden_http_close,eden_http"
prim__httpClose : Int -> PrimIO ()

%foreign "C:eden_http_stop,eden_http"
prim__httpStop : Int -> PrimIO ()

------------------------------------------------------------------------
-- JSON helpers (minimal, self-contained)
------------------------------------------------------------------------

escJ : Char -> List Char
escJ '"'  = ['\\', '"']
escJ '\\' = ['\\', '\\']
escJ '\n' = ['\\', 'n']
escJ '\t' = ['\\', 't']
escJ c    = [c]

jEsc : String -> String
jEsc = pack . concatMap escJ . unpack

jStr : String -> String
jStr s = "\"" ++ jEsc s ++ "\""

jNum : Double -> String
jNum d =
  let i = cast {to=Integer} (d * 1000.0)
  in show (cast {to=Double} i / 1000.0)

jNat : Nat -> String
jNat = show

jObj : List (String, String) -> String
jObj fields =
  "{" ++ joinBy ", " (map (\kv => jStr (fst kv) ++ ": " ++ snd kv) fields) ++ "}"

jArr : List String -> String
jArr items = "[" ++ joinBy ", " items ++ "]"

------------------------------------------------------------------------
-- Entity -> JSON serializers
------------------------------------------------------------------------

memeJson : Meme -> String
memeJson m = jObj
  [ ("id",            jStr (show m.id))
  , ("label",         jStr m.label)
  , ("kind",          jStr "meme")
  , ("domain",        jStr (show m.domain))
  , ("scope",         jStr (show m.scope))
  , ("source",        jStr (show m.sourceKind))
  , ("text",          jStr (substr 0 500 m.text))
  , ("rewardEma",     jNum m.rewardEma)
  , ("riskEma",       jNum m.riskEma)
  , ("editEma",       jNum m.editEma)
  , ("evidenceN",     jNum m.evidenceN)
  , ("usageCount",    jNat m.usageCount)
  , ("feedbackCount", jNat m.feedbackCount)
  , ("entity_type",     jStr "meme")
  , ("speech_act_mode", jStr (show m.domain))
  , ("storage_kind",    jStr "persisted")
  ]

edgeJson : Edge -> String
edgeJson e = jObj
  [ ("id",          jStr (show e.id))
  , ("source",      jStr e.srcId)
  , ("target",      jStr e.dstId)
  , ("type",        jStr (show e.edgeType))
  , ("weight",      jNum e.weight)
  , ("source_kind", jStr (show e.srcKind))
  , ("target_kind", jStr (show e.dstKind))
  ]

memodeJson : Memode -> String
memodeJson md = jObj
  [ ("id",         jStr (show md.id))
  , ("label",      jStr md.label)
  , ("kind",       jStr "memode")
  , ("domain",     jStr (show md.domain))
  , ("summary",    jStr md.summary)
  , ("memberHash", jStr md.memberHash)
  ]

sessionJson : Session -> String
sessionJson s = jObj
  [ ("id",            jStr (show s.id))
  , ("experiment_id", jStr (show s.experimentId))
  , ("agent_id",      jStr (show s.agentId))
  , ("title",         jStr s.title)
  , ("created_at",    jStr (show s.createdAt))
  , ("updated_at",    jStr (show s.updatedAt))
  ]

turnJson : Turn -> String
turnJson t = jObj
  [ ("id",            jStr (show t.id))
  , ("session_id",    jStr (show t.sessionId))
  , ("turn_index",    jNat t.turnIndex)
  , ("user_text",     jStr (substr 0 500 t.userText))
  , ("response",      jStr (substr 0 500 t.membraneText))
  , ("created_at",    jStr (show t.createdAt))
  ]

feedbackJson : FeedbackRecord -> String
feedbackJson fb = jObj
  [ ("id",          jStr (show fb.frId))
  , ("session_id",  jStr (show fb.frSessionId))
  , ("turn_id",     jStr (show fb.frTurnId))
  , ("verdict",     jStr (show fb.frVerdict))
  , ("explanation", jStr fb.frExplanation)
  , ("reward",      jNum fb.frSignal.reward)
  , ("risk",        jNum fb.frSignal.risk)
  , ("edit",        jNum fb.frSignal.edit)
  ]

regardJson : Meme -> String
regardJson m =
  let ns = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau 0.0 m.feedbackCount m.editEma m.contradictionCount m.membraneConflicts
      gm = MkGraphMetrics 0.5 0.4 0.3
      rb = regardBreakdown defaultRegardWeights ns gm
  in jObj
    [ ("meme_id",    jStr (show m.id))
    , ("label",      jStr m.label)
    , ("reward",     jNum rb.reward)
    , ("evidence",   jNum rb.evidence)
    , ("coherence",  jNum rb.coherence)
    , ("persistence", jNum rb.persistence)
    , ("decay",      jNum rb.decay)
    , ("isolation",  jNum rb.isolationPenalty)
    , ("risk",       jNum rb.risk)
    , ("activation", jNum rb.activation)
    , ("total",      jNum rb.totalRegard)
    ]

measurementJson : MeasurementEvent -> String
measurementJson me = jObj
  [ ("id",             jStr me.id)
  , ("experiment_id",  jStr (show me.experimentId))
  , ("session_id",     jStr (show me.sessionId))
  , ("action",         jStr (show me.action))
  , ("state",          jStr (show me.state))
  , ("operator",       jStr me.operator)
  , ("evidence",       jStr me.evidence)
  , ("before_state",   jStr me.beforeState)
  , ("proposed_state", jStr me.proposedState)
  , ("committed_state", jStr me.committedState)
  , ("revert_of",      jStr me.revertOf)
  , ("created_at",     jStr (show me.createdAt))
  ]

experimentJson : Experiment -> String
experimentJson exp = jObj
  [ ("id",         jStr (show exp.id))
  , ("name",       jStr exp.name)
  , ("slug",       jStr exp.slug)
  , ("mode",       jStr (show exp.mode))
  , ("status",     jStr (show exp.status))
  , ("created_at", jStr (show exp.createdAt))
  , ("updated_at", jStr (show exp.updatedAt))
  ]

------------------------------------------------------------------------
-- Minimal JSON field extraction (for POST body parsing)
------------------------------------------------------------------------

findSubstr : List Char -> List Char -> Maybe (List Char)
findSubstr [] haystack = Just haystack
findSubstr _ [] = Nothing
findSubstr needle (c :: cs) =
  if isPrefixList needle (c :: cs)
    then Just (c :: cs)
    else findSubstr needle cs
  where
    isPrefixList : List Char -> List Char -> Bool
    isPrefixList [] _ = True
    isPrefixList _ [] = False
    isPrefixList (a :: as) (b :: bs) = a == b && isPrefixList as bs

extractJsonString : String -> String -> String
extractJsonString key json =
  let needle = "\"" ++ key ++ "\""
      cs = unpack json
  in case findSubstr (unpack needle) cs of
       Nothing  => ""
       Just rest =>
         let afterColon = dropWhile (\c => c /= ':') rest
             afterWs    = drop 1 (dropWhile (\c => c == ':' || c == ' ') afterColon)
         in case afterWs of
              ('"' :: vs) => pack (takeWhile (\c => c /= '"') vs)
              _           => ""

extractJsonDouble : String -> String -> Double
extractJsonDouble key json =
  let needle = "\"" ++ key ++ "\""
      cs = unpack json
  in case findSubstr (unpack needle) cs of
       Nothing  => 0.0
       Just rest =>
         let afterColon = dropWhile (\c => c /= ':') rest
             afterWs    = drop 1 (dropWhile (\c => c == ':' || c == ' ') afterColon)
             numStr     = pack (takeWhile (\c => isDigit c || c == '.' || c == '-') afterWs)
         in case parseDouble numStr of
              Just d  => d
              Nothing => 0.0

extractJsonStringArray : String -> String -> List String
extractJsonStringArray key json =
  let needle = "\"" ++ key ++ "\""
      cs = unpack json
  in case findSubstr (unpack needle) cs of
       Nothing  => []
       Just rest =>
         let afterColon = dropWhile (\c => c /= ':') rest
             afterWs    = drop 1 (dropWhile (\c => c == ':' || c == ' ') afterColon)
         in case afterWs of
              ('[' :: vs) =>
                let arrStr = pack (takeWhile (\c => c /= ']') vs)
                in parseStringArr (unpack arrStr) []
              _ => []
  where
    parseStringArr : List Char -> List String -> List String
    parseStringArr [] acc = reverse acc
    parseStringArr ('"' :: rest) acc =
      let val = pack (takeWhile (\c => c /= '"') rest)
          remaining = drop (length val + 1) rest
      in parseStringArr remaining (val :: acc)
    parseStringArr (_ :: rest) acc = parseStringArr rest acc

------------------------------------------------------------------------
-- Parse edge type from string
------------------------------------------------------------------------

parseEdgeType : String -> EdgeType
parseEdgeType "CO_OCCURS_WITH"    = CoOccursWith
parseEdgeType "AUTHOR_OF"         = AuthorOf
parseEdgeType "INFLUENCES"        = Influences
parseEdgeType "SUPPORTS"          = Supports
parseEdgeType "REINFORCES"        = Reinforces
parseEdgeType "REFINES"           = Refines
parseEdgeType "CONTRADICTS"       = ContradictsEdge
parseEdgeType "DERIVED_FROM"      = DerivedFrom
parseEdgeType "RELATES_TO"        = RelatesTo
parseEdgeType "MEMBER_OF"         = MemberOf
parseEdgeType "CONTEXTUALIZES_DOCUMENT" = ContextualizesDocument
parseEdgeType "FED_BACK_BY"       = FedBackBy
parseEdgeType "OCCURS_IN"         = OccursIn
parseEdgeType _                   = RelatesTo

------------------------------------------------------------------------
-- Preview state (held between preview and commit)
------------------------------------------------------------------------

record PreviewState where
  constructor MkPreviewState
  pvAction      : MeasurementAction
  pvBeforeState : String
  pvProposedState : String
  pvOperator    : String
  pvEvidence    : String
  pvSource      : String
  pvTarget      : String
  pvRelation    : EdgeType
  pvWeight      : Double
  pvRationale   : String
  pvEdgeId      : String
  pvMemberIds   : List String

------------------------------------------------------------------------
-- SSE notification helper
------------------------------------------------------------------------

notifySSE : String -> String -> IO ()
notifySSE eventType entityId = do
  let payload = jObj [("type", jStr eventType), ("id", jStr entityId)]
  primIO (prim__httpSendSse "invalidate" payload)

------------------------------------------------------------------------
-- Basin projection (pure computation)
------------------------------------------------------------------------

memeRegard : Meme -> Double
memeRegard m =
  let ns = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau 0.0 m.feedbackCount m.editEma m.contradictionCount m.membraneConflicts
      gm = MkGraphMetrics 0.5 0.4 0.3
      rb = regardBreakdown defaultRegardWeights ns gm
  in rb.totalRegard

record Basin where
  constructor MkBasin
  basinDomain   : Domain
  basinMemeIds  : List String
  basinCenterX  : Double
  basinCenterY  : Double
  basinWeight   : Double
  basinSize     : Nat

computeBasins : List Meme -> List Basin
computeBasins memes =
  let knowledge = filter (\m => m.domain == Knowledge) memes
      behavior  = filter (\m => m.domain == Behavior) memes
  in catMaybes [mkBasin Knowledge knowledge, mkBasin Behavior behavior]
  where
    totalWeight : List Meme -> Double
    totalWeight [] = 0.0
    totalWeight (m :: ms) = max 0.001 (memeRegard m) + totalWeight ms

    sumW : (Meme -> Double) -> List Meme -> Double
    sumW _ [] = 0.0
    sumW f (m :: ms) = f m * max 0.001 (memeRegard m) + sumW f ms

    mkBasin : Domain -> List Meme -> Maybe Basin
    mkBasin _   [] = Nothing
    mkBasin dom ms =
      let tw = totalWeight ms
          cx = if tw > 0.0 then sumW (\m => m.rewardEma) ms / tw else 0.0
          cy = if tw > 0.0 then sumW (\m => m.evidenceN) ms / tw else 0.0
      in Just (MkBasin dom (map (\m => show m.id) ms) cx cy tw (length ms))

basinJson : Basin -> String
basinJson b = jObj
  [ ("domain",    jStr (show b.basinDomain))
  , ("meme_ids",  jArr (map jStr b.basinMemeIds))
  , ("center_x",  jNum b.basinCenterX)
  , ("center_y",  jNum b.basinCenterY)
  , ("weight",    jNum b.basinWeight)
  , ("size",      jNat b.basinSize)
  , ("projection_method",  jStr "domain_partition")
  , ("projection_version", jStr "1.0")
  ]

------------------------------------------------------------------------
-- Geometry diagnostics (pure computation)
------------------------------------------------------------------------

record GeometryDiagnostics where
  constructor MkGeometryDiagnostics
  gdNodeCount        : Nat
  gdEdgeCount        : Nat
  gdDensity          : Double
  gdAverageDegree    : Double
  gdConnectedComponents : Nat
  gdDiameterEstimate : Nat
  gdClusteringCoeff  : Double

estimateComponents : List Meme -> List Edge -> Nat
estimateComponents memes edges =
  let memeIds = map (\m => show m.id) memes
      groups = map (\mid => [mid]) memeIds
      merged = foldl mergeEdge groups edges
  in length merged
  where
    inGroup : String -> List String -> Bool
    inGroup x xs = any (== x) xs

    mergeEdge : List (List String) -> Edge -> List (List String)
    mergeEdge groups edge =
      let src = edge.srcId
          dst = edge.dstId
          srcGroup = find (inGroup src) groups
          dstGroup = find (inGroup dst) groups
      in case (srcGroup, dstGroup) of
           (Just sg, Just dg) =>
             if sg == dg then groups
             else
               let merged = sg ++ dg
                   others = filter (\g => g /= sg && g /= dg) groups
               in merged :: others
           _ => groups

localClust : String -> List Edge -> Double
localClust nid edges =
  let neighbors = nub (mapMaybe (\e =>
        if e.srcId == nid then Just e.dstId
        else if e.dstId == nid then Just e.srcId
        else Nothing) edges)
      k = length neighbors
  in if k < 2 then 0.0
     else
       let cPairs = countPairs neighbors edges
           maxPairs = cast k * (cast k - 1.0) / 2.0
       in if maxPairs > 0.0 then cast cPairs / maxPairs else 0.0
  where
    edgeExists : String -> String -> List Edge -> Bool
    edgeExists a b es = any (\e =>
      (e.srcId == a && e.dstId == b) || (e.srcId == b && e.dstId == a)) es

    countPairs : List String -> List Edge -> Nat
    countPairs [] _ = 0
    countPairs (x :: xs) es =
      let xPairs = length (filter (\y => edgeExists x y es) xs)
      in xPairs + countPairs xs es

computeGeometry : List Meme -> List Edge -> GeometryDiagnostics
computeGeometry memes edges =
  let n = length memes
      m = length edges
      density = if n > 1
                then cast m / (cast n * (cast n - 1.0) / 2.0)
                else 0.0
      avgDeg  = if n > 0
                then cast (2 * m) / cast n
                else 0.0
      components = estimateComponents memes edges
      diamEst = if components > 0 then 2 * components else 0
      coeffs = map (\m2 => localClust (show m2.id) edges) memes
      avgClust = if n > 0
                 then foldl (+) 0.0 coeffs / cast n
                 else 0.0
  in MkGeometryDiagnostics n m density avgDeg components diamEst avgClust

geometryJson : GeometryDiagnostics -> String
geometryJson g = jObj
  [ ("node_count",           jNat g.gdNodeCount)
  , ("edge_count",           jNat g.gdEdgeCount)
  , ("density",              jNum g.gdDensity)
  , ("average_degree",       jNum g.gdAverageDegree)
  , ("connected_components", jNat g.gdConnectedComponents)
  , ("diameter_estimate",    jNat g.gdDiameterEstimate)
  , ("clustering_coefficient", jNum g.gdClusteringCoeff)
  , ("evidence_labels", jObj
      [ ("node_count",             jStr "OBSERVED")
      , ("edge_count",             jStr "OBSERVED")
      , ("density",                jStr "DERIVED")
      , ("average_degree",         jStr "DERIVED")
      , ("connected_components",   jStr "DERIVED")
      , ("clustering_coefficient", jStr "DERIVED")
      ])
  ]

------------------------------------------------------------------------
-- Route handling helpers
------------------------------------------------------------------------

send404 : Int -> String -> IO ()
send404 fd path = do
  let body = jObj [("error", jStr "not found"), ("path", jStr path)]
  primIO (prim__httpSendResponse fd "application/json" body)

send400 : Int -> String -> IO ()
send400 fd msg = do
  let body = jObj [("error", jStr msg)]
  primIO (prim__httpSendResponse fd "application/json" body)

sendOptions : Int -> IO ()
sendOptions fd = primIO (prim__httpSendResponse fd "text/plain" "")

nowTimestamp : IO Timestamp
nowTimestamp = currentTimestamp

getSessionId : StoreState -> ExperimentId -> IO SessionId
getSessionId st eid = do
  allSess <- readIORef st.sessions
  pure (case filter (\s => s.experimentId == eid) allSess of
          (s :: _) => s.id
          []       => MkId "sess-0")

------------------------------------------------------------------------
-- Index HTML
------------------------------------------------------------------------

indexHtml : String
indexHtml = unlines
  [ "<!DOCTYPE html>"
  , "<html><head><title>EDEN Observatory</title>"
  , "<style>"
  , "  body { font-family: monospace; background: #12080a; color: #ffd98a; padding: 2em; }"
  , "  a { color: #a890ff; }"
  , "  h1 { color: #ffae57; }"
  , "  li { margin: 0.3em 0; }"
  , "  .post { color: #ff8a8a; }"
  , "</style></head><body>"
  , "<h1>EDEN Observatory</h1>"
  , "<p>Graph API with measurement-first mutation.</p>"
  , "<ul>"
  , "  <li><a href=\"/api/health\">/api/health</a></li>"
  , "  <li><a href=\"/api/graph\">/api/graph</a></li>"
  , "  <li><a href=\"/api/memes\">/api/memes</a></li>"
  , "  <li><a href=\"/api/edges\">/api/edges</a> (GET | <span class=\"post\">POST</span>)</li>"
  , "  <li><a href=\"/api/memodes\">/api/memodes</a></li>"
  , "  <li><a href=\"/api/regard\">/api/regard</a></li>"
  , "  <li><a href=\"/api/feedback\">/api/feedback</a></li>"
  , "  <li><a href=\"/api/sessions\">/api/sessions</a></li>"
  , "  <li><a href=\"/api/turns\">/api/turns</a></li>"
  , "  <li><a href=\"/api/basins\">/api/basins</a></li>"
  , "  <li><a href=\"/api/geometry\">/api/geometry</a></li>"
  , "  <li><a href=\"/api/measurements\">/api/measurements</a></li>"
  , "  <li><a href=\"/api/models\">/api/models</a></li>"
  , "  <li><a href=\"/api/experiments\">/api/experiments</a></li>"
  , "  <li>/api/experiments/:id/memes</li>"
  , "  <li>/api/experiments/:id/sessions</li>"
  , "  <li>/api/experiments/:id/graph</li>"
  , "  <li><a href=\"/api/runtime/status\">/api/runtime/status</a></li>"
  , "  <li><a href=\"/api/runtime/model\">/api/runtime/model</a></li>"
  , "  <li><a href=\"/api/tanakh\">/api/tanakh</a></li>"
  , "  <li><a href=\"/api/events\">/api/events</a> (SSE)</li>"
  , "  <li>/api/sessions/:id/turns</li>"
  , "  <li>/api/sessions/:id/active-set</li>"
  , "  <li>/api/sessions/:id/trace</li>"
  , "  <li><span class=\"post\">POST /api/edges/:id/update</span></li>"
  , "  <li><span class=\"post\">POST /api/edges/:id/remove</span></li>"
  , "  <li><span class=\"post\">POST /api/memodes/assert</span></li>"
  , "  <li><span class=\"post\">POST /api/tanakh-run</span></li>"
  , "  <li><span class=\"post\">POST /api/preview</span></li>"
  , "  <li><span class=\"post\">POST /api/commit</span></li>"
  , "  <li><span class=\"post\">POST /api/revert/:eventId</span></li>"
  , "</ul>"
  , "</body></html>"
  ]

------------------------------------------------------------------------
-- GET route dispatcher
------------------------------------------------------------------------

serveGetRoute : StoreState -> ExperimentId -> Int -> String -> IO ()
serveGetRoute st eid fd "/" = primIO (prim__httpSendResponse fd "text/html; charset=utf-8" indexHtml)
serveGetRoute st eid fd "/index.html" = primIO (prim__httpSendResponse fd "text/html; charset=utf-8" indexHtml)
serveGetRoute st eid fd "/api/health" = do
  let body = jObj [("status", jStr "ok"), ("runtime", jStr "idris2-refc")]
  primIO (prim__httpSendResponse fd "application/json" body)
serveGetRoute st eid fd "/api/graph" = do
  body <- exportGraphJson st eid
  primIO (prim__httpSendResponse fd "application/json" body)
serveGetRoute st eid fd "/api/memes" = do
  allMemes <- readIORef st.memes
  let memes = filter (\m => m.experimentId == eid) allMemes
  primIO (prim__httpSendResponse fd "application/json" (jArr (map memeJson memes)))
serveGetRoute st eid fd "/api/edges" = do
  allEdges <- readIORef st.edges
  let edges = filter (\e => e.experimentId == eid) allEdges
  primIO (prim__httpSendResponse fd "application/json" (jArr (map edgeJson edges)))
serveGetRoute st eid fd "/api/memodes" = do
  allMemodes <- readIORef st.memodes
  let memodes = filter (\m => m.experimentId == eid) allMemodes
  primIO (prim__httpSendResponse fd "application/json" (jArr (map memodeJson memodes)))
serveGetRoute st eid fd "/api/regard" = do
  allMemes <- readIORef st.memes
  let memes = filter (\m => m.experimentId == eid) allMemes
  primIO (prim__httpSendResponse fd "application/json" (jArr (map regardJson memes)))
serveGetRoute st eid fd "/api/feedback" = do
  allFb <- readIORef st.feedbackEvents
  let fbs = filter (\fb => fb.frExperimentId == eid) allFb
  primIO (prim__httpSendResponse fd "application/json" (jArr (map feedbackJson fbs)))
serveGetRoute st eid fd "/api/sessions" = do
  allSess <- readIORef st.sessions
  let sessions = filter (\s => s.experimentId == eid) allSess
  primIO (prim__httpSendResponse fd "application/json" (jArr (map sessionJson sessions)))
serveGetRoute st eid fd "/api/turns" = do
  allTurns <- readIORef st.turns
  let turns = filter (\t => t.experimentId == eid) allTurns
  let sorted = sortBy (\a, b => compare b.turnIndex a.turnIndex) turns
  primIO (prim__httpSendResponse fd "application/json" (jArr (map turnJson (take 50 sorted))))
serveGetRoute st eid fd "/api/basins" = do
  allMemes <- readIORef st.memes
  let memes = filter (\m => m.experimentId == eid) allMemes
  primIO (prim__httpSendResponse fd "application/json" (jArr (map basinJson (computeBasins memes))))
serveGetRoute st eid fd "/api/geometry" = do
  allMemes <- readIORef st.memes
  allEdges <- readIORef st.edges
  let memes = filter (\m => m.experimentId == eid) allMemes
  let edges = filter (\e => e.experimentId == eid) allEdges
  primIO (prim__httpSendResponse fd "application/json" (geometryJson (computeGeometry memes edges)))
serveGetRoute st eid fd "/api/measurements" = do
  allMeas <- readIORef st.measurements
  let meas = filter (\e => e.experimentId == eid) allMeas
  primIO (prim__httpSendResponse fd "application/json" (jArr (map measurementJson meas)))
serveGetRoute st eid fd "/api/models" = do
  let cfg = defaultMLXConfig
  let info = mlxBackendInfo cfg
  let known = knownMLXModels
  let infoJson = jObj (map (\(k,v) => (k, v)) info)
  let modelsJson = jArr (map (\m => jStr m) known)
  let body = jObj [("config", infoJson), ("known_models", modelsJson)]
  primIO (prim__httpSendResponse fd "application/json" body)
serveGetRoute st eid fd "/api/runtime/status" = do
  allMemes <- readIORef st.memes
  allEdges <- readIORef st.edges
  allTurns <- readIORef st.turns
  allSess <- readIORef st.sessions
  let memes = filter (\m => m.experimentId == eid) allMemes
  let edges = filter (\e => e.experimentId == eid) allEdges
  let turns = filter (\t => t.experimentId == eid) allTurns
  let sessions = filter (\s => s.experimentId == eid) allSess
  let body = jObj
        [ ("status",        jStr "running")
        , ("runtime",       jStr "idris2-refc")
        , ("experiment_id", jStr (show eid))
        , ("session_count", jNat (length sessions))
        , ("meme_count",    jNat (length memes))
        , ("edge_count",    jNat (length edges))
        , ("turn_count",    jNat (length turns))
        ]
  primIO (prim__httpSendResponse fd "application/json" body)
serveGetRoute st eid fd "/api/runtime/model" = do
  let cfg = defaultMLXConfig
  let body = jObj (map (\kv => (fst kv, snd kv)) (mlxBackendInfo cfg))
  primIO (prim__httpSendResponse fd "application/json" body)
serveGetRoute st eid fd "/api/tanakh" = do
  allMemes <- readIORef st.memes
  let memes = filter (\m => m.experimentId == eid) allMemes
  let hebrewMemes = filter (\m => any isHebrew (unpack m.text)) memes
  let bundles = map (\m =>
        let a = analyzeHebrew m.text
        in jObj [ ("meme_id",     jStr (show m.id))
               , ("label",       jStr m.label)
               , ("text",        jStr (substr 0 200 m.text))
               , ("gematria",    show a.gematriaValue)
               , ("letter_count", jNat a.letterCount)
               , ("roshei",      jStr a.rosheiResult)
               , ("sofei",       jStr a.sofeiResult)
               , ("atbash",      jStr a.atBashResult)
               ]) hebrewMemes
  primIO (prim__httpSendResponse fd "application/json"
    (jObj [ ("hebrew_meme_count", jNat (length hebrewMemes))
          , ("passages", jArr bundles) ]))
serveGetRoute st eid fd "/api/events" = do
  _ <- primIO (prim__httpSendSseHeaders fd)
  pure ()
serveGetRoute st eid fd "/api/experiments" = do
  allExps <- readIORef st.experiments
  primIO (prim__httpSendResponse fd "application/json" (jArr (map experimentJson allExps)))
serveGetRoute st eid fd path =
  if isPrefixOf "/api/memes/" path
    then do let memeIdStr = substr 11 (length path) path
            allMemes <- readIORef st.memes
            case filter (\m => show m.id == memeIdStr) allMemes of
              (m :: _) => primIO (prim__httpSendResponse fd "application/json" (memeJson m))
              []        => send404 fd path
  else if isPrefixOf "/api/sessions/" path
    then serveSessionRoute st fd path
  else if isPrefixOf "/api/experiments/" path
    then serveExperimentRoute st fd path
    else send404 fd path
  where
    serveSessionRoute : StoreState -> Int -> String -> IO ()
    serveSessionRoute st fd path = do
      let rest = substr 14 (length path) path
      let sessIdStr = pack (takeWhile (\c => c /= '/') (unpack rest))
      let subPath = substr (length sessIdStr) (length rest) rest
      case subPath of
        "/turns" => do
          allTurns <- readIORef st.turns
          let turns = filter (\t => show t.sessionId == sessIdStr) allTurns
          let sorted = sortBy (\a, b => compare a.turnIndex b.turnIndex) turns
          primIO (prim__httpSendResponse fd "application/json" (jArr (map turnJson sorted)))
        "/active-set" => do
          allAsets <- readIORef st.activeSetSnaps
          let asets = filter (\a => show a.sessionId == sessIdStr) allAsets
          let asJson = map (\a => jObj
                [ ("id",       jStr a.id)
                , ("turn_id",  jStr (show a.turnId))
                , ("node_id",  jStr a.nodeId)
                , ("label",    jStr a.label)
                , ("domain",   jStr (show a.domain))
                , ("selection_score", jNum a.selectionScore)
                , ("semantic_sim",    jNum a.semanticSim)
                , ("activation",      jNum a.activationVal)
                , ("regard",          jNum a.regardVal)
                ]) asets
          primIO (prim__httpSendResponse fd "application/json" (jArr asJson))
        "/trace" => do
          allTrace <- readIORef st.traceEvts
          let traceJson = map (\tup => case tup of
                (evt, lvl, msg, ts) => jObj
                  [ ("event",     jStr (show evt))
                  , ("level",     jStr (show lvl))
                  , ("message",   jStr (substr 0 500 msg))
                  , ("timestamp", jStr (show ts))
                  ]) (take 200 allTrace)
          primIO (prim__httpSendResponse fd "application/json" (jArr traceJson))
        _ => send404 fd path

    serveExperimentRoute : StoreState -> Int -> String -> IO ()
    serveExperimentRoute st fd path = do
      -- /api/experiments/<id>/... => strip prefix (17 chars for "/api/experiments/")
      let rest = substr 17 (length path) path
      let expIdStr = pack (takeWhile (\c => c /= '/') (unpack rest))
      let subPath = substr (length expIdStr) (length rest) rest
      let scopedEid = MkId {a=ExperimentTag} expIdStr
      case subPath of
        "/memes" => do
          allMemes <- readIORef st.memes
          let memes = filter (\m => m.experimentId == scopedEid) allMemes
          primIO (prim__httpSendResponse fd "application/json" (jArr (map memeJson memes)))
        "/sessions" => do
          allSess <- readIORef st.sessions
          let sessions = filter (\s => s.experimentId == scopedEid) allSess
          primIO (prim__httpSendResponse fd "application/json" (jArr (map sessionJson sessions)))
        "/graph" => do
          body <- exportGraphJson st scopedEid
          primIO (prim__httpSendResponse fd "application/json" body)
        _ => send404 fd path

------------------------------------------------------------------------
-- POST mutation handlers
------------------------------------------------------------------------

handlePostEdges : StoreState -> ExperimentId -> Int -> String -> IO ()
handlePostEdges st eid fd body = do
  now <- nowTimestamp
  let src      = extractJsonString "source" body
  let target   = extractJsonString "target" body
  let relation = extractJsonString "relation" body
  let weight   = extractJsonDouble "weight" body
  let rationale = extractJsonString "rationale" body
  let operator = extractJsonString "operator" body
  if src == "" || target == ""
    then send400 fd "source and target required"
    else do
      sessId <- getSessionId st eid
      edge <- createEdge st eid MemeNode src MemeNode target (parseEdgeType relation) weight now
      _ <- recordMeasurementEvent st eid sessId EdgeAdd Committed
             operator rationale "" (edgeJson edge) (edgeJson edge) "" now
      recordTraceEvent st TraceObservatoryCommit Info ("edge_add: " ++ show edge.id) now
      notifySSE "edge_add" (show edge.id)
      primIO (prim__httpSendResponse fd "application/json" (edgeJson edge))

handlePostEdgeUpdate : StoreState -> ExperimentId -> Int -> String -> String -> IO ()
handlePostEdgeUpdate st eid fd edgeIdStr body = do
  now <- nowTimestamp
  allEdges <- readIORef st.edges
  case filter (\e => show e.id == edgeIdStr && e.experimentId == eid) allEdges of
    [] => send404 fd ("/api/edges/" ++ edgeIdStr ++ "/update")
    (oldEdge :: _) => do
      let newWeight   = extractJsonDouble "weight" body
      let newRelation = extractJsonString "relation" body
      let operator    = extractJsonString "operator" body
      let rationale   = extractJsonString "rationale" body
      let updatedEdge = { weight := (if newWeight /= 0.0 then newWeight else oldEdge.weight)
                        , edgeType := (if newRelation /= "" then parseEdgeType newRelation else oldEdge.edgeType)
                        , updatedAt := now } oldEdge
      let others = filter (\e => show e.id /= edgeIdStr) allEdges
      writeIORef st.edges (updatedEdge :: others)
      sessId <- getSessionId st eid
      _ <- recordMeasurementEvent st eid sessId EdgeUpdate Committed
             operator rationale (edgeJson oldEdge) (edgeJson updatedEdge) (edgeJson updatedEdge) "" now
      recordTraceEvent st TraceObservatoryCommit Info ("edge_update: " ++ edgeIdStr) now
      notifySSE "edge_update" edgeIdStr
      primIO (prim__httpSendResponse fd "application/json" (edgeJson updatedEdge))

handlePostEdgeRemove : StoreState -> ExperimentId -> Int -> String -> String -> IO ()
handlePostEdgeRemove st eid fd edgeIdStr body = do
  now <- nowTimestamp
  allEdges <- readIORef st.edges
  case filter (\e => show e.id == edgeIdStr && e.experimentId == eid) allEdges of
    [] => send404 fd ("/api/edges/" ++ edgeIdStr ++ "/remove")
    (edge :: _) => do
      let operator  = extractJsonString "operator" body
      let rationale = extractJsonString "rationale" body
      let others = filter (\e => show e.id /= edgeIdStr) allEdges
      writeIORef st.edges others
      sessId <- getSessionId st eid
      _ <- recordMeasurementEvent st eid sessId EdgeRemove Committed
             operator rationale (edgeJson edge) "" "" "" now
      recordTraceEvent st TraceObservatoryCommit Info ("edge_remove: " ++ edgeIdStr) now
      notifySSE "edge_remove" edgeIdStr
      primIO (prim__httpSendResponse fd "application/json"
        (jObj [("removed", jStr edgeIdStr), ("status", jStr "ok")]))

handlePostMemodeAssert : StoreState -> ExperimentId -> Int -> String -> IO ()
handlePostMemodeAssert st eid fd body = do
  now <- nowTimestamp
  let label     = extractJsonString "label" body
  let summary   = extractJsonString "summary" body
  let domStr    = extractJsonString "domain" body
  let memberIds = extractJsonStringArray "member_ids" body
  let operator  = extractJsonString "operator" body
  let rationale = extractJsonString "rationale" body
  let domain = if domStr == "knowledge" then Knowledge else Behavior
  if length memberIds < 2
    then send400 fd "memode_assert requires at least 2 member_ids"
    else do
      let mids = map (\s => MkId {a=MemeTag} s) memberIds
      memode <- upsertMemode st eid
        (if label == "" then "memode:asserted" else label)
        (if summary == "" then "operator-asserted" else summary)
        domain mids now
      _ <- traverse (\mid =>
        createEdge st eid MemeNode (show mid) MemodeNode (show memode.id) MemberOf 1.0 now) mids
      sessId <- getSessionId st eid
      _ <- recordMeasurementEvent st eid sessId MemodeAssert Committed
             operator rationale "" (memodeJson memode) (memodeJson memode) "" now
      recordTraceEvent st TraceObservatoryCommit Info ("memode_assert: " ++ show memode.id) now
      notifySSE "memode_assert" (show memode.id)
      primIO (prim__httpSendResponse fd "application/json" (memodeJson memode))

handlePostPreview : StoreState -> ExperimentId -> IORef (Maybe PreviewState) -> Int -> String -> IO ()
handlePostPreview st eid pvRef fd body = do
  let actionStr = extractJsonString "action" body
  let src       = extractJsonString "source" body
  let target    = extractJsonString "target" body
  let relation  = extractJsonString "relation" body
  let weight    = extractJsonDouble "weight" body
  let operator  = extractJsonString "operator" body
  let evidence  = extractJsonString "evidence" body
  let edgeId    = extractJsonString "edge_id" body
  let memberIds = extractJsonStringArray "member_ids" body
  let rationale = extractJsonString "rationale" body
  allMemes <- readIORef st.memes
  allEdges <- readIORef st.edges
  let memes = filter (\m => m.experimentId == eid) allMemes
  let edges = filter (\e => e.experimentId == eid) allEdges
  let beforeGeom = computeGeometry memes edges
  let action = case actionStr of
                 "edge_add"      => EdgeAdd
                 "edge_update"   => EdgeUpdate
                 "edge_remove"   => EdgeRemove
                 "memode_assert" => MemodeAssert
                 _               => EdgeAdd
  let beforeState = geometryJson beforeGeom
  let proposedEdges = case action of
        EdgeAdd    => MkEdge (MkId "preview") eid MemeNode src MemeNode target
                        (parseEdgeType relation) weight ""
                        (MkTimestamp "") (MkTimestamp "") :: edges
        EdgeRemove => filter (\e => show e.id /= edgeId) edges
        _          => edges
  let proposedGeom = computeGeometry memes proposedEdges
  let proposedState = geometryJson proposedGeom
  let pv = MkPreviewState action beforeState proposedState operator evidence
             src target (parseEdgeType relation) weight rationale edgeId memberIds
  writeIORef pvRef (Just pv)
  let graphPatch = case action of
        EdgeAdd    => jObj [ ("type", jStr "edge_add"),    ("source", jStr src),
                            ("target", jStr target),      ("relation", jStr relation),
                            ("weight", jNum weight) ]
        EdgeRemove => jObj [ ("type", jStr "edge_remove"), ("edge_id", jStr edgeId) ]
        EdgeUpdate => jObj [ ("type", jStr "edge_update"), ("edge_id", jStr edgeId),
                            ("relation", jStr relation),  ("weight", jNum weight) ]
        MemodeAssert => jObj [ ("type", jStr "memode_assert"),
                              ("member_ids", jArr (map jStr memberIds)) ]
        _ => jObj [("type", jStr "unknown")]
  let resp = jObj
        [ ("status",         jStr "previewed")
        , ("action",         jStr actionStr)
        , ("before_state",   beforeState)
        , ("proposed_state", proposedState)
        , ("compare_selection", jObj
             [ ("before_edge_count", jNat (length edges))
             , ("proposed_edge_count", jNat (length proposedEdges))
             , ("before_density",  jNum beforeGeom.gdDensity)
             , ("proposed_density", jNum proposedGeom.gdDensity)
             ])
        , ("preview_graph_patch", graphPatch)
        ]
  primIO (prim__httpSendResponse fd "application/json" resp)

handlePostCommit : StoreState -> ExperimentId -> IORef (Maybe PreviewState) -> Int -> String -> IO ()
handlePostCommit st eid pvRef fd body = do
  mpv <- readIORef pvRef
  case mpv of
    Nothing => send400 fd "no pending preview to commit"
    Just pv => do
      now <- nowTimestamp
      sessId <- getSessionId st eid
      committedId <- case pv.pvAction of
        EdgeAdd => do
          edge <- createEdge st eid MemeNode pv.pvSource MemeNode pv.pvTarget
                    pv.pvRelation pv.pvWeight now
          pure (show edge.id)
        EdgeUpdate => do
          allEdges <- readIORef st.edges
          case filter (\e => show e.id == pv.pvEdgeId) allEdges of
            [] => pure ""
            (old :: _) => do
              let upd = { weight := pv.pvWeight, edgeType := pv.pvRelation, updatedAt := now } old
              writeIORef st.edges (upd :: filter (\e => show e.id /= pv.pvEdgeId) allEdges)
              pure pv.pvEdgeId
        EdgeRemove => do
          allEdges <- readIORef st.edges
          writeIORef st.edges (filter (\e => show e.id /= pv.pvEdgeId) allEdges)
          pure pv.pvEdgeId
        MemodeAssert => do
          let mids = map (\s => MkId {a=MemeTag} s) pv.pvMemberIds
          memode <- upsertMemode st eid "memode:committed" "committed" Behavior mids now
          _ <- traverse (\mid =>
            createEdge st eid MemeNode (show mid) MemodeNode (show memode.id) MemberOf 1.0 now) mids
          pure (show memode.id)
        _ => pure ""
      let committedState = jObj [("committed_id", jStr committedId)]
      evt <- recordMeasurementEvent st eid sessId pv.pvAction Committed
               pv.pvOperator pv.pvEvidence pv.pvBeforeState pv.pvProposedState
               (show committedState) "" now
      recordTraceEvent st TraceObservatoryCommit Info
        ("commit: " ++ show pv.pvAction ++ " id=" ++ committedId) now
      writeIORef pvRef Nothing
      notifySSE (show pv.pvAction) committedId
      primIO (prim__httpSendResponse fd "application/json"
        (jObj [ ("status", jStr "committed"), ("event_id", jStr evt.id)
              , ("committed_id", jStr committedId), ("action", jStr (show pv.pvAction)) ]))

handlePostRevert : StoreState -> ExperimentId -> Int -> String -> String -> IO ()
handlePostRevert st eid fd eventIdStr body = do
  now <- nowTimestamp
  sessId <- getSessionId st eid
  result <- revertMeasurementEvent st eid sessId eventIdStr now
  case result of
    Nothing => send404 fd ("/api/revert/" ++ eventIdStr)
    Just revEvt => do
      recordTraceEvent st TraceObservatoryRevert Info ("revert: " ++ eventIdStr) now
      notifySSE "revert" eventIdStr
      primIO (prim__httpSendResponse fd "application/json"
        (jObj [ ("status", jStr "reverted"), ("event_id", jStr revEvt.id)
              , ("reverted", jStr eventIdStr) ]))

------------------------------------------------------------------------
-- POST route dispatcher
------------------------------------------------------------------------

servePostRoute : StoreState -> ExperimentId -> IORef (Maybe PreviewState) -> Int -> String -> String -> IO ()
servePostRoute st eid pvRef fd "/api/edges" body = handlePostEdges st eid fd body
servePostRoute st eid pvRef fd "/api/memodes/assert" body = handlePostMemodeAssert st eid fd body
servePostRoute st eid pvRef fd "/api/tanakh-run" body = do
  let text = extractJsonString "text" body
  if text == ""
    then send400 fd "text field required"
    else do let a = analyzeHebrew text
            let cr = crossReference text
            let resp = jObj
                  [ ("input_text",    jStr text)
                  , ("stripped_text", jStr a.strippedText)
                  , ("letter_count", jNat a.letterCount)
                  , ("gematria_standard", show a.gematriaValue)
                  , ("gematria_gadol",    show cr.crGadol)
                  , ("gematria_katan",    show cr.crKatan)
                  , ("gematria_ordinal",  show cr.crOrdinal)
                  , ("roshei_teivot",     jStr a.rosheiResult)
                  , ("sofei_teivot",      jStr a.sofeiResult)
                  , ("atbash",            jStr a.atBashResult)
                  ]
            primIO (prim__httpSendResponse fd "application/json" resp)
servePostRoute st eid pvRef fd "/api/preview" body = handlePostPreview st eid pvRef fd body
servePostRoute st eid pvRef fd "/api/commit" body = handlePostCommit st eid pvRef fd body
servePostRoute st eid pvRef fd path body =
  if isPrefixOf "/api/edges/" path && isSuffixOf "/update" path
    then do let stripped = substr 11 (length path) path
            let edgeId = pack (takeWhile (\c => c /= '/') (unpack stripped))
            handlePostEdgeUpdate st eid fd edgeId body
    else if isPrefixOf "/api/edges/" path && isSuffixOf "/remove" path
    then do let stripped = substr 11 (length path) path
            let edgeId = pack (takeWhile (\c => c /= '/') (unpack stripped))
            handlePostEdgeRemove st eid fd edgeId body
    else if isPrefixOf "/api/revert/" path
    then do let eventId = substr 12 (length path) path
            handlePostRevert st eid fd eventId body
    else send404 fd path

------------------------------------------------------------------------
-- Unified route dispatcher
------------------------------------------------------------------------

serveRoute : StoreState -> ExperimentId -> IORef (Maybe PreviewState) -> Int -> String -> IO ()
serveRoute st eid pvRef fd path = do
  method <- primIO (prim__httpGetMethod fd)
  case method of
    "OPTIONS" => sendOptions fd
    "POST"    => do
      contentLen <- primIO (prim__httpGetContentLength fd)
      body <- primIO (prim__httpReadBody fd contentLen)
      servePostRoute st eid pvRef fd path body
    _         => serveGetRoute st eid fd path

------------------------------------------------------------------------
-- Server loop
------------------------------------------------------------------------

partial
acceptLoop : StoreState -> ExperimentId -> IORef (Maybe PreviewState) -> Int -> IO ()
acceptLoop st eid pvRef serverFd = do
  clientFd <- primIO (prim__httpAccept serverFd)
  if clientFd < 0
    then putStrLn "Observatory: accept failed, stopping."
    else do path <- primIO (prim__httpReadRequest clientFd)
            if length path > 0
              then serveRoute st eid pvRef clientFd path
              else pure ()
            primIO (prim__httpClose clientFd)
            acceptLoop st eid pvRef serverFd

export
partial
runObservatory : Int -> StoreState -> ExperimentId -> IO ()
runObservatory port st eid = do
  pvRef <- newIORef Nothing
  serverFd <- primIO (prim__httpStart port)
  if serverFd < 0
    then putStrLn ("Observatory: failed to start on port " ++ show port)
    else do
      putStrLn ("Observatory running at http://localhost:" ++ show port)
      putStrLn "Endpoints: GET read, POST mutate, SSE /api/events"
      putStrLn "Press Ctrl+C to stop."
      acceptLoop st eid pvRef serverFd
      primIO (prim__httpStop serverFd)
