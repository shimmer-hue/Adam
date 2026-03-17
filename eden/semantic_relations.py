from __future__ import annotations

import re
from typing import Any

from .utils import safe_excerpt, slugify, top_phrases


MEMODE_MEMBERSHIP_EDGE_TYPE = "MEMODE_HAS_MEMBER"
AUTO_DERIVED_RELATION_RULESET = "semantic_relation_rules_v1"

_TITLE_CONNECTORS = r"(?:a|an|and|for|from|in|of|on|or|the|to|with)"
_CAPITALIZED = r"[A-Z][A-Za-z0-9'’:-]+"
_INITIAL = r"[A-Z]\."
_PERSON_TEXT = rf"(?:{_INITIAL}|{_CAPITALIZED})(?:\s+(?:{_INITIAL}|{_CAPITALIZED})){{1,3}}"
_WORK_TEXT = rf"(?:[\"“][^\"”]{{3,120}}[\"”]|{_CAPITALIZED}(?:\s+(?:{_CAPITALIZED}|{_TITLE_CONNECTORS})){{1,10}})"
_ENTITY_TEXT = rf"(?:{_PERSON_TEXT}|{_WORK_TEXT})"
_RELATION_LIMIT = 8

_AUTHOR_PATTERNS: tuple[tuple[str, re.Pattern[str], float], ...] = (
    (
        "author_of_by",
        re.compile(rf"(?P<work>{_WORK_TEXT})\s+by\s+(?P<author>{_PERSON_TEXT})"),
        0.84,
    ),
    (
        "author_of_authored",
        re.compile(rf"(?P<author>{_PERSON_TEXT})\s+(?:wrote|authored|published)\s+(?P<work>{_WORK_TEXT})"),
        0.82,
    ),
    (
        "author_of_author_phrase",
        re.compile(rf"(?P<author>{_PERSON_TEXT})\s+(?:is|was|were)?\s*(?:the\s+)?author(?:s)?\s+of\s+(?P<work>{_WORK_TEXT})"),
        0.8,
    ),
)

_BINARY_RELATION_PATTERNS: tuple[tuple[str, str, re.Pattern[str], float], ...] = (
    (
        "INFLUENCES",
        "influences",
        re.compile(rf"(?P<source>{_ENTITY_TEXT})\s+(?:influenced|influences|informed|informs|inspired|inspires|shaped|shapes)\s+(?P<target>{_ENTITY_TEXT})"),
        0.72,
    ),
    (
        "REFERENCES",
        "references",
        re.compile(rf"(?P<source>{_ENTITY_TEXT})\s+(?:references|refers\s+to|cites|quoted|quotes|discusses|reads)\s+(?P<target>{_ENTITY_TEXT})"),
        0.68,
    ),
)


def _clean_entity_label(text: str) -> str:
    label = re.sub(r"\s+", " ", str(text or "").strip())
    label = label.strip(" \t\n\r\"'“”‘’.,;:()[]{}")
    return label


def _looks_like_person(label: str) -> bool:
    parts = [part for part in re.split(r"\s+", label) if part]
    if len(parts) < 2:
        return False
    connector_values = {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
    if any(part.lower() in connector_values for part in parts):
        return False
    return all(bool(re.fullmatch(rf"(?:{_INITIAL}|{_CAPITALIZED})", part)) for part in parts)


def _split_relation_sentences(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _iter_relation_candidates(text: str) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for sentence in _split_relation_sentences(text):
        for rule_name, pattern, confidence in _AUTHOR_PATTERNS:
            for match in pattern.finditer(sentence):
                author = _clean_entity_label(match.group("author"))
                work = _clean_entity_label(match.group("work"))
                if not author or not work or author == work or _looks_like_person(work):
                    continue
                key = (slugify(author), slugify(work), "AUTHOR_OF")
                if key in seen:
                    continue
                seen.add(key)
                relations.append(
                    {
                        "source_label": author,
                        "target_label": work,
                        "edge_type": "AUTHOR_OF",
                        "confidence": confidence,
                        "rule": rule_name,
                        "sentence_excerpt": safe_excerpt(sentence, limit=220),
                    }
                )
        for edge_type, rule_name, pattern, confidence in _BINARY_RELATION_PATTERNS:
            for match in pattern.finditer(sentence):
                source = _clean_entity_label(match.group("source"))
                target = _clean_entity_label(match.group("target"))
                if not source or not target or source == target:
                    continue
                key = (slugify(source), slugify(target), edge_type)
                if key in seen:
                    continue
                seen.add(key)
                relations.append(
                    {
                        "source_label": source,
                        "target_label": target,
                        "edge_type": edge_type,
                        "confidence": confidence,
                        "rule": rule_name,
                        "sentence_excerpt": safe_excerpt(sentence, limit=220),
                    }
                )
    return relations[:_RELATION_LIMIT]


def extract_semantic_candidates(text: str, *, limit: int = 6) -> dict[str, list[dict[str, Any]]]:
    relation_candidates = _iter_relation_candidates(text)
    meme_candidates: list[dict[str, Any]] = []
    seen_labels: set[str] = set()

    def append_candidate(label: str, *, score: float, kind: str) -> None:
        normalized = slugify(label)
        if not normalized or normalized in seen_labels:
            return
        seen_labels.add(normalized)
        meme_candidates.append(
            {
                "label": label,
                "score": float(score),
                "kind": kind,
            }
        )

    for relation in relation_candidates:
        append_candidate(relation["source_label"], score=2.4, kind="relation_entity")
        append_candidate(relation["target_label"], score=2.4, kind="relation_entity")
    for phrase, score in top_phrases(text, limit=limit):
        append_candidate(phrase, score=score, kind="phrase")

    return {
        "meme_candidates": meme_candidates[: max(limit + 4, 8)],
        "relation_candidates": relation_candidates,
    }
