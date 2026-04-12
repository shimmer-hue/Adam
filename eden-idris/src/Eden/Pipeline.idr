||| Monadic turn pipeline using EdenM.
|||
||| Replaces manual parameter threading with the EdenM reader monad.
||| Each pipeline step reads environment via `ask`/`asks` instead of
||| taking 5+ explicit parameters.
|||
||| Compare with Loop.idr's executeTurn which threads
||| (StoreState, ExperimentId, SessionId, Timestamp) manually.
module Eden.Pipeline

import Data.IORef
import Data.List
import Data.Maybe
import Data.String
import Eden.Types
import Eden.Config
import Eden.Regard
import Eden.Retrieval
import Eden.Budget
import Eden.Inference
import Eden.Membrane
import Eden.Hum
import Eden.Models.Base
import Eden.Models.Mock
import Eden.Store.InMemory
import Eden.Runtime
import Eden.Indexer
import Eden.SemanticRelations
import Eden.OntologyProjection
import Eden.Trace
import Eden.Monad
import Eden.TermIO
import System.File

------------------------------------------------------------------------
-- Monadic turn result
------------------------------------------------------------------------

public export
record MTurnResult where
  constructor MkMTurnResult
  mrResponse    : String
  mrConcepts    : List String
  mrEdges       : Nat
  mrRelations   : List RelationCandidate
  mrProjections : List MemeProjection

------------------------------------------------------------------------
-- Pipeline steps in EdenM
------------------------------------------------------------------------

||| Step 1: Retrieve and score the active set.
||| Semantic similarity is computed against the user's query text.
||| Graph metrics are computed from real graph topology (§1.6).
||| Document chunks are included alongside memes (§2.8).
export
mRetrieve : String -> EdenM (List CandidateScore)
mRetrieve userText = do
  sid' <- getSessId
  env <- ask
  memes <- eGetMemes
  chunks <- eGetChunks
  -- §1.6: Compute real graph metrics from edge store
  gm <- liftIO (computeGraphMetrics env.store env.eid)
  let sw = defaultSelectionWeights
      memeCandidates = assembleActiveSet sw sid' gm 3600.0 5 userText memes
      -- §2.8: Score document chunks alongside memes
      chunkCandidates = map (\c => scoreChunkCandidate sw sid'
                               (computeSimilarity defaultSimilarityMethod userText c.text) c) chunks
      -- Merge meme and chunk candidates, re-select top-k
      allCandidates = selectTopK 5 (memeCandidates ++ chunkCandidates)
  pure allCandidates

||| Step 2: Assemble the prompt.
||| Uses the provided history depth (from session profile) instead of a hardcoded value.
export
mAssembleWith : Nat -> List CandidateScore -> String -> EdenM AssemblyResult
mAssembleWith histDepth activeSet userText = do
  history <- eGetRecentTurns histDepth
  princ <- asks principles
  pure (assemblePrompt "Adam" princ
          activeSet history "" userText)

||| Step 2 (default): Assemble with default history depth of 3.
export
mAssemble : List CandidateScore -> String -> EdenM AssemblyResult
mAssemble = mAssembleWith 3

||| Strip ANSI escape sequences and control characters from subprocess output.
||| Newlines become spaces; ESC[... sequences are removed entirely.
sanitizeOutput : String -> String
sanitizeOutput s = pack (norm (stripEsc (unpack s)))
  where
    stripEsc : List Char -> List Char
    stripEsc [] = []
    stripEsc (c :: '[' :: rest) =
      if c == chr 27
        then let skip : List Char -> List Char
                 skip [] = []
                 skip (x :: xs) = if isAlpha x then stripEsc xs else skip xs
             in skip rest
        else c :: '[' :: stripEsc rest
    stripEsc (c :: rest) =
      if c == chr 27 then stripEsc (drop 1 rest)
      else c :: stripEsc rest
    norm : List Char -> List Char
    norm [] = []
    norm ('\n' :: cs) = ' ' :: norm cs
    norm ('\r' :: cs) = norm cs
    norm (c :: cs) = if ord c < 32 then norm cs else c :: norm cs

||| Write prompt to file, pipe to CLI tool via popen, rearm terminal after.
cmdGenerateViaFile : String -> String -> String -> EdenM ModelResult
cmdGenerateViaFile name prompt cmd = do
  _ <- liftIO (writeFile "data/eden_prompt.tmp" prompt)
  -- popen uses MSYS2 shell (has cat); eden_run_cmd calls eden_term_rearm after pclose
  (output, exitCode) <- liftIO (runCommand ("cat data/eden_prompt.tmp | " ++ cmd))
  -- Extra rearm in case the in-C rearm wasn't enough
  liftIO rearmTerminal
  let answer = sanitizeOutput (trim output)
  let toks = length (words answer)
  pure (MkModelResult name (if exitCode /= 0 then "(" ++ name ++ " error)" else answer) toks answer "" answer)

------------------------------------------------------------------------
-- Deliberation (Talmud layer)
------------------------------------------------------------------------

||| Extract concept terms from query text for coverage assessment.
||| Uses the same word-level tokenization as retrieval.
extractQueryConcepts : String -> List String
extractQueryConcepts text =
  let ws = words (toLower text)
  in filter (\w => length w > 2 && not (elem w defaultStopwords)) ws
  where
    defaultStopwords : List String
    defaultStopwords = ["the", "and", "for", "are", "but", "not", "you",
                        "all", "can", "had", "her", "was", "one", "our",
                        "out", "has", "have", "been", "will", "with",
                        "this", "that", "from", "they", "were", "said"]

||| Check if a concept is covered by any meme in the active set.
conceptCovered : String -> List CandidateScore -> Bool
conceptCovered concept candidates =
  any (\c => isInfixOf concept (toLower c.text)) candidates

||| Compute coverage: fraction of query concepts found in active set.
computeCoverage : List String -> List CandidateScore -> Double
computeCoverage [] _ = 1.0
computeCoverage concepts candidates =
  let covered = filter (\c => conceptCovered c candidates) concepts
  in cast (length covered) / cast (length concepts)

||| Find memes with relevant content but low regard (minority opinions).
||| These are the Beit Shammai positions — rejected but preserved.
findDissentingMemes : String -> List CandidateScore -> List Meme -> List (MemeId, Double)
findDissentingMemes query activeSet allMemes =
  let activeIds = map (\c => c.nodeId) activeSet
      relevant  = filter (\m => not (elem (show m.id) activeIds)
                              && computeSimilarity TFIDF query m.text > 0.15) allMemes
      lowRegard = filter (\m => m.rewardEma < 0.0 || m.riskEma > 0.3) relevant
  in map (\m => (m.id, m.rewardEma)) lowRegard

||| Find prior turns with similar context (precedent retrieval).
findPrecedentTurns : String -> List Turn -> List TurnId
findPrecedentTurns query turns =
  let similar = filter (\t => computeSimilarity TFIDF query t.userText > 0.25) turns
  in map (\t => t.id) (take 3 similar)

||| Build a human-readable deliberation trace (the shakla v'tarya).
buildDeliberationTrace : Double -> List String -> List (MemeId, Double)
                      -> List TurnId -> Bool -> String
buildDeliberationTrace cov gaps dissent precs secondPass =
  "coverage=" ++ show cov
  ++ " gaps=" ++ show (length gaps)
  ++ " dissent=" ++ show (length dissent)
  ++ " precedents=" ++ show (length precs)
  ++ " second_pass=" ++ show secondPass
  ++ (if length gaps > 0
      then " uncovered=[" ++ unwords (take 5 gaps) ++ "]"
      else "")

||| Step 2.5: Deliberate — the Talmud layer.
||| Assesses coverage, surfaces dissent, retrieves precedent.
||| If coverage is below threshold, triggers second retrieval pass.
||| All decisions logged in trace. Observable. Not hidden.
export
mDeliberate : String -> List CandidateScore -> EdenM (DeliberationResult, List CandidateScore)
mDeliberate userText activeSet = do
  -- Extract concepts from user query
  let concepts = extractQueryConcepts userText
  let coverage = computeCoverage concepts activeSet
  let gaps = filter (\c => not (conceptCovered c activeSet)) concepts
  -- Find dissenting memes (minority opinions with low regard)
  allMemes <- eGetMemes
  let dissent = findDissentingMemes userText activeSet allMemes
  -- Find precedent turns
  allTurns <- eGetSessionTurns
  let precedents = findPrecedentTurns userText allTurns
  -- Second retrieval pass if coverage is low (Binah: research more)
  (enriched, secondPass) <-
    if coverage < 0.4
      then do
        -- Re-retrieve with gap terms as additional query
        let gapQuery = unwords gaps ++ " " ++ userText
        extraCandidates <- mRetrieve gapQuery
        let merged = selectTopK 7 (activeSet ++ extraCandidates)
        pure (merged, True)
      else pure (activeSet, False)
  -- Build trace
  let trace = buildDeliberationTrace coverage gaps dissent precedents secondPass
  let result = MkDeliberation coverage gaps dissent precedents secondPass trace
  pure (result, enriched)

------------------------------------------------------------------------
-- Generation
------------------------------------------------------------------------

||| Step 3: Generate a response via the specified backend.
||| topP and repPen are taken from the resolved profile's sampling parameters.
export
mGenerateWith : Backend -> Maybe String -> Double -> Double -> AssemblyResult -> EdenM ModelResult
mGenerateWith backend modelPath topP repPen assembly = do
  let params = MkGenerateParams assembly.arSysPrompt assembly.arConvPrompt
                 (cast assembly.arProfile.rpMaxOutput)
                 assembly.arProfile.rpTemp topP repPen
  case backend of
    Mock => pure (mockGenerate params)
    Claude => cmdGenerateViaFile "claude"
                (params.gpSystemPrompt ++ "\n\n" ++ params.gpConvPrompt)
                ("claude --model " ++ fromMaybe "sonnet" modelPath)
    MLX => do
      let model = fromMaybe "mlx-community/Llama-3.2-3B-Instruct-4bit" modelPath
      cmdGenerateViaFile "mlx" params.gpConvPrompt
        ("python3 -c \"from mlx_lm import load,generate;m,t=load('" ++ model ++ "');import sys;p=sys.stdin.read();print(generate(m,t,prompt=p,max_tokens=" ++ show params.gpMaxTokens ++ "))\"")

||| Step 4: Apply the membrane.
export
mMembrane : Nat -> String -> EdenM MembraneOutcome
mMembrane cap rawText =
  pure (applyMembraneStep cap rawText)

||| Step 5: Record the turn.
export
mRecordTurn : Nat -> String -> String -> String -> String -> EdenM Turn
mRecordTurn idx userText convPrompt rawResp cleaned =
  eRecordTurn idx userText convPrompt rawResp cleaned

||| Step 6: Index concepts from turn text (keyword fallback).
export
mIndex : String -> String -> EdenM IndexOutcome
mIndex userText cleanedText = do
  env <- ask
  liftIO (indexTurn env.store env.eid userText cleanedText env.ts)

||| Step 6 (model-aware): Index concepts using Claude when available.
export
mIndexWith : Backend -> String -> String -> EdenM IndexOutcome
mIndexWith Claude userText cleanedText = do
  env <- ask
  liftIO (indexTurnWithModel env.store env.eid userText cleanedText env.ts)
mIndexWith _ userText cleanedText = mIndex userText cleanedText

||| Step 7: Extract semantic relations.
export
mRelations : String -> String -> List String -> EdenM (List RelationCandidate)
mRelations userText cleanedText concepts = do
  let combined = userText ++ " " ++ cleanedText
  pure (extractRelations combined concepts)

||| Step 8: Create edges for detected relations.
export
mCreateRelationEdges : List RelationCandidate -> EdenM ()
mCreateRelationEdges rels =
  traverse_ createOne rels
  where
    createOne : RelationCandidate -> EdenM ()
    createOne rc = do
      _ <- eCreateEdge MemeNode rc.rcSrcLabel MemeNode rc.rcDstLabel
             rc.rcEdgeType (scoreRelation rc)
      pure ()

||| Step 9: Materialize memodes.
export
mMaterialize : EdenM (List Memode)
mMaterialize = eMaterializeMemodes

||| Step 10: Project ontology.
export
mProject : EdenM (List MemeProjection)
mProject = do
  memes <- eGetMemes
  pure (map projectMeme memes)

------------------------------------------------------------------------
-- Full monadic turn pipeline
------------------------------------------------------------------------

||| Execute a complete turn with explicit backend selection and profile.
||| The historyDepth parameter comes from the session profile (§2.1).
export
mExecuteTurnWith : Backend -> Maybe String -> Nat -> Nat -> String -> EdenM MTurnResult
mExecuteTurnWith be mp historyDepth idx userText = do
  let turnId = MkId {a=TurnTag} ("turn-" ++ show idx)
  -- Step 1: Retrieve active set (similarity scored against user query)
  activeSet <- mRetrieve userText
  eTraceTurn turnId ("retrieve: " ++ show (length activeSet) ++ " candidates")
  -- Step 1b: Deliberate (Talmud layer: coverage, dissent, precedent)
  (deliberation, enrichedSet) <- mDeliberate userText activeSet
  eTraceTurn turnId ("deliberate: " ++ deliberation.dlTrace)
  -- Step 1c: Snapshot active set (post-deliberation, possibly enriched)
  traverse_ (\cs => eRecordActiveSetEntry turnId cs.nodeId cs.label cs.domain
    cs.selection cs.semanticSimilarity cs.activationVal cs.regard) enrichedSet
  -- Step 2: Assemble prompt (§2.1: profile-driven history depth)
  assembly0 <- mAssembleWith historyDepth enrichedSet userText
  -- §2.3: Budget-aware history trimming — if pressure is High, halve
  -- history depth and re-assemble to fit within the budget envelope
  assembly  <- case assembly0.arBudget.pressure of
    High => do
      let halved = max 1 (natDiv historyDepth 2)
      eTraceTurn turnId ("budget-trim: pressure=HIGH, halving history "
                       ++ show historyDepth ++ " -> " ++ show halved)
      mAssembleWith halved activeSet userText
    _ => pure assembly0
  eTraceTurn turnId ("assemble: profile=" ++ show assembly.arProfile.rpEffective
                   ++ " budget=" ++ show assembly.arBudget.pressure)
  -- Step 3: Generate (pass profile sampling params)
  genResult <- mGenerateWith be mp assembly.arProfile.rpTopP assembly.arProfile.rpRepPen assembly
  eTraceTurn turnId ("generate: backend=" ++ genResult.mrBackend
                   ++ " tokens=" ++ show genResult.mrTokenEstimate)
  -- Step 4: Membrane
  mo        <- mMembrane assembly.arProfile.rpRespCap genResult.mrText
  eTraceTurn turnId ("membrane: events=" ++ show (length mo.moEvents))
  -- Step 5: Record turn
  _ <- mRecordTurn idx userText assembly.arConvPrompt genResult.mrText mo.moCleanedText
  -- Step 5b: Record turn metadata
  ts' <- getTimestamp
  let tmeta = MkTurnMetadata turnId
        (show assembly.arProfile.rpRequested)
        (show assembly.arProfile.rpEffective)
        (show assembly.arProfile.rpBudgetMode)
        (show assembly.arBudget.pressure)
        assembly.arBudget.usedPromptTokens
        assembly.arBudget.remainingInputTokens
        (length activeSet)
        mo.moReasoningText
        assembly.arProfile.rpTemp
        assembly.arProfile.rpMaxOutput
        assembly.arProfile.rpRespCap
        "default"
        "retrieval"
        "word_count"
        ts'
  eRecordTurnMetadata tmeta
  -- Step 6: Index (model-aware when backend supports it)
  idxResult <- mIndexWith be userText mo.moCleanedText
  eTraceTurn turnId ("index: concepts=" ++ show idxResult.ioConceptNames
                   ++ " edges=" ++ show idxResult.ioNewEdges)
  -- Step 7-9: Relations, materialization, projection
  rels <- mRelations userText mo.moCleanedText idxResult.ioConceptNames
  mCreateRelationEdges rels
  _ <- mMaterialize
  projs <- mProject
  eTraceTurn turnId ("complete: relations=" ++ show (length rels)
                   ++ " projections=" ++ show (length projs))
  pure (MkMTurnResult mo.moCleanedText idxResult.ioConceptNames idxResult.ioNewEdges rels projs)

||| Execute a complete turn (mock backend, default history depth 5).
export
mExecuteTurn : Nat -> String -> EdenM MTurnResult
mExecuteTurn = mExecuteTurnWith Mock Nothing 5

------------------------------------------------------------------------
-- Monadic feedback processing
------------------------------------------------------------------------

||| Process feedback in EdenM — no parameter threading needed.
||| Propagates memode-first (scale 1.0), then to constituent memes
||| (via MemberOf edges, 0.85 attenuation), then non-constituent (0.5).
||| Re-ingests feedback text as a behavior-domain meme (§2.2).
export
mProcessFeedback : TurnId -> Verdict -> String -> EdenM ()
mProcessFeedback tid verdict explanation = do
  let sig = feedbackSignal verdict
  _ <- eRecordFeedback tid verdict explanation "" sig

  env <- ask
  let scale = propagateScale verdict

  -- Step a: Propagate to memodes first (direct signal, scale 1.0)
  allMemodes <- liftIO (readIORef env.store.memodes)
  eTraceFeedback tid ("memode_propagation: " ++ show (length allMemodes) ++ " memodes")
  propagateMemodes sig scale allMemodes

  -- Step b: Find constituent meme IDs via MemberOf edges
  allEdges <- liftIO (readIORef env.store.edges)
  let memberEdges = filter (\e => e.edgeType == MemberOf) allEdges
      constituentIds = map (\e => e.srcId) memberEdges

  -- Step c: Propagate to memes with differentiated attenuation
  memes <- eGetMemes
  propagateMemes sig scale constituentIds memes

  -- Step d: Re-ingest feedback text as a behavior meme
  case verdict of
    Edit => do
      _ <- eUpsertMeme ("feedback:" ++ show tid) explanation Behavior FeedbackSource Global
      -- Create FedBackBy edge from feedback meme to the turn
      _ <- eCreateEdge MemeNode ("feedback:" ++ show tid) MemeNode (show tid) FedBackBy 0.9
      pure ()
    _ => pure ()

  -- Trace the event
  eTraceFeedback tid ("verdict=" ++ show verdict)
  where
    propagateMemodes : FeedbackSignal -> Double -> List Memode -> EdenM ()
    propagateMemodes _   _     []        = pure ()
    propagateMemodes sig scale (md :: mds) = do
      let (rw', rk', ed') = applyFeedback md.rewardEma md.riskEma md.editEma sig scale
      eUpdateMemodeChannels md.id rw' rk' ed'
      propagateMemodes sig scale mds

    isConstituent : List String -> Meme -> Bool
    isConstituent cids m = elem (show m.id) cids

    propagateMemes : FeedbackSignal -> Double -> List String -> List Meme -> EdenM ()
    propagateMemes _   _     _    []        = pure ()
    propagateMemes sig scale cids (m :: ms) = do
      let atten = if isConstituent cids m then 0.85 else 0.5
          s = scale * atten
          (rw', rk', ed') = applyFeedback m.rewardEma m.riskEma m.editEma sig s
      eUpdateMemeChannels m.id rw' rk' ed'
      propagateMemes sig scale cids ms

------------------------------------------------------------------------
-- Monadic hum generation
------------------------------------------------------------------------

||| Build a hum payload in EdenM.
export
mBuildHum : EdenM HumPayload
mBuildHum = do
  env   <- ask
  turns <- eGetSessionTurns
  let sorted = sortBy (\a, b => compare a.turnIndex b.turnIndex) turns
  pure (buildHumPayload env.eid env.sid sorted "" "" env.ts)
