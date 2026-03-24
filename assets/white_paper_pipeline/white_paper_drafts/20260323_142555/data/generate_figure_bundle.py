from __future__ import annotations

import csv
import hashlib
import json
import math
import sqlite3
import textwrap
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np
from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path("/Users/brianray/Adam")
RUN_ROOT = REPO_ROOT / "assets/white_paper_pipeline/white_paper_drafts/20260323_142555"
FIGURE_BUNDLE = RUN_ROOT / "figure_bundle"
STATIC_DIR = FIGURE_BUNDLE / "static"
INTERACTIVE_DIR = FIGURE_BUNDLE / "interactive"
FIGURE_DATA_DIR = FIGURE_BUNDLE / "data"
REGISTRY_DIR = FIGURE_BUNDLE / "registry"
LATEX_DIR = FIGURE_BUNDLE / "latex"
RUN_DATA_DIR = RUN_ROOT / "data"
GENERATOR_PATH = RUN_DATA_DIR / "generate_figure_bundle.py"

BRIEF_PATH = REPO_ROOT / "assets/white_paper_pipeline/intel_briefs/adam_intelligence_20260323_130734_core_audit.md"
MEMO_PATH = REPO_ROOT / "assets/white_paper_pipeline/writing_memos/20260323_131951_codex_memo.md"
BASELINE_TEXT_PATH = REPO_ROOT / "tmp/source_inventory/eden_whitepaper_v14.txt"
README_PATH = REPO_ROOT / "README.md"
CHARTER_PATH = REPO_ROOT / "docs/PROJECT_CHARTER.md"
RUNTIME_LOG_PATH = REPO_ROOT / "logs/runtime.jsonl"
DB_PATH = REPO_ROOT / "data/eden.db"
MEASUREMENT_PATH = REPO_ROOT / "exports/b178bed2-731e-4f8b-b5f8-a93d1300b2f7/measurement_events.json"
GRAPH_PATH = REPO_ROOT / "exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/graph_knowledge_base.json"
GEOMETRY_PATH = REPO_ROOT / "exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/geometry_diagnostics.json"
OBSERVATORY_INDEX_PATH = REPO_ROOT / "exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/observatory_index.json"
TRANSCRIPT_PATH = REPO_ROOT / "exports/conversations/adam-graph-bb298723/operator-session-8a5213f7.md"

WIDTH = 1800
HEIGHT = 1000
MARGIN = 120
BG = "#f5f1e8"
INK = "#1b1b1b"
MUTED = "#676054"
GRID = "#d9d0c0"
OBS = "#205f9f"
OBS_2 = "#3c7cc1"
OBS_3 = "#8ab0d6"
OBS_4 = "#dbe8f3"
SYN = "#a6422b"
SYN_2 = "#d88a4b"
SYN_3 = "#f0c58e"
GREEN = "#466b3f"
RED = "#8a2f2f"
PURPLE = "#5a4a82"
GOLD = "#9b7c17"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Tahoma.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE_FONT = load_font(54, bold=True)
SUBTITLE_FONT = load_font(26)
LABEL_FONT = load_font(24)
SMALL_FONT = load_font(20)
BODY_FONT = load_font(22)
BIG_NUMBER_FONT = load_font(42, bold=True)


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, *, font: ImageFont.ImageFont = BODY_FONT, fill: str = INK, anchor: str | None = None) -> None:
    draw.text(xy, value, font=font, fill=fill, anchor=anchor)


def wrap(value: str, width: int) -> str:
    return "\n".join(textwrap.wrap(value, width=width, break_long_words=False))


def new_canvas(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 120), fill="#ebe4d7")
    text(draw, (MARGIN, 44), title, font=TITLE_FONT)
    text(draw, (MARGIN, 92), subtitle, font=SUBTITLE_FONT, fill=MUTED)
    return image, draw


def save_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def save_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def bar_chart(
    labels: list[str],
    values: list[float],
    *,
    title: str,
    subtitle: str,
    fill: str,
    note: str,
    rotate: bool = False,
    value_fmt: str = "{:.0f}",
) -> Image.Image:
    image, draw = new_canvas(title, subtitle)
    chart_left = MARGIN
    chart_top = 220
    chart_right = WIDTH - MARGIN
    chart_bottom = HEIGHT - 200
    draw.rectangle((chart_left, chart_top, chart_right, chart_bottom), outline=GRID, width=2)
    max_value = max(values) if values else 1.0
    max_value = max_value if max_value > 0 else 1.0
    steps = 5
    for index in range(steps + 1):
        y = chart_bottom - (chart_bottom - chart_top) * index / steps
        draw.line((chart_left, y, chart_right, y), fill=GRID, width=2)
        value = max_value * index / steps
        text(draw, (chart_left - 20, int(y)), value_fmt.format(value), font=SMALL_FONT, fill=MUTED, anchor="ra")
    if not labels:
        return image
    bar_width = (chart_right - chart_left) / max(len(labels), 1)
    for idx, (label, value) in enumerate(zip(labels, values)):
        left = chart_left + idx * bar_width + bar_width * 0.15
        right = chart_left + (idx + 1) * bar_width - bar_width * 0.15
        top = chart_bottom - (chart_bottom - chart_top) * (value / max_value)
        draw.rounded_rectangle((left, top, right, chart_bottom), radius=14, fill=fill)
        text(draw, (int((left + right) / 2), int(top) - 14), value_fmt.format(value), font=SMALL_FONT, anchor="ms")
        label_text = wrap(label, 12)
        anchor = "ma"
        if rotate:
            label_image = Image.new("RGBA", (160, 220), (0, 0, 0, 0))
            label_draw = ImageDraw.Draw(label_image)
            label_draw.multiline_text((80, 10), wrap(label, 16), font=SMALL_FONT, fill=INK, anchor="ma", align="center", spacing=4)
            rotated = label_image.rotate(90, expand=True)
            image.paste(rotated, (int((left + right) / 2) - rotated.width // 2, chart_bottom + 10), rotated)
        else:
            text(draw, (int((left + right) / 2), chart_bottom + 16), label_text, font=SMALL_FONT, anchor=anchor)
    draw.multiline_text((MARGIN, HEIGHT - 120), wrap(note, 100), font=SMALL_FONT, fill=MUTED, spacing=6)
    return image


def line_chart(series: dict[str, list[float]], *, title: str, subtitle: str, note: str, colors: list[str], y_label: str) -> Image.Image:
    image, draw = new_canvas(title, subtitle)
    chart_left = MARGIN
    chart_top = 220
    chart_right = WIDTH - MARGIN
    chart_bottom = HEIGHT - 220
    draw.rectangle((chart_left, chart_top, chart_right, chart_bottom), outline=GRID, width=2)
    all_values = [value for values in series.values() for value in values]
    max_value = max(all_values) if all_values else 1.0
    min_value = min(all_values) if all_values else 0.0
    span = max(max_value - min_value, 1e-6)
    steps = 5
    for index in range(steps + 1):
        y = chart_bottom - (chart_bottom - chart_top) * index / steps
        draw.line((chart_left, y, chart_right, y), fill=GRID, width=2)
        value = min_value + span * index / steps
        text(draw, (chart_left - 18, int(y)), f"{value:.2f}", font=SMALL_FONT, fill=MUTED, anchor="ra")
    length = max(len(values) for values in series.values())
    for idx in range(length):
        x = chart_left + (chart_right - chart_left) * idx / max(length - 1, 1)
        draw.line((x, chart_top, x, chart_bottom), fill="#efe7d8", width=1)
        text(draw, (int(x), chart_bottom + 18), str(idx), font=SMALL_FONT, fill=MUTED, anchor="ma")
    for color, (label, values) in zip(colors, series.items()):
        points = []
        for idx, value in enumerate(values):
            x = chart_left + (chart_right - chart_left) * idx / max(len(values) - 1, 1)
            y = chart_bottom - (chart_bottom - chart_top) * ((value - min_value) / span)
            points.append((x, y))
        draw.line(points, fill=color, width=6, joint="curve")
        for x, y in points:
            draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=color, outline=BG, width=2)
    legend_left = chart_left
    legend_top = chart_bottom + 70
    for color, label in zip(colors, series.keys()):
        draw.rounded_rectangle((legend_left, legend_top, legend_left + 28, legend_top + 28), radius=6, fill=color)
        text(draw, (legend_left + 40, legend_top + 14), label, font=SMALL_FONT, anchor="lm")
        legend_left += 260
    text(draw, (chart_left - 78, chart_top - 24), y_label, font=SMALL_FONT, fill=MUTED)
    draw.multiline_text((MARGIN, HEIGHT - 100), wrap(note, 110), font=SMALL_FONT, fill=MUTED, spacing=6)
    return image


def matrix_chart(rows: list[str], cols: list[str], values: list[list[int]], *, title: str, subtitle: str, note: str, palette: list[str]) -> Image.Image:
    image, draw = new_canvas(title, subtitle)
    left = MARGIN + 240
    top = 240
    cell_w = 150
    cell_h = 72
    flat = [cell for row in values for cell in row]
    max_value = max(flat) if flat else 1
    for j, col in enumerate(cols):
        text(draw, (left + j * cell_w + cell_w // 2, top - 24), wrap(col, 10), font=SMALL_FONT, anchor="ms")
    for i, row in enumerate(rows):
        text(draw, (left - 18, top + i * cell_h + cell_h // 2), wrap(row, 18), font=SMALL_FONT, anchor="rm")
        for j, value in enumerate(values[i]):
            palette_idx = int(round((len(palette) - 1) * (value / max(max_value, 1))))
            color = palette[min(palette_idx, len(palette) - 1)]
            x0 = left + j * cell_w
            y0 = top + i * cell_h
            draw.rounded_rectangle((x0, y0, x0 + cell_w - 8, y0 + cell_h - 8), radius=10, fill=color, outline=GRID)
            label_fill = "#ffffff" if palette_idx >= len(palette) // 2 else INK
            text(draw, (x0 + (cell_w - 8) / 2, y0 + (cell_h - 8) / 2), str(value), font=BIG_NUMBER_FONT, fill=label_fill, anchor="mm")
    draw.multiline_text((MARGIN, HEIGHT - 150), wrap(note, 108), font=SMALL_FONT, fill=MUTED, spacing=6)
    return image


def table_chart(columns: list[str], rows: list[list[str]], *, title: str, subtitle: str, note: str) -> Image.Image:
    image, draw = new_canvas(title, subtitle)
    left = MARGIN
    top = 220
    col_widths = [180, 320, 430, 230, 300]
    row_height = 110
    header_h = 68
    x = left
    for width, col in zip(col_widths, columns):
        draw.rounded_rectangle((x, top, x + width, top + header_h), radius=8, fill="#ded3c3", outline=GRID)
        draw.multiline_text((x + width / 2, top + 16), wrap(col, 18), font=SMALL_FONT, fill=INK, anchor="ma", align="center", spacing=4)
        x += width + 8
    y = top + header_h + 16
    for index, row in enumerate(rows):
        x = left
        fill = "#fff9ef" if index % 2 == 0 else "#f1eadc"
        for width, cell in zip(col_widths, row):
            draw.rounded_rectangle((x, y, x + width, y + row_height), radius=8, fill=fill, outline=GRID)
            draw.multiline_text((x + 12, y + 12), wrap(cell, max(10, int(width / 13))), font=SMALL_FONT, fill=INK, spacing=4)
            x += width + 8
        y += row_height + 8
    draw.multiline_text((MARGIN, HEIGHT - 110), wrap(note, 108), font=SMALL_FONT, fill=MUTED, spacing=6)
    return image


def network_chart(graph_payload: dict[str, object], *, title: str, subtitle: str, note: str) -> Image.Image:
    image, draw = new_canvas(title, subtitle)
    memode = next(item for item in graph_payload["memode_audit"]["memodes"] if item["admissibility"]["passes"] and item["support_edges"])
    graph = nx.Graph()
    graph.add_node(memode["id"], kind="memode", label=memode["label"])
    for meme in memode["member_memes"]:
        graph.add_node(meme["id"], kind="meme", label=meme["label"])
        graph.add_edge(memode["id"], meme["id"], kind="membership")
    for edge in memode["support_edges"]:
        graph.add_edge(edge["source"], edge["target"], kind=edge["type"])
    positions = nx.spring_layout(graph, seed=42, k=0.8)
    plot_left, plot_top = 220, 220
    plot_right, plot_bottom = WIDTH - 220, HEIGHT - 220

    def scaled(node_id: str) -> tuple[int, int]:
        x, y = positions[node_id]
        plot_x = plot_left + int((x + 1.0) / 2.0 * (plot_right - plot_left))
        plot_y = plot_top + int((y + 1.0) / 2.0 * (plot_bottom - plot_top))
        return plot_x, plot_y

    for source, target, attrs in graph.edges(data=True):
        sx, sy = scaled(source)
        tx, ty = scaled(target)
        edge_color = OBS_2 if attrs["kind"] == "membership" else GOLD
        draw.line((sx, sy, tx, ty), fill=edge_color, width=4)
    for node_id, attrs in graph.nodes(data=True):
        x, y = scaled(node_id)
        if attrs["kind"] == "memode":
            radius = 52
            fill = SYN
            outline = "#ffffff"
        else:
            radius = 34
            fill = OBS
            outline = "#ffffff"
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill, outline=outline, width=5)
        label = wrap(str(attrs["label"]), 16)
        text(draw, (x, y + radius + 18), label, font=SMALL_FONT, anchor="ma")
    legend_x = MARGIN
    legend_y = HEIGHT - 170
    draw.rounded_rectangle((legend_x, legend_y, legend_x + 28, legend_y + 28), radius=6, fill=SYN)
    text(draw, (legend_x + 40, legend_y + 14), "Derived memode", font=SMALL_FONT, anchor="lm")
    draw.rounded_rectangle((legend_x + 260, legend_y, legend_x + 288, legend_y + 28), radius=6, fill=OBS)
    text(draw, (legend_x + 300, legend_y + 14), "Member meme", font=SMALL_FONT, anchor="lm")
    draw.line((legend_x + 540, legend_y + 14, legend_x + 580, legend_y + 14), fill=GOLD, width=4)
    text(draw, (legend_x + 592, legend_y + 14), "Qualifying support edge", font=SMALL_FONT, anchor="lm")
    draw.multiline_text((MARGIN, HEIGHT - 110), wrap(note, 108), font=SMALL_FONT, fill=MUTED, spacing=6)
    return image


def box_flow(title: str, subtitle: str, note: str, steps: list[tuple[str, str]], *, fill: str) -> Image.Image:
    image, draw = new_canvas(title, subtitle)
    box_w = 230
    box_h = 130
    gap = 40
    total_w = len(steps) * box_w + (len(steps) - 1) * gap
    start_x = (WIDTH - total_w) // 2
    y = 360
    for index, (heading, body) in enumerate(steps):
        x = start_x + index * (box_w + gap)
        draw.rounded_rectangle((x, y, x + box_w, y + box_h), radius=18, fill=fill, outline=GRID, width=3)
        text(draw, (x + box_w / 2, y + 22), heading, font=LABEL_FONT, anchor="ma")
        draw.multiline_text((x + 16, y + 46), wrap(body, 20), font=SMALL_FONT, fill=INK, spacing=4)
        if index < len(steps) - 1:
            ax = x + box_w
            bx = x + box_w + gap
            cy = y + box_h / 2
            draw.line((ax + 8, cy, bx - 8, cy), fill=MUTED, width=6)
            draw.polygon([(bx - 14, cy - 12), (bx, cy), (bx - 14, cy + 12)], fill=MUTED)
    draw.multiline_text((MARGIN, HEIGHT - 120), wrap(note, 108), font=SMALL_FONT, fill=MUTED, spacing=6)
    return image


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = value
    for key, replacement in replacements.items():
        escaped = escaped.replace(key, replacement)
    return escaped


def write_html(output_path: Path, title: str, image_name: str, payload: object) -> None:
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: Helvetica, Arial, sans-serif; margin: 32px; background: #f5f1e8; color: #1b1b1b; }}
    img {{ max-width: 100%; border: 1px solid #b8af9e; background: #fff; }}
    pre {{ background: #fff9ef; border: 1px solid #d9d0c0; padding: 16px; overflow: auto; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <img src="../static/{image_name}" alt="{title}">
  <h2>Underlying data</h2>
  <pre>{json.dumps(payload, indent=2)}</pre>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")


def register_figure(
    registry: list[dict[str, object]],
    *,
    figure_id: str,
    title: str,
    provenance: str,
    caption: str,
    inputs: list[Path],
    dataset_path: Path,
    static_path: Path,
    interactive_path: Path | None,
    section: str,
    order: int,
    generator_seed: int | None,
    provenance_locator: str,
) -> None:
    registry.append(
        {
            "figure_id": figure_id,
            "title": title,
            "provenance": provenance,
            "inputs": [str(path) for path in inputs],
            "outputs": {
                "data": str(dataset_path),
                "static": str(static_path),
                "interactive": str(interactive_path) if interactive_path else "",
            },
            "caption_tex": latex_escape(caption),
            "latex": "",
            "build": {
                "generator": str(GENERATOR_PATH),
                "seed": generator_seed,
                "input_hashes": {str(path): sha256_file(path) for path in inputs if path.exists()},
            },
            "provenance_locator": provenance_locator,
            "reproduction_notes": f"Run `./.venv/bin/python {GENERATOR_PATH.relative_to(REPO_ROOT)}` from the repo root.",
            "export_status": "ok",
            "failure_reason": "",
            "paper": {
                "include": True,
                "section": section,
                "order": order,
            },
        }
    )


def figure_latex(entry: dict[str, object]) -> str:
    figure_id = entry["figure_id"]
    static_rel = Path(entry["outputs"]["static"]).relative_to(RUN_ROOT)
    caption = entry["caption_tex"]
    label_id = figure_id.replace("_", "-")
    return (
        "\\begin{figure*}[t]\n"
        "\\centering\n"
        f"\\includegraphics[width=0.92\\textwidth]{{../{latex_escape(str(static_rel))}}}\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{fig:{label_id}}}\n"
        "\\end{figure*}\n"
    )


def main() -> None:
    runtime_rows = [json.loads(line) for line in RUNTIME_LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    runtime_event_counts = Counter(row["event"] for row in runtime_rows)
    runtime_event_counts = dict(sorted(runtime_event_counts.items(), key=lambda item: item[1], reverse=True))

    measurement_payload = json.loads(MEASUREMENT_PATH.read_text(encoding="utf-8"))
    graph_payload = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    geometry_payload = json.loads(GEOMETRY_PATH.read_text(encoding="utf-8"))
    observatory_payload = json.loads(OBSERVATORY_INDEX_PATH.read_text(encoding="utf-8"))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    key_tables = [
        "experiments",
        "sessions",
        "turns",
        "documents",
        "document_chunks",
        "memes",
        "memodes",
        "edges",
        "feedback_events",
        "measurement_events",
        "membrane_events",
        "trace_events",
        "export_artifacts",
    ]
    db_counts = {}
    for table in key_tables:
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        db_counts[table] = cur.fetchone()[0]
    conn.close()

    drift_sources = {
        "baseline_v14": BASELINE_TEXT_PATH.read_text(encoding="utf-8"),
        "readme": README_PATH.read_text(encoding="utf-8"),
        "project_charter": CHARTER_PATH.read_text(encoding="utf-8"),
        "intelligence_brief": BRIEF_PATH.read_text(encoding="utf-8"),
        "prewriting_memo": MEMO_PATH.read_text(encoding="utf-8"),
    }
    drift_terms = ["adam", "eden", "governor", "recursive", "rlm", "memode", "adam_auto", "observatory"]
    drift_matrix = []
    for source_text in drift_sources.values():
        lowered = source_text.lower()
        drift_matrix.append([lowered.count(term) for term in drift_terms])

    episodes = [
        {
            "episode_id": "E1",
            "status": "DONE",
            "hypothesis": "The direct v1 loop persists turn state, applies edit feedback, and emits the full export family.",
            "manipulation": "Bootstrap blank graph, run one chat turn, apply edit feedback, then export the experiment.",
            "observable": "Turn count increments, membrane strips scaffold headings, feedback enters retrieval, observatory exports materialize.",
            "outcome": "Observed in the current test pass: `tests/test_runtime_e2e.py::test_single_graph_bootstrap_chat_feedback_and_exports`.",
        },
        {
            "episode_id": "E2",
            "status": "DONE",
            "hypothesis": "Preview/commit/revert persists attributable measurement events and graph rollback.",
            "manipulation": "Seed a session, preview an edge-add action, commit it, then revert the committed event.",
            "observable": "Measurement ledger delta, committed edge present after commit and absent after revert.",
            "outcome": "Observed in the current test pass: `tests/test_observatory_measurements.py::test_edge_measurement_commit_and_revert_persist`.",
        },
        {
            "episode_id": "E3",
            "status": "DONE",
            "hypothesis": "Hum refresh remains a bounded continuity artifact and stays out of prompt injection.",
            "manipulation": "Run a chat turn, apply edit feedback, then inspect hum payload and next-turn preview prompt.",
            "observable": "Hum feedback counts rise; `current_hum.md` and `current_hum.json` are absent from prompt assembly.",
            "outcome": "Observed in the current test pass: `tests/test_hum_runtime.py::test_feedback_refreshes_hum_without_prompt_injection`.",
        },
    ]

    run_summary = {
        "inputs": {
            "runtime_log": str(RUNTIME_LOG_PATH),
            "measurement_events": str(MEASUREMENT_PATH),
            "graph_knowledge_base": str(GRAPH_PATH),
            "geometry_diagnostics": str(GEOMETRY_PATH),
            "observatory_index": str(OBSERVATORY_INDEX_PATH),
            "conversation_transcript": str(TRANSCRIPT_PATH),
            "brief": str(BRIEF_PATH),
            "memo": str(MEMO_PATH),
            "baseline_text": str(BASELINE_TEXT_PATH),
        },
        "runtime_event_counts": runtime_event_counts,
        "db_counts": db_counts,
        "graph_counts": graph_payload["counts"],
        "memode_audit_summary": graph_payload["memode_audit"]["summary"],
        "geometry_metrics": geometry_payload["full_graph"]["metrics"]["metrics"],
        "measurement_counts": measurement_payload["counts"],
        "observatory_index_counts": observatory_payload["summary"],
        "episodes": episodes,
    }
    save_json(RUN_DATA_DIR / "observed_repo_summary.json", run_summary)

    registry: list[dict[str, object]] = []

    observed_event_labels = list(runtime_event_counts.keys())[:10]
    observed_event_values = [runtime_event_counts[label] for label in observed_event_labels]
    dataset = [{"event": label, "count": value} for label, value in zip(observed_event_labels, observed_event_values)]
    dataset_path = FIGURE_DATA_DIR / "observed_runtime_event_counts.json"
    save_json(dataset_path, dataset)
    image = bar_chart(
        observed_event_labels,
        observed_event_values,
        title="Observed Runtime Event Counts",
        subtitle="Counts aggregated from logs/runtime.jsonl across the current repo evidence surface.",
        fill=OBS,
        note="Dominant events are export and generation surfaces, not hidden governance layers. The count distribution underwrites the paper's claim that Adam's operational evidence is trace-heavy and export-heavy.",
        rotate=True,
    )
    static_path = STATIC_DIR / "observed_runtime_event_counts.png"
    image.save(static_path)
    interactive_path = INTERACTIVE_DIR / "observed_runtime_event_counts.html"
    write_html(interactive_path, "Observed Runtime Event Counts", static_path.name, dataset)
    register_figure(
        registry,
        figure_id="observed_runtime_event_counts",
        title="Observed runtime event counts",
        provenance="OBSERVED",
        caption="[OBSERVED] Runtime event counts aggregated from `logs/runtime.jsonl`. Export, generation, and hum-refresh events dominate the current trace surface.",
        inputs=[RUNTIME_LOG_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=interactive_path,
        section="operational_evidence",
        order=1,
        generator_seed=None,
        provenance_locator="logs/runtime.jsonl:L1-L1366",
    )

    db_rows = [{"table": table, "count": count} for table, count in db_counts.items()]
    dataset_path = FIGURE_DATA_DIR / "observed_store_counts.csv"
    save_csv(dataset_path, db_rows)
    image = bar_chart(
        list(db_counts.keys()),
        list(db_counts.values()),
        title="Observed Persistent Store Cardinalities",
        subtitle="Selected table counts from data/eden.db at whitepaper build time.",
        fill=OBS_2,
        note="The persistent substrate is graph-shaped and external to model weights. Memes and edges dominate, while measurement events remain deliberately sparse and attributable.",
        rotate=True,
    )
    static_path = STATIC_DIR / "observed_store_counts.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="observed_store_counts",
        title="Observed persistent store cardinalities",
        provenance="OBSERVED",
        caption="[OBSERVED] Selected SQLite table counts from `data/eden.db` at run time. The persistence substrate is graph state rather than model-weight adaptation.",
        inputs=[DB_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="operational_evidence",
        order=2,
        generator_seed=None,
        provenance_locator="data/eden.db (SQLite counts query over experiments, sessions, turns, memes, memodes, edges, feedback_events, measurement_events, membrane_events, trace_events, export_artifacts)",
    )

    measurement_rows = [
        {
            "index": index,
            "event_id": event["id"],
            "action_type": event["action_type"],
            "evidence_label": event["evidence_label"],
            "created_at": event["created_at"],
            "reverted_from_event_id": event.get("reverted_from_event_id"),
        }
        for index, event in enumerate(measurement_payload["events"], start=1)
    ]
    dataset_path = FIGURE_DATA_DIR / "observed_measurement_ledger.csv"
    save_csv(dataset_path, measurement_rows)
    table_rows = [
        [
            row["event_id"][:8],
            row["action_type"],
            row["evidence_label"],
            row["created_at"].replace("T", " ").replace("+00:00", "Z"),
            (row["reverted_from_event_id"] or "none")[:8],
        ]
        for row in measurement_rows
    ]
    image = table_chart(
        ["Event", "Action", "Evidence", "Created At", "Reverted From"],
        table_rows,
        title="Observed Measurement Ledger Events",
        subtitle="Concrete preview/commit/revert persistence exported from the live observatory run.",
        note="The ledger records attributable graph mutation. Reversion is itself stored as a new event instead of silently rolling history backward.",
    )
    static_path = STATIC_DIR / "observed_measurement_ledger.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="observed_measurement_ledger",
        title="Observed measurement ledger events",
        provenance="OBSERVED",
        caption="[OBSERVED] The exported measurement ledger for experiment `b178bed2-...` shows explicit `edge_add` and `revert` events with operator and evidence metadata.",
        inputs=[MEASUREMENT_PATH, RUNTIME_LOG_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="observatory_contract",
        order=1,
        generator_seed=None,
        provenance_locator="exports/b178bed2-731e-4f8b-b5f8-a93d1300b2f7/measurement_events.json; logs/runtime.jsonl:L109-L114",
    )

    geometry_metrics = geometry_payload["full_graph"]["metrics"]["metrics"]
    dataset = [{"metric": name, **payload} for name, payload in geometry_metrics.items()]
    dataset_path = FIGURE_DATA_DIR / "observed_geometry_metrics.json"
    save_json(dataset_path, dataset)
    image = bar_chart(
        list(geometry_metrics.keys()),
        [payload["score"] for payload in geometry_metrics.values()],
        title="Observed Geometry Metrics and Labels",
        subtitle="Full-graph geometry diagnostics exported for the `bb298723-...` experiment.",
        fill=PURPLE,
        note="The geometry layer explicitly separates OBSERVED from DERIVED metrics. The paper can talk about these diagnostics as instrumentation, not as ontological proof of persona structure.",
        rotate=True,
        value_fmt="{:.2f}",
    )
    overlay = ImageDraw.Draw(image)
    for idx, payload in enumerate(geometry_metrics.values()):
        label_x = MARGIN + idx * ((WIDTH - 2 * MARGIN) / len(geometry_metrics)) + 64
        label_y = HEIGHT - 176
        overlay.rounded_rectangle((label_x - 40, label_y - 16, label_x + 40, label_y + 16), radius=8, fill=OBS_4 if payload["label"] == "OBSERVED" else "#efe3f7", outline=GRID)
        text(overlay, (label_x, label_y), payload["label"], font=SMALL_FONT, anchor="mm")
    static_path = STATIC_DIR / "observed_geometry_metrics.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="observed_geometry_metrics",
        title="Observed geometry metrics and labels",
        provenance="OBSERVED",
        caption="[OBSERVED] Geometry diagnostics exported from `geometry_diagnostics.json`. The current build labels circularity, radiality, linearity, community structure, and triadic closure as observed, while symmetry proxies remain derived.",
        inputs=[GEOMETRY_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="observatory_contract",
        order=2,
        generator_seed=None,
        provenance_locator="exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/geometry_diagnostics.json (full_graph.metrics.metrics)",
    )

    memode_summary = graph_payload["memode_audit"]["summary"]
    memode_rows = [{"metric": key, "count": value} for key, value in memode_summary.items()]
    dataset_path = FIGURE_DATA_DIR / "observed_memode_audit_summary.csv"
    save_csv(dataset_path, memode_rows)
    image = bar_chart(
        list(memode_summary.keys()),
        [float(value) for value in memode_summary.values()],
        title="Observed Memode Audit Summary",
        subtitle="Audit counts from `graph_knowledge_base.json` for the `bb298723-...` export family.",
        fill=GREEN,
        note="The audit surface distinguishes admissible memodes from informational relations and unmaterialized support candidates. This is the strongest current evidence that memodes are derived second-order structures with an admissibility floor.",
        rotate=True,
    )
    static_path = STATIC_DIR / "observed_memode_audit_summary.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="observed_memode_audit_summary",
        title="Observed memode audit summary",
        provenance="OBSERVED",
        caption="[OBSERVED] Memode audit summary exported with `graph_knowledge_base.json`: 200 audited memodes, 199 admissible, one flagged, and 1,189 materialized support edges.",
        inputs=[GRAPH_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="memetic_objects",
        order=1,
        generator_seed=None,
        provenance_locator="exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/graph_knowledge_base.json (memode_audit.summary)",
    )

    dataset_path = FIGURE_DATA_DIR / "observed_archaeology_term_drift.json"
    save_json(
        dataset_path,
        {
            "sources": list(drift_sources.keys()),
            "terms": drift_terms,
            "matrix": drift_matrix,
        },
    )
    image = matrix_chart(
        list(drift_sources.keys()),
        drift_terms,
        drift_matrix,
        title="Observed Claim Drift Across Baseline and Current Surfaces",
        subtitle="Term counts across the baseline draft, current README/docs, and the Step 1/2 pipeline artifacts.",
        note="High governor and recursive language concentration in the baseline draft, coupled with its near absence in current repo-truth surfaces, is the central drift signal driving the whitepaper rewrite.",
        palette=[OBS_4, "#c5d9ed", "#8fb4d7", OBS_2, "#153d63"],
    )
    static_path = STATIC_DIR / "observed_archaeology_term_drift.png"
    image.save(static_path)
    interactive_path = INTERACTIVE_DIR / "observed_archaeology_term_drift.html"
    write_html(interactive_path, "Observed Claim Drift Across Baseline and Current Surfaces", static_path.name, json.loads(dataset_path.read_text(encoding="utf-8")))
    register_figure(
        registry,
        figure_id="observed_archaeology_term_drift",
        title="Observed claim drift across baseline and current surfaces",
        provenance="OBSERVED",
        caption="[OBSERVED] Term-frequency drift across the baseline draft, current README/project charter, and the Step 1/2 pipeline artifacts. Governor and recursive language concentrate in the baseline rather than in current implementation-truth surfaces.",
        inputs=[BASELINE_TEXT_PATH, README_PATH, CHARTER_PATH, BRIEF_PATH, MEMO_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=interactive_path,
        section="archaeology",
        order=1,
        generator_seed=None,
        provenance_locator=f"tmp/source_inventory/eden_whitepaper_v14.txt; README.md; docs/PROJECT_CHARTER.md; {BRIEF_PATH.relative_to(REPO_ROOT)}; {MEMO_PATH.relative_to(REPO_ROOT)}",
    )

    dataset_path = FIGURE_DATA_DIR / "observed_memode_support_graph.json"
    support_memode = next(item for item in graph_payload["memode_audit"]["memodes"] if item["admissibility"]["passes"] and item["support_edges"])
    save_json(dataset_path, support_memode)
    image = network_chart(
        graph_payload,
        title="Observed Memode Support Graph",
        subtitle="One audited memode rendered as a derived node with member memes and qualifying support edges.",
        note="The central node is not a free-floating label. It is drawn from the memode audit surface and tied to member memes plus materialized support edges, which is the operational boundary between a memode and a cluster label.",
    )
    static_path = STATIC_DIR / "observed_memode_support_graph.png"
    image.save(static_path)
    interactive_path = INTERACTIVE_DIR / "observed_memode_support_graph.html"
    write_html(interactive_path, "Observed Memode Support Graph", static_path.name, support_memode)
    register_figure(
        registry,
        figure_id="observed_memode_support_graph",
        title="Observed memode support graph",
        provenance="OBSERVED",
        caption="[OBSERVED] One audited memode from `graph_knowledge_base.json`, shown with member memes and qualifying support edges. The memode is derived and admissibility-gated, not a free-floating cluster label.",
        inputs=[GRAPH_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=interactive_path,
        section="memetic_objects",
        order=2,
        generator_seed=42,
        provenance_locator="exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/graph_knowledge_base.json (memode_audit.memodes[passes=true, support_edges>0])",
    )

    dataset_path = FIGURE_DATA_DIR / "observed_done_episodes.json"
    save_json(dataset_path, episodes)
    table_rows = [
        [episode["episode_id"], episode["status"], episode["hypothesis"], episode["observable"], episode["outcome"]]
        for episode in episodes
    ]
    image = table_chart(
        ["Episode", "Status", "Hypothesis", "Observable", "Outcome"],
        table_rows,
        title="Observed Completed Episodes",
        subtitle="Three bounded `DONE` episodes carried into the empirical section from current-turn execution proof.",
        note="These episodes are narrow: they prove current repo behavior under specific tests and traces. The paper should not generalize beyond those bounded surfaces.",
    )
    static_path = STATIC_DIR / "observed_done_episodes.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="observed_done_episodes",
        title="Observed completed episodes",
        provenance="OBSERVED",
        caption="[OBSERVED] Three bounded `DONE` episodes anchored to current-turn test execution: direct-loop e2e, observatory commit/revert persistence, and hum refresh without prompt injection.",
        inputs=[
            REPO_ROOT / "tests/test_runtime_e2e.py",
            REPO_ROOT / "tests/test_observatory_measurements.py",
            REPO_ROOT / "tests/test_hum_runtime.py",
        ],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="empirical_program",
        order=1,
        generator_seed=None,
        provenance_locator="tests/test_runtime_e2e.py:L11-L75; tests/test_observatory_measurements.py:L53-L167; tests/test_hum_runtime.py:L92-L121; pytest Step 3 run outputs",
    )

    synthetic_decay = {
        "accept": [1.0, 1.16, 1.28, 1.34, 1.42, 1.46, 1.52, 1.57],
        "edit": [1.0, 1.10, 1.15, 1.21, 1.26, 1.28, 1.31, 1.34],
        "reject": [1.0, 0.87, 0.78, 0.72, 0.69, 0.66, 0.63, 0.61],
    }
    dataset_path = FIGURE_DATA_DIR / "synthetic_regard_decay.json"
    save_json(dataset_path, {"seed": 11, "series": synthetic_decay})
    image = line_chart(
        synthetic_decay,
        title="Synthetic Regard Trajectories",
        subtitle="Deterministic synthetic curves for the measurement pipeline only. Seed = 11.",
        note="Synthetic data here validates plotting and explanatory grammar. It does not claim observed Adam performance. The curves simply illustrate how reinforcement and penalty could diverge under a bounded regard update schedule.",
        colors=[GREEN, OBS_2, RED],
        y_label="Relative regard",
    )
    static_path = STATIC_DIR / "synthetic_regard_decay.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="synthetic_regard_decay",
        title="Synthetic regard trajectories",
        provenance="SYNTHETIC",
        caption="[SYNTHETIC] Deterministic regard trajectories used only to validate the paper's metric and visualization pipeline. Seed = 11; no observed runtime performance is implied.",
        inputs=[GENERATOR_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="synthetic_appendix",
        order=1,
        generator_seed=11,
        provenance_locator=str(GENERATOR_PATH.relative_to(REPO_ROOT)),
    )

    budget_rows = [
        {"profile": "manual:balanced", "history": 0.35, "feedback": 0.18, "active_set": 0.27, "instructions": 0.20},
        {"profile": "runtime_auto:wide", "history": 0.31, "feedback": 0.15, "active_set": 0.36, "instructions": 0.18},
        {"profile": "runtime_auto:tight", "history": 0.25, "feedback": 0.14, "active_set": 0.39, "instructions": 0.22},
    ]
    dataset_path = FIGURE_DATA_DIR / "synthetic_active_set_budgets.json"
    save_json(dataset_path, {"seed": 17, "rows": budget_rows})
    image, draw = new_canvas(
        "Synthetic Prompt-Budget Partition",
        "Deterministic profile slices for active-set assembly. Seed = 17.",
    )
    left, top, right, bottom = MARGIN, 240, WIDTH - MARGIN, HEIGHT - 240
    bar_height = 90
    for idx, row in enumerate(budget_rows):
        y0 = top + idx * 170
        x0 = left
        total_width = right - left
        text(draw, (left, y0 - 34), row["profile"], font=LABEL_FONT)
        for key, color in [("history", OBS_3), ("feedback", SYN_2), ("active_set", OBS), ("instructions", GOLD)]:
            width = total_width * row[key]
            draw.rounded_rectangle((x0, y0, x0 + width, y0 + bar_height), radius=10, fill=color)
            if width > 140:
                text(draw, (x0 + width / 2, y0 + bar_height / 2), f"{key} {int(row[key] * 100)}%", font=SMALL_FONT, anchor="mm")
            x0 += width
    draw.multiline_text((MARGIN, HEIGHT - 120), wrap("Synthetic partitioning clarifies the bounded-assembly story used in the text. The bars are not telemetry; they are deterministic scaffolds for explaining how prompt budget could be apportioned across history, feedback, active-set recall, and fixed instruction surfaces.", 110), font=SMALL_FONT, fill=MUTED, spacing=6)
    static_path = STATIC_DIR / "synthetic_active_set_budgets.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="synthetic_active_set_budgets",
        title="Synthetic prompt-budget partition",
        provenance="SYNTHETIC",
        caption="[SYNTHETIC] Deterministic prompt-budget partitions that illustrate bounded active-set assembly without claiming live telemetry. Seed = 17.",
        inputs=[GENERATOR_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="synthetic_appendix",
        order=2,
        generator_seed=17,
        provenance_locator=str(GENERATOR_PATH.relative_to(REPO_ROOT)),
    )

    dataset_path = FIGURE_DATA_DIR / "synthetic_browser_contract_layers.json"
    browser_layers = {
        "seed": 23,
        "layers": [
            {"name": "Browser view state", "claim": "Local presets, layouts, sort state, and preview styling", "status": "non-evidentiary"},
            {"name": "Browser mutation chrome", "claim": "Preview / commit / revert controls", "status": "live-only"},
            {"name": "Server mutation contract", "claim": "Preview, commit, revert, trace, and invalidation endpoints", "status": "authoritative"},
            {"name": "Persistent ledger", "claim": "measurement_events, trace_events, membrane_events", "status": "evidence"},
        ]
    }
    save_json(dataset_path, browser_layers)
    image = box_flow(
        "Synthetic Browser Contract Layers",
        "Deterministic explanatory stack for browser-local state versus authoritative mutation. Seed = 23.",
        "The diagram is synthetic because it compresses multiple implementation surfaces into one explanatory ladder. It preserves the repo's authority boundary: browser-local view state is not a measurement event.",
        [
            ("View State", "Presets, layout snapshots, filters, and preview styling stay browser-local."),
            ("Mutation Chrome", "Preview/commit/revert controls can be visible yet disabled in static mode."),
            ("Live API", "Preview, commit, revert, trace, and SSE invalidation stay server-authoritative."),
            ("Ledger", "Committed measurement events and trace links persist in SQLite and exports."),
        ],
        fill="#f6e7d6",
    )
    static_path = STATIC_DIR / "synthetic_browser_contract_layers.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="synthetic_browser_contract_layers",
        title="Synthetic browser contract layers",
        provenance="SYNTHETIC",
        caption="[SYNTHETIC] An explanatory stack that separates browser-local view state from live mutation and persistent measurement evidence. Seed = 23.",
        inputs=[GENERATOR_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="synthetic_appendix",
        order=3,
        generator_seed=23,
        provenance_locator=str(GENERATOR_PATH.relative_to(REPO_ROOT)),
    )

    dataset_path = FIGURE_DATA_DIR / "synthetic_measurement_state_machine.json"
    measurement_states = {
        "seed": 31,
        "states": [
            ["Observe", "Choose an attributable action and preserve the baseline."],
            ["Preview", "Compute deltas and `preview_graph_patch` without mutation."],
            ["Commit", "Persist a measurement event and refresh graph/geometry surfaces."],
            ["Revert", "Persist a second event that undoes the prior committed change."],
        ],
    }
    save_json(dataset_path, measurement_states)
    image = box_flow(
        "Synthetic Measurement State Machine",
        "Deterministic flow for preview-separated mutation. Seed = 31.",
        "This synthetic state machine exists to keep the public prose honest about the intended causal order. It mirrors the current repo contract without pretending to be a screenshot of runtime state.",
        measurement_states["states"],
        fill="#f0e2ef",
    )
    static_path = STATIC_DIR / "synthetic_measurement_state_machine.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="synthetic_measurement_state_machine",
        title="Synthetic measurement state machine",
        provenance="SYNTHETIC",
        caption="[SYNTHETIC] Deterministic preview-separated mutation flow used to explain the measurement-event contract. Seed = 31.",
        inputs=[GENERATOR_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="synthetic_appendix",
        order=4,
        generator_seed=31,
        provenance_locator=str(GENERATOR_PATH.relative_to(REPO_ROOT)),
    )

    synthetic_memetic = {
        "fidelity": [0.60, 0.67, 0.73, 0.79, 0.81, 0.84],
        "fecundity": [0.28, 0.34, 0.41, 0.44, 0.48, 0.53],
        "longevity": [0.20, 0.30, 0.38, 0.47, 0.55, 0.64],
    }
    dataset_path = FIGURE_DATA_DIR / "synthetic_memetic_proxies.json"
    save_json(dataset_path, {"seed": 37, "series": synthetic_memetic})
    image = line_chart(
        synthetic_memetic,
        title="Synthetic Memetic Proxy Trajectories",
        subtitle="Deterministic proxy curves for fidelity, fecundity, and longevity. Seed = 37.",
        note="The current repo does not yet emit these proxies directly. This synthetic chart exists to show how future empirical work could keep memetic language tied to inspectable operational measures.",
        colors=[OBS, SYN, GREEN],
        y_label="Proxy score",
    )
    static_path = STATIC_DIR / "synthetic_memetic_proxies.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="synthetic_memetic_proxies",
        title="Synthetic memetic proxy trajectories",
        provenance="SYNTHETIC",
        caption="[SYNTHETIC] Deterministic memetic proxy curves used only to show how fidelity, fecundity, and longevity could be operationalized in later work. Seed = 37.",
        inputs=[GENERATOR_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="synthetic_appendix",
        order=5,
        generator_seed=37,
        provenance_locator=str(GENERATOR_PATH.relative_to(REPO_ROOT)),
    )

    geometry_pipeline = {
        "seed": 43,
        "steps": [
            ["Slice", "Choose full graph, active set, session, or verdict slice."],
            ["Measure", "Compute observed metrics plus clearly labeled derived proxies."],
            ["Interpret", "Keep projection aesthetics subordinate to evidence labels."],
            ["Export", "Persist geometry, graph, and measurement sidecars for audit."],
        ],
    }
    dataset_path = FIGURE_DATA_DIR / "synthetic_geometry_pipeline.json"
    save_json(dataset_path, geometry_pipeline)
    image = box_flow(
        "Synthetic Geometry Evidence Pipeline",
        "Deterministic explanatory flow for geometry instrumentation. Seed = 43.",
        "The geometry story in the whitepaper should stay bounded by this evidence policy: slice first, measure second, interpret cautiously, and export with labels.",
        geometry_pipeline["steps"],
        fill="#e5eedf",
    )
    static_path = STATIC_DIR / "synthetic_geometry_pipeline.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="synthetic_geometry_pipeline",
        title="Synthetic geometry evidence pipeline",
        provenance="SYNTHETIC",
        caption="[SYNTHETIC] Deterministic geometry-instrumentation flow used to keep the paper's explanation aligned with the repo's evidence policy. Seed = 43.",
        inputs=[GENERATOR_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="synthetic_appendix",
        order=6,
        generator_seed=43,
        provenance_locator=str(GENERATOR_PATH.relative_to(REPO_ROOT)),
    )

    runtime_architecture = {
        "seed": 53,
        "steps": [
            ["Operator Input", "Brian writes to the TUI, not to a hidden planner."],
            ["Retrieve / Assemble", "The runtime builds a bounded active set and prompt context."],
            ["Respond / Membrane", "MLX generation yields a response, then the membrane sanitizes and records visible events."],
            ["Feedback / Graph Update", "Explicit verdicts and edits alter later retrieval pressure and persistence."],
        ],
    }
    dataset_path = FIGURE_DATA_DIR / "synthetic_runtime_spine.json"
    save_json(dataset_path, runtime_architecture)
    image = box_flow(
        "Synthetic Adam v1 Runtime Spine",
        "Deterministic controlled-English rendering of the direct v1 loop. Seed = 53.",
        "This figure is synthetic because it is a compact explanatory projection of code and docs rather than a screenshot. It is included to keep the whitepaper's causal story aligned with the repo's direct loop and to exclude obsolete governor language.",
        runtime_architecture["steps"],
        fill="#e7edf6",
    )
    static_path = STATIC_DIR / "synthetic_runtime_spine.png"
    image.save(static_path)
    register_figure(
        registry,
        figure_id="synthetic_runtime_spine",
        title="Synthetic Adam v1 runtime spine",
        provenance="SYNTHETIC",
        caption="[SYNTHETIC] Deterministic controlled-English rendering of the direct Adam v1 loop. Seed = 53.",
        inputs=[GENERATOR_PATH],
        dataset_path=dataset_path,
        static_path=static_path,
        interactive_path=None,
        section="synthetic_appendix",
        order=7,
        generator_seed=53,
        provenance_locator=str(GENERATOR_PATH.relative_to(REPO_ROOT)),
    )

    registry_sorted = sorted(registry, key=lambda entry: (entry["paper"]["section"], entry["paper"]["order"], entry["figure_id"]))
    for entry in registry_sorted:
        entry["latex"] = figure_latex(entry)
    save_json(REGISTRY_DIR / "FIGURE_REGISTRY.json", registry_sorted)
    (LATEX_DIR / "figures_generated.tex").write_text(
        "% Auto-generated figure include surface.\n\n" + "\n".join(entry["latex"] for entry in registry_sorted if entry["paper"]["include"]),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
