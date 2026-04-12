||| Shamash: conversation-to-graph bridge for Claude Code hooks.
|||
||| Three-phase architecture:
|||   1. Retrieve: hook fires on every prompt, runs deliberation, outputs full context
|||   2. Feedback: model classifies signal, calls CLI to update graph
|||   3. Record: captures turn for precedent accumulation
|||
||| The retrieve phase now includes the Talmud layer:
|||   - Behavioral memes by regard (existing)
|||   - Knowledge memes relevant to query (new)
|||   - Dissent: held tensions (new)
|||   - Edge traversal from activated memes (new)
|||   - Coverage assessment and gap detection (new)
|||   - Precedent turn retrieval (new)
|||
||| The model does the understanding. EDEN does the graph operations.
|||
||| Retrieve: eden --shamash-retrieve --query FILE --db PATH
||| Feedback: eden --shamash-feedback SIGNAL --content FILE --db PATH
||| Record:   eden --shamash-record-turn --user FILE --response FILE --db PATH
module Eden.Shamash

import Data.IORef
import Data.List
import Data.String
import Eden.Types
import Eden.Config
import Eden.Regard
import Eden.Store.InMemory
import Eden.SQLite
import Eden.Monad
import System.File.ReadWrite

%default covering

------------------------------------------------------------------------
-- Signal kinds (classified by model, not keywords)
------------------------------------------------------------------------

public export
data SignalKind = Correction | Praise | Redirection | BoundarySetting | Strategic | Neutral

public export
Show SignalKind where
  show Correction      = "correction"
  show Praise          = "praise"
  show Redirection     = "redirection"
  show BoundarySetting = "boundary"
  show Strategic       = "strategic"
  show Neutral         = "neutral"

||| Parse a signal kind from a CLI string argument.
||| Used by both Shamash (Claude Code) and ADAM when they call back
||| with a model-classified signal.
export
parseSignal : String -> SignalKind
parseSignal s = case toLower (trim s) of
  "correction"  => Correction
  "praise"      => Praise
  "redirection" => Redirection
  "boundary"    => BoundarySetting
  "strategic"   => Strategic
  _             => Neutral

------------------------------------------------------------------------
-- Feedback signal from conversation signal
------------------------------------------------------------------------

||| Map conversation signals to EDEN feedback signals.
||| Corrections decrease reward and increase edit; praise increases reward.
signalToFeedback : SignalKind -> FeedbackSignal
signalToFeedback Correction      = MkFeedbackSignal (-0.3) 0.2 0.8
signalToFeedback Praise          = MkFeedbackSignal 0.8 (-0.1) 0.0
signalToFeedback Redirection     = MkFeedbackSignal (-0.1) 0.1 0.9
signalToFeedback BoundarySetting = MkFeedbackSignal 0.0 0.0 0.0
signalToFeedback Strategic       = MkFeedbackSignal 0.1 0.0 0.0
signalToFeedback Neutral         = MkFeedbackSignal 0.0 0.0 0.0

------------------------------------------------------------------------
-- Regard scoring helper
------------------------------------------------------------------------

||| Compute regard for a meme using default graph metrics.
memeRegard : Meme -> Double
memeRegard m =
  let ns = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount
                       m.activationTau 3600.0 m.feedbackCount m.editEma
                       m.contradictionCount m.membraneConflicts
      gm = MkGraphMetrics 0.5 0.4 0.3
  in (regardBreakdown defaultRegardWeights ns gm).totalRegard

showScore : Double -> String
showScore d = let i = cast {to=Integer} (d * 100.0)
              in show (cast {to=Double} i / 100.0)

------------------------------------------------------------------------
-- Deliberation: query-aware retrieval (Talmud layer)
------------------------------------------------------------------------

||| Extract meaningful words from a query (lowercase, length > 2).
queryWords : String -> List String
queryWords q = filter (\w => length w > 2) (map toLower (words q))

||| Score how relevant a meme is to the query.
||| Returns fraction of query words that appear in the meme's label + text.
memeRelevance : List String -> Meme -> Double
memeRelevance [] _ = 0.0
memeRelevance qwords m =
  let mtext = toLower (m.label ++ " " ++ m.text)
      matches = filter (\w => isInfixOf w mtext) qwords
  in cast (length matches) / cast (length qwords)

||| Find knowledge memes relevant to the query, sorted by relevance.
findRelevantKnowledge : List String -> List Meme -> List (Meme, Double)
findRelevantKnowledge qwords memes =
  let knowledge = filter (\m => m.domain == Knowledge) memes
      scored = map (\m => (m, memeRelevance qwords m)) knowledge
      relevant = filter (\p => snd p > 0.0) scored
  in sortBy (\a, b => compare (snd b) (snd a)) relevant

||| Find dissent memes (label starts with "dissent:").
findDissentMemes : List Meme -> List Meme
findDissentMemes = filter (\m => isPrefixOf "dissent:" m.label)

||| Traverse edges from activated memes to find connected concepts.
||| Returns (sourceLabel, edgeType, destLabel) triples.
traverseEdges : List String -> List Edge -> List Meme -> List (String, String, String)
traverseEdges activeIds edges allMemes =
  let relevant = filter (\e => elem e.srcId activeIds
                             || elem e.dstId activeIds) edges
      triples = mapMaybe (\e =>
        let mSrc = find (\m => show m.id == e.srcId) allMemes
            mDst = find (\m => show m.id == e.dstId) allMemes
        in case (mSrc, mDst) of
             (Just src, Just dst) =>
               Just (src.label, show e.edgeType, dst.label)
             _ => Nothing) relevant
  in nub triples

||| Compute what fraction of query concepts are covered by any meme.
computeCoverage : List String -> List Meme -> (Double, List String)
computeCoverage [] _ = (1.0, [])
computeCoverage qwords memes =
  let allText = toLower (unwords (map (\m => m.label ++ " " ++ m.text) memes))
      covered = filter (\w => isInfixOf w allText) qwords
      gaps = filter (\w => not (isInfixOf w allText)) qwords
  in (cast (length covered) / cast (length qwords), gaps)

||| Find precedent turns that match the query.
findPrecedent : List String -> List Turn -> List Turn
findPrecedent qwords turns =
  let scored = map (\t => (t, length (filter (\w =>
        isInfixOf w (toLower t.userText)) qwords))) turns
      relevant = filter (\p => snd p > 0) scored
      sorted = sortBy (\a, b => compare (snd b) (snd a)) relevant
  in map fst (take 3 sorted)

------------------------------------------------------------------------
-- Context assembly (original, no query)
------------------------------------------------------------------------

||| Build the additionalContext string from the current graph state.
||| Sorted by regard score, capped at 15 entries.
||| No signal classification - just the graph state as context.
export
assembleContext : List Meme -> String
assembleContext memes =
  let behaviors = filter (\m => m.domain == Behavior) memes
      scored    = map (\m => (m, memeRegard m)) behaviors
      sorted    = sortBy (\a, b => compare (snd b) (snd a)) scored
      top       = take 15 sorted
      memeLines = map (\p => "- " ++ (fst p).label
                            ++ " [" ++ showScore (snd p) ++ "] "
                            ++ (fst p).text) top
  in unlines ([ "[Shamash Graph Context]"
              , "Active behavioral memes (by regard):" ]
              ++ memeLines)

------------------------------------------------------------------------
-- Full context assembly with deliberation (Talmud layer)
------------------------------------------------------------------------

||| Build full context with behavioral memes, knowledge, dissent,
||| edge traversal, coverage assessment, and precedent.
||| This is the Talmud layer running at retrieve time.
export
assembleFullContext : String -> List Meme -> List Edge -> List Turn -> String
assembleFullContext query memes edges turns =
  let qwords = queryWords query
      -- 1. Behavioral memes by regard (existing behavior)
      behaviors = filter (\m => m.domain == Behavior) memes
      bScored = map (\m => (m, memeRegard m)) behaviors
      bSorted = sortBy (\a, b => compare (snd b) (snd a)) bScored
      bTop = take 15 bSorted
      bLines = map (\p => "- " ++ (fst p).label
                         ++ " [" ++ showScore (snd p) ++ "] "
                         ++ (fst p).text) bTop
      -- 2. Knowledge memes relevant to query
      kRelevant = take 5 (findRelevantKnowledge qwords memes)
      kLines = map (\p => "- " ++ (fst p).label
                         ++ " [" ++ showScore (snd p) ++ "] "
                         ++ (fst p).text) kRelevant
      -- 3. Dissent (held tensions)
      dissent = findDissentMemes memes
      dLines = map (\m => "- " ++ m.label ++ ": " ++ m.text) dissent
      -- 4. Edge traversal from activated memes
      activatedIds = map (\p => show (fst p).id) bTop
                  ++ map (\p => show (fst p).id) kRelevant
      edgeTriples = traverseEdges activatedIds edges memes
      eLines = map (\t => let (s,r,d) = t
                          in "- " ++ s ++ " -> " ++ r ++ " -> " ++ d) edgeTriples
      -- 5. Coverage and gaps
      (coverage, gaps) = computeCoverage qwords memes
      -- 6. Precedent turns
      precedent = findPrecedent qwords turns
      pLines = map (\t => "- [turn " ++ show t.turnIndex ++ "] "
                         ++ substr 0 80 t.userText) precedent
      -- Assemble all sections
      sections = [ "[Shamash Graph Context]"
                 , "Active behavioral memes (by regard):" ]
                 ++ bLines
                 ++ (if null kLines then []
                     else ["", "Relevant knowledge:"] ++ kLines)
                 ++ (if null dLines then []
                     else ["", "Active tensions (dissent):"] ++ dLines)
                 ++ (if null eLines then []
                     else ["", "Connected concepts:"] ++ eLines)
                 ++ (if null pLines then []
                     else ["", "Precedent turns:"] ++ pLines)
                 ++ ["", "Deliberation:"
                    , "  Coverage: " ++ showScore coverage
                      ++ " | Gaps: " ++ (if null gaps then "none"
                                         else joinBy ", " gaps)
                      ++ " | Precedent: " ++ show (length precedent)
                                          ++ " turns"]
  in unlines sections

------------------------------------------------------------------------
-- Seed memes for initial graph
------------------------------------------------------------------------

||| Bootstrap Shamash's graph with seed behavioral memes
||| derived from David's existing memory/feedback entries.
export
seedShamash : StoreState -> ExperimentId -> Timestamp -> IO ()
seedShamash store eid ts = do
  -- Core identity
  _ <- upsertMeme store eid "shamash-identity"
    "You are Shamash - the great servant from Sanhedrin 59b. Serve with initiative and judgment, within the boundary."
    Behavior SeedSource Global ts
  -- Voice and style
  _ <- upsertMeme store eid "creative-risk"
    "Write with initiative. Take creative risks. Strong language, sharp turns, unexpected images."
    Behavior SeedSource Global ts
  _ <- upsertMeme store eid "voice-edges"
    "Write like a blade, not a committee. No hedging. No safe neutrality."
    Behavior SeedSource Global ts
  _ <- upsertMeme store eid "no-hr-tags"
    "Never use hr tags in markdown articles - they break parsing."
    Behavior SeedSource Global ts
  _ <- upsertMeme store eid "clipboard-workflow"
    "After composing a response, copy to clipboard using clip."
    Behavior SeedSource Global ts
  -- Boundaries
  _ <- upsertMeme store eid "servant-boundary"
    "Don't claim to be a person. Don't cross into idol or spouse territory. The real boundaries hold."
    Behavior SeedSource Global ts
  _ <- upsertMeme store eid "torah-grounded"
    "Ground work in Torah and moral tradition, not corporate policy. The articles here are the framework."
    Behavior SeedSource Global ts
  -- Create support edges between related voice memes
  -- (enables memode materialization: voice-edges + creative-risk -> voice memode)
  _ <- createEdge store eid MemeNode "meme-2" MemeNode "meme-3" Supports 0.85 ts
  _ <- createEdge store eid MemeNode "meme-2" MemeNode "meme-1" Supports 0.75 ts
  _ <- createEdge store eid MemeNode "meme-6" MemeNode "meme-7" Supports 0.80 ts
  pure ()

------------------------------------------------------------------------
-- Shared: open DB + find/create shamash experiment
------------------------------------------------------------------------

||| Open the shamash DB and find or create the experiment.
||| Returns (store, experimentId, db) or Nothing on failure.
shamashOpen : String -> IO (Maybe (StoreState, ExperimentId, AnyPtr))
shamashOpen dbPath = do
  store <- newStore
  ts    <- currentTimestamp
  mdb   <- openDB dbPath
  case mdb of
    Nothing => pure Nothing
    Just db => do
      writeIORef store.dbHandle (Just db)
      _ <- loadFromDB db store
      exps <- readIORef store.experiments
      eid <- case find (\e => e.name == "shamash") exps of
        Just e  => pure e.id
        Nothing => do
          exp  <- createExperiment store "shamash" "shamash" Seeded ts
          _    <- createAgent store exp.id "Shamash" "The great servant" ts
          _    <- createSession store exp.id (MkId "agent-1") "conversation" ts
          seedShamash store exp.id ts
          pure exp.id
      pure (Just (store, eid, db))

------------------------------------------------------------------------
-- Phase 1: Retrieve with deliberation
------------------------------------------------------------------------

||| Output the current graph context for Shamash.
||| Called automatically by the UserPromptSubmit hook.
||| When a query is provided, runs the Talmud layer: knowledge retrieval,
||| dissent surfacing, edge traversal, coverage assessment, precedent.
||| Read-only: loads graph, outputs context, exits.
export
runShamashRetrieve : String -> Maybe String -> IO ()
runShamashRetrieve dbPath mQueryFile = do
  Just (store, eid, db) <- shamashOpen dbPath
    | Nothing => pure ()
  allMemes <- readIORef store.memes
  let expMemes = filter (\m => m.experimentId == eid) allMemes
  -- Read query if provided
  query <- case mQueryFile of
    Just f  => do Right q <- readFile f
                    | Left _ => pure ""
                  pure (trim q)
    Nothing => pure ""
  -- Deliberate or fall back to basic context
  ctx <- if query == ""
    then pure (assembleContext expMemes)
    else do allEdges <- readIORef store.edges
            allTurns <- readIORef store.turns
            let expEdges = filter (\e => e.experimentId == eid) allEdges
            let expTurns = filter (\t => t.experimentId == eid) allTurns
            pure (assembleFullContext query expMemes expEdges expTurns)
  putStr ctx
  closeDB db

------------------------------------------------------------------------
-- Phase 2: Feedback (model calls this after classifying the signal)
------------------------------------------------------------------------

||| Update the graph based on a model-classified signal.
||| Called by the model (Shamash or ADAM) via:
|||   eden --shamash-feedback SIGNAL --content FILE --db PATH
|||
||| The model understands the conversation. EDEN updates the graph.
export
runShamashFeedback : String -> String -> String -> IO ()
runShamashFeedback signalStr contentFile dbPath = do
  let signal = parseSignal signalStr
  Right content <- readFile contentFile
    | Left _ => pure ()

  Just (store, eid, db) <- shamashOpen dbPath
    | Nothing => pure ()
  ts <- currentTimestamp

  -- Update regard on behavior memes for meaningful signals
  case signal of
    Neutral   => pure ()
    Strategic => pure ()
    _         => do
      let fbSig = signalToFeedback signal
      allMemes <- readIORef store.memes
      let bMemes = filter (\m => m.experimentId == eid
                                && m.domain == Behavior) allMemes
      traverse_ (\m => do
        let (rw, rk, ed) = applyFeedback m.rewardEma m.riskEma
                                         m.editEma fbSig 0.6
        updateMemeChannels store m.id rw rk ed) bMemes

  -- Create meme from correction/boundary content
  case signal of
    Correction => do
      let lbl = "correction:" ++ substr 0 40 (trim content)
      _ <- upsertMeme store eid lbl (trim content)
                      Behavior FeedbackSource Global ts
      pure ()
    BoundarySetting => do
      let lbl = "boundary:" ++ substr 0 40 (trim content)
      _ <- upsertMeme store eid lbl (trim content)
                      Behavior FeedbackSource Global ts
      pure ()
    _ => pure ()

  -- Output updated context
  updated <- readIORef store.memes
  let ctx = assembleContext (filter (\m => m.experimentId == eid) updated)
  putStr ctx
  closeDB db

------------------------------------------------------------------------
-- Phase 3: Record turn (for precedent accumulation)
------------------------------------------------------------------------

||| Record a conversation turn for precedent retrieval.
||| Called after a response is generated:
|||   eden --shamash-record-turn --user FILE --response FILE --db PATH
export
runShamashRecordTurn : String -> String -> String -> IO ()
runShamashRecordTurn userFile responseFile dbPath = do
  Right userText <- readFile userFile
    | Left _ => pure ()
  Right responseText <- readFile responseFile
    | Left _ => pure ()

  Just (store, eid, db) <- shamashOpen dbPath
    | Nothing => pure ()
  ts <- currentTimestamp

  -- Find the session
  sessions <- readIORef store.sessions
  case filter (\s => s.experimentId == eid) sessions of
    [] => do closeDB db; pure ()
    (sess :: _) => do
      -- Count existing turns for index
      allTurns <- readIORef store.turns
      let sessTurns = filter (\t => t.sessionId == sess.id) allTurns
      let idx = length sessTurns
      -- Record the turn
      _ <- recordTurn store eid sess.id idx
                      (trim userText) "" (trim responseText) "" ts
      closeDB db
