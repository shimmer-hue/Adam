from __future__ import annotations

import json

from eden.models.base import ModelResult
from eden.models.mock import MockModelAdapter


def test_session_start_persists_manual_profile(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(
        experiment["id"],
        title="Manual profile",
        profile_request={
            "mode": "manual",
            "budget_mode": "wide",
            "temperature": 0.65,
            "max_output_tokens": 720,
            "top_p": 0.88,
            "repetition_penalty": 1.11,
            "retrieval_depth": 18,
            "max_context_items": 9,
            "history_turns": 6,
            "response_char_cap": 2100,
            "low_motion": True,
            "debug": False,
        },
    )
    metadata = json.loads(runtime.store.get_session(session["id"])["metadata_json"])
    profile = metadata["requested_inference_profile"]
    assert metadata["requested_mode"] == "manual"
    assert profile["budget_mode"] == "wide"
    assert profile["retrieval_depth"] == 18
    assert profile["history_turns"] == 6
    assert profile["low_motion"] is True


def test_runtime_auto_profile_generation_is_visible(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(
        experiment["id"],
        profile_request={"mode": "runtime_auto", "budget_mode": "balanced"},
    )
    preview = runtime.preview_turn(session_id=session["id"], user_text="Give a concise explanation of graph-conditioned identity.")
    assert preview.profile["requested_mode"] == "runtime_auto"
    assert preview.profile["effective_mode"] == "runtime_auto"
    assert preview.profile["selection_source"] == "runtime_auto_policy"
    assert preview.profile["prompt_budget_tokens"] > 0


def test_adam_auto_falls_back_to_runtime_auto_for_mlx(runtime) -> None:
    runtime.settings.model_backend = "mlx"
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(
        experiment["id"],
        profile_request={"mode": "adam_auto", "budget_mode": "balanced"},
    )
    preview = runtime.preview_turn(session_id=session["id"], user_text="Analyze the geometry of recurrence under ablation.")
    assert preview.profile["requested_mode"] == "adam_auto"
    assert preview.profile["effective_mode"] == "runtime_auto"
    assert preview.profile["selection_source"] == "adam_auto_fallback_runtime_auto"


def test_history_turns_limits_prompt_history_window(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(
        experiment["id"],
        title="History Window",
        profile_request={"mode": "manual", "budget_mode": "wide", "history_turns": 2},
    )
    runtime.chat(session_id=session["id"], user_text="Turn zero about continuity.")
    runtime.chat(session_id=session["id"], user_text="Turn one about persona persistence.")
    runtime.chat(session_id=session["id"], user_text="Turn two about feedback loops.")

    preview = runtime.preview_turn(session_id=session["id"], user_text="Turn three asks for a recap.")

    assert "T0 Brian the operator: Turn zero about continuity." not in preview.history_context
    assert "T1 Brian the operator: Turn one about persona persistence." in preview.history_context
    assert "T2 Brian the operator: Turn two about feedback loops." in preview.history_context
    assert preview.profile["history_turns"] == 2
    assert preview.budget["history_turns"] == 2


def test_history_turns_clamps_to_two_hundred_fifty_six(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(
        experiment["id"],
        title="Extended History Window",
        profile_request={"mode": "manual", "budget_mode": "wide", "history_turns": 999},
    )

    profile = runtime.session_profile_request(session["id"])

    assert profile["history_turns"] == 256


def test_max_output_tokens_and_response_cap_clamp_to_long_form_bounds(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(
        experiment["id"],
        title="Long Form Bounds",
        profile_request={
            "mode": "manual",
            "budget_mode": "wide",
            "max_output_tokens": 99999,
            "response_char_cap": 99999,
        },
    )

    profile = runtime.session_profile_request(session["id"])

    assert profile["max_output_tokens"] == 4096
    assert profile["response_char_cap"] == 12000


def test_recent_history_injection_respects_prompt_budget(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(
        experiment["id"],
        title="Budget Bounded History",
        profile_request={"mode": "manual", "budget_mode": "tight", "history_turns": 256},
    )
    for index in range(6):
        runtime.chat(
            session_id=session["id"],
            user_text=f"Turn {index} " + ("continuity signal " * 32),
        )

    history_context, injected_turns = runtime._recent_history_context(
        session["id"],
        limit=256,
        prompt_budget_tokens=160,
        system_prompt="system prompt",
        active_set_context="active set context",
        feedback_context="feedback context",
        user_text="recap request",
        token_counter=lambda text: len(text.split()),
    )

    assert injected_turns < 6
    assert injected_turns >= 1
    assert "T5 Brian the operator: Turn 5" in history_context
    assert "T0 Brian the operator: Turn 0" not in history_context


def test_session_snapshot_recovers_long_visible_response_from_raw_turn_text(runtime, monkeypatch) -> None:
    class LongMockAdapter(MockModelAdapter):
        def generate(
            self,
            *,
            system_prompt: str,
            conversation_prompt: str,
            max_tokens: int = 420,
            temperature: float = 0.0,
            top_p: float = 0.0,
            repetition_penalty: float = 0.0,
            progress_callback=None,
        ) -> ModelResult:
            answer = "Long-form operator-facing answer. " * 260
            return ModelResult(
                backend=self.backend_name,
                text=answer,
                tokens_estimate=min(max_tokens, max(64, len(answer.split()))),
                metadata={},
                answer_text=answer,
                reasoning_text="",
                raw_text=answer,
            )

    monkeypatch.setattr(runtime, "_get_model_adapter", lambda: LongMockAdapter())

    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(
        experiment["id"],
        title="Long Form Snapshot",
        profile_request={
            "mode": "manual",
            "budget_mode": "balanced",
            "max_output_tokens": 1800,
            "response_char_cap": 1600,
        },
    )

    outcome = runtime.chat(session_id=session["id"], user_text="Give me a long-form answer.")
    snapshot = runtime.session_state_snapshot(session["id"])

    assert len(outcome.turn["membrane_text"]) <= 1600
    assert len(snapshot["last_response"]) > len(outcome.turn["membrane_text"])
    assert len(snapshot["last_response"]) > 3000
