from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable


THINK_BLOCK_RE = re.compile(r"<think>\s*(.*?)\s*</think>\s*(.*)", re.DOTALL)
THINKING_HEADER_RE = re.compile(r"^(Thinking Process|Reasoning(?: Process)?)(?:\s*:)?\s*", re.IGNORECASE)
FINAL_RESPONSE_MARKER_RE = re.compile(
    r"(?im)^\s*(?:[*_]{1,2})?\s*(Final Answer|Answer|Final Version|Final Response)\s*:?\s*(?:[*_]{1,2})?\s*(.*)$"
)
FOLLOWUP_META_RE = re.compile(r"(?im)^\s*[*_]{1,2}(?:Wait|Actually|Revised?|Check|Final Plan)\b")
GenerationProgressCallback = Callable[[dict[str, Any]], None]


def _truncate_answer_followup(text: str) -> str:
    stripped = (text or "").strip()
    if not stripped:
        return ""
    followup = FOLLOWUP_META_RE.search(stripped)
    if followup:
        return stripped[: followup.start()].rstrip()
    return stripped


def _split_thinking_header_block(text: str, *, progressive: bool) -> tuple[str, str]:
    stripped = (text or "").strip()
    if not stripped or not THINKING_HEADER_RE.match(stripped):
        return "", stripped
    matches = list(FINAL_RESPONSE_MARKER_RE.finditer(stripped))
    if matches:
        marker = matches[-1]
        inline_answer = str(marker.group(2) or "").strip()
        trailing_answer = stripped[marker.end() :].strip()
        answer = "\n".join(part for part in (inline_answer, trailing_answer) if part).strip()
        answer = _truncate_answer_followup(answer)
        reasoning = stripped[: marker.start()].strip()
        if answer:
            return reasoning or stripped, answer
    return stripped, "" if progressive else stripped


def split_model_output(text: str) -> tuple[str, str]:
    stripped = (text or "").strip()
    if not stripped:
        return "", ""
    think_match = THINK_BLOCK_RE.search(stripped)
    if think_match:
        reasoning = think_match.group(1).strip()
        answer = think_match.group(2).strip()
        return reasoning, answer or stripped
    reasoning, answer = _split_thinking_header_block(stripped, progressive=False)
    if reasoning:
        return reasoning, answer or stripped
    return "", stripped


def split_model_output_progressive(text: str) -> tuple[str, str]:
    stripped = (text or "").strip()
    if not stripped:
        return "", ""
    if "<think>" in stripped:
        _, tail = stripped.split("<think>", 1)
        if "</think>" in tail:
            reasoning, answer = tail.split("</think>", 1)
            return reasoning.strip(), answer.strip()
        return tail.strip(), ""
    reasoning, answer = _split_thinking_header_block(stripped, progressive=True)
    if reasoning:
        return reasoning, answer
    return "", stripped


@dataclass(slots=True)
class ModelResult:
    backend: str
    text: str
    tokens_estimate: int
    metadata: dict[str, object]
    answer_text: str = ""
    reasoning_text: str = ""
    raw_text: str = ""

    def __post_init__(self) -> None:
        if not self.raw_text:
            self.raw_text = self.text
        if not self.answer_text:
            self.answer_text = self.text


class BaseModelAdapter:
    backend_name = "base"

    def count_tokens(self, text: str) -> int | None:
        return None

    def generate(
        self,
        *,
        system_prompt: str,
        conversation_prompt: str,
        max_tokens: int = 420,
        temperature: float = 0.0,
        top_p: float = 0.0,
        repetition_penalty: float = 0.0,
        progress_callback: GenerationProgressCallback | None = None,
    ) -> ModelResult:
        raise NotImplementedError
