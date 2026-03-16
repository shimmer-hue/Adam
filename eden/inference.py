from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .config import RuntimeSettings
from .utils import now_utc


INFERENCE_MODES = {"manual", "runtime_auto", "adam_auto"}
MAX_HISTORY_TURNS = 256
PROFILE_PRESETS: dict[str, dict[str, float | int]] = {
    "tight": {
        "prompt_budget_tokens": 3072,
        "temperature": 0.25,
        "max_output_tokens": 320,
        "retrieval_depth": 8,
        "max_context_items": 6,
        "response_char_cap": 1100,
    },
    "balanced": {
        "prompt_budget_tokens": 5120,
        "temperature": 0.4,
        "max_output_tokens": 480,
        "retrieval_depth": 12,
        "max_context_items": 8,
        "response_char_cap": 1600,
    },
    "wide": {
        "prompt_budget_tokens": 7168,
        "temperature": 0.55,
        "max_output_tokens": 640,
        "retrieval_depth": 16,
        "max_context_items": 10,
        "response_char_cap": 2200,
    },
}


@dataclass(slots=True)
class InferenceProfileRequest:
    mode: str = "manual"
    temperature: float = 0.4
    max_output_tokens: int = 480
    top_p: float = 0.9
    repetition_penalty: float = 1.05
    retrieval_depth: int = 12
    max_context_items: int = 8
    history_turns: int = 3
    response_char_cap: int = 1600
    low_motion: bool = False
    debug: bool = True
    budget_mode: str = "balanced"
    title: str = "Operator Session"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ResolvedInferenceProfile:
    requested_mode: str
    effective_mode: str
    profile_name: str
    budget_mode: str
    prompt_budget_tokens: int
    temperature: float
    max_output_tokens: int
    top_p: float
    repetition_penalty: float
    retrieval_depth: int
    max_context_items: int
    history_turns: int
    response_char_cap: int
    low_motion: bool
    debug: bool
    selection_source: str
    rationale: list[str]
    heuristic_inputs: dict[str, Any]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_profile_request(settings: RuntimeSettings) -> InferenceProfileRequest:
    return InferenceProfileRequest(
        mode="manual",
        temperature=0.4,
        max_output_tokens=480,
        top_p=0.9,
        repetition_penalty=1.05,
        retrieval_depth=settings.retrieval_depth,
        max_context_items=settings.max_context_items,
        history_turns=settings.history_turns,
        response_char_cap=1600,
        low_motion=settings.low_motion,
        debug=settings.debug,
        budget_mode="balanced",
    )


def request_from_dict(payload: dict[str, Any] | None, settings: RuntimeSettings) -> InferenceProfileRequest:
    base = default_profile_request(settings)
    if not payload:
        return base
    return clamp_request(
        InferenceProfileRequest(
            mode=str(payload.get("mode", base.mode)),
            temperature=float(payload.get("temperature", base.temperature)),
            max_output_tokens=int(payload.get("max_output_tokens", base.max_output_tokens)),
            top_p=float(payload.get("top_p", base.top_p)),
            repetition_penalty=float(payload.get("repetition_penalty", base.repetition_penalty)),
            retrieval_depth=int(payload.get("retrieval_depth", base.retrieval_depth)),
            max_context_items=int(payload.get("max_context_items", base.max_context_items)),
            history_turns=int(payload.get("history_turns", base.history_turns)),
            response_char_cap=int(payload.get("response_char_cap", base.response_char_cap)),
            low_motion=bool(payload.get("low_motion", base.low_motion)),
            debug=bool(payload.get("debug", base.debug)),
            budget_mode=str(payload.get("budget_mode", base.budget_mode)),
            title=str(payload.get("title", base.title)),
        )
    )


def clamp_request(request: InferenceProfileRequest) -> InferenceProfileRequest:
    mode = request.mode.lower().strip()
    if mode not in INFERENCE_MODES:
        mode = "manual"
    budget_mode = request.budget_mode.lower().strip()
    if budget_mode not in PROFILE_PRESETS:
        budget_mode = "balanced"
    return replace(
        request,
        mode=mode,
        temperature=max(0.0, min(1.5, request.temperature)),
        max_output_tokens=max(128, min(1200, request.max_output_tokens)),
        top_p=max(0.0, min(1.0, request.top_p)),
        repetition_penalty=max(0.0, min(2.5, request.repetition_penalty)),
        retrieval_depth=max(4, min(32, request.retrieval_depth)),
        max_context_items=max(4, min(16, request.max_context_items)),
        history_turns=max(1, min(MAX_HISTORY_TURNS, request.history_turns)),
        response_char_cap=max(600, min(3200, request.response_char_cap)),
        budget_mode=budget_mode,
        title=request.title.strip() or "Operator Session",
    )


def runtime_settings_for_profile(settings: RuntimeSettings, profile: ResolvedInferenceProfile) -> RuntimeSettings:
    return replace(
        settings,
        retrieval_depth=profile.retrieval_depth,
        max_context_items=profile.max_context_items,
        history_turns=profile.history_turns,
        low_motion=profile.low_motion,
        debug=profile.debug,
    )


def resolve_profile(
    request: InferenceProfileRequest,
    *,
    query: str,
    graph_health: dict[str, Any],
    feedback_balance: float,
    recent_membrane_events: int,
    backend: str,
) -> ResolvedInferenceProfile:
    request = clamp_request(request)
    if request.mode == "manual":
        return _manual_profile(request)
    if request.mode == "adam_auto":
        return _adam_auto_profile(
            request,
            query=query,
            graph_health=graph_health,
            feedback_balance=feedback_balance,
            recent_membrane_events=recent_membrane_events,
            backend=backend,
        )
    return _runtime_auto_profile(
        request,
        query=query,
        graph_health=graph_health,
        feedback_balance=feedback_balance,
        recent_membrane_events=recent_membrane_events,
        selection_source="runtime_auto_policy",
        requested_mode=request.mode,
    )


def _manual_profile(request: InferenceProfileRequest) -> ResolvedInferenceProfile:
    preset = PROFILE_PRESETS[request.budget_mode]
    prompt_budget_tokens = int(preset["prompt_budget_tokens"])
    return ResolvedInferenceProfile(
        requested_mode="manual",
        effective_mode="manual",
        profile_name=f"manual:{request.budget_mode}",
        budget_mode=request.budget_mode,
        prompt_budget_tokens=prompt_budget_tokens,
        temperature=request.temperature,
        max_output_tokens=request.max_output_tokens,
        top_p=request.top_p,
        repetition_penalty=request.repetition_penalty,
        retrieval_depth=request.retrieval_depth,
        max_context_items=request.max_context_items,
        history_turns=request.history_turns,
        response_char_cap=request.response_char_cap,
        low_motion=request.low_motion,
        debug=request.debug,
        selection_source="operator_manual",
        rationale=[
            "Operator supplied bounded parameters directly.",
            f"EDEN prompt budget preset set to {request.budget_mode}.",
        ],
        heuristic_inputs={"query_chars": 0, "graph_nodes": 0, "feedback_balance": 0.0},
        generated_at=now_utc(),
    )


def _runtime_auto_profile(
    request: InferenceProfileRequest,
    *,
    query: str,
    graph_health: dict[str, Any],
    feedback_balance: float,
    recent_membrane_events: int,
    selection_source: str,
    requested_mode: str,
) -> ResolvedInferenceProfile:
    query_chars = len(query)
    graph_nodes = int(graph_health.get("memes", 0)) + int(graph_health.get("memodes", 0))
    triadic_closure = float(graph_health.get("triadic_closure", 0.0))
    memode_coverage = float(graph_health.get("memode_coverage", 0.0))
    if query_chars >= 800 or triadic_closure >= 0.22 or memode_coverage >= 0.35:
        budget_mode = "wide"
        rationale = [
            "Long query or denser graph slice detected.",
            "Expanding prompt budget and retrieval aperture within bounded preset limits.",
        ]
    elif query_chars <= 180 and feedback_balance >= 0 and recent_membrane_events == 0 and graph_nodes <= 64:
        budget_mode = "tight"
        rationale = [
            "Short query with low recent turbulence detected.",
            "Using tighter budget and smaller aperture for faster bounded turns.",
        ]
    else:
        budget_mode = "balanced"
        rationale = [
            "Mixed query and graph conditions detected.",
            "Using balanced preset to preserve retrieval breadth without overcommitting budget.",
        ]
    preset = PROFILE_PRESETS[budget_mode]
    retrieval_depth = int(max(4, min(32, preset["retrieval_depth"] + (2 if recent_membrane_events >= 2 else 0))))
    max_context_items = int(max(4, min(16, preset["max_context_items"] + (1 if feedback_balance < 0 else 0))))
    return ResolvedInferenceProfile(
        requested_mode=requested_mode,
        effective_mode="runtime_auto",
        profile_name=f"runtime_auto:{budget_mode}",
        budget_mode=budget_mode,
        prompt_budget_tokens=int(preset["prompt_budget_tokens"]),
        temperature=float(preset["temperature"]),
        max_output_tokens=int(preset["max_output_tokens"]),
        top_p=0.9 if budget_mode != "tight" else 0.82,
        repetition_penalty=1.05 if feedback_balance >= 0 else 1.12,
        retrieval_depth=retrieval_depth,
        max_context_items=max_context_items,
        history_turns=request.history_turns,
        response_char_cap=int(preset["response_char_cap"]),
        low_motion=request.low_motion,
        debug=request.debug,
        selection_source=selection_source,
        rationale=rationale
        + [
            f"feedback_balance={feedback_balance:.2f}",
            f"recent_membrane_events={recent_membrane_events}",
        ],
        heuristic_inputs={
            "query_chars": query_chars,
            "graph_nodes": graph_nodes,
            "triadic_closure": triadic_closure,
            "memode_coverage": memode_coverage,
            "feedback_balance": feedback_balance,
            "recent_membrane_events": recent_membrane_events,
        },
        generated_at=now_utc(),
    )


def _adam_auto_profile(
    request: InferenceProfileRequest,
    *,
    query: str,
    graph_health: dict[str, Any],
    feedback_balance: float,
    recent_membrane_events: int,
    backend: str,
) -> ResolvedInferenceProfile:
    if backend != "mock":
        profile = _runtime_auto_profile(
            request,
            query=query,
            graph_health=graph_health,
            feedback_balance=feedback_balance,
            recent_membrane_events=recent_membrane_events,
            selection_source="adam_auto_fallback_runtime_auto",
            requested_mode="adam_auto",
        )
        profile.rationale.append("ADAM_AUTO fell back to runtime_auto because v1.1 does not run a separate MLX prepass chooser.")
        return profile
    lower_query = query.lower()
    if any(term in lower_query for term in ("geometry", "ablation", "compare", "analyze", "inspect")):
        budget_mode = "wide"
    elif any(term in lower_query for term in ("brief", "quick", "tight", "short")):
        budget_mode = "tight"
    else:
        budget_mode = "balanced"
    preset = PROFILE_PRESETS[budget_mode]
    return ResolvedInferenceProfile(
        requested_mode="adam_auto",
        effective_mode="adam_auto",
        profile_name=f"adam_auto:{budget_mode}",
        budget_mode=budget_mode,
        prompt_budget_tokens=int(preset["prompt_budget_tokens"]),
        temperature=float(preset["temperature"]),
        max_output_tokens=int(preset["max_output_tokens"]),
        top_p=0.9,
        repetition_penalty=1.05,
        retrieval_depth=int(preset["retrieval_depth"]),
        max_context_items=int(preset["max_context_items"]),
        history_turns=request.history_turns,
        response_char_cap=int(preset["response_char_cap"]),
        low_motion=request.low_motion,
        debug=request.debug,
        selection_source="adam_auto_mock_contract",
        rationale=[
            "Bounded mock-safe ADAM_AUTO selected a preset from operator-approved ranges.",
            f"query_chars={len(query)}",
            f"feedback_balance={feedback_balance:.2f}",
        ],
        heuristic_inputs={
            "query_chars": len(query),
            "feedback_balance": feedback_balance,
            "recent_membrane_events": recent_membrane_events,
            "graph_nodes": int(graph_health.get("memes", 0)) + int(graph_health.get("memodes", 0)),
        },
        generated_at=now_utc(),
    )
