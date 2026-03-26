from __future__ import annotations

from .base import BaseModelAdapter, ModelResult


class MockModelAdapter(BaseModelAdapter):
    backend_name = "mock"

    def count_tokens(self, text: str) -> int | None:
        return max(0, len(text.split()))

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
        lines = [line.strip() for line in conversation_prompt.splitlines() if line.strip()]
        user_line = next((line for line in reversed(lines) if line.startswith("USER:")), "USER: request unavailable")
        active_lines = [line for line in lines if line.startswith("[")]
        anchors = []
        for line in active_lines[:3]:
            anchors.append(line.split("]", 1)[0].strip("["))
        anchor_text = ", ".join(anchors) if anchors else "no strong prior anchors"
        answer = (
            f"I am responding through the current aperture rather than pretending to speak from fixed weights. "
            f"Your latest request was: {user_line[5:].strip()}\n\n"
            f"The highest-pressure structures in the active set were {anchor_text}, so I leaned on the strongest regard, recency, and feedback surfaces available in this moment.\n\n"
            "If you want me to stabilize or revise this behavior, apply explicit feedback so the graph updates instead of the answer merely disappearing."
        )
        if progress_callback is not None:
            progress_callback(
                {
                    "backend": self.backend_name,
                    "phase": "answer",
                    "reasoning_text": "",
                    "answer_text": answer[:max_tokens * 5],
                    "raw_text": answer[:max_tokens * 5],
                    "generation_tokens": min(max_tokens, max(1, len(answer.split()))),
                    "done": False,
                }
            )
        return ModelResult(
            backend=self.backend_name,
            text=answer[:max_tokens * 5],
            tokens_estimate=min(max_tokens, max(64, len(answer.split()))),
            metadata={
                "mode": "deterministic_mock",
                "temperature": temperature,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty,
            },
            answer_text=answer[:max_tokens * 5],
            reasoning_text="",
            raw_text=answer[:max_tokens * 5],
        )
