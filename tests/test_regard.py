from __future__ import annotations

from eden.config import RegardWeights, SelectionWeights
from eden.regard import explicit_feedback_relevance, regard_breakdown, selection_score


def test_regard_increases_with_evidence_and_reward() -> None:
    node = {
        "last_active_at": "2026-03-06T00:00:00+00:00",
        "activation_tau": 86400,
        "evidence_n": 8,
        "usage_count": 6,
        "feedback_count": 4,
        "reward_ema": 0.8,
        "risk_ema": 0.1,
        "edit_ema": 0.2,
        "contradiction_count": 0,
        "membrane_conflicts": 0,
    }
    metrics = {"degree": 4.0, "clustering": 0.75, "triangles": 3.0, "component_size": 5.0, "memode_count": 2.0}
    breakdown = regard_breakdown(node, metrics, "2026-03-06T06:00:00+00:00", RegardWeights())
    assert breakdown.total > 0
    assert explicit_feedback_relevance(node) > 0


def test_selection_penalizes_scope_and_membrane_conflicts() -> None:
    value = selection_score(
        semantic_similarity=0.8,
        activation_value=0.7,
        regard_value=1.1,
        session_bias=0.0,
        explicit_feedback_value=0.3,
        scope_penalty=1.0,
        membrane_penalty=1.0,
        weights=SelectionWeights(),
    )
    assert value < 2.0
