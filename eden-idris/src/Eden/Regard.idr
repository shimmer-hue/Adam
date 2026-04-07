||| Regard valuation: EMA decay, activation, feedback signal mapping,
||| and the composite regard breakdown.
|||
||| Regard is durable selection pressure over persistent graph objects.
||| It is NOT identical to prompt-time salience or active-set membership.
module Eden.Regard

import Eden.Types
import Eden.Config

%default total

------------------------------------------------------------------------
-- Bounded arithmetic
------------------------------------------------------------------------

public export
dmax : Double -> Double -> Double
dmax a b = if a >= b then a else b

public export
dmin : Double -> Double -> Double
dmin a b = if a <= b then a else b

||| Clamp x to [lo, hi].
public export
bounded : Double -> Double -> Double -> Double
bounded lo hi x = if x < lo then lo else if x > hi then hi else x

------------------------------------------------------------------------
-- EMA (Exponential Moving Average)
------------------------------------------------------------------------

||| new = (1 - eta) * old + eta * signal
public export
ema : (old : Double) -> (signal : Double) -> (eta : Double) -> Double
ema old signal eta = ((1.0 - eta) * old) + (eta * signal)

public export
defaultEta : Double
defaultEta = 0.35

------------------------------------------------------------------------
-- Activation decay: exp(-(delta / tau))
------------------------------------------------------------------------

public export
activationDecay : (deltaSec : Double) -> (tau : Double) -> Double
activationDecay deltaSec tau =
  let safeDelta = dmax 0.0 deltaSec
      safeTau   = dmax 60.0 tau
  in exp (negate (safeDelta / safeTau))

------------------------------------------------------------------------
-- Feedback signal mapping
------------------------------------------------------------------------

public export
feedbackSignal : Verdict -> FeedbackSignal
feedbackSignal Accept = MkFeedbackSignal 1.0    (-0.1)  0.0
feedbackSignal Edit   = MkFeedbackSignal 0.45   0.15    0.9
feedbackSignal Reject = MkFeedbackSignal (-0.4) 1.0     0.0
feedbackSignal Skip   = MkFeedbackSignal 0.0    0.05    0.0

------------------------------------------------------------------------
-- Component scoring
------------------------------------------------------------------------

||| Spec: reward_i = reward_ema + 0.35 * edit_ema
public export
rewardScore : (rewardEma : Double) -> (editEma : Double) -> Double
rewardScore rw ed = bounded (-2.0) 2.0 (rw + 0.35 * ed)

||| Spec: evidence_i = log(1 + evidence_n + usage_count + 0.5 * feedback_count)
public export
evidenceScore : (evidenceN : Double) -> (usageCount : Nat) -> (feedbackCount : Nat) -> Double
evidenceScore n uc fc = bounded 0.0 2.0 (log (1.0 + n + cast uc + 0.5 * cast fc) / log 10.0)

public export
persistenceScore : (usageCount : Nat) -> (evidenceN : Double) -> (act : Double) -> Double
persistenceScore usage evN act =
  let logPart = log (cast usage + evN + 1.0) * 0.35
      actPart = act * 0.65
  in bounded 0.0 2.0 (logPart + actPart)

public export
coherenceFromMetrics : (clustering : Double) -> (normDegree : Double) -> (triangles : Double) -> Double
coherenceFromMetrics cl deg tri =
  bounded 0.0 1.5 ((cl + deg + tri) / 3.0)

public export
isolationPenalty : (normDegree : Double) -> Double
isolationPenalty deg = bounded 0.0 1.5 (1.0 - deg)

||| Spec: risk_i = risk_ema + 0.35 * contradiction_count + 0.3 * membrane_conflicts
public export
riskScore : (riskEma : Double) -> (contradictionCount : Nat) -> (membraneConflicts : Nat) -> Double
riskScore rk cc mc = bounded 0.0 2.0 (rk + 0.35 * cast cc + 0.3 * cast mc)

------------------------------------------------------------------------
-- Graph metrics input
------------------------------------------------------------------------

public export
record GraphMetrics where
  constructor MkGraphMetrics
  clustering   : Double
  normDegree   : Double
  trianglePart : Double

------------------------------------------------------------------------
-- Node state input
------------------------------------------------------------------------

public export
record NodeState where
  constructor MkNodeState
  nsRewardEma          : Double
  nsRiskEma            : Double
  nsEvidenceN          : Double
  nsUsageCount         : Nat
  nsActivTau           : Double
  nsDeltaSec           : Double
  nsFeedbackCount      : Nat
  nsEditEma            : Double
  nsContradictionCount : Nat
  nsMembraneConflicts  : Nat

------------------------------------------------------------------------
-- Regard breakdown computation
------------------------------------------------------------------------

||| Compute the full regard breakdown. Total bounded to [-8, 8].
public export
regardBreakdown : RegardWeights -> NodeState -> GraphMetrics -> RegardBreakdown
regardBreakdown w ns gm =
  let act   = activationDecay ns.nsDeltaSec ns.nsActivTau
      rw    = rewardScore ns.nsRewardEma ns.nsEditEma
      ev    = evidenceScore ns.nsEvidenceN ns.nsUsageCount ns.nsFeedbackCount
      coh   = coherenceFromMetrics gm.clustering gm.normDegree gm.trianglePart
      pers  = persistenceScore ns.nsUsageCount ns.nsEvidenceN act
      dec   = 1.0 - act
      iso   = isolationPenalty gm.normDegree
      rsk   = riskScore ns.nsRiskEma ns.nsContradictionCount ns.nsMembraneConflicts
      tot   = w.wReward      * rw
            + w.wEvidence    * ev
            + w.wCoherence   * coh
            + w.wPersistence * pers
            - w.wDecay       * dec
            - w.wIsolation   * iso
            - w.wRisk        * rsk
  in MkRegardBreakdown
       { reward           = rw
       , evidence         = ev
       , coherence        = coh
       , persistence      = pers
       , decay            = dec
       , isolationPenalty = iso
       , risk             = rsk
       , activation       = act
       , totalRegard      = bounded (-8.0) 8.0 tot
       }

------------------------------------------------------------------------
-- Feedback integration
------------------------------------------------------------------------

||| Propagation scale: how strongly a verdict propagates to related nodes.
public export
propagateScale : Verdict -> Double
propagateScale Edit = 0.65
propagateScale _    = 0.80

||| Default activation tau for memodes (§6.8): 172800 seconds (2 days).
||| Memodes decay more slowly than individual memes (86400 = 1 day).
public export
memodeDefaultTau : Double
memodeDefaultTau = 172800.0

||| Default activation tau for memes: 86400 seconds (1 day).
public export
memeDefaultTau : Double
memeDefaultTau = 86400.0

||| Apply feedback signal to a node's EMA channels.
||| Returns (newReward, newRisk, newEdit).
public export
applyFeedback : (oldRw : Double) -> (oldRk : Double) -> (oldEd : Double)
             -> FeedbackSignal -> (scale : Double)
             -> (Double, Double, Double)
applyFeedback oldRw oldRk oldEd sig scale =
  ( ema oldRw (sig.reward * scale) defaultEta
  , ema oldRk (sig.risk   * scale) defaultEta
  , ema oldEd (sig.edit   * scale) defaultEta
  )
