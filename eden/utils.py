from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "with",
}


TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-/']+")


def now_utc() -> str:
    return datetime.now(tz=UTC).isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "untitled"


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def cosine_similarity(left: str, right: str) -> float:
    left_counts = Counter(token for token in tokenize(left) if token not in STOPWORDS)
    right_counts = Counter(token for token in tokenize(right) if token not in STOPWORDS)
    if not left_counts or not right_counts:
        return 0.0
    intersection = set(left_counts) & set(right_counts)
    numerator = sum(left_counts[token] * right_counts[token] for token in intersection)
    left_mag = math.sqrt(sum(value * value for value in left_counts.values()))
    right_mag = math.sqrt(sum(value * value for value in right_counts.values()))
    if left_mag == 0.0 or right_mag == 0.0:
        return 0.0
    return numerator / (left_mag * right_mag)


def sentence_chunks(text: str, *, max_chars: int = 1200) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if current and current_size + len(sentence) + 1 > max_chars:
            chunks.append(" ".join(current))
            current = [sentence]
            current_size = len(sentence)
        else:
            current.append(sentence)
            current_size += len(sentence) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def top_phrases(text: str, *, limit: int = 6) -> list[tuple[str, float]]:
    tokens = [token for token in tokenize(text) if token not in STOPWORDS and len(token) > 2]
    if not tokens:
        return []
    counts: Counter[str] = Counter()
    for n in (1, 2, 3):
        for idx in range(len(tokens) - n + 1):
            phrase_tokens = tokens[idx : idx + n]
            phrase = " ".join(phrase_tokens)
            score = n + 0.25
            if len(set(phrase_tokens)) != len(phrase_tokens):
                score -= 0.5
            counts[phrase] += score
    scored = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    deduped: list[tuple[str, float]] = []
    seen: set[str] = set()
    for phrase, score in scored:
        if any(phrase in prior for prior in seen):
            continue
        seen.add(phrase)
        deduped.append((phrase, round(float(score), 3)))
        if len(deduped) >= limit:
            break
    return deduped


def compact_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def safe_excerpt(text: str, *, limit: int = 240) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def flatten(iterables: Iterable[Iterable[str]]) -> list[str]:
    return [item for iterable in iterables for item in iterable]
