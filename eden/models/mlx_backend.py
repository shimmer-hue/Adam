from __future__ import annotations

import threading
from inspect import signature

from .base import (
    BaseModelAdapter,
    GenerationProgressCallback,
    ModelResult,
    split_model_output,
    split_model_output_progressive,
)


class MLXModelAdapter(BaseModelAdapter):
    backend_name = "mlx"

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        try:
            import mlx_lm  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on local install
            raise RuntimeError(
                "mlx-lm is not installed. Install the project with the mlx extra: `uv pip install -e .[mlx]`."
            ) from exc
        try:
            from mlx_lm.sample_utils import make_logits_processors, make_sampler  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on local install
            raise RuntimeError("mlx-lm sample utilities are unavailable in this installation.") from exc
        self._mlx_lm = mlx_lm
        self._make_sampler = make_sampler
        self._make_logits_processors = make_logits_processors
        self._generation_lock = threading.RLock()
        self.model, self.tokenizer = self._load_model()

    def _load_model(self):  # pragma: no cover - depends on local install
        if hasattr(self._mlx_lm, "load"):
            return self._mlx_lm.load(self.model_path)
        from mlx_lm import load  # type: ignore

        return load(self.model_path)

    def count_tokens(self, text: str) -> int | None:
        if not text.strip():
            return 0
        if hasattr(self.tokenizer, "encode"):
            try:
                return int(len(self.tokenizer.encode(text)))
            except Exception:  # pragma: no cover - tokenizer-specific failures
                return None
        return None

    def _build_prompt(self, system_prompt: str, conversation_prompt: str, *, enable_thinking: bool) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": conversation_prompt},
        ]
        if hasattr(self.tokenizer, "apply_chat_template"):
            try:
                return self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=enable_thinking,
                )
            except TypeError:
                return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        return f"{system_prompt}\n\n{conversation_prompt}\n\nAssistant:"

    def _generate_text(
        self,
        *,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        repetition_penalty: float,
        progress_callback: GenerationProgressCallback | None = None,
        phase: str = "answer",
    ) -> str:
        if progress_callback is not None:
            return self._stream_text(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                repetition_penalty=repetition_penalty,
                progress_callback=progress_callback,
                phase=phase,
            )
        if hasattr(self._mlx_lm, "generate"):
            generate_fn = self._mlx_lm.generate
        else:
            from mlx_lm import generate as generate_fn  # type: ignore

        kwargs = {"max_tokens": max_tokens, "verbose": False}
        kwargs["sampler"] = self._make_sampler(temp=temperature, top_p=top_p)
        kwargs["logits_processors"] = self._make_logits_processors(repetition_penalty=repetition_penalty)
        try:
            sig = signature(generate_fn)
            if "prompt" in sig.parameters:
                result = generate_fn(self.model, self.tokenizer, prompt=prompt, **kwargs)
            else:
                result = generate_fn(self.model, self.tokenizer, prompt, **kwargs)
        except TypeError:
            result = generate_fn(self.model, self.tokenizer, prompt, max_tokens=max_tokens)

        if isinstance(result, str):
            return result
        if hasattr(result, "text"):
            return str(result.text)
        return str(result)

    def _stream_text(
        self,
        *,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        repetition_penalty: float,
        progress_callback: GenerationProgressCallback,
        phase: str,
    ) -> str:
        if hasattr(self._mlx_lm, "stream_generate"):
            stream_fn = self._mlx_lm.stream_generate
        else:
            from mlx_lm import stream_generate as stream_fn  # type: ignore

        kwargs = {"max_tokens": max_tokens}
        kwargs["sampler"] = self._make_sampler(temp=temperature, top_p=top_p)
        kwargs["logits_processors"] = self._make_logits_processors(repetition_penalty=repetition_penalty)
        pieces: list[str] = []
        last_tokens = 0
        for response in stream_fn(self.model, self.tokenizer, prompt, **kwargs):
            segment = str(getattr(response, "text", "") or "")
            if segment:
                pieces.append(segment)
            combined = "".join(pieces).strip()
            reasoning_text, answer_text = (
                split_model_output_progressive(combined) if phase == "reasoning" else ("", combined)
            )
            last_tokens = int(getattr(response, "generation_tokens", last_tokens) or last_tokens)
            progress_callback(
                {
                    "backend": self.backend_name,
                    "phase": phase,
                    "reasoning_text": reasoning_text,
                    "answer_text": answer_text,
                    "raw_text": combined,
                    "generation_tokens": last_tokens,
                    "done": bool(getattr(response, "finish_reason", None)),
                }
            )
        return "".join(pieces).strip()

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
    ) -> ModelResult:  # pragma: no cover - depends on local install
        with self._generation_lock:
            prompt = self._build_prompt(system_prompt, conversation_prompt, enable_thinking=True)
            text = self._generate_text(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                repetition_penalty=repetition_penalty,
                progress_callback=progress_callback,
                phase="reasoning",
            )
            reasoning_text, answer_text = split_model_output(text)
            used_answer_fallback = False
            if reasoning_text and answer_text.strip() == text.strip():
                answer_prompt = self._build_prompt(
                    system_prompt
                    + "\nThis is the final answer pass. Do not emit reasoning. Return one clean operator-facing response with no headings or scaffolding.",
                    conversation_prompt,
                    enable_thinking=False,
                )
                answer_text = self._generate_text(
                    prompt=answer_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    repetition_penalty=repetition_penalty,
                    progress_callback=(
                        (lambda payload: progress_callback({**payload, "phase": "answer_fallback", "reasoning_text": reasoning_text.strip()}))
                        if progress_callback is not None
                        else None
                    ),
                    phase="answer",
                ).strip()
                used_answer_fallback = True
            return ModelResult(
                backend=self.backend_name,
                text=text.strip(),
                tokens_estimate=min(max_tokens, max(64, len(text.split()))),
                metadata={
                    "model_path": self.model_path,
                    "temperature": temperature,
                    "top_p": top_p,
                    "repetition_penalty": repetition_penalty,
                    "answer_completion_fallback": used_answer_fallback,
                },
                answer_text=answer_text.strip() or text.strip(),
                reasoning_text=reasoning_text.strip(),
                raw_text=text.strip(),
            )
