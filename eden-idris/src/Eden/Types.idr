||| Core ontology types for the EDEN/Adam runtime.
||| Memes are first-class; memodes are derived. Regard is durable selection
||| pressure, distinct from prompt-time salience.
module Eden.Types

import Data.Vect
import Data.List
import Data.String

%default total

------------------------------------------------------------------------
-- Identifiers (phantom-tagged)
------------------------------------------------------------------------

public export
data Id : Type -> Type where
  MkId : String -> Id a

public export
Eq (Id a) where
  (MkId x) == (MkId y) = x == y

public export
Show (Id a) where
  show (MkId s) = s

public export
unwrapId : Id a -> String
unwrapId (MkId s) = s

-- Phantom tags
public export data ExperimentTag : Type where
public export data SessionTag    : Type where
public export data TurnTag       : Type where
public export data MemeTag       : Type where
public export data MemodeTag     : Type where
public export data EdgeTag       : Type where
public export data DocumentTag   : Type where
public export data ChunkTag      : Type where
public export data AgentTag      : Type where
public export data FeedbackTag   : Type where

public export ExperimentId : Type
ExperimentId = Id ExperimentTag

public export SessionId : Type
SessionId = Id SessionTag

public export TurnId : Type
TurnId = Id TurnTag

public export MemeId : Type
MemeId = Id MemeTag

public export MemodeId : Type
MemodeId = Id MemodeTag

public export EdgeId : Type
EdgeId = Id EdgeTag

public export DocumentId : Type
DocumentId = Id DocumentTag

public export ChunkId : Type
ChunkId = Id ChunkTag

public export AgentId : Type
AgentId = Id AgentTag

public export FeedbackId : Type
FeedbackId = Id FeedbackTag

------------------------------------------------------------------------
-- Timestamps
------------------------------------------------------------------------

public export
record Timestamp where
  constructor MkTimestamp
  isoString : String

public export
Show Timestamp where
  show ts = ts.isoString

------------------------------------------------------------------------
-- Domain (knowledge vs behavior)
------------------------------------------------------------------------

public export
data Domain = Knowledge | Behavior

public export
Eq Domain where
  Knowledge == Knowledge = True
  Behavior  == Behavior  = True
  _         == _         = False

public export
Show Domain where
  show Knowledge = "knowledge"
  show Behavior  = "behavior"

------------------------------------------------------------------------
-- Source kind
------------------------------------------------------------------------

public export
data SourceKind
  = TurnUser
  | TurnAdam
  | FeedbackSource
  | IngestSource
  | SeedSource
  | ManualSource

public export
Show SourceKind where
  show TurnUser       = "turn_user"
  show TurnAdam       = "turn_adam"
  show FeedbackSource = "feedback"
  show IngestSource   = "document"
  show SeedSource     = "seed"
  show ManualSource   = "manual"

------------------------------------------------------------------------
-- Scope
------------------------------------------------------------------------

public export
data Scope = Global | SessionScoped SessionId

public export
Show Scope where
  show Global             = "global"
  show (SessionScoped id) = "session:" ++ show id

------------------------------------------------------------------------
-- Verdict (feedback)
------------------------------------------------------------------------

||| Explicit operator verdicts. Accept/reject require explanation;
||| edit requires explanation + corrected text.
public export
data Verdict = Accept | Reject | Edit | Skip

public export
Eq Verdict where
  Accept == Accept = True
  Reject == Reject = True
  Edit   == Edit   = True
  Skip   == Skip   = True
  _      == _      = False

public export
Show Verdict where
  show Accept = "accept"
  show Reject = "reject"
  show Edit   = "edit"
  show Skip   = "skip"

public export
record FeedbackSignal where
  constructor MkFeedbackSignal
  reward : Double
  risk   : Double
  edit   : Double

||| Type-level proof that a verdict carries its required explanation.
||| Encodes Austin felicity conditions.
public export
data ExplainedVerdict : Verdict -> Type where
  ExplainAccept : (explanation : String) ->
                  ExplainedVerdict Accept
  ExplainReject : (explanation : String) ->
                  ExplainedVerdict Reject
  ExplainEdit   : (explanation : String) ->
                  (correctedText : String) ->
                  ExplainedVerdict Edit
  ExplainSkip   : ExplainedVerdict Skip

||| Extract the explanation text from any explained verdict.
public export
explanationText : {v : Verdict} -> ExplainedVerdict v -> String
explanationText (ExplainAccept e)   = e
explanationText (ExplainReject e)   = e
explanationText (ExplainEdit e _)   = e
explanationText ExplainSkip         = ""

------------------------------------------------------------------------
-- Edge types
------------------------------------------------------------------------

public export
data EdgeType
  = CoOccursWith
  | AuthorOf
  | Influences
  | Supports
  | Reinforces
  | Refines
  | ContradictsEdge
  | DerivedFrom
  | RelatesTo
  | ChunkOf
  | MemberOf
  | SourceDocument
  | HasTurn
  | HasFeedback
  | BelongsToSession
  | BelongsToAgent
  | ContextualizesDocument
  | FedBackBy
  | OccursIn

public export
Show EdgeType where
  show CoOccursWith    = "CO_OCCURS_WITH"
  show AuthorOf        = "AUTHOR_OF"
  show Influences      = "INFLUENCES"
  show Supports        = "SUPPORTS"
  show Reinforces      = "REINFORCES"
  show Refines         = "REFINES"
  show ContradictsEdge = "CONTRADICTS"
  show DerivedFrom     = "DERIVED_FROM"
  show RelatesTo       = "RELATES_TO"
  show ChunkOf         = "CHUNK_OF"
  show MemberOf        = "MEMBER_OF"
  show SourceDocument  = "SOURCE_DOCUMENT"
  show HasTurn         = "HAS_TURN"
  show HasFeedback     = "HAS_FEEDBACK"
  show BelongsToSession = "BELONGS_TO_SESSION"
  show BelongsToAgent  = "BELONGS_TO_AGENT"
  show ContextualizesDocument = "CONTEXTUALIZES_DOCUMENT"
  show FedBackBy       = "FED_BACK_BY"
  show OccursIn        = "OCCURS_IN"

public export
Eq EdgeType where
  CoOccursWith    == CoOccursWith    = True
  AuthorOf        == AuthorOf        = True
  Influences      == Influences      = True
  Supports        == Supports        = True
  Reinforces      == Reinforces      = True
  Refines         == Refines         = True
  ContradictsEdge == ContradictsEdge = True
  DerivedFrom     == DerivedFrom     = True
  RelatesTo       == RelatesTo       = True
  ChunkOf         == ChunkOf         = True
  MemberOf        == MemberOf        = True
  SourceDocument  == SourceDocument  = True
  HasTurn         == HasTurn         = True
  HasFeedback     == HasFeedback     = True
  BelongsToSession == BelongsToSession = True
  BelongsToAgent  == BelongsToAgent  = True
  ContextualizesDocument == ContextualizesDocument = True
  FedBackBy       == FedBackBy       = True
  OccursIn        == OccursIn        = True
  _               == _               = False

public export
data NodeKind = MemeNode | MemodeNode | DocumentNode | TurnNode | ChunkNode
              | SessionNode | AgentNode | FeedbackNode

public export
Show NodeKind where
  show MemeNode     = "meme"
  show MemodeNode   = "memode"
  show DocumentNode = "document"
  show TurnNode     = "turn"
  show ChunkNode    = "chunk"
  show SessionNode  = "session"
  show AgentNode    = "agent"
  show FeedbackNode = "feedback"

public export
Eq NodeKind where
  MemeNode     == MemeNode     = True
  MemodeNode   == MemodeNode   = True
  DocumentNode == DocumentNode = True
  TurnNode     == TurnNode     = True
  ChunkNode    == ChunkNode    = True
  SessionNode  == SessionNode  = True
  AgentNode    == AgentNode    = True
  FeedbackNode == FeedbackNode = True
  _            == _            = False

------------------------------------------------------------------------
-- Meme
------------------------------------------------------------------------

public export
record Meme where
  constructor MkMeme
  id                 : MemeId
  experimentId       : ExperimentId
  label              : String
  canonicalLabel     : String
  text               : String
  domain             : Domain
  sourceKind         : SourceKind
  scope              : Scope
  evidenceN          : Double
  usageCount         : Nat
  rewardEma          : Double
  riskEma            : Double
  editEma            : Double
  skipCount          : Nat
  contradictionCount : Nat
  membraneConflicts  : Nat
  feedbackCount      : Nat
  activationTau      : Double
  lastActiveAt       : Timestamp
  createdAt          : Timestamp
  updatedAt          : Timestamp
  metadataJson       : String

------------------------------------------------------------------------
-- Memode (derived, requires >= 2 behavior memes)
------------------------------------------------------------------------

public export
record Memode where
  constructor MkMemode
  id            : MemodeId
  experimentId  : ExperimentId
  label         : String
  memberHash    : String
  summary       : String
  domain        : Domain
  scope         : Scope
  evidenceN     : Double
  usageCount    : Nat
  rewardEma     : Double
  riskEma       : Double
  editEma       : Double
  feedbackCount : Nat
  activationTau : Double
  lastActiveAt  : Timestamp
  createdAt     : Timestamp
  updatedAt     : Timestamp
  metadataJson  : String

||| Proof that a memode has >= 2 behavior-domain member memes.
public export
data AdmissibleMemode : Type where
  MkAdmissible : (memode : Memode)
              -> (members : Vect (S (S n)) MemeId)
              -> AdmissibleMemode

------------------------------------------------------------------------
-- Edge
------------------------------------------------------------------------

public export
record Edge where
  constructor MkEdge
  id             : EdgeId
  experimentId   : ExperimentId
  srcKind        : NodeKind
  srcId          : String
  dstKind        : NodeKind
  dstId          : String
  edgeType       : EdgeType
  weight         : Double
  provenanceJson : String
  createdAt      : Timestamp
  updatedAt      : Timestamp

------------------------------------------------------------------------
-- Session, Turn, Experiment
------------------------------------------------------------------------

public export
data ExperimentStatus = Active | Completed | Archived

public export
Show ExperimentStatus where
  show Active    = "active"
  show Completed = "completed"
  show Archived  = "archived"

public export
data ExperimentMode = Blank | Seeded | Resumed

public export
Show ExperimentMode where
  show Blank   = "blank"
  show Seeded  = "seeded"
  show Resumed = "resumed"

public export
record Experiment where
  constructor MkExperiment
  id        : ExperimentId
  name      : String
  slug      : String
  mode      : ExperimentMode
  status    : ExperimentStatus
  createdAt : Timestamp
  updatedAt : Timestamp

public export
record Session where
  constructor MkSession
  id           : SessionId
  experimentId : ExperimentId
  agentId      : AgentId
  title        : String
  createdAt    : Timestamp
  updatedAt    : Timestamp
  endedAt      : Maybe Timestamp

public export
record Turn where
  constructor MkTurn
  id            : TurnId
  experimentId  : ExperimentId
  sessionId     : SessionId
  turnIndex     : Nat
  userText      : String
  promptContext : String
  responseText  : String
  membraneText  : String
  createdAt     : Timestamp

------------------------------------------------------------------------
-- Document & Chunk
------------------------------------------------------------------------

public export
data DocStatus = Processing | Ingested | Failed

public export
Show DocStatus where
  show Processing = "processing"
  show Ingested   = "ingested"
  show Failed     = "failed"

public export
data DocKind = PDF | Markdown | PlainText | CSV

public export
Show DocKind where
  show PDF       = "pdf"
  show Markdown  = "markdown"
  show PlainText = "txt"
  show CSV       = "csv"

public export
record Document where
  constructor MkDocument
  id           : DocumentId
  experimentId : ExperimentId
  path         : String
  kind         : DocKind
  title        : String
  sha256       : String
  status       : DocStatus
  metadataJson : String
  createdAt    : Timestamp

public export
record Chunk where
  constructor MkChunk
  id           : ChunkId
  experimentId : ExperimentId
  documentId   : DocumentId
  chunkIndex   : Nat
  pageNumber   : Maybe Nat
  text         : String
  metadataJson : String
  createdAt    : Timestamp

------------------------------------------------------------------------
-- Membrane events
------------------------------------------------------------------------

public export
data MembraneEventType
  = ControlCharStripped
  | ReasoningSplit
  | SupportStripped
  | LabelStripped
  | Trimmed
  | Passthrough

public export
Show MembraneEventType where
  show ControlCharStripped = "CONTROL_CHAR_STRIPPED"
  show ReasoningSplit      = "REASONING_SPLIT"
  show SupportStripped     = "SUPPORT_STRIPPED"
  show LabelStripped       = "LABEL_STRIPPED"
  show Trimmed             = "TRIMMED"
  show Passthrough         = "PASSTHROUGH"

------------------------------------------------------------------------
-- Trace events
------------------------------------------------------------------------

public export
data TraceLevel = Info | Error

public export
Show TraceLevel where
  show Info  = "INFO"
  show Error = "ERROR"

public export
data TraceEventType
  = TraceTurn
  | TraceFeedback
  | TraceIngest
  | TraceExport
  | TraceGeneration
  | TraceHumRefresh
  | TraceObservatoryCommit
  | TraceObservatoryRevert
  | TraceGraphNormalization
  | TraceGraphTaxonomy
  | TraceGraphCoherence
  | TraceGraphWakeup

public export
Show TraceEventType where
  show TraceTurn              = "TURN"
  show TraceFeedback          = "FEEDBACK"
  show TraceIngest            = "INGEST"
  show TraceExport            = "EXPORT"
  show TraceGeneration        = "GENERATION"
  show TraceHumRefresh        = "HUM_REFRESH"
  show TraceObservatoryCommit = "OBSERVATORY_COMMIT"
  show TraceObservatoryRevert = "OBSERVATORY_REVERT"
  show TraceGraphNormalization = "GRAPH_NORMALIZATION"
  show TraceGraphTaxonomy     = "GRAPH_TAXONOMY_AUDIT"
  show TraceGraphCoherence    = "GRAPH_COHERENCE_REWEAVE"
  show TraceGraphWakeup       = "GRAPH_WAKEUP_AUDIT"

------------------------------------------------------------------------
-- Measurement events (observatory)
------------------------------------------------------------------------

public export
data MeasurementAction
  = EdgeAdd | EdgeUpdate | EdgeRemove
  | MemodeAssert | MemodeUpdateMembership
  | NodeEdit | MotifAnnotation
  | GeometryMeasurementRun | AblationMeasurementRun
  | MeasurementRevert

public export
Show MeasurementAction where
  show EdgeAdd                = "edge_add"
  show EdgeUpdate             = "edge_update"
  show EdgeRemove             = "edge_remove"
  show MemodeAssert           = "memode_assert"
  show MemodeUpdateMembership = "memode_update_membership"
  show NodeEdit               = "node_edit"
  show MotifAnnotation        = "motif_annotation"
  show GeometryMeasurementRun = "geometry_measurement_run"
  show AblationMeasurementRun = "ablation_measurement_run"
  show MeasurementRevert      = "revert"

public export
data MeasurementState = Previewed | Committed | Reverted

public export
Show MeasurementState where
  show Previewed = "previewed"
  show Committed = "committed"
  show Reverted  = "reverted"

------------------------------------------------------------------------
-- Evidence and provenance labels
------------------------------------------------------------------------

public export
data EvidenceLabel = Observed | Derived | Speculative

public export
Show EvidenceLabel where
  show Observed    = "OBSERVED"
  show Derived     = "DERIVED"
  show Speculative = "SPECULATIVE"

public export
data ProvenanceLabel = OperatorAsserted | OperatorRefined | AutoDerived

public export
Show ProvenanceLabel where
  show OperatorAsserted = "OPERATOR_ASSERTED"
  show OperatorRefined  = "OPERATOR_REFINED"
  show AutoDerived      = "AUTO_DERIVED"

------------------------------------------------------------------------
-- Regard breakdown
------------------------------------------------------------------------

public export
record RegardBreakdown where
  constructor MkRegardBreakdown
  reward           : Double
  evidence         : Double
  coherence        : Double
  persistence      : Double
  decay            : Double
  isolationPenalty : Double
  risk             : Double
  activation       : Double
  totalRegard      : Double

------------------------------------------------------------------------
-- Candidate score (retrieval)
------------------------------------------------------------------------

public export
record CandidateScore where
  constructor MkCandidateScore
  nodeKind           : NodeKind
  nodeId             : String
  label              : String
  domain             : Domain
  scope              : Scope
  sourceKind         : SourceKind
  semanticSimilarity : Double
  activationVal      : Double
  regard             : Double
  sessionBias        : Double
  explicitFeedback   : Double
  scopePenalty       : Double
  membranePenalty    : Double
  selection          : Double
  text               : String
  provenance         : String

------------------------------------------------------------------------
-- Graph counts
------------------------------------------------------------------------

public export
record GraphCounts where
  constructor MkGraphCounts
  memeCount          : Nat
  memodeCount        : Nat
  edgeCount          : Nat
  turnCount          : Nat
  feedbackCount      : Nat
  measurementCount   : Nat
  membraneEventCount : Nat
  traceEventCount    : Nat

------------------------------------------------------------------------
-- Index result
------------------------------------------------------------------------

public export
record IndexResult where
  constructor MkIndexResult
  memeIds    : List MemeId
  memodeIds  : List MemodeId
  edgeIds    : List EdgeId
  newMemes   : Nat
  newMemodes : Nat
  newEdges   : Nat

------------------------------------------------------------------------
-- Agent
------------------------------------------------------------------------

public export
record Agent where
  constructor MkAgent
  id           : AgentId
  experimentId : ExperimentId
  name         : String
  persona      : String
  createdAt    : Timestamp

------------------------------------------------------------------------
-- Active set entry (per-turn snapshot)
------------------------------------------------------------------------

public export
record ActiveSetEntry where
  constructor MkActiveSetEntry
  id             : String
  experimentId   : ExperimentId
  sessionId      : SessionId
  turnId         : TurnId
  nodeKind       : NodeKind
  nodeId         : String
  label          : String
  domain         : Domain
  selectionScore : Double
  semanticSim    : Double
  activationVal  : Double
  regardVal      : Double
  createdAt      : Timestamp

------------------------------------------------------------------------
-- Measurement event (observatory audit trail)
------------------------------------------------------------------------

public export
record MeasurementEvent where
  constructor MkMeasurementEvent
  id                : String
  experimentId      : ExperimentId
  sessionId         : SessionId
  action            : MeasurementAction
  state             : MeasurementState
  operator          : String
  evidence          : String
  beforeState       : String
  proposedState     : String
  committedState    : String
  revertOf          : String
  turnId            : String
  targetIdsJson     : String
  rationale         : String
  operatorLabel     : String
  measurementMethod : String
  confidence        : Double
  createdAt         : Timestamp

------------------------------------------------------------------------
-- Export artifact registry
------------------------------------------------------------------------

public export
record ExportArtifact where
  constructor MkExportArtifact
  id           : String
  experimentId : ExperimentId
  artifactType : String
  path         : String
  graphHash    : String
  createdAt    : Timestamp

------------------------------------------------------------------------
-- Turn metadata (inference profile, budget, reasoning)
------------------------------------------------------------------------

public export
record TurnMetadata where
  constructor MkTurnMetadata
  turnId                : TurnId
  inferenceModeReq      : String
  inferenceModeEff      : String
  budgetMode            : String
  budgetPressure        : String
  budgetUsedTokens      : Nat
  budgetRemainingTokens : Nat
  activeSetSize         : Nat
  reasoningText         : String
  temperature           : Double
  maxOutput             : Nat
  responseCap           : Nat
  profileName           : String
  selectionSource       : String
  countMethod           : String
  createdAt             : Timestamp
