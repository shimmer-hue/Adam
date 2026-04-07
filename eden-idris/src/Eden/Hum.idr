||| Hum: bounded continuity artifact.
|||
||| NOT an input to generation, NOT a hidden inner voice, NOT a planner
||| residue, and NOT identical to the active set or the whole graph.
module Eden.Hum

import Data.List
import Data.String
import Eden.Types

%default total

------------------------------------------------------------------------
-- Hum status
------------------------------------------------------------------------

public export
data HumStatus = HumFresh | HumStale | HumUnavailable

public export
Show HumStatus where
  show HumFresh       = "fresh"
  show HumStale       = "stale"
  show HumUnavailable = "unavailable"

------------------------------------------------------------------------
-- Hum metrics
------------------------------------------------------------------------

public export
record HumMetrics where
  constructor MkHumMetrics
  turnsCovered   : Nat
  hmFeedbackEvts : Nat
  hmMembraneEvts : Nat
  recurringItems : Nat
  uniqueMotifs   : Nat

------------------------------------------------------------------------
-- Hum surface stats
------------------------------------------------------------------------

public export
record HumSurfaceStats where
  constructor MkHumSurfaceStats
  lineCount : Nat
  charCount : Nat
  wordCount : Nat

------------------------------------------------------------------------
-- Hum token row (motif)
------------------------------------------------------------------------

public export
record HumTokenRow where
  constructor MkHumTokenRow
  htToken     : String
  htFrequency : Nat
  htSource    : String
  htFirstSeen : Timestamp
  htLastSeen  : Timestamp

------------------------------------------------------------------------
-- Hum payload
------------------------------------------------------------------------

public export
record HumPayload where
  constructor MkHumPayload
  artifactVersion : String
  generatedAt     : Timestamp
  hpExperimentId  : ExperimentId
  hpSessionId     : SessionId
  latestTurnId    : Maybe TurnId
  turnIds         : List TurnId
  turnIndices     : List Nat
  derivedFrom     : List String
  hpStatus        : HumStatus
  metrics         : HumMetrics
  textSurface     : String
  surfaceLines    : List String
  surfaceStats    : HumSurfaceStats
  tokenTable      : List HumTokenRow

------------------------------------------------------------------------
-- Boundedness invariant
------------------------------------------------------------------------

||| The hum covers at most the last N turns (default 3).
public export
HumTurnCap : Nat
HumTurnCap = 3

public export
boundTurns : List TurnId -> List TurnId
boundTurns xs =
  let l = length xs
  in if l <= HumTurnCap then xs
     else drop (minus l HumTurnCap) xs

------------------------------------------------------------------------
-- Surface generation
------------------------------------------------------------------------

public export
generateSurface : List String -> String -> String -> (List String, HumSurfaceStats)
generateSurface turns fb memb =
  let turnLines = map (\s => "- " ++ s) turns
      sections  = turnLines
               ++ (if fb == "" then [] else ["", "Feedback: " ++ fb])
               ++ (if memb == "" then [] else ["", "Membrane: " ++ memb])
      text = Data.String.unlines sections
      wc   = length (words text)
  in (sections, MkHumSurfaceStats (length sections) (length text) wc)

------------------------------------------------------------------------
-- Token table construction
------------------------------------------------------------------------

||| Extract recurring motifs from turn texts.
||| Groups words by frequency; keeps those appearing 2+ times.
public export
extractMotifs : List String -> Timestamp -> List HumTokenRow
extractMotifs texts now =
  let allWords = concatMap words texts
      lower    = map toLower allWords
      counted  = countWords lower
      frequent = filter (\entry => snd entry >= 2) counted
  in map (\entry => MkHumTokenRow (fst entry) (snd entry) "turns" now now) frequent
  where
    countWords : List String -> List (String, Nat)
    countWords [] = []
    countWords (w :: ws) =
      let filtered = filter (\x => toLower x /= toLower w) ws
          rest = assert_total (countWords filtered)
          cnt  = 1 + length (filter (\x => toLower x == toLower w) ws)
      in (w, cnt) :: rest

------------------------------------------------------------------------
-- Hum payload assembly
------------------------------------------------------------------------

||| Build a HumPayload from recent turns and feedback.
||| Enforces the boundedness invariant: at most HumTurnCap turns.
public export
buildHumPayload : ExperimentId -> SessionId -> List Turn
               -> String -> String -> Timestamp -> HumPayload
buildHumPayload eid sid allTurns feedbackCtx membraneCtx now =
  let boundedTurnIds = boundTurns (map (\t => t.id) allTurns)
      boundedTurns   = take HumTurnCap allTurns
      turnTexts      = map (\t => t.userText ++ " " ++ t.membraneText) boundedTurns
      (surfLines, stats) = generateSurface
                             (map (\t => t.membraneText) boundedTurns)
                             feedbackCtx membraneCtx
      motifs      = extractMotifs turnTexts now
      turnIndices = map (\t => t.turnIndex) boundedTurns
      derivedFrom = ["turns.active_set_json", "feedback_events", "membrane_events"]
      status      = case boundedTurns of
                      [] => HumUnavailable
                      _  => HumFresh
  in MkHumPayload
       { artifactVersion = "hum-v1"
       , generatedAt     = now
       , hpExperimentId  = eid
       , hpSessionId     = sid
       , latestTurnId    = case boundedTurns of
                             []      => Nothing
                             (t::_)  => Just t.id
       , turnIds         = boundedTurnIds
       , turnIndices     = turnIndices
       , derivedFrom     = derivedFrom
       , hpStatus        = status
       , metrics         = MkHumMetrics
                             (length boundedTurns)
                             0  -- feedback events counted at call site
                             0  -- membrane events counted at call site
                             (length motifs)
                             (length (filter (\m => m.htFrequency >= 3) motifs))
       , textSurface     = Data.String.unlines surfLines
       , surfaceLines    = surfLines
       , surfaceStats    = stats
       , tokenTable      = motifs
       }
