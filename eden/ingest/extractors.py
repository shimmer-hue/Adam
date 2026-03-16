from __future__ import annotations

import csv
import subprocess
from pathlib import Path
from typing import Iterator

import pdfplumber
from pypdf import PdfReader

from ..utils import sentence_chunks


def iter_extract_pdf(path: Path) -> Iterator[dict[str, object]]:
    extraction_errors: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    yield {"page_number": idx + 1, "text": text, "parser": "pdfplumber"}
        return
    except Exception as exc:
        extraction_errors.append(f"pdfplumber:{exc}")

    try:
        reader = PdfReader(str(path))
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                yield {"page_number": idx + 1, "text": text, "parser": "pypdf"}
        return
    except Exception as exc:
        extraction_errors.append(f"pypdf:{exc}")

    try:
        result = subprocess.run(
            ["pdftotext", str(path), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
        text = result.stdout.strip()
        if text:
            yield {"page_number": None, "text": text, "parser": "pdftotext"}
            return
    except Exception as exc:
        extraction_errors.append(f"pdftotext:{exc}")

    raise RuntimeError("; ".join(extraction_errors) or "No extractable PDF text found.")


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
    return [{"page_number": None, "text": chunk, "parser": "csv"} for chunk in sentence_chunks(text, max_chars=1000)]


def extract_plaintext(path: Path) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [{"page_number": None, "text": chunk, "parser": "text"} for chunk in sentence_chunks(text, max_chars=1200)]


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
