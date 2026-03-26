from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eden import __version__

from ..utils import now_utc

TANAKH_HOME_URL = "https://tanach.us/Tanach.xml"
TANAKH_LICENSE_URL = "https://tanach.us/License.html"
TANAKH_ZIP_URL = "https://tanach.us/Books/Tanach.xml.zip"
TANAKH_HEADER_URL = "https://tanach.us/Books/TanachHeader.xml"
TANAKH_INDEX_URL = "https://tanach.us/Books/TanachIndex.xml"
DEFAULT_TANAKH_REF = "Ezek 1"
DEFAULT_TANAKH_PARAMS: dict[str, Any] = {
    "preprocess": "strip_pointing",
    "gematria_scheme": "mispar_hechrechi",
    "notarikon_mode": "first_letter",
    "temurah_mapping": "atbash",
    "scene": {
        "letter_angle": 0.14,
        "word_radius": 0.22,
        "verse_height": 1.1,
        "theme": "amber",
        "oscillation_amplitude": 0.18,
        "seed": 11,
    },
}
HEBREW_LETTER_RE = re.compile("[\u05d0-\u05ea]")
REF_RE = re.compile(
    r"^\s*(?P<book>.+?)\s+(?P<chapter>\d+)(?::(?P<verse_start>\d+)(?:-(?P<verse_end>\d+))?)?\s*$"
)
WORDLIKE_TAGS = {"w", "q", "k"}
PREPROCESS_MODES = {"strip_pointing", "keep_vowels", "keep_cantillation"}
NOTARIKON_MODES = {"first_letter", "last_letter"}
TEMURAH_MAPPINGS = {"atbash"}
GEMATRIA_SCHEMES = {"mispar_hechrechi", "mispar_gadol"}
SCENE_THEMES = {"amber", "brass", "sea"}
USER_AGENT = "Mozilla/5.0 (EDEN Adam Tanakh service)"

HEBREW_CANTILLATION = {chr(codepoint) for codepoint in range(0x0591, 0x05AF + 1)}
HEBREW_VOWELS = {chr(codepoint) for codepoint in range(0x05B0, 0x05BC + 1)}
HEBREW_VOWELS.update({"ׁ", "ׂ", "ׇ"})
FINAL_TO_STANDARD = {
    "ך": "כ",
    "ם": "מ",
    "ן": "נ",
    "ף": "פ",
    "ץ": "צ",
}
STANDARD_GEMATRIA = {
    "א": 1,
    "ב": 2,
    "ג": 3,
    "ד": 4,
    "ה": 5,
    "ו": 6,
    "ז": 7,
    "ח": 8,
    "ט": 9,
    "י": 10,
    "כ": 20,
    "ל": 30,
    "מ": 40,
    "נ": 50,
    "ס": 60,
    "ע": 70,
    "פ": 80,
    "צ": 90,
    "ק": 100,
    "ר": 200,
    "ש": 300,
    "ת": 400,
}
FINAL_GEMATRIA = {
    **STANDARD_GEMATRIA,
    "ך": 500,
    "ם": 600,
    "ן": 700,
    "ף": 800,
    "ץ": 900,
}
ATBASH_STANDARD = {
    "א": "ת",
    "ב": "ש",
    "ג": "ר",
    "ד": "ק",
    "ה": "צ",
    "ו": "פ",
    "ז": "ע",
    "ח": "ס",
    "ט": "נ",
    "י": "מ",
    "כ": "ל",
    "ל": "כ",
    "מ": "י",
    "נ": "ט",
    "ס": "ח",
    "ע": "ז",
    "פ": "ו",
    "צ": "ה",
    "ק": "ד",
    "ר": "ג",
    "ש": "ב",
    "ת": "א",
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(encoded)


def _iso_utc_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _slugify_ref(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    return lowered.strip("_")


def _grapheme_count(text: str) -> int:
    count = 0
    for char in text:
        if char.isspace():
            continue
        if unicodedata.combining(char):
            continue
        count += 1
    return count


def _mark_counts(text: str) -> dict[str, int]:
    vowels = 0
    cantillation = 0
    for char in text:
        if char in HEBREW_VOWELS:
            vowels += 1
        if char in HEBREW_CANTILLATION:
            cantillation += 1
    return {"vowels": vowels, "cantillation": cantillation}


def _preprocess_text(text: str, mode: str) -> dict[str, Any]:
    if mode not in PREPROCESS_MODES:
        raise ValueError(f"Unsupported preprocess mode '{mode}'.")
    kept_chars: list[str] = []
    removed = {"vowels": 0, "cantillation": 0}
    for char in text:
        if char in HEBREW_CANTILLATION and mode != "keep_cantillation":
            removed["cantillation"] += 1
            continue
        if char in HEBREW_VOWELS and mode == "strip_pointing":
            removed["vowels"] += 1
            continue
        kept_chars.append(char)
    processed = "".join(kept_chars)
    return {
        "mode": mode,
        "text": processed,
        "removed": removed,
        "codepoint_count": len(processed),
        "grapheme_count": _grapheme_count(processed),
        "mark_counts": _mark_counts(processed),
    }


def _normalize_letter(char: str) -> str:
    return FINAL_TO_STANDARD.get(char, char)


def _hebrew_letters(text: str) -> list[str]:
    return [char for char in text if HEBREW_LETTER_RE.match(char)]


def _tokenize_words(text: str) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    cursor = 0
    for raw_token in text.split():
        start = text.find(raw_token, cursor)
        if start < 0:
            start = cursor
        end = start + len(raw_token)
        cursor = end
        letters = _hebrew_letters(raw_token)
        if not letters:
            continue
        tokens.append(
            {
                "raw": raw_token,
                "letters": letters,
                "span": {"start": start, "end": end},
            }
        )
    return tokens


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _require_choice(value: Any, *, label: str, allowed: set[str]) -> str:
    normalized = str(value or "").strip()
    if normalized not in allowed:
        allowed_display = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported {label} '{normalized}'. Allowed values: {allowed_display}.")
    return normalized


@dataclass(slots=True)
class ParsedRef:
    raw_ref: str
    canonical_ref: str
    book_name: str
    book_abbrev: str
    filename: str
    chapter: int
    verse_start: int
    verse_end: int
    chapter_verse_count: int


class TanakhService:
    def __init__(
        self,
        *,
        cache_root: Path,
        fixture_root: Path | None = None,
        network_enabled: bool = True,
    ) -> None:
        self.cache_root = cache_root
        self.fixture_root = fixture_root
        self.network_enabled = network_enabled
        self._book_cache: dict[str, ET.Element] = {}
        self._manifest_cache: dict[str, Any] | None = None
        self._index_cache: dict[str, Any] | None = None

    @property
    def zip_path(self) -> Path:
        return self.cache_root / "Tanach.xml.zip"

    @property
    def header_path(self) -> Path:
        return self.cache_root / "Books" / "TanachHeader.xml"

    @property
    def index_xml_path(self) -> Path:
        return self.cache_root / "Books" / "TanachIndex.xml"

    @property
    def manifest_path(self) -> Path:
        return self.cache_root / "tanakh_manifest.json"

    @property
    def index_json_path(self) -> Path:
        return self.cache_root / "tanakh_index.json"

    def sync_substrate(self, *, force_refresh: bool = False) -> dict[str, Any]:
        required = [self.zip_path, self.header_path, self.index_xml_path]
        substrate_present = all(path.exists() for path in required)
        if substrate_present and not force_refresh and self.manifest_path.exists() and self.index_json_path.exists():
            self._manifest_cache = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            self._index_cache = json.loads(self.index_json_path.read_text(encoding="utf-8"))
            return self._manifest_cache

        fetch_timestamp_source = "manifest"
        if force_refresh or not substrate_present:
            self.cache_root.mkdir(parents=True, exist_ok=True)
            if self.network_enabled:
                self._fetch_network_substrate()
            elif self.fixture_root is not None:
                self._copy_fixture_substrate()
            else:
                raise RuntimeError("Tanakh substrate is missing and no network or fixture source is available.")
            fetch_timestamp = now_utc()
            fetch_timestamp_source = "sync_fetch"
        else:
            existing_manifest = json.loads(self.manifest_path.read_text(encoding="utf-8")) if self.manifest_path.exists() else {}
            fetch_timestamp = str(existing_manifest.get("fetch_timestamp") or "").strip()
            if not fetch_timestamp:
                fetch_timestamp = _iso_utc_from_timestamp(self.zip_path.stat().st_mtime)
                fetch_timestamp_source = "archive_mtime_inferred"
            else:
                fetch_timestamp_source = str(existing_manifest.get("fetch_timestamp_source") or "manifest")
        manifest = self._build_manifest(
            fetch_timestamp=fetch_timestamp,
            fetch_timestamp_source=fetch_timestamp_source,
        )
        self._manifest_cache = manifest
        index_payload = self._build_index()
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.index_json_path.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._index_cache = index_payload
        return manifest

    def get_manifest(self) -> dict[str, Any]:
        if self._manifest_cache is not None:
            return self._manifest_cache
        if self.manifest_path.exists():
            self._manifest_cache = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            return self._manifest_cache
        return self.sync_substrate()

    def get_index(self) -> dict[str, Any]:
        if self._index_cache is not None:
            return self._index_cache
        if self.index_json_path.exists():
            self._index_cache = json.loads(self.index_json_path.read_text(encoding="utf-8"))
            return self._index_cache
        self.sync_substrate()
        return self._index_cache or {}

    def get_passage(self, ref: str, mode: str = "keep_cantillation") -> dict[str, Any]:
        manifest = self.sync_substrate()
        parsed = self.parse_ref(ref)
        book_root = self._load_book_root(parsed.filename)
        book = book_root.find("tanach/book")
        if book is None:
            raise ValueError(f"Book XML for '{parsed.filename}' is malformed.")
        chapter = book.find(f"c[@n='{parsed.chapter}']")
        if chapter is None:
            raise ValueError(f"Chapter {parsed.chapter} is missing in {parsed.book_name}.")
        verses: list[dict[str, Any]] = []
        canonical_texts: list[str] = []
        processed_texts: list[str] = []
        for verse_number in range(parsed.verse_start, parsed.verse_end + 1):
            verse = chapter.find(f"v[@n='{verse_number}']")
            if verse is None:
                raise ValueError(f"Verse {parsed.chapter}:{verse_number} is missing in {parsed.book_name}.")
            verse_payload = self._verse_payload(parsed=parsed, verse=verse, mode=mode)
            canonical_texts.append(verse_payload["canonical_text"])
            processed_texts.append(verse_payload["processed"]["text"])
            verses.append(verse_payload)
        hash_basis = {
            "canonical_ref": parsed.canonical_ref,
            "mode": mode,
            "dataset_id": manifest["dataset_id"],
            "archive_sha256": manifest["archive_sha256"],
            "verses": [
                {
                    "ref": verse["ref"],
                    "canonical_text": verse["canonical_text"],
                    "processed_text": verse["processed"]["text"],
                }
                for verse in verses
            ],
        }
        output_hash = _stable_hash(hash_basis)
        return {
            "canonical_ref": parsed.canonical_ref,
            "requested_ref": ref,
            "mode": mode,
            "book": parsed.book_name,
            "book_abbrev": parsed.book_abbrev,
            "book_filename": parsed.filename,
            "chapter": parsed.chapter,
            "verse_range": {"start": parsed.verse_start, "end": parsed.verse_end},
            "verse_count": len(verses),
            "word_count": sum(len(verse["tokens"]) for verse in verses),
            "canonical_text": "\n".join(canonical_texts),
            "processed_text": "\n".join(processed_texts),
            "verses": verses,
            "output_hash": output_hash,
            "provenance": self._provenance(
                canonical_citation=parsed.canonical_ref,
                output_kind="canonical_text",
                preprocessing={"mode": mode},
                parameterization={"mode": mode},
                dataset=manifest,
                raw_text_source={
                    "home_url": TANAKH_HOME_URL,
                    "license_url": TANAKH_LICENSE_URL,
                    "book_file": f"Books/{parsed.filename}.xml",
                },
            ),
        }

    def gematria(self, input_text: str, scheme: str, preprocess: str) -> dict[str, Any]:
        if scheme not in GEMATRIA_SCHEMES:
            raise ValueError(f"Unsupported gematria scheme '{scheme}'.")
        processed = _preprocess_text(input_text, preprocess)
        table = STANDARD_GEMATRIA if scheme == "mispar_hechrechi" else FINAL_GEMATRIA
        breakdown: list[dict[str, Any]] = []
        total = 0
        for index, char in enumerate(processed["text"]):
            normalized = _normalize_letter(char)
            value = table.get(char, table.get(normalized))
            if value is None:
                continue
            total += value
            breakdown.append(
                {
                    "position": index,
                    "char": char,
                    "normalized_char": normalized,
                    "value": value,
                }
            )
        hash_basis = {
            "scheme": scheme,
            "preprocess": preprocess,
            "processed_text": processed["text"],
            "breakdown": breakdown,
            "total": total,
        }
        return {
            "input_text": input_text,
            "processed_text": processed["text"],
            "scheme": scheme,
            "preprocess": preprocess,
            "letter_count": len(breakdown),
            "total": total,
            "breakdown": breakdown,
            "output_hash": _stable_hash(hash_basis),
            "provenance": self._provenance(
                canonical_citation=None,
                output_kind="derived_transformation",
                preprocessing=processed,
                parameterization={"scheme": scheme, "preprocess": preprocess},
                dataset=self.get_manifest(),
                raw_text_source={"operation": "gematria"},
            ),
        }

    def notarikon(self, input_text: str, mode: str, preprocess: str) -> dict[str, Any]:
        if mode not in NOTARIKON_MODES:
            raise ValueError(f"Unsupported notarikon mode '{mode}'.")
        processed = _preprocess_text(input_text, preprocess)
        tokens = _tokenize_words(processed["text"])
        extracted: list[dict[str, Any]] = []
        letters: list[str] = []
        for index, token in enumerate(tokens, start=1):
            letter = token["letters"][0] if mode == "first_letter" else token["letters"][-1]
            letters.append(letter)
            extracted.append(
                {
                    "word_index": index,
                    "source_word": token["raw"],
                    "letter": letter,
                    "span": token["span"],
                }
            )
        hash_basis = {"mode": mode, "processed_text": processed["text"], "letters": letters}
        return {
            "input_text": input_text,
            "processed_text": processed["text"],
            "mode": mode,
            "result": "".join(letters),
            "extracted": extracted,
            "output_hash": _stable_hash(hash_basis),
            "provenance": self._provenance(
                canonical_citation=None,
                output_kind="derived_transformation",
                preprocessing=processed,
                parameterization={"mode": mode, "preprocess": preprocess},
                dataset=self.get_manifest(),
                raw_text_source={"operation": "notarikon"},
            ),
        }

    def temurah(self, input_text: str, mapping: str, preprocess: str) -> dict[str, Any]:
        if mapping not in TEMURAH_MAPPINGS:
            raise ValueError(f"Unsupported temurah mapping '{mapping}'.")
        processed = _preprocess_text(input_text, preprocess)
        transformed_chars: list[str] = []
        replacements: list[dict[str, Any]] = []
        for index, char in enumerate(processed["text"]):
            normalized = _normalize_letter(char)
            replacement = ATBASH_STANDARD.get(normalized)
            if replacement is None:
                transformed_chars.append(char)
                continue
            transformed_chars.append(replacement)
            replacements.append(
                {
                    "position": index,
                    "char": char,
                    "normalized_char": normalized,
                    "replacement": replacement,
                }
            )
        result = "".join(transformed_chars)
        hash_basis = {
            "mapping": mapping,
            "processed_text": processed["text"],
            "result": result,
            "replacements": replacements,
        }
        return {
            "input_text": input_text,
            "processed_text": processed["text"],
            "mapping": mapping,
            "normalization_note": "Final letters are normalized to standard forms before substitution.",
            "result": result,
            "replacements": replacements,
            "output_hash": _stable_hash(hash_basis),
            "provenance": self._provenance(
                canonical_citation=None,
                output_kind="derived_transformation",
                preprocessing=processed,
                parameterization={"mapping": mapping, "preprocess": preprocess},
                dataset=self.get_manifest(),
                raw_text_source={"operation": "temurah"},
            ),
        }

    def compile_merkavah_scene(self, ref: str, params: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_scene_params(params)
        passage = self.get_passage(ref, normalized["preprocess"])
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        link_map: list[dict[str, Any]] = []
        palette = self._scene_palette(normalized["theme"])
        node_index = 0
        last_word_node_id: str | None = None
        for verse_index, verse in enumerate(passage["verses"], start=1):
            verse_node_id = f"{passage['book_abbrev'].lower()}_{passage['chapter']}_{verse['verse']:02d}"
            verse_height = round((verse_index - 1) * normalized["verse_height"], 6)
            verse_node = {
                "id": verse_node_id,
                "kind": "verse",
                "label": verse["ref"],
                "position": {"x": 0.0, "y": verse_height, "z": 0.0},
                "color": palette["verse"],
            }
            nodes.append(verse_node)
            link_map.append({"scene_node_id": verse_node_id, "citation_span": verse["ref"]})
            for token in verse["tokens"]:
                node_index += 1
                letters = _hebrew_letters(token["processed_text"])
                letter_sum = sum(STANDARD_GEMATRIA.get(_normalize_letter(char), 0) for char in letters) or len(letters) or 1
                phase = self._unit_interval(f"{normalized['seed']}|{verse['ref']}|{token['word_index']}|{token['processed_text']}")
                angle = round((letter_sum * normalized["letter_angle"]) + (phase * 0.25), 6)
                radius = round((token["word_index"] * normalized["word_radius"]) + normalized["oscillation_amplitude"] * phase, 6)
                x = round(radius * self._cos(angle), 6)
                z = round(radius * self._sin(angle), 6)
                word_node_id = f"{verse_node_id}_w{token['word_index']:02d}"
                word_node = {
                    "id": word_node_id,
                    "kind": "word",
                    "label": token["processed_text"] or token["raw_text"],
                    "position": {"x": x, "y": verse_height, "z": z},
                    "color": palette["word"],
                    "angle": angle,
                    "radius": radius,
                }
                nodes.append(word_node)
                link_map.append(
                    {
                        "scene_node_id": word_node_id,
                        "citation_span": f"{verse['ref']} word {token['word_index']}",
                    }
                )
                edges.append({"id": f"{verse_node_id}->{word_node_id}", "source": verse_node_id, "target": word_node_id, "kind": "contains"})
                if last_word_node_id is not None:
                    edges.append(
                        {
                            "id": f"{last_word_node_id}->{word_node_id}",
                            "source": last_word_node_id,
                            "target": word_node_id,
                            "kind": "sequence",
                        }
                    )
                last_word_node_id = word_node_id
        hash_basis = {
            "ref": passage["canonical_ref"],
            "params": normalized,
            "nodes": nodes,
            "edges": edges,
            "link_map": link_map,
        }
        scene_hash = _stable_hash(hash_basis)
        scene_id = scene_hash[:12]
        return {
            "scene_id": scene_id,
            "scene_hash": scene_hash,
            "ref": passage["canonical_ref"],
            "params": normalized,
            "classification": "derived_visualization",
            "nodes": nodes,
            "edges": edges,
            "link_map": link_map,
            "provenance": self._provenance(
                canonical_citation=passage["canonical_ref"],
                output_kind="derived_visualization",
                preprocessing={"mode": normalized["preprocess"]},
                parameterization=normalized,
                dataset=self.get_manifest(),
                raw_text_source={"book_file": f"Books/{passage['book_filename']}.xml", "operation": "compile_merkavah_scene"},
            ),
        }

    def build_surface_bundle(self, *, ref: str = DEFAULT_TANAKH_REF, params: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized = self._normalize_surface_params(params or {})
        passage = self.get_passage(ref, normalized["preprocess"])
        passage_text = passage["canonical_text"]
        gematria_payload = self.gematria(passage_text, normalized["gematria_scheme"], normalized["preprocess"])
        notarikon_payload = self.notarikon(passage_text, normalized["notarikon_mode"], normalized["preprocess"])
        temurah_payload = self.temurah(passage_text, normalized["temurah_mapping"], normalized["preprocess"])
        scene_payload = self.compile_merkavah_scene(passage["canonical_ref"], {**normalized["scene"], "preprocess": normalized["preprocess"]})
        validation = self.build_render_validation_bundle()
        bundle_basis = {
            "ref": passage["canonical_ref"],
            "params": normalized,
            "passage_hash": passage["output_hash"],
            "gematria_hash": gematria_payload["output_hash"],
            "notarikon_hash": notarikon_payload["output_hash"],
            "temurah_hash": temurah_payload["output_hash"],
            "scene_hash": scene_payload["scene_hash"],
            "validation_hash": validation["report_hash"],
        }
        bundle_hash = _stable_hash(bundle_basis)
        return {
            "schema_version": 1,
            "generated_at": now_utc(),
            "current_ref": passage["canonical_ref"],
            "bundle_hash": bundle_hash,
            "params": normalized,
            "manifest": self.get_manifest(),
            "index_summary": self._index_summary(),
            "passage": passage,
            "analyses": {
                "gematria": gematria_payload,
                "notarikon": notarikon_payload,
                "temurah": temurah_payload,
            },
            "scene": scene_payload,
            "validation": validation,
        }

    def build_render_validation_bundle(self) -> dict[str, Any]:
        cases: list[dict[str, Any]] = []
        refs = [
            ("cantillation", "Ezek 1:1", "keep_cantillation"),
            ("vowels", "Ezek 1:3", "keep_vowels"),
            ("mixed_direction", "Ezek 1:5", "keep_cantillation"),
        ]
        for case_id, ref, mode in refs:
            passage = self.get_passage(ref, mode)
            text = passage["canonical_text"]
            rendered = text if case_id != "mixed_direction" else f"Ezek 1:5 :: {text}"
            cases.append(
                {
                    "case_id": case_id,
                    "ref": passage["canonical_ref"],
                    "mode": mode,
                    "render_text": rendered,
                    "oracle_text": text,
                    "codepoint_count": len(rendered),
                    "grapheme_count": _grapheme_count(rendered),
                    "mark_counts": _mark_counts(text),
                    "comparison_status": "manual_review_required",
                    "manual_check": "Open tanakh_render_validation.html and compare each rendered line with the oracle text; verify niqqud/cantillation placement and mixed-direction ordering.",
                }
            )
        report_basis = {
            "dataset_id": self.get_manifest()["dataset_id"],
            "cases": [
                {
                    "case_id": case["case_id"],
                    "ref": case["ref"],
                    "mode": case["mode"],
                    "render_text": case["render_text"],
                    "oracle_text": case["oracle_text"],
                }
                for case in cases
            ],
        }
        report_hash = _stable_hash(report_basis)
        return {
            "generated_at": now_utc(),
            "dataset_id": self.get_manifest()["dataset_id"],
            "comparison_status": "manual_review_required",
            "comparison_boundary": "The harness automates artifact generation, codepoint/grapheme counts, and oracle capture. Glyph-placement comparison remains manual.",
            "cases": cases,
            "report_hash": report_hash,
            "html": self._render_validation_html(cases),
        }

    def export_surface_bundle(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        out_dir: Path,
        ref: str = DEFAULT_TANAKH_REF,
        params: dict[str, Any] | None = None,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        out_dir.mkdir(parents=True, exist_ok=True)
        bundle = self.build_surface_bundle(ref=ref, params=params)
        manifest_path = out_dir / "tanakh_manifest.json"
        index_path = out_dir / "tanakh_index.json"
        passage_dir = out_dir / "tanakh_passage_cache"
        passage_dir.mkdir(parents=True, exist_ok=True)
        passage_path = passage_dir / f"{_slugify_ref(bundle['current_ref'])}.json"
        scene_path = out_dir / f"tanakh_scene_{bundle['scene']['scene_id']}.json"
        measurements_path = out_dir / "tanakh_measurements.json"
        validation_json_path = out_dir / "tanakh_render_validation.json"
        validation_html_path = out_dir / "tanakh_render_validation.html"
        surface_path = out_dir / "tanakh_surface.json"

        manifest_path.write_text(json.dumps(bundle["manifest"], ensure_ascii=False, indent=2), encoding="utf-8")
        index_path.write_text(json.dumps(self.get_index(), ensure_ascii=False, indent=2), encoding="utf-8")
        passage_path.write_text(json.dumps(bundle["passage"], ensure_ascii=False, indent=2), encoding="utf-8")
        scene_path.write_text(json.dumps(bundle["scene"], ensure_ascii=False, indent=2), encoding="utf-8")
        validation_payload = dict(bundle["validation"])
        validation_html = validation_payload.pop("html")
        validation_json_path.write_text(json.dumps(validation_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        validation_html_path.write_text(validation_html, encoding="utf-8")

        measurement_payload = {
            "generated_at": now_utc(),
            "dataset_id": bundle["manifest"]["dataset_id"],
            "current_ref": bundle["current_ref"],
            "runs": [
                {
                    "run_id": bundle["bundle_hash"][:12],
                    "ref": bundle["current_ref"],
                    "created_at": bundle["generated_at"],
                    "output_hashes": {
                        "passage": bundle["passage"]["output_hash"],
                        "gematria": bundle["analyses"]["gematria"]["output_hash"],
                        "notarikon": bundle["analyses"]["notarikon"]["output_hash"],
                        "temurah": bundle["analyses"]["temurah"]["output_hash"],
                        "scene": bundle["scene"]["scene_hash"],
                        "validation": bundle["validation"]["report_hash"],
                    },
                    "artifacts": {
                        "passage": f"./tanakh_passage_cache/{passage_path.name}",
                        "scene": f"./{scene_path.name}",
                        "validation": "./tanakh_render_validation.json",
                    },
                }
            ],
        }
        measurements_path.write_text(json.dumps(measurement_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        surface_payload = {
            "generated_at": now_utc(),
            "experiment_id": experiment_id,
            "session_id": session_id,
            "current_ref": bundle["current_ref"],
            "bundle_hash": bundle["bundle_hash"],
            "live_query_supported": True,
            "artifacts": {
                "manifest": "./tanakh_manifest.json",
                "index": "./tanakh_index.json",
                "passage": f"./tanakh_passage_cache/{passage_path.name}",
                "scene": f"./{scene_path.name}",
                "measurements": "./tanakh_measurements.json",
                "validation": "./tanakh_render_validation.json",
                "validation_html": "./tanakh_render_validation.html",
            },
            "bundle": {
                **bundle,
                "validation": validation_payload,
            },
        }
        surface_path.write_text(json.dumps(surface_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return (
            {
                "tanakh_surface_json": str(surface_path),
                "tanakh_manifest": str(manifest_path),
                "tanakh_index": str(index_path),
                "tanakh_passage": str(passage_path),
                "tanakh_scene": str(scene_path),
                "tanakh_measurements": str(measurements_path),
                "tanakh_render_validation": str(validation_json_path),
                "tanakh_render_validation_html": str(validation_html_path),
            },
            surface_payload,
        )

    def parse_ref(self, ref: str) -> ParsedRef:
        index = self.get_index()
        match = REF_RE.match(ref)
        if match is None:
            raise ValueError(f"Unsupported reference format '{ref}'. Expected 'Book chapter[:start-end]'.")
        book_key = _normalize_alias(match.group("book"))
        aliases = index.get("aliases", {})
        filename = aliases.get(book_key)
        if filename is None:
            raise ValueError(f"Unknown Tanakh book '{match.group('book')}'.")
        book_entry = index["book_lookup"][filename]
        chapter = int(match.group("chapter"))
        if chapter < 1 or chapter > len(book_entry["chapters"]):
            raise ValueError(f"{book_entry['name']} chapter {chapter} is outside the indexed range.")
        chapter_verse_count = book_entry["chapters"][chapter - 1]["verse_count"]
        verse_start = int(match.group("verse_start")) if match.group("verse_start") else 1
        verse_end = int(match.group("verse_end")) if match.group("verse_end") else (verse_start if match.group("verse_start") else chapter_verse_count)
        if verse_start < 1 or verse_end < verse_start or verse_end > chapter_verse_count:
            raise ValueError(f"{book_entry['name']} {chapter}:{verse_start}-{verse_end} is outside the indexed verse range.")
        canonical_ref = f"{book_entry['abbrev']} {chapter}"
        if verse_start != 1 or verse_end != chapter_verse_count:
            canonical_ref = f"{book_entry['abbrev']} {chapter}:{verse_start}"
            if verse_end != verse_start:
                canonical_ref = f"{canonical_ref}-{verse_end}"
        return ParsedRef(
            raw_ref=ref,
            canonical_ref=canonical_ref,
            book_name=book_entry["name"],
            book_abbrev=book_entry["abbrev"],
            filename=filename,
            chapter=chapter,
            verse_start=verse_start,
            verse_end=verse_end,
            chapter_verse_count=chapter_verse_count,
        )

    def _fetch_network_substrate(self) -> None:
        self.cache_root.mkdir(parents=True, exist_ok=True)
        zip_bytes, _ = self._fetch_url(TANAKH_ZIP_URL)
        self.zip_path.write_bytes(zip_bytes)
        with zipfile.ZipFile(self.zip_path) as archive:
            archive.extractall(self.cache_root)
        header_bytes, _ = self._fetch_url(TANAKH_HEADER_URL)
        index_bytes, _ = self._fetch_url(TANAKH_INDEX_URL)
        self.header_path.parent.mkdir(parents=True, exist_ok=True)
        self.header_path.write_bytes(header_bytes)
        self.index_xml_path.write_bytes(index_bytes)

    def _copy_fixture_substrate(self) -> None:
        if self.fixture_root is None:
            raise RuntimeError("Fixture root is not configured.")
        if self.cache_root.exists():
            shutil.rmtree(self.cache_root)
        shutil.copytree(self.fixture_root, self.cache_root)

    def _fetch_url(self, url: str) -> tuple[bytes, dict[str, str]]:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read()
            headers = {key: value for key, value in response.headers.items()}
        return body, headers

    def _build_manifest(self, *, fetch_timestamp: str, fetch_timestamp_source: str) -> dict[str, Any]:
        header_root = ET.parse(self.header_path).getroot()
        edition = header_root.find("teiHeader/fileDesc/editionStmt/edition")
        if edition is None:
            raise RuntimeError("TanachHeader.xml is missing edition metadata.")
        version = (edition.findtext("version") or "").strip()
        text_date = (edition.findtext("date") or "").strip()
        build = (edition.findtext("build") or "").strip()
        build_datetime = (edition.findtext("buildDateTime") or "").strip()
        archive_sha256 = _sha256_path(self.zip_path)
        archive_length = self.zip_path.stat().st_size
        dataset_id = f"uxlc-{version.lower().replace(' ', '-')}-build-{build}"
        source_mode = "network" if self.network_enabled else "fixture"
        return {
            "dataset_id": dataset_id,
            "text_version": version,
            "text_date": text_date,
            "build": build,
            "build_datetime": build_datetime,
            "archive_length_bytes": archive_length,
            "archive_sha256": archive_sha256,
            "source_urls": {
                "home": TANAKH_HOME_URL,
                "license": TANAKH_LICENSE_URL,
                "zip": TANAKH_ZIP_URL,
                "header": TANAKH_HEADER_URL,
                "index": TANAKH_INDEX_URL,
            },
            "fetch_timestamp": fetch_timestamp,
            "fetch_timestamp_source": fetch_timestamp_source,
            "source_mode": source_mode,
            "header_path": str(self.header_path),
            "index_path": str(self.index_xml_path),
            "zip_path": str(self.zip_path),
        }

    def _build_index(self) -> dict[str, Any]:
        root = ET.parse(self.index_xml_path).getroot()
        manifest = self._manifest_cache
        if manifest is None:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8")) if self.manifest_path.exists() else self.sync_substrate()
        books: list[dict[str, Any]] = []
        aliases: dict[str, str] = {}
        lookup: dict[str, dict[str, Any]] = {}
        for book in root.findall("tanach/book"):
            names = book.find("names")
            if names is None:
                continue
            name = (names.findtext("name") or "").strip()
            abbrev = (names.findtext("abbrev") or name).strip()
            filename = (names.findtext("filename") or name).strip()
            chapters = [
                {
                    "chapter": int(chapter.get("n", "0")),
                    "verse_count": int(chapter.findtext("vs") or "0"),
                }
                for chapter in book.findall("c")
            ]
            book_payload = {
                "name": name,
                "abbrev": abbrev,
                "filename": filename,
                "chapter_count": len(chapters),
                "chapters": chapters,
            }
            books.append(book_payload)
            lookup[filename] = book_payload
            for alias in {name, abbrev, filename, name.replace("_", " "), filename.replace("_", " ")}:
                aliases[_normalize_alias(alias)] = filename
        return {
            "generated_at": now_utc(),
            "dataset_id": manifest["dataset_id"],
            "books": books,
            "aliases": aliases,
            "book_lookup": lookup,
        }

    def _load_book_root(self, filename: str) -> ET.Element:
        if filename in self._book_cache:
            return self._book_cache[filename]
        path = self.cache_root / "Books" / f"{filename}.xml"
        if not path.exists():
            raise ValueError(f"Missing Tanakh book file '{path.name}'.")
        root = ET.parse(path).getroot()
        self._book_cache[filename] = root
        return root

    def _verse_payload(self, *, parsed: ParsedRef, verse: ET.Element, mode: str) -> dict[str, Any]:
        tokens: list[dict[str, Any]] = []
        canonical_cursor = 0
        raw_parts: list[str] = []
        markers: list[dict[str, Any]] = []
        for child in list(verse):
            tag = child.tag
            token_text = "".join(child.itertext()).replace("\n", "")
            if tag in WORDLIKE_TAGS:
                raw_parts.append(token_text)
                processed = _preprocess_text(token_text, mode)
                start = canonical_cursor
                canonical_cursor += len(token_text)
                tokens.append(
                    {
                        "tag": tag,
                        "word_index": len(tokens) + 1,
                        "raw_text": token_text,
                        "processed_text": processed["text"],
                        "canonical_span": {"start": start, "end": canonical_cursor},
                        "processed_span_length": len(processed["text"]),
                    }
                )
            else:
                markers.append({"tag": tag, "value": token_text})
        canonical_text = "".join(raw_parts).strip()
        processed = _preprocess_text(canonical_text, mode)
        verse_number = int(verse.get("n", "0"))
        return {
            "ref": f"{parsed.book_abbrev} {parsed.chapter}:{verse_number}",
            "verse": verse_number,
            "canonical_text": canonical_text,
            "processed": processed,
            "tokens": tokens,
            "markers": markers,
            "codepoint_count": len(canonical_text),
            "grapheme_count": _grapheme_count(canonical_text),
        }

    def _provenance(
        self,
        *,
        canonical_citation: str | None,
        output_kind: str,
        preprocessing: dict[str, Any],
        parameterization: dict[str, Any],
        dataset: dict[str, Any],
        raw_text_source: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "canonical_citation": canonical_citation,
            "raw_text_source": raw_text_source,
            "dataset": {
                "dataset_id": dataset["dataset_id"],
                "text_version": dataset["text_version"],
                "build": dataset["build"],
                "build_datetime": dataset["build_datetime"],
                "archive_sha256": dataset["archive_sha256"],
            },
            "preprocessing": preprocessing,
            "operator_version": __version__,
            "parameterization": parameterization,
            "created_at": now_utc(),
            "output_kind": output_kind,
        }

    def _index_summary(self) -> dict[str, Any]:
        index = self.get_index()
        return {
            "book_count": len(index.get("books", [])),
            "dataset_id": index.get("dataset_id"),
            "books": [book["abbrev"] for book in index.get("books", [])[:12]],
        }

    def _normalize_scene_params(self, params: dict[str, Any]) -> dict[str, Any]:
        preprocess = _require_choice(
            params.get("preprocess", DEFAULT_TANAKH_PARAMS["preprocess"]),
            label="preprocess mode",
            allowed=PREPROCESS_MODES,
        )
        theme = _require_choice(params.get("theme", "amber"), label="scene theme", allowed=SCENE_THEMES)
        return {
            "preprocess": preprocess,
            "letter_angle": round(_clamp(float(params.get("letter_angle", 0.14)), 0.02, 1.5), 6),
            "word_radius": round(_clamp(float(params.get("word_radius", 0.22)), 0.05, 4.0), 6),
            "verse_height": round(_clamp(float(params.get("verse_height", 1.1)), 0.1, 5.0), 6),
            "theme": theme,
            "oscillation_amplitude": round(_clamp(float(params.get("oscillation_amplitude", 0.18)), 0.0, 2.0), 6),
            "seed": _safe_int(params.get("seed"), 11),
        }

    def _normalize_surface_params(self, params: dict[str, Any]) -> dict[str, Any]:
        preprocess = _require_choice(
            params.get("preprocess", DEFAULT_TANAKH_PARAMS["preprocess"]),
            label="preprocess mode",
            allowed=PREPROCESS_MODES,
        )
        scene = dict(DEFAULT_TANAKH_PARAMS["scene"])
        scene.update(params.get("scene") or {})
        scene["preprocess"] = preprocess
        return {
            "preprocess": preprocess,
            "gematria_scheme": _require_choice(
                params.get("gematria_scheme", DEFAULT_TANAKH_PARAMS["gematria_scheme"]),
                label="gematria scheme",
                allowed=GEMATRIA_SCHEMES,
            ),
            "notarikon_mode": _require_choice(
                params.get("notarikon_mode", DEFAULT_TANAKH_PARAMS["notarikon_mode"]),
                label="notarikon mode",
                allowed=NOTARIKON_MODES,
            ),
            "temurah_mapping": _require_choice(
                params.get("temurah_mapping", DEFAULT_TANAKH_PARAMS["temurah_mapping"]),
                label="temurah mapping",
                allowed=TEMURAH_MAPPINGS,
            ),
            "scene": self._normalize_scene_params(scene),
        }

    def _scene_palette(self, theme: str) -> dict[str, str]:
        palettes = {
            "amber": {"verse": "#ffd18a", "word": "#efb15f"},
            "brass": {"verse": "#f4c66f", "word": "#c58a2d"},
            "sea": {"verse": "#a9dbff", "word": "#5aa8d6"},
        }
        return palettes.get(theme, palettes["amber"])

    def _unit_interval(self, seed: str) -> float:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) / 0xFFFFFFFF

    def _sin(self, angle: float) -> float:
        import math

        return math.sin(angle)

    def _cos(self, angle: float) -> float:
        import math

        return math.cos(angle)

    def _render_validation_html(self, cases: list[dict[str, Any]]) -> str:
        cards: list[str] = []
        for case in cases:
            direction = "ltr" if case["case_id"] == "mixed_direction" else "rtl"
            cards.append(
                f"""
<section class="case-card">
  <h2>{html.escape(case['case_id'])} · {html.escape(case['ref'])}</h2>
  <p class="meta">mode={html.escape(case['mode'])} codepoints={case['codepoint_count']} graphemes={case['grapheme_count']}</p>
  <div class="rendered" dir="{direction}" lang="he">{html.escape(case['render_text'])}</div>
  <div class="oracle" dir="rtl" lang="he">{html.escape(case['oracle_text'])}</div>
  <p class="manual">{html.escape(case['manual_check'])}</p>
</section>
"""
            )
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Tanakh Render Validation</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #120b07;
      --panel: rgba(34, 22, 13, 0.95);
      --border: rgba(239, 177, 95, 0.24);
      --ink: #f7ecd4;
      --muted: #d2bf9e;
      --amber: #efb15f;
    }}
    body {{
      margin: 0;
      padding: 24px;
      background: radial-gradient(circle at top left, rgba(239, 177, 95, 0.14), transparent 28%), linear-gradient(180deg, #120b07 0%, #0d0805 100%);
      color: var(--ink);
      font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
    }}
    .case-grid {{
      display: grid;
      gap: 18px;
    }}
    .case-card {{
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
      background: var(--panel);
    }}
    h1, h2 {{
      margin: 0 0 10px;
    }}
    .meta, .manual {{
      color: var(--muted);
    }}
    .rendered, .oracle {{
      margin-top: 12px;
      padding: 14px;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.02);
      font-size: 1.35rem;
      line-height: 1.8;
      unicode-bidi: plaintext;
      font-family: "Times New Roman", "Noto Serif Hebrew", "David", serif;
    }}
    .oracle {{
      margin-top: 10px;
      color: var(--amber);
    }}
  </style>
</head>
<body>
  <h1>Tanakh Render Validation</h1>
  <p class="manual">This harness automates artifact generation only. Compare each rendered line with the oracle line before claiming the Hebrew surface is correct.</p>
  <div class="case-grid">
    {"".join(cards)}
  </div>
</body>
</html>"""
