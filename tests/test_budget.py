from __future__ import annotations

from eden.budget import BudgetEstimate, estimate_budget


def test_budget_estimator_uses_exact_counter_when_available() -> None:
    budget = estimate_budget(
        prompt_budget_tokens=200,
        reserved_output_tokens=48,
        system_prompt="system prompt",
        active_set_context="active set context",
        history_context="history words here",
        feedback_context="feedback words",
        user_text="one two three four",
        response_char_cap=1200,
        active_set_items=4,
        history_turns=2,
        token_counter=lambda text: len(text.split()),
    )
    assert budget.exact is True
    assert budget.count_method == "exact_tokenizer"
    assert budget.user_tokens == 4
    assert budget.remaining_input_tokens == 186


def test_budget_estimator_falls_back_to_heuristic_and_tracks_changes() -> None:
    previous = estimate_budget(
        prompt_budget_tokens=100,
        reserved_output_tokens=32,
        system_prompt="system",
        active_set_context="active",
        history_context="history",
        feedback_context="feedback",
        user_text="short",
        response_char_cap=900,
        active_set_items=2,
        history_turns=1,
    )
    current = estimate_budget(
        prompt_budget_tokens=100,
        reserved_output_tokens=48,
        system_prompt="system",
        active_set_context="active set grew substantially",
        history_context="history",
        feedback_context="feedback",
        user_text="short plus more context",
        response_char_cap=900,
        active_set_items=4,
        history_turns=1,
        previous=previous,
    )
    assert current.exact is False
    assert current.count_method == "heuristic_chars_per_token"
    assert current.remaining_input_tokens < previous.remaining_input_tokens
    assert any("Reserved output" in reason or "active set" in reason or "input" in reason for reason in current.change_reasons)
