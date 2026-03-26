from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .config import RegardWeights, SelectionWeights


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def bounded(value: float, lo: float = -5.0, hi: float = 5.0) -> float:
    return max(lo, min(hi, value))


@dataclass(slots=True)
class RegardBreakdown:
    reward: float
    evidence: float
    coherence: float
    persistence: float
    decay: float
    isolation_penalty: float
    risk: float
    activation: float
    total: float


def activation(last_active_at: str, tau: float, now_utc: str) -> float:
    last = _parse_ts(last_active_at)
    now = _parse_ts(now_utc)
    delta = max(0.0, (now - last).total_seconds())
    tau = max(60.0, tau)
    return math.exp(-(delta / tau))


def coherence_from_metrics(metrics: dict[str, float]) -> float:
    degree = metrics.get("degree", 0.0)
    clustering = metrics.get("clustering", 0.0)
    triangles = metrics.get("triangles", 0.0)
    memode_count = metrics.get("memode_count", 0.0)
    degree_term = 1.0 - math.exp(-degree / 3.0)
    triangle_term = 1.0 - math.exp(-triangles / 2.0)
    memode_term = 1.0 - math.exp(-memode_count / 2.0)
    return bounded(0.45 * clustering + 0.25 * degree_term + 0.2 * triangle_term + 0.1 * memode_term, 0.0, 1.5)


def isolation_penalty_from_metrics(metrics: dict[str, float]) -> float:
    degree = metrics.get("degree", 0.0)
    component_size = metrics.get("component_size", 1.0)
    if degree <= 0:
        return 1.0
    return bounded((1.0 / (1.0 + degree)) + (0.5 if component_size <= 2 else 0.0), 0.0, 1.5)


def evidence_score(node: dict[str, Any]) -> float:
    support = float(node.get("evidence_n", 0.0)) + float(node.get("usage_count", 0.0))
    support += float(node.get("feedback_count", 0.0)) * 0.5
    return math.log1p(max(0.0, support))


def risk_score(node: dict[str, Any]) -> float:
    return (
        float(node.get("risk_ema", 0.0))
        + float(node.get("contradiction_count", 0.0)) * 0.35
        + float(node.get("membrane_conflicts", 0.0)) * 0.3
    )


def reward_score(node: dict[str, Any]) -> float:
    return float(node.get("reward_ema", 0.0)) + (float(node.get("edit_ema", 0.0)) * 0.35)


def persistence_score(node: dict[str, Any], activation_value: float) -> float:
    usage = float(node.get("usage_count", 0.0))
    evidence = float(node.get("evidence_n", 0.0))
    return bounded((math.log1p(usage + evidence) * 0.35) + (activation_value * 0.65), 0.0, 3.0)


def regard_breakdown(
    node: dict[str, Any],
    graph_metrics: dict[str, float],
    now_utc: str,
    weights: RegardWeights,
) -> RegardBreakdown:
    act = activation(node["last_active_at"], float(node.get("activation_tau", 86400.0)), now_utc)
    coherence = coherence_from_metrics(graph_metrics)
    isolation = isolation_penalty_from_metrics(graph_metrics)
    reward = reward_score(node)
    evidence = evidence_score(node)
    persistence = persistence_score(node, act)
    decay = 1.0 - act
    risk = risk_score(node)
    total = (
        weights.reward * reward
        + weights.evidence * evidence
        + weights.coherence * coherence
        + weights.persistence * persistence
        - weights.decay * decay
        - weights.isolation * isolation
        - weights.risk * risk
    )
    return RegardBreakdown(
        reward=reward,
        evidence=evidence,
        coherence=coherence,
        persistence=persistence,
        decay=decay,
        isolation_penalty=isolation,
        risk=risk,
        activation=act,
        total=bounded(total, -8.0, 8.0),
    )


def explicit_feedback_relevance(node: dict[str, Any]) -> float:
    feedback_count = float(node.get("feedback_count", 0.0))
    if feedback_count <= 0:
        return 0.0
    balance = float(node.get("reward_ema", 0.0)) - float(node.get("risk_ema", 0.0))
    return bounded((math.tanh(balance) * (1.0 - math.exp(-feedback_count / 3.0))), -1.0, 1.0)


def selection_score(
    *,
    semantic_similarity: float,
    activation_value: float,
    regard_value: float,
    session_bias: float,
    explicit_feedback_value: float,
    scope_penalty: float,
    membrane_penalty: float,
    weights: SelectionWeights,
) -> float:
    value = (
        weights.semantic_similarity * semantic_similarity
        + weights.activation * activation_value
        + weights.regard * regard_value
        + weights.session_bias * session_bias
        + weights.explicit_feedback * explicit_feedback_value
        - weights.scope_penalty * scope_penalty
        - weights.membrane_penalty * membrane_penalty
    )
    return bounded(value, -12.0, 12.0)


def feedback_signal(verdict: str) -> dict[str, float]:
    verdict = verdict.lower().strip()
    if verdict == "accept":
        return {"reward": 1.0, "risk": -0.1, "edit": 0.0}
    if verdict == "edit":
        return {"reward": 0.45, "risk": 0.15, "edit": 0.9}
    if verdict == "reject":
        return {"reward": -0.4, "risk": 1.0, "edit": 0.0}
    return {"reward": 0.0, "risk": 0.05, "edit": 0.0}


def ema(old: float, signal: float, eta: float = 0.35) -> float:
    return ((1.0 - eta) * old) + (eta * signal)
