||| Retrieval and candidate scoring for active-set assembly.
|||
||| The active set is the bounded retrieval and prompt-compilation slice.
||| It is NOT a hidden governor or planning layer.
module Eden.Retrieval

import Data.List
import Data.String
import Eden.Types
import Eden.Config
import Eden.Regard

%default total

------------------------------------------------------------------------
-- Term-overlap similarity (Jaccard)
------------------------------------------------------------------------

||| Normalize a word for comparison: lowercase, strip short noise words.
normWord : String -> String
normWord = toLower

||| Compute Jaccard similarity between a query and a meme's combined text.
||| Returns a value in [0.0, 1.0].
wordOverlap : List String -> List String -> Nat
wordOverlap qs ms = length (filter (\w => elem w ms) qs)

||| Compute Jaccard similarity between a query and a meme's combined text.
||| Returns a value in [0.0, 1.0].
public export
termSimilarity : String -> String -> Double
termSimilarity query memeText =
  let qWords = nub (map normWord (words query))
      mWords = nub (map normWord (words memeText))
  in simFromWords qWords mWords
  where
    simFromWords : List String -> List String -> Double
    simFromWords qs ms =
      let unionSize = length (nub (qs ++ ms))
      in if unionSize == 0 then 0.0
         else cast (wordOverlap qs ms) / cast unionSize

------------------------------------------------------------------------
-- Selection scoring
------------------------------------------------------------------------

||| Composite selection score, bounded to [-12, 12].
public export
selectionScore : SelectionWeights
             -> (sim : Double) -> (act : Double) -> (reg : Double)
             -> (sb : Double)  -> (ef : Double)
             -> (sp : Double)  -> (mp : Double)
             -> Double
selectionScore w sim act reg sb ef sp mp =
  bounded (-12.0) 12.0
    ( w.wSemantic     * sim
    + w.wActivation   * act
    + w.wRegard       * reg
    + w.wSessionBias  * sb
    + w.wFeedback     * ef
    - w.wScopePenalty * sp
    - w.wMembrane     * mp
    )

------------------------------------------------------------------------
-- Component helpers
------------------------------------------------------------------------

public export
calcSessionBias : Scope -> SessionId -> Double
calcSessionBias (SessionScoped sid) current = if sid == current then 1.0 else 0.0
calcSessionBias Global              _       = 0.0

public export
calcExplicitFeedback : (rewardEma : Double) -> (riskEma : Double) -> (fc : Nat) -> Double
calcExplicitFeedback rw rk fc =
  if fc == 0 then 0.0
  else let raw   = rw - rk
           t     = if raw > 3.0 then 1.0
                   else if raw < (-3.0) then (-1.0)
                   else raw / (1.0 + abs raw)
           scale = dmin 1.0 (log (cast fc + 1.0) / log 5.0)
       in t * scale

public export
calcScopePenalty : Scope -> SessionId -> Double
calcScopePenalty (SessionScoped sid) current = if sid == current then 0.0 else 1.0
calcScopePenalty Global              _       = 0.0

public export
calcMembranePenalty : (conflicts : Nat) -> Double
calcMembranePenalty conflicts =
  if conflicts == 0 then 0.0
  else dmin 1.5 (log (cast conflicts + 1.0) / log 3.0)

------------------------------------------------------------------------
-- Score a single candidate
------------------------------------------------------------------------

public export
scoreCandidate : SelectionWeights -> SessionId
              -> (sim : Double) -> (deltaSec : Double) -> (tau : Double)
              -> (regardVal : Double) -> (scope : Scope)
              -> (rw : Double) -> (rk : Double)
              -> (fc : Nat) -> (mc : Nat)
              -> Double
scoreCandidate w curSess sim deltaSec tau reg scope rw rk fc mc =
  let act = activationDecay deltaSec tau
      sb  = calcSessionBias scope curSess
      ef  = calcExplicitFeedback rw rk fc
      sp  = calcScopePenalty scope curSess
      mp  = calcMembranePenalty mc
  in selectionScore w sim act reg sb ef sp mp

------------------------------------------------------------------------
-- Candidate construction from a meme
------------------------------------------------------------------------

||| Build a CandidateScore from a Meme and its graph context.
||| This is the pure scoring step: takes precomputed metrics, returns a score.
public export
buildCandidateScore : SelectionWeights -> SessionId
                   -> (sim : Double) -> (deltaSec : Double)
                   -> Meme -> CandidateScore
buildCandidateScore w curSess sim deltaSec m =
  let act  = activationDecay deltaSec m.activationTau
      ns   = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau deltaSec
      gm   = MkGraphMetrics 0.5 0.4 0.3  -- defaults until live graph metrics
      rb   = regardBreakdown defaultRegardWeights ns gm
      reg  = rb.totalRegard
      sb   = calcSessionBias m.scope curSess
      ef   = calcExplicitFeedback m.rewardEma m.riskEma m.feedbackCount
      sp   = calcScopePenalty m.scope curSess
      mp   = calcMembranePenalty m.membraneConflicts
      sel  = selectionScore w sim act reg sb ef sp mp
  in MkCandidateScore
       { nodeKind           = MemeNode
       , nodeId             = show m.id
       , label              = m.label
       , domain             = m.domain
       , scope              = m.scope
       , sourceKind         = m.sourceKind
       , semanticSimilarity = sim
       , activationVal      = act
       , regard             = reg
       , sessionBias        = sb
       , explicitFeedback   = ef
       , scopePenalty        = sp
       , membranePenalty    = mp
       , selection          = sel
       , text               = m.text
       , provenance         = show m.sourceKind
       }

------------------------------------------------------------------------
-- Active-set selection (top-k)
------------------------------------------------------------------------

public export
selectTopK : (k : Nat) -> List CandidateScore -> List CandidateScore
selectTopK k candidates =
  let sorted = sortBy (\a, b => compare b.selection a.selection) candidates
  in take k sorted

------------------------------------------------------------------------
-- Active-set assembly from memes
------------------------------------------------------------------------

||| Score all memes and select the top k as the active set.
||| Semantic similarity is computed via term overlap (Jaccard) between
||| the query and each meme's label + text.
public export
assembleActiveSet : SelectionWeights -> SessionId
                 -> (deltaSec : Double) -> (k : Nat)
                 -> (query : String) -> List Meme -> List CandidateScore
assembleActiveSet w curSess deltaSec k query memes =
  let candidates = map (\m => buildCandidateScore w curSess
                          (termSimilarity query (m.label ++ " " ++ m.text))
                          deltaSec m) memes
  in selectTopK k candidates
