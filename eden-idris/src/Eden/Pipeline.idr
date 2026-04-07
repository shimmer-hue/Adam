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
  -- Step 1b: Snapshot active set
  traverse_ (\cs => eRecordActiveSetEntry turnId cs.nodeId cs.label cs.domain
    cs.selection cs.semanticSimilarity cs.activationVal cs.regard) activeSet
  -- Step 2: Assemble prompt (§2.1: profile-driven history depth)
  assembly  <- mAssembleWith historyDepth activeSet userText
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
||| Propagates to memodes first, then to constituent memes (via MemberOf
||| edges) with 0.85 attenuation, and non-constituent memes with 0.5.
export
mProcessFeedback : TurnId -> Verdict -> String -> EdenM ()
mProcessFeedback tid verdict explanation = do
  let sig = feedbackSignal verdict
  _ <- eRecordFeedback tid verdict explanation "" sig

  env <- ask
  let scale = propagateScale verdict

  -- Step a: Read memodes and log feedback propagation
  allMemodes <- liftIO (readIORef env.store.memodes)
  eTraceFeedback tid ("memode_propagation: " ++ show (length allMemodes) ++ " memodes")

  -- Step b: Find constituent meme IDs via MemberOf edges
  allEdges <- liftIO (readIORef env.store.edges)
  let memberEdges = filter (\e => e.edgeType == MemberOf) allEdges
      constituentIds = map (\e => e.srcId) memberEdges

  -- Step c: Propagate to memes with differentiated attenuation
  memes <- eGetMemes
  propagateAll sig scale constituentIds memes

  -- Trace the event
  eTraceFeedback tid ("verdict=" ++ show verdict)
  where
    isConstituent : List String -> Meme -> Bool
    isConstituent cids m = elem (show m.id) cids

    propagateAll : FeedbackSignal -> Double -> List String -> List Meme -> EdenM ()
    propagateAll _   _     _    []        = pure ()
    propagateAll sig scale cids (m :: ms) = do
      let atten = if isConstituent cids m then 0.85 else 0.5
          s = scale * atten
          (rw', rk', ed') = applyFeedback m.rewardEma m.riskEma m.editEma sig s
      eUpdateMemeChannels m.id rw' rk' ed'
      propagateAll sig scale cids ms

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
