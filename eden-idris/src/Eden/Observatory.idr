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
-- Turn trajectory projection (basin overlay)
------------------------------------------------------------------------

record TurnOverlay where
  constructor MkTurnOverlay
  toTurnId         : String
  toTurnIndex      : Nat
  toX              : Double
  toY              : Double
  toActiveSetSize  : Nat
  toBudgetPressure : Double

computeTurnTrajectory : List Turn -> List ActiveSetEntry -> List TurnMetadata -> List TurnOverlay
computeTurnTrajectory turns asets metas =
  let maxIdx = foldl (\mx, t => max mx t.turnIndex) 0 turns
      normFactor = if maxIdx > 0 then cast {to=Double} maxIdx else 1.0
  in map (\t =>
    let tidStr = show t.id
        asSize = length (filter (\a => show a.turnId == tidStr) asets)
        pressure = case find (\m => show m.turnId == tidStr) metas of
                     Just md => case parseDouble md.budgetPressure of
                                  Just d  => d
                                  Nothing => 0.0
                     Nothing => 0.0
        nx = cast {to=Double} t.turnIndex / normFactor
    in MkTurnOverlay tidStr t.turnIndex nx pressure asSize pressure
  ) turns

turnOverlayJson : TurnOverlay -> String
turnOverlayJson to2 = jObj
  [ ("turn_id",          jStr to2.toTurnId)
  , ("turn_index",       jNat to2.toTurnIndex)
  , ("x",               jNum to2.toX)
  , ("y",               jNum to2.toY)
  , ("active_set_size",  jNat to2.toActiveSetSize)
  , ("budget_pressure",  jNum to2.toBudgetPressure)
  ]

basinWithTrajectoryJson : List Basin -> List TurnOverlay -> Nat -> Nat -> String
basinWithTrajectoryJson basins trajectory sourceTurnCount filteredTurnCount =
  jObj
    [ ("basins",     jArr (map basinJson basins))
    , ("trajectory", jArr (map turnOverlayJson trajectory))
    , ("projection_metadata", jObj
        [ ("projection_method",    jStr "turn_index_vs_pressure")
        , ("source_turn_count",    jNat sourceTurnCount)
        , ("filtered_turn_count",  jNat filteredTurnCount)
        ])
    ]

------------------------------------------------------------------------
-- Geometry diagnostics (pure computation)
------------------------------------------------------------------------

record NodeCoord where
  constructor MkNodeCoord
  ncNodeId : String
  ncX      : Double
  ncY      : Double

record GeometryDiagnostics where
  constructor MkGeometryDiagnostics
  gdNodeCount           : Nat
  gdEdgeCount           : Nat
  gdDensity             : Double
  gdAverageDegree       : Double
  gdConnectedComponents : Nat
  gdDiameterEstimate    : Nat
  gdClusteringCoeff     : Double
  gdCircularity         : Double
  gdLinearity           : Double
  gdCommunityCount      : Nat
  gdTriadicClosure      : Double
  gdMirrorSymmetry      : Double
  gdProjection          : List NodeCoord

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

||| Compute node degree (undirected) for a given node ID.
nodeDegree : String -> List Edge -> Nat
nodeDegree nid edges =
  length (filter (\e => e.srcId == nid || e.dstId == nid) edges)

||| Simple pseudo-random number from seed in [0, 1).
pseudoRand : Nat -> Double
pseudoRand seed =
  let s1 : Integer
      s1 = cast seed * 1103515245 + 12345
      masked = mod s1 65536
  in cast {to=Double} masked / 65536.0

||| Fruchterman-Reingold-style force-directed layout approximation.
forceLayout : List String -> List Edge -> List NodeCoord
forceLayout nodeIds edges =
  let initCoords = initPos nodeIds 0
      final = iterateLayout 10 1.0 initCoords
  in map (\t => MkNodeCoord (fst t) (fst (snd t)) (snd (snd t))) final
  where
    initPos : List String -> Nat -> List (String, Double, Double)
    initPos [] _ = []
    initPos (nid :: rest) idx =
      let x = pseudoRand (idx * 7 + 3) * 2.0 - 1.0
          y = pseudoRand (idx * 13 + 7) * 2.0 - 1.0
      in (nid, x, y) :: initPos rest (idx + 1)

    lookupPos : String -> List (String, Double, Double) -> (Double, Double)
    lookupPos _ [] = (0.0, 0.0)
    lookupPos nid ((n2, x, y) :: rest) =
      if nid == n2 then (x, y) else lookupPos nid rest

    clampD : Double -> Double -> Double -> Double
    clampD lo hi v = if v < lo then lo else if v > hi then hi else v

    repelForce : String -> Double -> Double -> List (String, Double, Double) -> Double -> Double -> (Double, Double)
    repelForce nid px py [] accX accY = (accX, accY)
    repelForce nid px py ((oid, ox, oy) :: rest) accX accY =
      if oid == nid then repelForce nid px py rest accX accY
      else
        let dx = px - ox
            dy = py - oy
            dist = sqrt (dx * dx + dy * dy) + 0.001
            force = 0.5 / (dist * dist)
        in repelForce nid px py rest (accX + dx / dist * force) (accY + dy / dist * force)

    attractForce : String -> Double -> Double -> List (String, Double, Double) -> List Edge -> Double -> Double -> (Double, Double)
    attractForce nid px py coords [] accX accY = (accX, accY)
    attractForce nid px py coords (e :: rest) accX accY =
      let other = if e.srcId == nid then Just e.dstId
                  else if e.dstId == nid then Just e.srcId
                  else Nothing
      in case other of
           Nothing => attractForce nid px py coords rest accX accY
           Just oid =>
             let opos = lookupPos oid coords
                 ox2 = fst opos
                 oy2 = snd opos
                 dx = ox2 - px
                 dy = oy2 - py
                 dist = sqrt (dx * dx + dy * dy) + 0.001
                 force = dist * 0.1
             in attractForce nid px py coords rest (accX + dx / dist * force) (accY + dy / dist * force)

    computeDisp : String -> List (String, Double, Double) -> List Edge -> Double -> (String, Double, Double)
    computeDisp nid coords es temp =
      let posResult = lookupPos nid coords
          px = fst posResult
          py = snd posResult
          repResult = repelForce nid px py coords 0.0 0.0
          rx = fst repResult
          ry = snd repResult
          atResult = attractForce nid px py coords es 0.0 0.0
          atx = fst atResult
          aty = snd atResult
          totalX = rx + atx
          totalY = ry + aty
          mag = sqrt (totalX * totalX + totalY * totalY) + 0.001
          dx2 = totalX / mag * min mag temp
          dy2 = totalY / mag * min mag temp
      in (nid, clampD (-5.0) 5.0 (px + dx2), clampD (-5.0) 5.0 (py + dy2))

    applyForces : List (String, Double, Double) -> List Edge -> Double -> List (String, Double, Double)
    applyForces coords es temp = map (\t => computeDisp (fst t) coords es temp) coords

    iterateLayout : Nat -> Double -> List (String, Double, Double) -> List (String, Double, Double)
    iterateLayout Z _ coords = coords
    iterateLayout (S k) temp coords =
      let newCoords = applyForces coords edges temp
      in iterateLayout k (temp * 0.9) newCoords

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
      -- Circularity: fraction of nodes with degree >= 2
      nodeIds = map (\m2 => show m2.id) memes
      degrees = map (\nid => nodeDegree nid edges) nodeIds
      circCount = length (filter (\d => d >= 2) degrees)
      circularity = if n > 0 then cast circCount / cast n else 0.0
      -- Linearity: fraction of nodes with degree <= 2
      linCount = length (filter (\d => d <= 2) degrees)
      linearity = if n > 0 then cast linCount / cast n else 0.0
      -- Community count = connected components
      communityCount = components
      -- Triadic closure: closed triangles / (closed + open triads)
      closedTriads = foldl (\acc, nid =>
        let nbrs = nub (mapMaybe (\e =>
              if e.srcId == nid then Just e.dstId
              else if e.dstId == nid then Just e.srcId
              else Nothing) edges)
            pairs = concatMap (\u => map (\v => (u, v)) (filter (\v => v > u) nbrs)) nbrs
            closed = length (filter (\p =>
              any (\e => (e.srcId == fst p && e.dstId == snd p) ||
                         (e.srcId == snd p && e.dstId == fst p)) edges) pairs)
        in acc + closed) 0 nodeIds
      totalTriads = foldl (\acc, nid =>
        let nbrs = nub (mapMaybe (\e =>
              if e.srcId == nid then Just e.dstId
              else if e.dstId == nid then Just e.srcId
              else Nothing) edges)
            k = length nbrs
            pairInt : Integer
            pairInt = if k >= 2 then (cast k * (cast k - 1)) `div` 2 else 0
            pairs = cast {to=Nat} pairInt
        in acc + pairs) 0 nodeIds
      triadicClosure = if totalTriads > 0
                       then cast closedTriads / cast totalTriads
                       else 0.0
      -- Mirror symmetry: compare sorted degree sequence to its reverse
      sortedDegs = sortBy compare degrees
      revDegs = reverse sortedDegs
      matchCount = length (filter (\p => fst p == snd p) (zip sortedDegs revDegs))
      mirrorSym = if n > 0 then cast matchCount / cast n else 1.0
      -- Projection coordinates via force-directed layout
      projection = forceLayout nodeIds edges
  in MkGeometryDiagnostics n m density avgDeg components diamEst avgClust
       circularity linearity communityCount triadicClosure mirrorSym projection

------------------------------------------------------------------------
-- Ablation computation (§4.3)
------------------------------------------------------------------------

||| Result of a single ablation run.
record AblationResult where
  constructor MkAblationResult
  arAblationType   : String    -- "mask_co_occurs" | "remove_dominant_community" | "subgraph_compare"
  arDetail         : String    -- human-readable explanation
  arBeforeScores   : GeometryDiagnostics
  arAfterScores    : GeometryDiagnostics
  arPersistence    : Double    -- 0..1, higher = property survives ablation

||| Persistence score: how much of the geometry survives the ablation.
||| Compares key metrics (clustering, density, circularity, triadic closure)
||| between before and after, returning the average ratio.
persistenceScore : GeometryDiagnostics -> GeometryDiagnostics -> Double
persistenceScore before after =
  let ratios = [ safeRatio after.gdClusteringCoeff before.gdClusteringCoeff
               , safeRatio after.gdDensity         before.gdDensity
               , safeRatio after.gdCircularity      before.gdCircularity
               , safeRatio after.gdTriadicClosure   before.gdTriadicClosure
               ]
      sum = foldl (+) 0.0 ratios
  in sum / 4.0
  where
    safeRatio : Double -> Double -> Double
    safeRatio _ 0.0 = 1.0   -- if before was 0, property trivially persists
    safeRatio a b   = min 1.0 (a / b)

||| Compute ablation by masking CO_OCCURS_WITH edges.
ablationMaskCoOccurs : List Meme -> List Edge -> AblationResult
ablationMaskCoOccurs memes edges =
  let before = computeGeometry memes edges
      masked = filter (\e => e.edgeType /= CoOccursWith) edges
      after  = computeGeometry memes masked
      detail = "Masked " ++ show (length edges `minus` length masked)
            ++ " CO_OCCURS_WITH edges (" ++ show (length masked) ++ " remaining)"
  in MkAblationResult "mask_co_occurs" detail before after (persistenceScore before after)

||| Find the dominant community (largest connected component) and remove it.
ablationRemoveDominantCommunity : List Meme -> List Edge -> AblationResult
ablationRemoveDominantCommunity memes edges =
  let before   = computeGeometry memes edges
      nodeIds  = map (\m => show m.id) memes
      -- BFS to find connected components
      comps    = findComponents nodeIds edges [] []
      -- Find largest component
      largest  = foldl (\best, c => if length c > length best then c else best) [] comps
      -- Remove memes in dominant component
      filtMemes = filter (\m => not (any (== show m.id) largest)) memes
      filtEdges = filter (\e => not (any (== e.srcId) largest) && not (any (== e.dstId) largest)) edges
      after    = computeGeometry filtMemes filtEdges
      detail   = "Removed dominant community (" ++ show (length largest)
              ++ " nodes), " ++ show (length filtMemes) ++ " nodes remaining"
  in MkAblationResult "remove_dominant_community" detail before after (persistenceScore before after)
  where
    bfsNeighbors : String -> List Edge -> List String
    bfsNeighbors nid es =
      Prelude.List.(++) (map (.dstId) (filter (\e => e.srcId == nid) es))
                        (map (.srcId) (filter (\e => e.dstId == nid) es))
    bfs : List String -> List String -> List Edge -> List String
    bfs [] visited _ = visited
    bfs (q :: qs) visited es =
      let nbrs = filter (\n => not (any (== n) visited)) (bfsNeighbors q es)
      in bfs (Prelude.List.(++) qs nbrs) (Prelude.List.(++) visited nbrs) es
    findComponents : List String -> List Edge -> List String -> List (List String) -> List (List String)
    findComponents [] _ _ acc = acc
    findComponents (n :: ns) es visited acc =
      if any (== n) visited
        then findComponents ns es visited acc
        else let comp = bfs [n] [n] es
                 visited' = Prelude.List.(++) visited comp
             in findComponents ns es visited' (comp :: acc)

||| Compare a local subgraph (nodes with degree >= 2) against the full graph.
ablationSubgraphCompare : List Meme -> List Edge -> AblationResult
ablationSubgraphCompare memes edges =
  let before   = computeGeometry memes edges
      nodeIds  = map (\m => show m.id) memes
      -- Select nodes with degree >= 2 as the "core" subgraph
      coreIds  = filter (\nid => nodeDegree nid edges >= 2) nodeIds
      coreMemes = filter (\m => any (== show m.id) coreIds) memes
      coreEdges = filter (\e => any (== e.srcId) coreIds && any (== e.dstId) coreIds) edges
      after    = computeGeometry coreMemes coreEdges
      detail   = "Core subgraph (degree >= 2): " ++ show (length coreMemes)
              ++ " of " ++ show (length memes) ++ " nodes"
  in MkAblationResult "subgraph_compare" detail before after (persistenceScore before after)

||| Run all three ablation types and return results.
runAllAblations : List Meme -> List Edge -> List AblationResult
runAllAblations memes edges =
  [ ablationMaskCoOccurs memes edges
  , ablationRemoveDominantCommunity memes edges
  , ablationSubgraphCompare memes edges
  ]

||| Serialize an AblationResult to JSON.
ablationResultJson : AblationResult -> String
ablationResultJson ar = jObj
  [ ("ablation_type", jStr ar.arAblationType)
  , ("detail",        jStr ar.arDetail)
  , ("persistence",   jNum ar.arPersistence)
  , ("before_scores", jObj
      [ ("clustering_coefficient", jNum ar.arBeforeScores.gdClusteringCoeff)
      , ("density",                jNum ar.arBeforeScores.gdDensity)
      , ("circularity",            jNum ar.arBeforeScores.gdCircularity)
      , ("triadic_closure",        jNum ar.arBeforeScores.gdTriadicClosure)
      , ("node_count",             jNat ar.arBeforeScores.gdNodeCount)
      , ("edge_count",             jNat ar.arBeforeScores.gdEdgeCount)
      ])
  , ("after_scores", jObj
      [ ("clustering_coefficient", jNum ar.arAfterScores.gdClusteringCoeff)
      , ("density",                jNum ar.arAfterScores.gdDensity)
      , ("circularity",            jNum ar.arAfterScores.gdCircularity)
      , ("triadic_closure",        jNum ar.arAfterScores.gdTriadicClosure)
      , ("node_count",             jNat ar.arAfterScores.gdNodeCount)
      , ("edge_count",             jNat ar.arAfterScores.gdEdgeCount)
      ])
  , ("evidence_label", jStr "DERIVED")
  ]

sessionAsets : Maybe Session -> List ActiveSetEntry -> List ActiveSetEntry
sessionAsets Nothing  _     = []
sessionAsets (Just s) asets = filter (\a => a.sessionId == s.id) asets

computeGeometrySliced : String -> List Meme -> List Edge
                     -> List Session -> List ActiveSetEntry
                     -> GeometryDiagnostics
computeGeometrySliced "current_session" memes edges sessions asets =
  let latestSess = head' (sortBy (\a, b => compare (show b.createdAt) (show a.createdAt)) sessions)
      filtAsets = sessionAsets latestSess asets
      activeNodeIds = nub (map (\a => a.nodeId) filtAsets)
      filteredMemes = filter (\m => any (== show m.id) activeNodeIds) memes
      filteredEdges = filter (\e =>
        any (== e.srcId) activeNodeIds && any (== e.dstId) activeNodeIds) edges
  in computeGeometry filteredMemes filteredEdges
computeGeometrySliced _ memes edges _ _ = computeGeometry memes edges

nodeCoordJson : NodeCoord -> String
nodeCoordJson nc = jObj
  [ ("node_id", jStr nc.ncNodeId)
  , ("x",       jNum nc.ncX)
  , ("y",       jNum nc.ncY)
  ]

geometryJson : GeometryDiagnostics -> String
geometryJson g = jObj
  [ ("node_count",           jNat g.gdNodeCount)
  , ("edge_count",           jNat g.gdEdgeCount)
  , ("density",              jNum g.gdDensity)
  , ("average_degree",       jNum g.gdAverageDegree)
  , ("connected_components", jNat g.gdConnectedComponents)
  , ("diameter_estimate",    jNat g.gdDiameterEstimate)
  , ("clustering_coefficient", jNum g.gdClusteringCoeff)
  , ("circularity",          jNum g.gdCircularity)
  , ("linearity",            jNum g.gdLinearity)
  , ("community_count",      jNat g.gdCommunityCount)
  , ("triadic_closure",      jNum g.gdTriadicClosure)
  , ("mirror_symmetry",      jNum g.gdMirrorSymmetry)
  , ("projection",           jArr (map nodeCoordJson g.gdProjection))
  , ("evidence_labels", jObj
      [ ("node_count",             jStr "OBSERVED")
      , ("edge_count",             jStr "OBSERVED")
      , ("density",                jStr "DERIVED")
      , ("average_degree",         jStr "DERIVED")
      , ("connected_components",   jStr "DERIVED")
      , ("clustering_coefficient", jStr "DERIVED")
      , ("circularity",            jStr "DERIVED")
      , ("linearity",              jStr "DERIVED")
      , ("community_count",        jStr "DERIVED")
      , ("triadic_closure",        jStr "DERIVED")
      , ("mirror_symmetry",        jStr "DERIVED")
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
  , "  <li><a href=\"/api/ablations\">/api/ablations</a></li>"
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
  allTurns <- readIORef st.turns
  allAsets <- readIORef st.activeSetSnaps
  allMeta  <- readIORef st.turnMetadata
  let memes = filter (\m => m.experimentId == eid) allMemes
  let turns = filter (\t => t.experimentId == eid) allTurns
  let asets = filter (\a => a.experimentId == eid) allAsets
  let basins = computeBasins memes
  let trajectory = computeTurnTrajectory turns asets allMeta
  let turnCount = length turns
  primIO (prim__httpSendResponse fd "application/json"
    (basinWithTrajectoryJson basins trajectory turnCount turnCount))
serveGetRoute st eid fd "/api/geometry" = do
  allMemes <- readIORef st.memes
  allEdges <- readIORef st.edges
  let memes = filter (\m => m.experimentId == eid) allMemes
  let edges = filter (\e => e.experimentId == eid) allEdges
  primIO (prim__httpSendResponse fd "application/json" (geometryJson (computeGeometry memes edges)))
serveGetRoute st eid fd "/api/ablations" = do
  allMemes <- readIORef st.memes
  allEdges <- readIORef st.edges
  let memes = filter (\m => m.experimentId == eid) allMemes
  let edges = filter (\e => e.experimentId == eid) allEdges
  let results = runAllAblations memes edges
  primIO (prim__httpSendResponse fd "application/json"
    (jObj [ ("ablation_results", jArr (map ablationResultJson results))
          , ("experiment_id",    jStr (show eid))
          ]))
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
        "/payload" => do
          body <- exportGraphJson st scopedEid
          primIO (prim__httpSendResponse fd "application/json" body)
        "/overview" => do
          allMemes <- readIORef st.memes
          allEdges <- readIORef st.edges
          allMemodes <- readIORef st.memodes
          allTurns <- readIORef st.turns
          allFb <- readIORef st.feedbackEvents
          allSess <- readIORef st.sessions
          let memes = filter (\m => m.experimentId == scopedEid) allMemes
          let edges = filter (\e => e.experimentId == scopedEid) allEdges
          let memodes = filter (\m => m.experimentId == scopedEid) allMemodes
          let turns = filter (\t => t.experimentId == scopedEid) allTurns
          let fbs = filter (\fb => fb.frExperimentId == scopedEid) allFb
          let sessions = filter (\s => s.experimentId == scopedEid) allSess
          let recentSess = take 5 (sortBy (\a, b => compare (show b.createdAt) (show a.createdAt)) sessions)
          let body = jObj
                [ ("experiment_id", jStr expIdStr)
                , ("counts", jObj
                    [ ("meme_count",     jNat (length memes))
                    , ("edge_count",     jNat (length edges))
                    , ("memode_count",   jNat (length memodes))
                    , ("turn_count",     jNat (length turns))
                    , ("feedback_count", jNat (length fbs))
                    ])
                , ("recent_sessions", jArr (map sessionJson recentSess))
                ]
          primIO (prim__httpSendResponse fd "application/json" body)
        "/measurement-events" => do
          allMeas <- readIORef st.measurements
          let meas = filter (\e => e.experimentId == scopedEid) allMeas
          primIO (prim__httpSendResponse fd "application/json" (jArr (map measurementJson meas)))
        "/basin" => do
          allMemes <- readIORef st.memes
          allTurns <- readIORef st.turns
          allAsets <- readIORef st.activeSetSnaps
          allMeta  <- readIORef st.turnMetadata
          let memes = filter (\m => m.experimentId == scopedEid) allMemes
          let turns = filter (\t => t.experimentId == scopedEid) allTurns
          let asets = filter (\a => a.experimentId == scopedEid) allAsets
          let basins = computeBasins memes
          let trajectory = computeTurnTrajectory turns asets allMeta
          let turnCount = length turns
          primIO (prim__httpSendResponse fd "application/json"
            (basinWithTrajectoryJson basins trajectory turnCount turnCount))
        "/geometry" => do
          allMemes <- readIORef st.memes
          allEdges <- readIORef st.edges
          let memes = filter (\m => m.experimentId == scopedEid) allMemes
          let edges = filter (\e => e.experimentId == scopedEid) allEdges
          primIO (prim__httpSendResponse fd "application/json" (geometryJson (computeGeometry memes edges)))
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
                 "edge_add"                  => EdgeAdd
                 "edge_update"               => EdgeUpdate
                 "edge_remove"               => EdgeRemove
                 "memode_assert"             => MemodeAssert
                 "memode_update_membership"  => MemodeUpdateMembership
                 "node_edit"                 => NodeEdit
                 "motif_annotation"          => MotifAnnotation
                 "geometry_measurement_run"  => GeometryMeasurementRun
                 "ablation_measurement_run"  => AblationMeasurementRun
                 "measurement_revert"        => MeasurementRevert
                 _                           => EdgeAdd
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
        MemodeUpdateMembership => jObj [ ("type", jStr "memode_update_membership"),
                              ("member_ids", jArr (map jStr memberIds)) ]
        NodeEdit => jObj [ ("type", jStr "node_edit"),
                          ("source", jStr src) ]
        MotifAnnotation => jObj [ ("type", jStr "motif_annotation") ]
        GeometryMeasurementRun => jObj [ ("type", jStr "geometry_measurement_run") ]
        AblationMeasurementRun => jObj [ ("type", jStr "ablation_measurement_run") ]
        MeasurementRevert => jObj [ ("type", jStr "measurement_revert"),
                                   ("edge_id", jStr edgeId) ]
  -- For ablation runs, compute and include ablation results
  let ablationField = case action of
        AblationMeasurementRun =>
          let ablationType = extractJsonString "ablation_type" body
              results = case ablationType of
                "mask_co_occurs"            => [ablationMaskCoOccurs memes edges]
                "remove_dominant_community" => [ablationRemoveDominantCommunity memes edges]
                "subgraph_compare"          => [ablationSubgraphCompare memes edges]
                _                           => runAllAblations memes edges
          in [ ("ablation_results", jArr (map ablationResultJson results)) ]
        _ => []
  let resp = jObj (Prelude.List.(++)
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
        ] ablationField)
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
        MemodeUpdateMembership => do
          recordTraceEvent st TraceObservatoryCommit Info
            ("memode_update_membership: members=" ++ show pv.pvMemberIds) now
          pure (case pv.pvMemberIds of
                  (x :: _) => x
                  []       => "memode-update")
        NodeEdit => do
          allMemes <- readIORef st.memes
          let memeIdStr = pv.pvSource
          let newLabel = pv.pvRationale
          case filter (\m => show m.id == memeIdStr && m.experimentId == eid) allMemes of
            [] => do
              recordTraceEvent st TraceObservatoryCommit Info
                ("node_edit: meme not found " ++ memeIdStr) now
              pure memeIdStr
            (old :: _) => do
              let upd = { label := (if newLabel /= "" then newLabel else old.label)
                        , updatedAt := now } old
              let others = filter (\m => show m.id /= memeIdStr) allMemes
              writeIORef st.memes (upd :: others)
              recordTraceEvent st TraceObservatoryCommit Info
                ("node_edit: updated label for " ++ memeIdStr) now
              pure memeIdStr
        MotifAnnotation => do
          recordTraceEvent st TraceObservatoryCommit Info
            ("motif_annotation: " ++ pv.pvEvidence) now
          pure "motif-annotation"
        GeometryMeasurementRun => do
          recordTraceEvent st TraceObservatoryCommit Info
            "geometry_measurement_run: computed" now
          pure "geometry-run"
        AblationMeasurementRun => do
          -- Run all ablations and record the aggregate persistence
          allMemes <- readIORef st.memes
          allEdges2 <- readIORef st.edges
          let expMemes = filter (\m => m.experimentId == eid) allMemes
              expEdges = filter (\e => e.experimentId == eid) allEdges2
              results = runAllAblations expMemes expEdges
              avgPersist = case results of
                [] => 0.0
                rs => foldl (\s, r => s + r.arPersistence) 0.0 rs / cast (length rs)
          recordTraceEvent st TraceObservatoryCommit Info
            ("ablation_measurement_run: persistence=" ++ show avgPersist
              ++ " ablations=" ++ show (length results)) now
          pure "ablation-run"
        MeasurementRevert => do
          recordTraceEvent st TraceObservatoryCommit Info
            ("measurement_revert: " ++ pv.pvEdgeId) now
          pure pv.pvEdgeId
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
