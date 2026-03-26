from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Callable, Any


TokenCounter = Callable[[str], int]


@dataclass(slots=True)
class BudgetEstimate:
    context_window_tokens: int
    prompt_budget_tokens: int
    reserved_output_tokens: int
    system_tokens: int
    active_set_tokens: int
    history_tokens: int
    feedback_tokens: int
    user_tokens: int
    used_prompt_tokens: int
    remaining_input_tokens: int
    user_chars: int
    remaining_input_chars: int
    count_method: str
    exact: bool
    response_char_cap: int
    pressure_ratio: float
    pressure_level: str
    active_set_items: int
    history_turns: int
    change_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def heuristic_token_count(text: str) -> int:
    clean = text.strip()
    if not clean:
        return 0
    return max(1, math.ceil(len(clean) / 4.2))


def estimate_budget(
    *,
    prompt_budget_tokens: int,
    reserved_output_tokens: int,
    system_prompt: str,
    active_set_context: str,
    history_context: str,
    feedback_context: str,
    user_text: str,
    response_char_cap: int,
    active_set_items: int,
    history_turns: int,
    token_counter: TokenCounter | None = None,
    previous: BudgetEstimate | None = None,
) -> BudgetEstimate:
    exact = token_counter is not None
    counter = token_counter or heuristic_token_count
    system_tokens = counter(system_prompt)
    active_set_tokens = counter(active_set_context)
    history_tokens = counter(history_context)
    feedback_tokens = counter(feedback_context)
    user_tokens = counter(user_text)
    used_prompt_tokens = system_tokens + active_set_tokens + history_tokens + feedback_tokens + user_tokens
    remaining_input_tokens = max(0, prompt_budget_tokens - used_prompt_tokens)
    chars_per_token = 4.2
    if user_tokens > 0 and user_text.strip():
        chars_per_token = max(2.8, len(user_text) / user_tokens)
    remaining_input_chars = int(round(remaining_input_tokens * chars_per_token))
    pressure_ratio = used_prompt_tokens / max(1, prompt_budget_tokens)
    if pressure_ratio >= 0.9:
        pressure_level = "HIGH"
    elif pressure_ratio >= 0.7:
        pressure_level = "ELEVATED"
    else:
        pressure_level = "LOW"
    return BudgetEstimate(
        context_window_tokens=prompt_budget_tokens + reserved_output_tokens,
        prompt_budget_tokens=prompt_budget_tokens,
        reserved_output_tokens=reserved_output_tokens,
        system_tokens=system_tokens,
        active_set_tokens=active_set_tokens,
        history_tokens=history_tokens,
        feedback_tokens=feedback_tokens,
        user_tokens=user_tokens,
        used_prompt_tokens=used_prompt_tokens,
        remaining_input_tokens=remaining_input_tokens,
        user_chars=len(user_text),
        remaining_input_chars=remaining_input_chars,
        count_method="exact_tokenizer" if exact else "heuristic_chars_per_token",
        exact=exact,
        response_char_cap=response_char_cap,
        pressure_ratio=round(float(pressure_ratio), 4),
        pressure_level=pressure_level,
        active_set_items=active_set_items,
        history_turns=history_turns,
        change_reasons=_change_reasons(previous=previous, prompt_budget_tokens=prompt_budget_tokens, reserved_output_tokens=reserved_output_tokens, system_tokens=system_tokens, active_set_tokens=active_set_tokens, history_tokens=history_tokens, feedback_tokens=feedback_tokens, user_tokens=user_tokens, pressure_level=pressure_level),
    )


def _change_reasons(
    *,
    previous: BudgetEstimate | None,
    prompt_budget_tokens: int,
    reserved_output_tokens: int,
    system_tokens: int,
    active_set_tokens: int,
    history_tokens: int,
    feedback_tokens: int,
    user_tokens: int,
    pressure_level: str,
) -> list[str]:
    if previous is None:
        return ["Baseline estimate created."]
    reasons: list[str] = []
    if prompt_budget_tokens != previous.prompt_budget_tokens:
        reasons.append(f"Prompt budget {previous.prompt_budget_tokens}->{prompt_budget_tokens} tok.")
    if reserved_output_tokens != previous.reserved_output_tokens:
        reasons.append(f"Reserved output {previous.reserved_output_tokens}->{reserved_output_tokens} tok.")
    for label, current, prior in (
        ("system", system_tokens, previous.system_tokens),
        ("active set", active_set_tokens, previous.active_set_tokens),
        ("history", history_tokens, previous.history_tokens),
        ("feedback", feedback_tokens, previous.feedback_tokens),
        ("input", user_tokens, previous.user_tokens),
    ):
        delta = current - prior
        if delta:
            sign = "+" if delta > 0 else ""
            reasons.append(f"{label} {sign}{delta} tok.")
    if pressure_level != previous.pressure_level:
        reasons.append(f"Pressure {previous.pressure_level}->{pressure_level}.")
    return reasons or ["No material budget change."]
