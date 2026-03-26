from __future__ import annotations

import csv
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pdfplumber
from pypdf import PdfReader

from ..utils import sentence_chunks

PDF_LIGATURE_TRANSLATION = str.maketrans(
    {
        "\u00a0": " ",
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
    }
)
PDF_LIGATURE_CHARS = tuple("\ufb00\ufb01\ufb02\ufb03\ufb04")
PDF_ORPHAN_ARTIFACT_LINES = {"fi", "fl", "ffi", "ffl", "ff"}
PDF_PARSER_PRIORITY = {"pdfplumber": 3, "pypdf": 2, "pdftotext_layout": 1}
SEVERE_QUALITY_FLAGS = {"replacement_glyphs", "fragmented_lines", "sparse_text"}


@dataclass(slots=True)
class PdfPageCandidate:
    parser: str
    page_number: int
    text: str
    quality_score: float
    quality_flags: list[str]
    word_count: int


def normalize_pdf_text(text: str) -> tuple[str, list[str]]:
    translated = text.translate(PDF_LIGATURE_TRANSLATION).replace("\x0c", "\n")
    flags: list[str] = []
    if any(char in text for char in PDF_LIGATURE_CHARS):
        flags.append("ligatures_normalized")

    paragraphs: list[str] = []
    current_lines: list[str] = []
    artifact_lines_removed = 0
    hyphen_repairs = 0

    for raw_line in translated.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            if current_lines:
                paragraphs.append(" ".join(current_lines))
                current_lines = []
            continue
        if line.lower() in PDF_ORPHAN_ARTIFACT_LINES:
            artifact_lines_removed += 1
            continue
        if current_lines and re.search(r"[A-Za-z]{2,}-$", current_lines[-1]) and re.match(r"^[a-z][A-Za-z-]*\b", line):
            current_lines[-1] = current_lines[-1][:-1] + line
            hyphen_repairs += 1
            continue
        current_lines.append(line)

    if current_lines:
        paragraphs.append(" ".join(current_lines))

    normalized = "\n\n".join(paragraph for paragraph in paragraphs if paragraph).strip()
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    if artifact_lines_removed:
        flags.append("artifact_lines_removed")
    if hyphen_repairs:
        flags.append("hyphenated_linebreaks_repaired")
    return normalized, flags


def score_pdf_text_quality(raw_text: str, normalized_text: str, cleanup_flags: list[str] | None = None) -> tuple[float, list[str], int]:
    raw_lines = [re.sub(r"[ \t]+", " ", line.translate(PDF_LIGATURE_TRANSLATION)).strip() for line in raw_text.replace("\x0c", "\n").splitlines()]
    nonblank_lines = [line for line in raw_lines if line]
    word_count = len(re.findall(r"\b[\w']+\b", normalized_text))
    sentence_count = len(re.findall(r"[.!?](?:\s|$)", normalized_text))
    replacement_count = normalized_text.count("\ufffd")
    artifact_line_count = sum(1 for line in nonblank_lines if line.lower() in PDF_ORPHAN_ARTIFACT_LINES)
    short_lines = sum(1 for line in nonblank_lines if len(line) < 24)
    very_short_lines = sum(1 for line in nonblank_lines if len(line) < 8)
    short_line_ratio = short_lines / max(1, len(nonblank_lines))
    very_short_line_ratio = very_short_lines / max(1, len(nonblank_lines))

    flags = list(cleanup_flags or [])
    if replacement_count:
        flags.append("replacement_glyphs")
    if word_count < 30:
        flags.append("sparse_text")
    if short_line_ratio > 0.4 or very_short_line_ratio > 0.18:
        flags.append("fragmented_lines")
    if sentence_count == 0 and word_count >= 30:
        flags.append("low_sentence_density")

    score = 1.0
    if replacement_count:
        score -= min(0.35, replacement_count * 0.08)
    if artifact_line_count:
        score -= min(0.15, artifact_line_count * 0.04)
    if word_count < 30:
        score -= 0.22
    elif word_count < 80:
        score -= 0.08
    if short_line_ratio > 0.4:
        score -= min(0.18, (short_line_ratio - 0.4) * 0.45 + 0.08)
    if very_short_line_ratio > 0.18:
        score -= min(0.12, (very_short_line_ratio - 0.18) * 0.6 + 0.04)
    if sentence_count == 0 and word_count >= 30:
        score -= 0.08
    score = max(0.0, min(1.0, score))

    deduped_flags = list(dict.fromkeys(flags))
    return score, deduped_flags, word_count


def _build_pdf_candidate(parser: str, page_number: int, text: str) -> PdfPageCandidate | None:
    normalized_text, cleanup_flags = normalize_pdf_text(text)
    if not normalized_text.strip():
        return None
    score, flags, word_count = score_pdf_text_quality(text, normalized_text, cleanup_flags)
    return PdfPageCandidate(
        parser=parser,
        page_number=page_number,
        text=normalized_text,
        quality_score=score,
        quality_flags=flags,
        word_count=word_count,
    )


def _candidate_rank(candidate: PdfPageCandidate) -> tuple[float, int, int, int]:
    severe_flag_count = sum(1 for flag in candidate.quality_flags if flag in SEVERE_QUALITY_FLAGS)
    return (
        candidate.quality_score,
        -severe_flag_count,
        PDF_PARSER_PRIORITY.get(candidate.parser, 0),
        candidate.word_count,
    )


def _document_quality_score(candidates: list[PdfPageCandidate]) -> tuple[float, list[str]]:
    weighted_total = 0.0
    total_weight = 0.0
    flags: set[str] = set()
    parser_counts: dict[str, int] = {}

    for candidate in candidates:
        weight = max(1.0, min(8.0, candidate.word_count / 40.0))
        weighted_total += candidate.quality_score * weight
        total_weight += weight
        flags.update(candidate.quality_flags)
        parser_counts[candidate.parser] = parser_counts.get(candidate.parser, 0) + 1

    score = weighted_total / total_weight if total_weight else 0.0
    if len(parser_counts) > 1:
        flags.add("mixed_parser_selection")
    return score, sorted(flags)


def _iter_pdfplumber_pages(path: Path) -> Iterator[tuple[int, str]]:
    with pdfplumber.open(path) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            yield idx, page.extract_text() or ""


def _iter_pypdf_pages(path: Path) -> Iterator[tuple[int, str]]:
    reader = PdfReader(str(path))
    for idx, page in enumerate(reader.pages, start=1):
        yield idx, page.extract_text() or ""


def _iter_pdftotext_layout_pages(path: Path) -> Iterator[tuple[int, str]]:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    for idx, page in enumerate(result.stdout.split("\x0c"), start=1):
        yield idx, page


def iter_extract_pdf(path: Path) -> Iterator[dict[str, object]]:
    extraction_errors: list[str] = []
    best_by_page: dict[int, PdfPageCandidate] = {}
    extracted_any = False

    parser_extractors = [
        ("pdfplumber", _iter_pdfplumber_pages),
        ("pypdf", _iter_pypdf_pages),
        ("pdftotext_layout", _iter_pdftotext_layout_pages),
    ]

    for parser_name, parser_extract in parser_extractors:
        try:
            parser_found_page = False
            for page_number, text in parser_extract(path):
                parser_found_page = True
                candidate = _build_pdf_candidate(parser_name, page_number, text)
                if candidate is None:
                    continue
                extracted_any = True
                current = best_by_page.get(page_number)
                if current is None or _candidate_rank(candidate) > _candidate_rank(current):
                    best_by_page[page_number] = candidate
            if not parser_found_page:
                extraction_errors.append(f"{parser_name}:no pages")
        except Exception as exc:
            extraction_errors.append(f"{parser_name}:{exc}")

    if not extracted_any or not best_by_page:
        raise RuntimeError("; ".join(extraction_errors) or "No extractable PDF text found.")

    selected_candidates = [best_by_page[page_number] for page_number in sorted(best_by_page)]
    document_score, document_flags = _document_quality_score(selected_candidates)
    if document_score < 0.2:
        detail = ",".join(document_flags) if document_flags else "no_flags"
        raise RuntimeError(f"PDF extraction unusable after scoring (quality_score={document_score:.3f}; flags={detail})")

    for candidate in selected_candidates:
        yield {
            "page_number": candidate.page_number,
            "text": candidate.text,
            "parser": candidate.parser,
            "quality_score": round(candidate.quality_score, 4),
            "quality_flags": candidate.quality_flags,
        }


def extract_pdf(path: Path) -> list[dict[str, object]]:
    return list(iter_extract_pdf(path))


def extract_csv(path: Path) -> list[dict[str, object]]:
    rows: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if any(cell.strip() for cell in row):
                rows.append(" | ".join(cell.strip() for cell in row))
    text = "\n".join(rows)
    return [
        {"page_number": None, "text": chunk, "parser": "csv", "quality_score": 1.0, "quality_flags": []}
        for chunk in sentence_chunks(text, max_chars=1000)
    ]


def extract_plaintext(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [
        {"page_number": None, "text": chunk, "parser": "text", "quality_score": 1.0, "quality_flags": []}
        for chunk in sentence_chunks(text, max_chars=1200)
    ]


def extract_document(path: Path) -> list[dict[str, object]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".csv":
        return extract_csv(path)
    if suffix in {".txt", ".md", ".markdown"}:
        return extract_plaintext(path)
    raise ValueError(f"Unsupported ingest format: {path.suffix}")


def iter_extract_document(path: Path) -> Iterator[dict[str, object]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        yield from iter_extract_pdf(path)
        return
    for page in extract_document(path):
        yield page
