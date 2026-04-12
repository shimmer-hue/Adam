||| EdenRuntime: central orchestrator for the direct turn loop.
|||
||| The v1 turn loop is:
|||   input -> retrieve/assemble -> deliberate -> Adam response -> membrane -> feedback -> graph update
|||
||| The deliberation phase (Talmud layer) checks coverage, surfaces
||| dissent, and retrieves precedent — all observable, all logged.
||| NO hidden governor, NO recursive decomposition, NO latent planning layer.
||| adam_auto falls back to runtime_auto.
|||
||| Dependent types encode the turn-loop state machine and the
||| observatory measurement protocol.
module Eden.Runtime

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
import Eden.Storage
import Eden.Models.Base

------------------------------------------------------------------------
-- Turn-loop state machine
------------------------------------------------------------------------

||| The turn loop proceeds through well-defined phases.
public export
data TurnPhase
  = Idle
  | Assembling
  | Deliberating
  | Generating
  | MembraneApplied
  | AwaitingFeedback
  | FeedbackIntegrated

||| Valid phase transitions (only forward along the pipeline).
public export
data ValidTransition : TurnPhase -> TurnPhase -> Type where
  IdleToAssemble       : ValidTransition Idle Assembling
  AssembleToDeliberate : ValidTransition Assembling Deliberating
  DeliberateToGenerate : ValidTransition Deliberating Generating
  GenerateToMembrane   : ValidTransition Generating MembraneApplied
  MembraneToFeedback   : ValidTransition MembraneApplied AwaitingFeedback
  FeedbackToIntegrate  : ValidTransition AwaitingFeedback FeedbackIntegrated
  IntegrateToIdle      : ValidTransition FeedbackIntegrated Idle
  MembraneToIdle       : ValidTransition MembraneApplied Idle

------------------------------------------------------------------------
-- Turn preview (pre-generation assembly)
------------------------------------------------------------------------

public export
record TurnPreview where
  constructor MkTurnPreview
  tpSessionId    : SessionId
  tpExperimentId : ExperimentId
  tpUserText     : String
  tpSystemPrompt : String
  tpConvPrompt   : String
  tpActiveSet    : List CandidateScore
  tpProfile      : ResolvedProfile
  tpBudget       : BudgetEstimate
  tpHistory      : List Turn

------------------------------------------------------------------------
-- Chat outcome
------------------------------------------------------------------------

public export
record ChatOutcome where
  constructor MkChatOutcome
  coTurn           : Turn
  coActiveSet      : List CandidateScore
  coMembraneEvents : List MembraneEventType
  coGraphCounts    : GraphCounts
  coBudget         : BudgetEstimate
  coProfile        : ResolvedProfile
  coReasoningText  : String

------------------------------------------------------------------------
-- Feedback outcome
------------------------------------------------------------------------

public export
record FeedbackOutcome where
  constructor MkFeedbackOutcome
  foFeedbackId     : FeedbackId
  foVerdict        : Verdict
  foSignal         : FeedbackSignal
  foAffectedMemes  : List MemeId
  foAffectedMemodes : List MemodeId
  foIndexResult    : IndexResult

------------------------------------------------------------------------
-- Prompt assembly
------------------------------------------------------------------------

public export
buildSystemPrompt : String -> String -> String
buildSystemPrompt agentName principles =
  "You are " ++ agentName ++ ".\n\n" ++ principles

public export
buildConversationPrompt : List CandidateScore -> List Turn -> String -> String -> String
buildConversationPrompt activeSet history feedbackCtx userText =
  let asSection = case activeSet of
        [] => ""
        items =>
          "## Active Context\n\n"
          ++ unlines (map (\c => "- [" ++ c.label ++ "] " ++ substr 0 200 c.text) items)
          ++ "\n\n"
      histSection = case history of
        [] => ""
        turns =>
          "## Recent History\n\n"
          ++ unlines (map (\t => "User: " ++ substr 0 100 t.userText
                              ++ "\nAdam: " ++ substr 0 200 t.membraneText) turns)
          ++ "\n\n"
      fbSection = if feedbackCtx == "" then ""
                  else "## Feedback\n\n" ++ feedbackCtx ++ "\n\n"
  in asSection ++ histSection ++ fbSection ++ "## Current\n\nUser: " ++ userText

------------------------------------------------------------------------
-- Text index request
------------------------------------------------------------------------

public export
record TextIndexRequest where
  constructor MkTextIndexRequest
  tirExperimentId : ExperimentId
  tirTurnId       : TurnId
  tirSessionId    : SessionId
  tirText         : String
  tirDomain       : Domain
  tirSourceKind   : SourceKind
  tirActor        : String

------------------------------------------------------------------------
-- Observatory measurement state machine
------------------------------------------------------------------------

||| Preview -> Commit -> (optionally) Revert.
||| Each transition is a distinct attributable act with its own event.

||| Proof that a measurement has been previewed.
public export
data HasPreview : String -> Type where
  MkHasPreview : HasPreview eventId

||| Proof that a measurement has been committed.
public export
data HasCommit : String -> Type where
  MkHasCommit : HasCommit eventId

||| Observatory operations with felicity-conditioned state machine.
public export
interface GraphStore m => ObservatoryOps (m : Type -> Type) where
  ||| Preview a graph mutation (does not persist yet).
  obsPreview : ExperimentId -> SessionId -> MeasurementAction
            -> String -> m (eid : String ** HasPreview eid)

  ||| Commit a previewed mutation. Requires preview proof.
  obsCommit  : (eventId : String) -> HasPreview eventId
            -> m (HasCommit eventId)

  ||| Revert a committed mutation. Reversion is itself a new act.
  obsRevert  : (eventId : String) -> HasCommit eventId -> m ()

------------------------------------------------------------------------
-- Deliberation result (Talmud layer output)
------------------------------------------------------------------------

||| Output of the deliberation phase: coverage assessment, dissenting
||| positions, and precedent from prior turns. All observable.
public export
record DeliberationResult where
  constructor MkDeliberation
  ||| Fraction of query concepts covered by active set [0.0, 1.0].
  dlCoverage       : Double
  ||| Concepts in the query not covered by any active-set meme.
  dlGaps           : List String
  ||| Memes with relevant content but low regard (minority opinions).
  dlDissent        : List (MemeId, Double)
  ||| Prior turns with similar context (precedent retrieval).
  dlPrecedents     : List TurnId
  ||| Whether a second retrieval pass was triggered by low coverage.
  dlSecondPassUsed : Bool
  ||| Visible deliberation trace (the shakla v'tarya).
  dlTrace          : String

------------------------------------------------------------------------
-- Phase-enforced turn pipeline
------------------------------------------------------------------------

||| A turn in a specific phase, carrying accumulated state.
||| The phantom `phase` parameter is checked at compile time.
public export
data PhasedTurn : TurnPhase -> Type where
  ||| Idle: no turn in progress.
  PTIdle       : PhasedTurn Idle
  ||| Assembly complete: active set and prompt ready.
  PTAssembled  : (activeSet : List CandidateScore)
              -> (profile : ResolvedProfile)
              -> (budget : BudgetEstimate)
              -> (convPrompt : String)
              -> PhasedTurn Assembling
  ||| Deliberation complete: coverage assessed, dissent surfaced.
  PTDeliberated : (activeSet : List CandidateScore)
               -> (deliberation : DeliberationResult)
               -> (profile : ResolvedProfile)
               -> (budget : BudgetEstimate)
               -> (convPrompt : String)
               -> PhasedTurn Deliberating
  ||| Generation complete: raw response available.
  PTGenerated  : (rawText : String)
              -> (reasoningText : String)
              -> (activeSet : List CandidateScore)
              -> (profile : ResolvedProfile)
              -> PhasedTurn Generating
  ||| Membrane applied: cleaned response available.
  PTMembrane   : (cleanedText : String)
              -> (membraneEvents : List MembraneEventType)
              -> (reasoningText : String)
              -> (activeSet : List CandidateScore)
              -> (profile : ResolvedProfile)
              -> PhasedTurn MembraneApplied
  ||| Awaiting feedback: response delivered, waiting for verdict.
  PTAwaiting   : (turn : Turn)
              -> (activeSet : List CandidateScore)
              -> (membraneEvents : List MembraneEventType)
              -> (profile : ResolvedProfile)
              -> PhasedTurn AwaitingFeedback
  ||| Feedback integrated: graph updated.
  PTIntegrated : (turn : Turn)
              -> (verdict : Verdict)
              -> (affectedMemes : Nat)
              -> PhasedTurn FeedbackIntegrated

||| Advance a turn from one phase to the next.
||| The ValidTransition proof ensures only legal transitions compile.
public export
advanceTurn : ValidTransition from to
           -> PhasedTurn from
           -> PhasedTurn to
           -> PhasedTurn to
advanceTurn _ _ target = target

------------------------------------------------------------------------
-- Pipeline step records
------------------------------------------------------------------------

||| Result of the assembly step.
public export
record AssemblyResult where
  constructor MkAssemblyResult
  arActiveSet   : List CandidateScore
  arProfile     : ResolvedProfile
  arBudget      : BudgetEstimate
  arSysPrompt   : String
  arConvPrompt  : String
  arHistory     : List Turn

||| Result of the generation step.
public export
record GenerationResult where
  constructor MkGenerationResult
  grRawText       : String
  grReasoningText : String
  grTokenEstimate : Nat

||| Result of the membrane step.
public export
record MembraneOutcome where
  constructor MkMembraneOutcome
  moCleanedText   : String
  moEvents        : List MembraneEventType
  moReasoningText : String

||| Result of the index step (post-turn concept extraction).
public export
record IndexingOutcome where
  constructor MkIndexingOutcome
  ixNewMemes  : Nat
  ixNewEdges  : Nat
  ixConcepts  : List String
  ixMemodes   : Nat

------------------------------------------------------------------------
-- Pure pipeline steps
------------------------------------------------------------------------

||| Assemble the prompt from active set, history, and user text.
||| Pure: no IO needed.
public export
assemblePrompt : String -> String -> List CandidateScore
              -> List Turn -> String -> String
              -> AssemblyResult
assemblePrompt agentName principles activeSet history feedbackCtx userText =
  let profile = resolveProfile defaultProfileRequest
                  (MkTimestamp "now")
      pp      = presetParams profile.rpBudgetMode
      sysP    = buildSystemPrompt agentName principles
      convP   = buildConversationPrompt activeSet history feedbackCtx userText
      sysLen  = length sysP
      asLen   = length convP
      budget  = estimateBudget
                  (cast pp.ppBudgetTokens * 2)
                  pp.ppBudgetTokens
                  (cast pp.ppMaxOutput)
                  sysLen asLen 0 0 (length userText)
                  pp.ppResponseCap
                  (length activeSet)
                  (length history) False
  in MkAssemblyResult activeSet profile budget sysP convP history

||| Apply the membrane pipeline to generation output. Pure.
public export
applyMembraneStep : Nat -> String -> MembraneOutcome
applyMembraneStep respCap rawText =
  let mr = applyMembrane respCap rawText
  in MkMembraneOutcome mr.cleanedText mr.events mr.reasoningText

------------------------------------------------------------------------
-- Full turn summary
------------------------------------------------------------------------

||| Complete record of what happened in a turn, produced after all
||| phases complete. This is the type-safe equivalent of Python's
||| ChatOutcome + FeedbackOutcome combined.
public export
record TurnSummary where
  constructor MkTurnSummary
  tsPhase          : TurnPhase
  tsTurn           : Turn
  tsActiveSet      : List CandidateScore
  tsMembraneEvents : List MembraneEventType
  tsProfile        : ResolvedProfile
  tsBudget         : BudgetEstimate
  tsReasoningText  : String
  tsIndexing       : IndexingOutcome
  tsVerdict        : Maybe Verdict

------------------------------------------------------------------------
-- Mode invariant proofs
------------------------------------------------------------------------

||| adam_auto always resolves to runtime_auto in v1.
public export
noHiddenGovernor : resolveMode AdamAuto = RuntimeAuto
noHiddenGovernor = Refl

||| manual mode is never overridden.
public export
manualRespected : resolveMode Manual = Manual
manualRespected = Refl

------------------------------------------------------------------------
-- Phase transition proofs
------------------------------------------------------------------------

||| The pipeline is acyclic (except the Idle reset).
||| Every forward path from Idle reaches either AwaitingFeedback
||| or loops back to Idle via MembraneToIdle.
||| This documents the intended state machine for the reader.
public export
fullPipelineWitness : ( ValidTransition Idle Assembling
                      , ValidTransition Assembling Deliberating
                      , ValidTransition Deliberating Generating
                      , ValidTransition Generating MembraneApplied
                      , ValidTransition MembraneApplied AwaitingFeedback
                      , ValidTransition AwaitingFeedback FeedbackIntegrated
                      , ValidTransition FeedbackIntegrated Idle )
fullPipelineWitness =
  ( IdleToAssemble
  , AssembleToDeliberate
  , DeliberateToGenerate
  , GenerateToMembrane
  , MembraneToFeedback
  , FeedbackToIntegrate
  , IntegrateToIdle )

||| The skip-feedback path (membrane -> idle directly).
public export
skipFeedbackWitness : ValidTransition MembraneApplied Idle
skipFeedbackWitness = MembraneToIdle
