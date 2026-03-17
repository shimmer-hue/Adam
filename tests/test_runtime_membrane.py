from __future__ import annotations


def test_sanitize_operator_response_drops_reasoning_only_spill(runtime) -> None:
    cleaned, events = runtime.sanitize_operator_response(
        "Thinking Process\n\n1. Analyze the request.\n2. Plan the answer.",
        response_char_cap=1200,
    )
    assert cleaned == "I am ready for Brian's next prompt."
    assert [event["event_type"] for event in events] == ["REASONING_ONLY_DROPPED", "EMPTY_REPAIRED"]


def test_sanitize_operator_response_recovers_final_version_from_reasoning_spill(runtime) -> None:
    text = (
        "Thinking Process\n\n"
        "1. Analyze the request.\n"
        "2. Draft the reply.\n\n"
        "*Final Version:*\n"
        "Brian, I have a clear sense of this schema within my phenomenology.\n"
        "Let us begin refining the codebase.\n\n"
        "*Wait, I need to make sure I do not violate the rule.*"
    )
    cleaned, events = runtime.sanitize_operator_response(text, response_char_cap=1200)
    assert cleaned == "Brian, I have a clear sense of this schema within my phenomenology.\nLet us begin refining the codebase."
    assert [event["event_type"] for event in events] == ["REASONING_SPLIT"]
