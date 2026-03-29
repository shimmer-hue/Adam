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

------------------------------------------------------------------------
-- Agent principles (loaded from seed_constitution.md at startup)
------------------------------------------------------------------------

||| Global principles string, set at startup from agent profile files.
export
gPrinciples : IORef String
gPrinciples = unsafePerformIO (newIORef "You are a curious, honest thinker.")

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
export
mRetrieve : String -> EdenM (List CandidateScore)
mRetrieve userText = do
  sid' <- getSessId
  memes <- eGetMemes
  let sw = defaultSelectionWeights
  pure (assembleActiveSet sw sid' 3600.0 5 userText memes)

||| Step 2: Assemble the prompt.
export
mAssemble : List CandidateScore -> String -> EdenM AssemblyResult
mAssemble activeSet userText = do
  history <- eGetRecentTurns 3
  principles <- liftIO (readIORef gPrinciples)
  pure (assemblePrompt "Adam" principles
          activeSet history "" userText)

||| Run a subprocess backend (claude or mlx) and return a ModelResult.
cmdGenerate : String -> String -> EdenM ModelResult
cmdGenerate name cmd = do
  (output, exitCode) <- liftIO (runCommand cmd)
  let answer = trim output
  let toks = length (words answer)
  pure (MkModelResult name (if exitCode /= 0 then "(" ++ name ++ " error)" else answer) toks answer "" answer)

||| Step 3: Generate a response via the specified backend.
export
mGenerateWith : Backend -> Maybe String -> AssemblyResult -> EdenM ModelResult
mGenerateWith backend modelPath assembly = do
  let params = MkGenerateParams assembly.arSysPrompt assembly.arConvPrompt
                 (cast assembly.arProfile.rpMaxOutput)
                 assembly.arProfile.rpTemp 0.9 1.05
  case backend of
    Mock => pure (mockGenerate params)
    Claude => cmdGenerate "claude" ("claude -p " ++ show (params.gpSystemPrompt ++ "\n\n" ++ params.gpConvPrompt) ++ " --model " ++ fromMaybe "sonnet" modelPath)
    MLX => cmdGenerate "mlx" ("python3 -c \"from mlx_lm import load,generate;m,t=load('" ++ fromMaybe "mlx-community/Llama-3.2-3B-Instruct-4bit" modelPath ++ "');print(generate(m,t,prompt=" ++ show params.gpConvPrompt ++ ",max_tokens=" ++ show params.gpMaxTokens ++ "))\"")

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

||| Step 6: Index concepts from turn text.
export
mIndex : String -> String -> EdenM IndexOutcome
mIndex userText cleanedText = do
  env <- ask
  liftIO (indexTurn env.store env.eid userText cleanedText env.ts)

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

||| Execute a complete turn with explicit backend selection.
export
mExecuteTurnWith : Backend -> Maybe String -> Nat -> String -> EdenM MTurnResult
mExecuteTurnWith be mp idx userText = do
  let turnId = MkId {a=TurnTag} ("turn-" ++ show idx)
  -- Step 1: Retrieve active set (similarity scored against user query)
  activeSet <- mRetrieve userText
  eTraceTurn turnId ("retrieve: " ++ show (length activeSet) ++ " candidates")
  -- Step 1b: Snapshot active set
  traverse_ (\cs => eRecordActiveSetEntry turnId cs.nodeId cs.label cs.domain
    cs.selection cs.semanticSimilarity cs.activationVal cs.regard) activeSet
  -- Step 2: Assemble prompt
  assembly  <- mAssemble activeSet userText
  eTraceTurn turnId ("assemble: profile=" ++ show assembly.arProfile.rpEffective
                   ++ " budget=" ++ show assembly.arBudget.pressure)
  -- Step 3: Generate
  genResult <- mGenerateWith be mp assembly
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
        ts'
  eRecordTurnMetadata tmeta
  -- Step 6: Index
  idxResult <- mIndex userText mo.moCleanedText
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

||| Execute a complete turn (mock backend).
export
mExecuteTurn : Nat -> String -> EdenM MTurnResult
mExecuteTurn = mExecuteTurnWith Mock Nothing

------------------------------------------------------------------------
-- Monadic feedback processing
------------------------------------------------------------------------

||| Process feedback in EdenM — no parameter threading needed.
export
mProcessFeedback : TurnId -> Verdict -> String -> EdenM ()
mProcessFeedback tid verdict explanation = do
  let sig = feedbackSignal verdict
  _ <- eRecordFeedback tid verdict explanation "" sig

  -- Propagate to all memes with distance-based attenuation
  memes <- eGetMemes
  let scale = propagateScale verdict
  propagateAll sig scale 1.0 memes

  -- Trace the event
  eTraceFeedback tid ("verdict=" ++ show verdict)
  where
    propagateAll : FeedbackSignal -> Double -> Double -> List Meme -> EdenM ()
    propagateAll _   _     _      []        = pure ()
    propagateAll sig scale atten (m :: ms)  = do
      let s = scale * atten
          (rw', rk', ed') = applyFeedback m.rewardEma m.riskEma m.editEma sig s
      eUpdateMemeChannels m.id rw' rk' ed'
      propagateAll sig scale (atten * 0.85) ms

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
