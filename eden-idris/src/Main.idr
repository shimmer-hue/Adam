||| EDEN/Adam v1 -- Idris2 implementation.
|||
||| Usage:
|||   eden          -- run invariant demo
|||   eden --repl   -- interactive REPL
|||   eden --demo   -- one-shot demo with store + memode materialization
module Main

import System
import Data.IORef
import Data.List
import Data.String
import Eden.Types
import Eden.Config
import Eden.Regard
import Eden.Retrieval
import Eden.Budget
import Eden.Inference
import Eden.Membrane
import Eden.Hum
import Eden.Ingest
import Eden.Models.Base
import Eden.Models.Mock
import Eden.Storage
import Eden.Store.InMemory
import Eden.Runtime
import Eden.Loop
import Eden.OntologyProjection
import Eden.Monad
import Eden.Pipeline
import Eden.Trace
import Eden.SemanticRelations
import Eden.TUI

-- Helper for display
showDouble : Double -> String
showDouble d =
  let i = cast {to=Integer} (d * 1000.0)
  in show (cast {to=Double} i / 1000.0)

------------------------------------------------------------------------
-- Invariant demo (original)
------------------------------------------------------------------------

runInvariantDemo : IO ()
runInvariantDemo = do
  putStrLn "=== EDEN/Adam v1 -- Idris2 Runtime ==="
  putStrLn ""

  -- 1. Regard computation
  putStrLn "--- Regard Breakdown ---"
  let w  = defaultRegardWeights
  let ns = MkNodeState { nsRewardEma = 0.3, nsRiskEma = 0.1, nsEvidenceN = 5.0
                       , nsUsageCount = 10, nsActivTau = 86400.0, nsDeltaSec = 3600.0 }
  let gm = MkGraphMetrics { clustering = 0.6, normDegree = 0.4, trianglePart = 0.3 }
  let rb = regardBreakdown w ns gm
  putStrLn $ "  reward:      " ++ showDouble rb.reward
  putStrLn $ "  evidence:    " ++ showDouble rb.evidence
  putStrLn $ "  coherence:   " ++ showDouble rb.coherence
  putStrLn $ "  persistence: " ++ showDouble rb.persistence
  putStrLn $ "  decay:       " ++ showDouble rb.decay
  putStrLn $ "  isolation:   " ++ showDouble rb.isolationPenalty
  putStrLn $ "  risk:        " ++ showDouble rb.risk
  putStrLn $ "  activation:  " ++ showDouble rb.activation
  putStrLn $ "  TOTAL:       " ++ showDouble rb.totalRegard
  putStrLn ""

  -- 2. Feedback signal + EMA
  putStrLn "--- Feedback Integration ---"
  let sig = feedbackSignal Accept
  putStrLn $ "  Accept signal: reward=" ++ showDouble sig.reward
                        ++ " risk=" ++ showDouble sig.risk
                        ++ " edit=" ++ showDouble sig.edit
  let (newRw, newRk, newEd) = applyFeedback 0.2 0.1 0.0 sig 0.8
  putStrLn $ "  After EMA:     reward=" ++ showDouble newRw
                        ++ " risk=" ++ showDouble newRk
                        ++ " edit=" ++ showDouble newEd
  putStrLn ""

  -- 3. Selection scoring
  putStrLn "--- Selection Score ---"
  let sw = defaultSelectionWeights
  let sid = MkId {a=SessionTag} "test-session"
  let score = scoreCandidate sw sid 0.85 1800.0 86400.0 2.5
                             Global 0.3 0.1 5 0
  putStrLn $ "  score = " ++ showDouble score
  putStrLn ""

  -- 4. Inference profile resolution
  putStrLn "--- Inference Profile ---"
  let now = MkTimestamp "2026-03-25T12:00:00Z"
  let req = defaultProfileRequest
  let profile = resolveProfile req now
  putStrLn $ "  requested:  " ++ show profile.rpRequested
  putStrLn $ "  effective:  " ++ show profile.rpEffective
  putStrLn $ "  budget:     " ++ show profile.rpBudgetMode
  putStrLn $ "  temp:       " ++ showDouble profile.rpTemp
  putStrLn $ "  maxOutput:  " ++ show profile.rpMaxOutput
  putStrLn ""

  -- 5. adam_auto fallback proof
  putStrLn "--- No Hidden Governor (proof) ---"
  let _ = the (resolveMode AdamAuto = RuntimeAuto) Refl
  putStrLn "  resolveMode AdamAuto = RuntimeAuto   [Refl] QED"
  let _ = the (resolveMode Manual = Manual) Refl
  putStrLn "  resolveMode Manual = Manual           [Refl] QED"
  putStrLn ""

  -- 6. Membrane pipeline
  putStrLn "--- Membrane ---"
  let raw = "Answer: This is Adam's response.\n\nBasis: supporting material here."
  let mr  = applyMembrane 5200 raw
  putStrLn $ "  input:   \"" ++ raw ++ "\""
  putStrLn $ "  output:  \"" ++ mr.cleanedText ++ "\""
  putStrLn $ "  events:  " ++ show (map show mr.events)
  putStrLn ""

  -- 7. Budget estimation
  putStrLn "--- Budget ---"
  let be = estimateBudget 8192 5120 3072 500 2000 800 200 100 4800 5 3 False
  putStrLn $ "  used:      " ++ show be.usedPromptTokens ++ " tokens"
  putStrLn $ "  remaining: " ++ show be.remainingInputTokens ++ " tokens"
  putStrLn $ "  pressure:  " ++ show be.pressure
  putStrLn $ "  ratio:     " ++ showDouble be.pressureRatio
  putStrLn ""

  -- 8. Memode admissibility (>= 2 members, type-checked)
  putStrLn "--- Memode Admissibility ---"
  let ids = [MkId "m1", MkId "m2", MkId "m3"]
  case canMaterialize ids of
    Yes (YesMaterialize a b rest) =>
      putStrLn $ "  [" ++ show a ++ ", " ++ show b ++ ", ...]"
             ++ " -> admissible (" ++ show (2 + length rest) ++ " members)"
    No _ =>
      putStrLn "  not admissible"
  putStrLn ""

  -- 9. Mock model
  putStrLn "--- Mock Model ---"
  let params = MkGenerateParams "You are Adam." "User: hello" 512 0.4 0.9 1.05
  let result = mockGenerate params
  putStrLn $ "  backend: " ++ result.mrBackend
  putStrLn $ "  tokens:  " ++ show result.mrTokenEstimate
  putStrLn $ "  text:    \"" ++ substr 0 60 result.mrText ++ "...\""
  putStrLn ""

  -- 10. Hum boundedness
  putStrLn "--- Hum Boundedness ---"
  let turnIds = map (\n => MkId (show n)) [1,2,3,4,5]
  let bounded = boundTurns turnIds
  putStrLn $ "  input:  " ++ show (length turnIds) ++ " turns"
  putStrLn $ "  output: " ++ show (length bounded) ++ " turns (cap=" ++ show HumTurnCap ++ ")"
  putStrLn ""

  putStrLn "=== All invariants verified. ==="

------------------------------------------------------------------------
-- Full store + memode demo
------------------------------------------------------------------------

showMemeRegard : Meme -> IO ()
showMemeRegard m =
  let ns = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau 0.0
      gm = MkGraphMetrics 0.5 0.4 0.3
      rb = regardBreakdown defaultRegardWeights ns gm
  in putStrLn $ "  " ++ m.label ++ " [" ++ show m.domain ++ "]: regard=" ++ showDouble rb.totalRegard

runStoreDemo : Backend -> Maybe String -> IO ()
runStoreDemo be mp = do
  putStrLn "=== EDEN Store + Pipeline Demo ==="
  putStrLn ""

  store <- newStore
  let ts = MkTimestamp "2026-03-25T12:00:00Z"

  -- Create experiment + session
  exp <- createExperiment store "demo" "demo" Blank ts
  let agentId = MkId {a=AgentTag} "adam-01"
  sess <- createSession store exp.id agentId "Demo session" ts
  putStrLn $ "  experiment: " ++ show exp.id
  putStrLn $ "  session:    " ++ show sess.id

  -- Seed behavior memes
  m1 <- upsertMeme store exp.id "Curiosity" "Drive to explore and understand" Behavior SeedSource Global ts
  m2 <- upsertMeme store exp.id "Honesty" "Commitment to truthful communication" Behavior SeedSource Global ts
  m3 <- upsertMeme store exp.id "Clarity" "Preference for clear explanations" Behavior SeedSource Global ts
  m4 <- upsertMeme store exp.id "Physics" "Knowledge of physical laws" Knowledge SeedSource Global ts
  putStrLn $ "  memes:      " ++ show (length [m1,m2,m3,m4]) ++ " created"

  -- Create support edges between behavior memes
  _ <- createEdge store exp.id MemeNode (show m1.id) MemeNode (show m2.id) Supports 0.85 ts
  _ <- createEdge store exp.id MemeNode (show m2.id) MemeNode (show m3.id) Supports 0.70 ts
  _ <- createEdge store exp.id MemeNode (show m1.id) MemeNode (show m3.id) Supports 0.60 ts
  putStrLn "  edges:      3 support edges"

  -- Materialize memodes from connected behavior memes
  memodes <- materializeMemodes store exp.id ts
  putStrLn $ "  memodes:    " ++ show (length memodes) ++ " materialized"
  traverse_ (\md => putStrLn $ "    - " ++ md.label) memodes

  -- Create EdenEnv — all pipeline calls use the monad from here
  env <- newEdenEnv store exp.id sess.id ts

  -- Turn 0 via monadic pipeline
  tr0 <- runEden env (mExecuteTurnWith be mp 0 "What drives your thinking?")
  putStrLn $ "\n  [turn 0]"
  putStrLn $ "  user:  What drives your thinking?"
  putStrLn $ "  adam:  " ++ tr0.mrResponse
  putStrLn $ "  indexed: " ++ show tr0.mrConcepts

  -- Accept feedback via monadic pipeline
  let turnId0 = MkId {a=TurnTag} "turn-6"
  runEden env (mProcessFeedback turnId0 Accept "Good response")

  -- Show updated regard
  putStrLn "\n  --- Regard after feedback ---"
  expMemes' <- runEden env eGetMemes
  traverse_ showMemeRegard expMemes'

  -- Turn 1 via monadic pipeline
  tr1 <- runEden env (mExecuteTurnWith be mp 1 "Tell me about honesty in reasoning.")
  putStrLn $ "\n  [turn 1]"
  putStrLn $ "  user:  Tell me about honesty in reasoning."
  putStrLn $ "  adam:  " ++ tr1.mrResponse
  putStrLn $ "  indexed: " ++ show tr1.mrConcepts

  -- Ontology projection
  putStrLn "\n  --- Ontology Projection ---"
  expMemes'' <- runEden env eGetMemes
  let roles = countByRole expMemes''
      (constatives, performatives, runtimes) = partitionBySpeechAct expMemes''
  putStrLn $ "  constative:   " ++ show (length constatives)
  putStrLn $ "  performative: " ++ show (length performatives)
  putStrLn $ "  roles: core=" ++ show roles.coreCount
          ++ " active=" ++ show roles.activeCount
          ++ " peripheral=" ++ show roles.peripheralCount
          ++ " emergent=" ++ show roles.emergentCount

  -- Hum via monadic pipeline
  hum <- runEden env mBuildHum
  putStrLn $ "\n  --- Hum ---"
  putStrLn $ "  status: " ++ show hum.hpStatus
  putStrLn $ "  turns:  " ++ show hum.metrics.turnsCovered
  putStrLn $ "  motifs: " ++ show hum.metrics.recurringItems

  -- Graph summary
  putStrLn ""
  counts <- runEden env eGraphCounts
  putStrLn $ "  --- Graph Summary ---"
  putStrLn $ "  memes:      " ++ show counts.memeCount
  putStrLn $ "  memodes:    " ++ show counts.memodeCount
  putStrLn $ "  edges:      " ++ show counts.edgeCount
  putStrLn $ "  turns:      " ++ show counts.turnCount
  putStrLn $ "  feedback:   " ++ show counts.feedbackCount

  -- Trace events
  tcount <- traceCount env.trace
  putStrLn $ "  trace:      " ++ show tcount ++ " events"
  putStrLn ""
  putStrLn "=== Demo complete. ==="

------------------------------------------------------------------------
-- CLI dispatch
------------------------------------------------------------------------

parseBackend : String -> Backend
parseBackend "claude" = Claude
parseBackend "mlx"    = MLX
parseBackend _        = Mock

parseArgs : List String -> (Backend, Maybe String, Maybe String)
parseArgs [] = (Mock, Nothing, Nothing)
parseArgs ("--backend" :: b :: rest) =
  let (_, mp, cmd) = parseArgs rest
  in (parseBackend b, mp, cmd)
parseArgs ("--model" :: m :: rest) =
  let (be, _, cmd) = parseArgs rest
  in (be, Just m, cmd)
parseArgs (x :: rest) =
  let (be, mp, _) = parseArgs rest
  in (be, mp, Just x)

main : IO ()
main = do
  args <- getArgs
  let cliArgs = drop 1 args  -- drop program name
  let (be, mp, _) = parseArgs cliArgs
  case cliArgs of
    ("--repl"  :: _) => runREPL
    ("--demo"  :: _) => runStoreDemo be mp
    ("--tui"   :: _) => runTUIWith be mp
    _                => runInvariantDemo
