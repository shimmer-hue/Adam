||| Interactive turn loop using the EdenM monad.
|||
||| Replaces manual parameter threading with environment-based dispatch.
||| All turn execution, feedback, and hum generation delegate to Eden.Pipeline.
module Eden.Loop

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
import Eden.Indexer
import Eden.Trace
import Eden.SemanticRelations
import Eden.OntologyProjection
import Eden.Monad
import Eden.Pipeline
import Eden.Export
import Eden.SQLite

------------------------------------------------------------------------
-- REPL commands
------------------------------------------------------------------------

data ReplCmd = CmdQuit | CmdStats | CmdMemes | CmdRegard | CmdHum | CmdHelp | CmdChat String

parseCmd : String -> ReplCmd
parseCmd s =
  let t = trim s
  in if t == "/quit" || t == ""
       then CmdQuit
       else if t == "/stats"
         then CmdStats
         else if t == "/memes"
           then CmdMemes
           else if t == "/regard"
             then CmdRegard
             else if t == "/hum"
               then CmdHum
               else if t == "/help"
                 then CmdHelp
                 else CmdChat t

parseVerdict : String -> Maybe Verdict
parseVerdict s =
  let s' = toLower (trim s)
  in if s' == "accept" || s' == "a"
       then Just Accept
       else if s' == "reject" || s' == "r"
         then Just Reject
         else if s' == "edit" || s' == "e"
           then Just Edit
           else if s' == "skip" || s' == "s"
             then Just Skip
             else Nothing

------------------------------------------------------------------------
-- Display helpers
------------------------------------------------------------------------

showD : Double -> String
showD d =
  let i = cast {to=Integer} (d * 1000.0)
  in show (cast {to=Double} i / 1000.0)

showMemeRegard : Meme -> IO ()
showMemeRegard m =
  let ns = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau 0.0 m.feedbackCount m.editEma m.contradictionCount m.membraneConflicts
      gm = MkGraphMetrics 0.5 0.4 0.3
      rb = regardBreakdown defaultRegardWeights ns gm
  in putStrLn $ "  " ++ m.label ++ " [" ++ show m.domain ++ "]"
    ++ " total=" ++ showD rb.totalRegard
    ++ " rw=" ++ showD rb.reward
    ++ " ev=" ++ showD rb.evidence
    ++ " act=" ++ showD rb.activation

------------------------------------------------------------------------
-- REPL handlers (all use EdenM via runEden)
------------------------------------------------------------------------

handleStats : EdenEnv -> IO ()
handleStats env = do
  counts <- runEden env eGraphCounts
  putStrLn $ "  memes:    " ++ show counts.memeCount
  putStrLn $ "  edges:    " ++ show counts.edgeCount
  putStrLn $ "  turns:    " ++ show counts.turnCount
  putStrLn $ "  feedback: " ++ show counts.feedbackCount

handleMemes : EdenEnv -> IO ()
handleMemes env = do
  memes <- runEden env eGetMemes
  traverse_ (\m => putStrLn $ "  " ++ m.label
    ++ " [" ++ show m.domain ++ "]"
    ++ " regard=" ++ show (m.rewardEma - 0.3 * m.riskEma)
    ++ " usage=" ++ show m.usageCount) memes

handleRegard : EdenEnv -> IO ()
handleRegard env = do
  memes <- runEden env eGetMemes
  let sorted = sortBy (\a, b => compare b.rewardEma a.rewardEma) memes
  putStrLn "  --- Regard Breakdown ---"
  traverse_ showMemeRegard sorted
  -- Ontology projection
  let roles = countByRole memes
      (constatives, performatives, runtimes) = partitionBySpeechAct memes
  putStrLn "  --- Ontology ---"
  putStrLn $ "  constative:   " ++ show (length constatives)
  putStrLn $ "  performative: " ++ show (length performatives)
  putStrLn $ "  runtime:      " ++ show (length runtimes)
  putStrLn $ "  roles: core=" ++ show roles.coreCount
          ++ " active=" ++ show roles.activeCount
          ++ " peripheral=" ++ show roles.peripheralCount
          ++ " contested=" ++ show roles.contestedCount
          ++ " emergent=" ++ show roles.emergentCount
  counts <- runEden env eGraphCounts
  putStrLn $ "  memodes: " ++ show counts.memodeCount

handleHum : EdenEnv -> IO ()
handleHum env = do
  payload <- runEden env mBuildHum
  writeHumFile payload
  putStrLn $ "  --- Hum (v1) ---"
  putStrLn $ "  status:   " ++ show payload.hpStatus
  putStrLn $ "  turns:    " ++ show payload.metrics.turnsCovered
  putStrLn $ "  motifs:   " ++ show payload.metrics.recurringItems
  putStrLn $ "  unique:   " ++ show payload.metrics.uniqueMotifs
  putStrLn $ "  lines:    " ++ show payload.surfaceStats.lineCount
  putStrLn $ "  words:    " ++ show payload.surfaceStats.wordCount
  case payload.tokenTable of
    [] => putStrLn "  (no recurring motifs yet)"
    rows => traverse_ (\r => putStrLn $ "    " ++ r.htToken
                          ++ " x" ++ show r.htFrequency) (take 10 rows)

handleHelp : IO ()
handleHelp = do
  putStrLn "  Commands:"
  putStrLn "    /stats   - graph counts"
  putStrLn "    /memes   - list memes with usage"
  putStrLn "    /regard  - regard breakdown + ontology"
  putStrLn "    /hum     - hum continuity artifact"
  putStrLn "    /help    - this message"
  putStrLn "    /quit    - end session"
  putStrLn "  Feedback: accept(a) reject(r) edit(e) skip(s)"

handleChat : Backend -> Maybe String -> EdenEnv -> IORef Nat -> String -> IO ()
handleChat be mp env turnIdx msg = do
  idx <- readIORef turnIdx
  writeIORef turnIdx (idx + 1)

  -- Execute turn via monadic pipeline
  tr <- runEden env (mExecuteTurnWith be mp idx msg)
  putStrLn $ "\n[adam] " ++ tr.mrResponse
  case tr.mrConcepts of
    [] => pure ()
    cs => putStrLn $ "  [indexed: " ++ show cs ++ "]"
  case tr.mrRelations of
    [] => pure ()
    rs => traverse_ (\r => putStrLn $ "  [relation: "
            ++ r.rcSrcLabel ++ " --" ++ show r.rcEdgeType
            ++ "--> " ++ r.rcDstLabel ++ "]") rs

  putStr "[feedback accept/reject/edit/skip] > "
  fbLine <- getLine
  case parseVerdict fbLine of
    Nothing => putStrLn "  (skipped - unrecognized verdict)"
    Just v => do
      putStr "[explanation] > "
      expl <- getLine
      let turnId = MkId {a=TurnTag} ("turn-" ++ show (idx + 3))
      runEden env (mProcessFeedback turnId v expl)
      putStrLn $ "  feedback recorded: " ++ show v

------------------------------------------------------------------------
-- Main REPL
------------------------------------------------------------------------

mutual
  replLoop : Backend -> Maybe String -> EdenEnv -> IORef Nat -> IO ()
  replLoop be mp env turnIdx = do
    putStr "\n[you] > "
    input <- getLine
    dispatch be mp env turnIdx (parseCmd input)

  dispatch : Backend -> Maybe String -> EdenEnv -> IORef Nat -> ReplCmd -> IO ()
  dispatch be mp env turnIdx CmdQuit = do
    putStrLn "\n--- Session complete ---"
    handleStats env
    -- Close SQLite handle if open
    mdb <- readIORef env.store.dbHandle
    case mdb of
      Just db => do closeDB db
                    writeIORef env.store.dbHandle Nothing
                    putStrLn "  graph saved to data/eden.db"
      Nothing => do saveGraph env.store
                    putStrLn "  graph saved to data/graph.eden"
    putStrLn "Goodbye."
  dispatch be mp env turnIdx CmdStats = do
    handleStats env
    replLoop be mp env turnIdx
  dispatch be mp env turnIdx CmdMemes = do
    handleMemes env
    replLoop be mp env turnIdx
  dispatch be mp env turnIdx CmdRegard = do
    handleRegard env
    replLoop be mp env turnIdx
  dispatch be mp env turnIdx CmdHum = do
    handleHum env
    replLoop be mp env turnIdx
  dispatch be mp env turnIdx CmdHelp = do
    handleHelp
    replLoop be mp env turnIdx
  dispatch be mp env turnIdx (CmdChat msg) = do
    handleChat be mp env turnIdx msg
    replLoop be mp env turnIdx

||| Run the interactive REPL with a specific backend.
export
runREPLWith : Backend -> Maybe String -> String -> IO ()
runREPLWith be mp principles = do
  putStrLn ("=== EDEN/Adam Interactive REPL [" ++ show be ++ "] ===")
  putStrLn "    Type a message, then provide feedback."
  putStrLn "    Commands: /quit /stats /memes /regard /hum /help"
  putStrLn ""

  store <- newStore
  ts <- currentTimestamp

  -- Open SQLite database
  mdb <- openDB "data/eden.db"
  case mdb of
    Just db => do writeIORef store.dbHandle (Just db)
                  _ <- loadFromDB db store
                  putStrLn "  [db] opened data/eden.db"
    Nothing => putStrLn "  [db] warning: could not open data/eden.db, using in-memory only"

  -- Check if experiment was loaded from DB
  exps <- readIORef store.experiments
  eid <- case exps of
    (e :: _) => do
      putStrLn $ "  [db] resumed experiment: " ++ show e.id
      pure e.id
    [] => do
      exp <- createExperiment store "repl" "repl" Blank ts
      -- Seed initial memes on first run
      _ <- upsertMeme store exp.id "Curiosity" "Drive to explore and understand" Behavior SeedSource Global ts
      _ <- upsertMeme store exp.id "Honesty" "Commitment to truthful communication" Behavior SeedSource Global ts
      _ <- upsertMeme store exp.id "Clarity" "Preference for clear explanations" Behavior SeedSource Global ts
      pure exp.id
  turns <- readIORef store.turns
  let turnStart = length turns

  let agentId = MkId {a=AgentTag} "adam-01"
  sess <- createSession store eid agentId "REPL session" ts

  env <- newEdenEnv store eid sess.id ts principles
  turnIdx <- newIORef (the Nat turnStart)
  replLoop be mp env turnIdx

||| Run the interactive REPL (mock backend).
export
runREPL : IO ()
runREPL = runREPLWith Mock Nothing "You are a curious, honest thinker."
