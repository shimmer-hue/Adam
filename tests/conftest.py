from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from eden.config import RuntimeSettings
from eden.logging import RuntimeLog
from eden.runtime import EdenRuntime
from eden.storage.graph_store import GraphStore
from eden.tanakh import TanakhService


EZEKIEL_1_WORDS: dict[int, list[str]] = {
    1: [
        "\u05d5\u05b7\u05d9\u05b0\u05d4\u05b4\u05a3\u05d9 \u05c0",
        "\u05d1\u05bc\u05b4\u05e9\u05c1\u05b0\u05dc\u05b9\u05e9\u05c1\u05b4\u05a3\u05d9\u05dd",
        "\u05e9\u05c1\u05b8\u05e0\u05b8\u0597\u05d4",
        "\u05d1\u05bc\u05b8\u05bd\u05e8\u05b0\u05d1\u05b4\u05d9\u05e2\u05b4\u05d9\u0599",
        "\u05d1\u05bc\u05b7\u05d7\u05b2\u05de\u05b4\u05e9\u05c1\u05bc\u05b8\u05a3\u05d4",
        "\u05dc\u05b7\u05d7\u05b9\u0594\u05d3\u05b6\u05e9\u05c1",
        "\u05d5\u05b7\u05d0\u05b2\u05e0\u05b4\u05a5\u05d9",
        "\u05d1\u05b0\u05ea\u05bd\u05d5\u05b9\u05da\u05b0\u05be",
        "\u05d4\u05b7\u05d2\u05bc\u05d5\u05b9\u05dc\u05b8\u0596\u05d4",
        "\u05e2\u05b7\u05dc\u05be",
        "\u05e0\u05b0\u05d4\u05b7\u05e8\u05be",
        "\u05db\u05bc\u05b0\u05d1\u05b8\u0591\u05e8",
        "\u05e0\u05b4\u05e4\u05b0\u05ea\u05bc\u05b0\u05d7\u05d5\u05bc\u0599",
        "\u05d4\u05b7\u05e9\u05c1\u05bc\u05b8\u05de\u05b7\u0594\u05d9\u05b4\u05dd",
        "\u05d5\u05b8\u05d0\u05b6\u05e8\u05b0\u05d0\u05b6\u0596\u05d4",
        "\u05de\u05b7\u05e8\u05b0\u05d0\u05a5\u05d5\u05b9\u05ea",
        "\u05d0\u05b1\u05dc\u05b9\u05d4\u05b4\u05bd\u05d9\u05dd\u05c3",
    ],
    2: [
        "\u05d1\u05bc\u05b7\u05d7\u05b2\u05de\u05b4\u05e9\u05c1\u05bc\u05b8\u0596\u05d4",
        "\u05dc\u05b7\u05d7\u05b9\u0591\u05d3\u05b6\u05e9\u05c1",
        "\u05d4\u05b4\u059a\u05d9\u05d0",
        "\u05d4\u05b7\u05e9\u05c1\u05bc\u05b8\u05e0\u05b8\u05a3\u05d4",
        "\u05d4\u05b7\u05d7\u05b2\u05de\u05b4\u05d9\u05e9\u05c1\u05b4\u0594\u05d9\u05ea",
        "\u05dc\u05b0\u05d2\u05b8\u05dc\u0596\u05d5\u05bc\u05ea",
        "\u05d4\u05b7\u05de\u05bc\u05b6\u05a5\u05dc\u05b6\u05da\u05b0",
        "\u05d9\u05d5\u05b9\u05d9\u05b8\u05db\u05b4\u05bd\u05d9\u05df\u05c3",
    ],
    3: [
        "\u05d4\u05b8\u05d9\u05b9\u05a3\u05d4",
        "\u05d4\u05b8\u05d9\u05b8\u05a3\u05d4",
        "\u05d3\u05b0\u05d1\u05b7\u05e8\u05be",
        "\u05d9\u05b0\u05a0\u05d4\u05d5\u05b8\u05d4",
        "\u05d0\u05b6\u05dc\u05be",
        "\u05d9\u05b0\u05d7\u05b6\u05d6\u05b0\u05e7\u05b5\u05a8\u05d0\u05dc",
        "\u05d1\u05bc\u05b6\u05df\u05be",
        "\u05d1\u05bc\u05d5\u05bc\u05d6\u05b4\u05a7\u05d9",
        "\u05d4\u05b7\u05db\u05bc\u05b9\u05d4\u05b5\u059b\u05df",
        "\u05d1\u05bc\u05b0\u05d0\u05b6\u05a5\u05e8\u05b6\u05e5",
        "\u05db\u05bc\u05b7\u05e9\u05c2\u05b0\u05d3\u05bc\u05b4\u0596\u05d9\u05dd",
        "\u05e2\u05b7\u05dc\u05be",
        "\u05e0\u05b0\u05d4\u05b7\u05e8\u05be",
        "\u05db\u05bc\u05b0\u05d1\u05b8\u0591\u05e8",
        "\u05d5\u05b7\u05ea\u05bc\u05b0\u05d4\u05b4\u05a5\u05d9",
        "\u05e2\u05b8\u05dc\u05b8\u059b\u05d9\u05d5",
        "\u05e9\u05c1\u05b8\u0596\u05dd",
        "\u05d9\u05b7\u05d3\u05be",
        "\u05d9\u05b0\u05d4\u05d5\u05b8\u05bd\u05d4\u05c3",
    ],
    4: [
        "\u05d5\u05b8\u05d0\u05b5\u05a1\u05e8\u05b6\u05d0",
        "\u05d5\u05b0\u05d4\u05b4\u05e0\u05bc\u05b5\u05d4\u05a9",
        "\u05e8\u05a8\u05d5\u05bc\u05d7\u05b7",
        "\u05e1\u05b0\u05e2\u05b8\u05e8\u05b8\u059c\u05d4",
        "\u05d1\u05bc\u05b8\u05d0\u05b8\u05a3\u05d4",
        "\u05de\u05b4\u05df\u05be",
        "\u05d4\u05b7\u05e6\u05bc\u05b8\u05e4\u0597\u05d5\u05b9\u05df",
        "\u05e2\u05b8\u05e0\u05b8\u05a4\u05df",
        "\u05d2\u05bc\u05b8\u05d3\u05d5\u05b9\u05dc\u0599",
        "\u05d5\u05b0\u05d0\u05b5\u05a3\u05e9\u05c1",
        "\u05de\u05b4\u05ea\u05b0\u05dc\u05b7\u05e7\u05bc\u05b7\u0594\u05d7\u05b7\u05ea",
        "\u05d5\u05b0\u05e0\u05b9\u05a5\u05d2\u05b7\u05bd\u05d4\u05bc",
        "\u05dc\u0596\u05d5\u05b9",
        "\u05e1\u05b8\u05d1\u05b4\u0591\u05d9\u05d1",
        "\u05d5\u05bc\u05de\u05b4\u05a8\u05ea\u05bc\u05d5\u05b9\u05db\u05b8\u0594\u05d4\u05bc",
        "\u05db\u05bc\u05b0\u05e2\u05b5\u05a5\u05d9\u05df",
        "\u05d4\u05b7\u05d7\u05b7\u05e9\u05c1\u05b0\u05de\u05b7\u0596\u05dc",
        "\u05de\u05b4\u05ea\u05bc\u05a5\u05d5\u05b9\u05da\u05b0",
        "\u05d4\u05b8\u05d0\u05b5\u05bd\u05e9\u05c1\u05c3",
    ],
    5: [
        "\u05d5\u05bc\u05de\u05b4\u05a8\u05ea\u05bc\u05d5\u05b9\u05db\u05b8\u0594\u05d4\u05bc",
        "\u05d3\u05bc\u05b0\u05de\u0596\u05d5\u05bc\u05ea",
        "\u05d0\u05b7\u05e8\u05b0\u05d1\u05bc\u05b7\u05a3\u05e2",
        "\u05d7\u05b7\u05d9\u05bc\u0591\u05d5\u05b9\u05ea",
        "\u05d5\u05b0\u05d6\u05b6\u05d4\u0599",
        "\u05de\u05b7\u05e8\u05b0\u05d0\u05b5\u05bd\u05d9\u05d4\u05b6\u0594\u05df",
        "\u05d3\u05bc\u05b0\u05de\u05a5\u05d5\u05bc\u05ea",
        "\u05d0\u05b8\u05d3\u05b8\u0596\u05dd",
        "\u05dc\u05b8\u05d4\u05b5\u05bd\u05e0\u05bc\u05b8\u05d4\u05c3",
    ],
}


def _build_tanakh_fixture(root: Path) -> Path:
    books_dir = root / "Books"
    books_dir.mkdir(parents=True, exist_ok=True)

    header_xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
  <teiHeader>
    <fileDesc>
      <editionStmt>
        <edition>
          <version>UXLC 2.4</version>
          <date>19 Oct 2025</date>
          <build>27.5</build>
          <buildDateTime>13 Oct 2025  06:35</buildDateTime>
        </edition>
      </editionStmt>
    </fileDesc>
  </teiHeader>
</root>
"""
    index_xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
  <tanach>
    <book>
      <names>
        <name>Ezekiel</name>
        <abbrev>Ezek</abbrev>
        <filename>Ezekiel</filename>
      </names>
      <c n="1"><vs>5</vs></c>
    </book>
  </tanach>
</root>
"""

    verse_blocks: list[str] = []
    for verse_number, words in EZEKIEL_1_WORDS.items():
        word_xml = "".join(f"<w>{word}</w>" for word in words)
        verse_blocks.append(f'      <v n="{verse_number}">{word_xml}</v>')
    book_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<root>\n"
        "  <tanach>\n"
        "    <book>\n"
        "      <names><name>Ezekiel</name><abbrev>Ezek</abbrev><filename>Ezekiel</filename></names>\n"
        "      <c n=\"1\">\n"
        f"{chr(10).join(verse_blocks)}\n"
        "      </c>\n"
        "    </book>\n"
        "  </tanach>\n"
        "</root>\n"
    )

    (books_dir / "TanachHeader.xml").write_text(header_xml, encoding="utf-8")
    (books_dir / "TanachIndex.xml").write_text(index_xml, encoding="utf-8")
    (books_dir / "Ezekiel.xml").write_text(book_xml, encoding="utf-8")

    zip_path = root / "Tanach.xml.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for arcname in ("Books/TanachHeader.xml", "Books/TanachIndex.xml", "Books/Ezekiel.xml"):
            info = zipfile.ZipInfo(arcname)
            info.date_time = (2025, 10, 13, 6, 35, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (root / arcname).read_bytes())
    return root


def _write_minimal_text_pdf(path: Path, text: str) -> None:
    stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body.extend(f"{index} 0 obj\n".encode("ascii"))
        body.extend(obj)
        body.extend(b"\nendobj\n")
    xref_start = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    body.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(bytes(body))


@pytest.fixture()
def runtime(tmp_path: Path) -> EdenRuntime:
    store = GraphStore(tmp_path / "eden.db")
    log = RuntimeLog(tmp_path / "runtime.jsonl")
    settings = RuntimeSettings(model_backend="mock")
    runtime = EdenRuntime(store=store, settings=settings, runtime_log=log)
    runtime.conversation_export_root = tmp_path / "exports" / "conversations"
    runtime.hum_service.root = tmp_path / "hum_state"
    fixture_root = _build_tanakh_fixture(tmp_path / "tanakh_fixture")
    tanakh_service = TanakhService(
        cache_root=tmp_path / "tanakh_cache",
        fixture_root=fixture_root,
        network_enabled=False,
    )
    runtime.tanakh_service = tanakh_service
    runtime.exporter.tanakh_service = tanakh_service
    runtime.observatory_service.tanakh_service = tanakh_service
    return runtime


@pytest.fixture()
def sample_files(tmp_path: Path) -> dict[str, Path]:
    txt_path = tmp_path / "sample.txt"
    txt_path.write_text("EDEN remembers by external graph state rather than by weight updates.", encoding="utf-8")

    md_path = tmp_path / "sample.md"
    md_path.write_text("# Adam\n\nFeedback changes regard and retrieval pressure.\n", encoding="utf-8")

    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("term,weight\nregard,0.9\nmembrane,0.7\n", encoding="utf-8")

    pdf_path = tmp_path / "sample.pdf"
    _write_minimal_text_pdf(pdf_path, "EDEN PDF memory graph")

    return {"txt": txt_path, "md": md_path, "csv": csv_path, "pdf": pdf_path}
