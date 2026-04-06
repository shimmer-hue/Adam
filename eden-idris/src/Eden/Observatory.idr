||| Minimal read-only HTTP observatory server for EDEN graph inspection.
|||
||| Serves the graph store as JSON over HTTP, matching the observatory
||| payload contract where possible. Single-threaded blocking server
||| using C FFI sockets.
module Eden.Observatory

import Data.IORef
import Data.List
import Data.String
import Eden.Types
import Eden.Config
import Eden.Regard
import Eden.Store.InMemory
import Eden.Export
import Eden.OntologyProjection

------------------------------------------------------------------------
-- C FFI declarations
------------------------------------------------------------------------

%foreign "C:eden_http_start,eden_http"
prim__httpStart : Int -> PrimIO Int

%foreign "C:eden_http_accept,eden_http"
prim__httpAccept : Int -> PrimIO Int

%foreign "C:eden_http_read_request,eden_http"
prim__httpReadRequest : Int -> PrimIO String

%foreign "C:eden_http_send_response,eden_http"
prim__httpSendResponse : Int -> String -> String -> PrimIO ()

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
  let ns = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau 0.0
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

------------------------------------------------------------------------
-- Route handling
------------------------------------------------------------------------

||| Send a 404 response.
send404 : Int -> String -> IO ()
send404 fd path = do
  let body = jObj [("error", jStr "not found"), ("path", jStr path)]
  primIO (prim__httpSendResponse fd "application/json" body)

||| Send a CORS preflight response for OPTIONS.
sendOptions : Int -> IO ()
sendOptions fd = do
  primIO (prim__httpSendResponse fd "text/plain" "")

||| The simple index HTML page.
indexHtml : String
indexHtml = unlines
  [ "<!DOCTYPE html>"
  , "<html><head><title>EDEN Observatory</title>"
  , "<style>"
  , "  body { font-family: monospace; background: #12080a; color: #ffd98a; padding: 2em; }"
  , "  a { color: #a890ff; }"
  , "  h1 { color: #ffae57; }"
  , "  li { margin: 0.3em 0; }"
  , "</style></head><body>"
  , "<h1>EDEN Observatory</h1>"
  , "<p>Read-only graph API. Available endpoints:</p>"
  , "<ul>"
  , "  <li><a href=\"/api/health\">/api/health</a> -- health check</li>"
  , "  <li><a href=\"/api/graph\">/api/graph</a> -- full graph export</li>"
  , "  <li><a href=\"/api/memes\">/api/memes</a> -- all memes</li>"
  , "  <li><a href=\"/api/edges\">/api/edges</a> -- all edges</li>"
  , "  <li><a href=\"/api/memodes\">/api/memodes</a> -- all memodes</li>"
  , "  <li><a href=\"/api/regard\">/api/regard</a> -- regard breakdown</li>"
  , "  <li><a href=\"/api/feedback\">/api/feedback</a> -- feedback events</li>"
  , "  <li><a href=\"/api/sessions\">/api/sessions</a> -- sessions</li>"
  , "  <li><a href=\"/api/turns\">/api/turns</a> -- recent turns</li>"
  , "</ul>"
  , "</body></html>"
  ]

||| Dispatch a route and send the response.
serveRoute : StoreState -> ExperimentId -> Int -> String -> IO ()
serveRoute st eid fd "OPTIONS" = sendOptions fd
serveRoute st eid fd "/" = primIO (prim__httpSendResponse fd "text/html; charset=utf-8" indexHtml)
serveRoute st eid fd "/index.html" = primIO (prim__httpSendResponse fd "text/html; charset=utf-8" indexHtml)
serveRoute st eid fd "/api/health" = do
  let body = jObj [("status", jStr "ok"), ("runtime", jStr "idris2-refc")]
  primIO (prim__httpSendResponse fd "application/json" body)
serveRoute st eid fd "/api/graph" = do
  body <- exportGraphJson st eid
  primIO (prim__httpSendResponse fd "application/json" body)
serveRoute st eid fd "/api/memes" = do
  allMemes <- readIORef st.memes
  let memes = filter (\m => m.experimentId == eid) allMemes
  primIO (prim__httpSendResponse fd "application/json" (jArr (map memeJson memes)))
serveRoute st eid fd "/api/edges" = do
  allEdges <- readIORef st.edges
  let edges = filter (\e => e.experimentId == eid) allEdges
  primIO (prim__httpSendResponse fd "application/json" (jArr (map edgeJson edges)))
serveRoute st eid fd "/api/memodes" = do
  allMemodes <- readIORef st.memodes
  let memodes = filter (\m => m.experimentId == eid) allMemodes
  primIO (prim__httpSendResponse fd "application/json" (jArr (map memodeJson memodes)))
serveRoute st eid fd "/api/regard" = do
  allMemes <- readIORef st.memes
  let memes = filter (\m => m.experimentId == eid) allMemes
  primIO (prim__httpSendResponse fd "application/json" (jArr (map regardJson memes)))
serveRoute st eid fd "/api/feedback" = do
  allFb <- readIORef st.feedbackEvents
  let fbs = filter (\fb => fb.frExperimentId == eid) allFb
  primIO (prim__httpSendResponse fd "application/json" (jArr (map feedbackJson fbs)))
serveRoute st eid fd "/api/sessions" = do
  allSess <- readIORef st.sessions
  let sessions = filter (\s => s.experimentId == eid) allSess
  primIO (prim__httpSendResponse fd "application/json" (jArr (map sessionJson sessions)))
serveRoute st eid fd "/api/turns" = do
  allTurns <- readIORef st.turns
  let turns = filter (\t => t.experimentId == eid) allTurns
  let sorted = sortBy (\a, b => compare b.turnIndex a.turnIndex) turns
  let recent = take 50 sorted
  primIO (prim__httpSendResponse fd "application/json" (jArr (map turnJson recent)))
serveRoute st eid fd path =
  if isPrefixOf "/api/memes/" path
    then do let memeIdStr = substr 11 (length path) path
            allMemes <- readIORef st.memes
            case filter (\m => show m.id == memeIdStr) allMemes of
              (m :: _) => primIO (prim__httpSendResponse fd "application/json" (memeJson m))
              []        => send404 fd path
    else send404 fd path

------------------------------------------------------------------------
-- Server loop
------------------------------------------------------------------------

||| Accept loop: blocks on each connection, handles request, repeats.
partial
acceptLoop : StoreState -> ExperimentId -> Int -> IO ()
acceptLoop st eid serverFd = do
  clientFd <- primIO (prim__httpAccept serverFd)
  if clientFd < 0
    then putStrLn "Observatory: accept failed, stopping."
    else do path <- primIO (prim__httpReadRequest clientFd)
            if length path > 0
              then serveRoute st eid clientFd path
              else pure ()
            primIO (prim__httpClose clientFd)
            acceptLoop st eid serverFd

||| Start the observatory HTTP server on the given port.
||| Blocks forever (or until accept fails).
export
partial
runObservatory : Int -> StoreState -> ExperimentId -> IO ()
runObservatory port st eid = do
  serverFd <- primIO (prim__httpStart port)
  if serverFd < 0
    then putStrLn ("Observatory: failed to start on port " ++ show port)
    else do
      putStrLn ("Observatory running at http://localhost:" ++ show port)
      putStrLn "Press Ctrl+C to stop."
      acceptLoop st eid serverFd
      primIO (prim__httpStop serverFd)
