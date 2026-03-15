from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .utils import now_utc, safe_excerpt


HUM_ARTIFACT_VERSION = "hum.v1"
HUM_DERIVED_FROM = ["turns.active_set_json", "feedback_events", "membrane_events"]
HUM_LIMITS = {
    "artifact_version": HUM_ARTIFACT_VERSION,
    "turn_window": 3,
    "max_text_chars": 320,
    "max_lines": 6,
    "max_recurring_items": 4,
    "max_table_rows": 6,
    "max_feedback_events": 4,
    "max_membrane_events": 6,
    "max_line_tokens": 12,
}
_FEEDBACK_ORDER = ("accept", "edit", "reject", "skip")
_HUM_STOPWORDS = {
    "about",
    "after",
    "again",
    "agent",
    "answer",
    "automatic",
    "automatically",
    "because",
    "been",
    "before",
    "being",
    "between",
    "bound",
    "bounded",
    "brian",
    "chat",
    "clear",
    "conversation",
    "current",
    "detail",
    "details",
    "dialogue",
    "explicit",
    "focus",
    "from",
    "graph",
    "here",
    "into",
    "latest",
    "operator",
    "passed",
    "pending",
    "persisted",
    "popup",
    "present",
    "reply",
    "review",
    "session",
    "state",
    "stored",
    "surface",
    "text",
    "that",
    "there",
    "through",
    "turn",
    "unchanged",
    "with",
}
_TOKEN_RE = re.compile(r"[a-zA-Z']+")


@dataclass(slots=True)
class HumRecurringItem:
    node_id: str
    node_kind: str
    label: str
    count: int
    turn_indices: list[int]


@dataclass(slots=True)
class HumOverlap:
    latest_turn_id: str | None
    previous_turn_id: str | None
    count: int
    labels: list[str]


@dataclass(slots=True)
class HumFeedbackSummary:
    counts: dict[str, int]
    recent: list[dict[str, Any]]


@dataclass(slots=True)
class HumMembraneSummary:
    counts: dict[str, int]
    recent: list[dict[str, Any]]


@dataclass(slots=True)
class HumStatus:
    cross_turn_recurrence_present: bool
    feedback_present: bool
    membrane_activity_present: bool


@dataclass(slots=True)
class HumMetrics:
    char_count: int
    line_count: int
    turn_window_size: int
    recurring_item_count: int
    feedback_event_count: int
    membrane_event_count: int


@dataclass(slots=True)
class HumSurfaceStats:
    entries: int
    lines_total: int
    words: int
    unique_tokens: int
    repeated_tokens: int
    hapax_tokens: int
    type_token_ratio: float
    avg_token_len: float
    avg_line_words: float
    chars_total: int
    top10_coverage_pct: float


@dataclass(slots=True)
class HumTokenRow:
    token: str
    count: int
    pct_of_all_tokens: float


@dataclass(slots=True)
class HumPayload:
    artifact_version: str
    generated_at: str
    experiment_id: str
    session_id: str
    latest_turn_id: str | None
    turn_ids: list[str]
    turn_indices: list[int]
    derived_from: list[str]
    boundedness: dict[str, Any]
    status: HumStatus
    continuity: dict[str, Any]
    metrics: HumMetrics
    text_surface: str
    surface_lines: list[str]
    surface_stats: HumSurfaceStats
    token_table: list[HumTokenRow]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = asdict(self.status)
        payload["metrics"] = asdict(self.metrics)
        payload["surface_stats"] = asdict(self.surface_stats)
        payload["token_table"] = [asdict(row) for row in self.token_table]
        return payload


class HumService:
    def __init__(self, *, store, runtime_log, root: Path) -> None:
        self.store = store
        self.runtime_log = runtime_log
        self.root = root

    def refresh(self, *, session_id: str) -> dict[str, Any]:
        payload, markdown_path, json_path = self._build_artifact(session_id)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload.to_dict(), indent=2), encoding="utf-8")
        markdown_path.write_text(self._render_markdown(payload, markdown_path=markdown_path, json_path=json_path), encoding="utf-8")
        metadata = {
            "artifact_version": payload.artifact_version,
            "generated_at": payload.generated_at,
            "latest_turn_id": payload.latest_turn_id,
            "turn_window_size": payload.metrics.turn_window_size,
            "cross_turn_recurrence_present": payload.status.cross_turn_recurrence_present,
        }
        self.store.record_export_artifact(
            experiment_id=payload.experiment_id,
            session_id=payload.session_id,
            artifact_type="hum_markdown",
            path=markdown_path,
            metadata=metadata,
        )
        self.store.record_export_artifact(
            experiment_id=payload.experiment_id,
            session_id=payload.session_id,
            artifact_type="hum_json",
            path=json_path,
            metadata=metadata,
        )
        self.runtime_log.emit(
            "INFO",
            "hum_refreshed",
            "Refreshed bounded hum artifact.",
            experiment_id=payload.experiment_id,
            session_id=payload.session_id,
            latest_turn_id=payload.latest_turn_id,
            recurring_item_count=payload.metrics.recurring_item_count,
            feedback_event_count=payload.metrics.feedback_event_count,
            membrane_event_count=payload.metrics.membrane_event_count,
        )
        return self.snapshot(session_id)

    def snapshot(self, session_id: str) -> dict[str, Any]:
        markdown_path, json_path = self._artifact_paths(session_id)
        base = {
            "present": False,
            "artifact_version": HUM_ARTIFACT_VERSION,
            "generated_at": None,
            "markdown_path": str(markdown_path),
            "json_path": str(json_path),
            "latest_turn_id": None,
            "turn_window_size": 0,
            "cross_turn_recurrence_present": False,
            "text_surface": "",
            "surface_lines": [],
            "surface_stats": {},
            "token_table": [],
        }
        if not json_path.exists() or not markdown_path.exists():
            return base
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {**base, "error": "invalid_hum_json"}
        metrics = payload.get("metrics", {})
        status = payload.get("status", {})
        return {
            **base,
            "present": True,
            "artifact_version": payload.get("artifact_version", HUM_ARTIFACT_VERSION),
            "generated_at": payload.get("generated_at"),
            "latest_turn_id": payload.get("latest_turn_id"),
            "turn_window_size": int(metrics.get("turn_window_size", 0) or 0),
            "cross_turn_recurrence_present": bool(status.get("cross_turn_recurrence_present")),
            "text_surface": str(payload.get("text_surface") or ""),
            "surface_lines": list(payload.get("surface_lines") or []),
            "surface_stats": dict(payload.get("surface_stats") or {}),
            "token_table": list(payload.get("token_table") or []),
        }

    def _artifact_paths(self, session_id: str) -> tuple[Path, Path]:
        session = self.store.get_session(session_id)
        experiment_id = str(session["experiment_id"])
        base_dir = self.root / experiment_id / session_id
        return base_dir / "current_hum.md", base_dir / "current_hum.json"

    def _build_artifact(self, session_id: str) -> tuple[HumPayload, Path, Path]:
        session = self.store.get_session(session_id)
        experiment = self.store.get_experiment(session["experiment_id"])
        markdown_path, json_path = self._artifact_paths(session_id)
        turns = self.store.list_all_turns(session_id)[-HUM_LIMITS["turn_window"] :]
        feedback_events = self.store.recent_feedback(session_id, limit=HUM_LIMITS["max_feedback_events"])
        membrane_events = self.store.list_membrane_events(
            experiment["id"],
            limit=HUM_LIMITS["max_membrane_events"],
            session_id=session_id,
        )
        recurring_items, overlap = self._summarize_active_set_recurrence(turns)
        feedback_summary = self._summarize_feedback(feedback_events)
        membrane_summary = self._summarize_membrane(membrane_events)
        surface_lines, motif_tokens = self._render_surface_lines(
            turns=turns,
            recurring_items=recurring_items,
            overlap=overlap,
            feedback_summary=feedback_summary,
            membrane_summary=membrane_summary,
        )
        text_surface = "\n".join(surface_lines)
        surface_stats = self._surface_stats(surface_lines, motif_tokens)
        token_table = self._surface_token_table(motif_tokens)
        payload = HumPayload(
            artifact_version=HUM_ARTIFACT_VERSION,
            generated_at=now_utc(),
            experiment_id=str(experiment["id"]),
            session_id=str(session["id"]),
            latest_turn_id=str(turns[-1]["id"]) if turns else None,
            turn_ids=[str(turn["id"]) for turn in turns],
            turn_indices=[int(turn.get("turn_index", 0) or 0) for turn in turns],
            derived_from=list(HUM_DERIVED_FROM),
            boundedness=dict(HUM_LIMITS),
            status=HumStatus(
                cross_turn_recurrence_present=bool(recurring_items),
                feedback_present=bool(feedback_events),
                membrane_activity_present=bool(membrane_events),
            ),
            continuity={
                "recurring_items": [asdict(item) for item in recurring_items],
                "active_set_overlap": asdict(overlap),
                "feedback_summary": asdict(feedback_summary),
                "membrane_summary": asdict(membrane_summary),
            },
            metrics=HumMetrics(
                char_count=len(text_surface),
                line_count=max(1, text_surface.count("\n") + 1) if text_surface else 0,
                turn_window_size=len(turns),
                recurring_item_count=len(recurring_items),
                feedback_event_count=len(feedback_events),
                membrane_event_count=len(membrane_events),
            ),
            text_surface=text_surface,
            surface_lines=surface_lines,
            surface_stats=surface_stats,
            token_table=token_table,
        )
        return payload, markdown_path, json_path

    def _summarize_active_set_recurrence(self, turns: list[dict[str, Any]]) -> tuple[list[HumRecurringItem], HumOverlap]:
        latest_labels: dict[str, tuple[str, str]] = {}
        appearances: dict[str, set[int]] = defaultdict(set)
        turn_node_labels: list[dict[str, str]] = []
        for turn in turns:
            items = json.loads(turn.get("active_set_json") or "[]")
            labels_for_turn: dict[str, str] = {}
            seen_ids: set[str] = set()
            turn_index = int(turn.get("turn_index", 0) or 0)
            for item in items:
                node_id = str(item.get("node_id") or "").strip()
                if not node_id or node_id in seen_ids:
                    continue
                seen_ids.add(node_id)
                label = safe_excerpt(str(item.get("label") or node_id), limit=72)
                node_kind = str(item.get("node_kind") or "unknown")
                latest_labels[node_id] = (label, node_kind)
                appearances[node_id].add(turn_index)
                labels_for_turn[node_id] = label
            turn_node_labels.append(labels_for_turn)

        recurring: list[HumRecurringItem] = []
        for node_id, turn_indices in appearances.items():
            if len(turn_indices) < 2:
                continue
            label, node_kind = latest_labels[node_id]
            recurring.append(
                HumRecurringItem(
                    node_id=node_id,
                    node_kind=node_kind,
                    label=label,
                    count=len(turn_indices),
                    turn_indices=sorted(turn_indices),
                )
            )
        recurring.sort(key=lambda item: (-item.count, -max(item.turn_indices), item.label.lower(), item.node_id))
        recurring = recurring[: HUM_LIMITS["max_recurring_items"]]

        latest_turn = turns[-1] if turns else None
        previous_turn = turns[-2] if len(turns) > 1 else None
        latest_ids = set(turn_node_labels[-1].keys()) if turn_node_labels else set()
        previous_ids = set(turn_node_labels[-2].keys()) if len(turn_node_labels) > 1 else set()
        overlap_ids = sorted(latest_ids & previous_ids)
        overlap_labels = [turn_node_labels[-1].get(node_id) or turn_node_labels[-2].get(node_id) or node_id for node_id in overlap_ids]
        overlap = HumOverlap(
            latest_turn_id=str(latest_turn["id"]) if latest_turn else None,
            previous_turn_id=str(previous_turn["id"]) if previous_turn else None,
            count=len(overlap_ids),
            labels=overlap_labels[: HUM_LIMITS["max_recurring_items"]],
        )
        return recurring, overlap

    def _summarize_feedback(self, feedback_events: list[dict[str, Any]]) -> HumFeedbackSummary:
        ordered_counts: dict[str, int] = {}
        verdict_counts = Counter(str(item.get("verdict") or "").lower() for item in feedback_events)
        for verdict in _FEEDBACK_ORDER:
            if verdict_counts.get(verdict):
                ordered_counts[verdict] = int(verdict_counts[verdict])
        recent = [
            {
                "turn_index": int(item.get("turn_index", 0) or 0),
                "verdict": str(item.get("verdict") or "").lower(),
                "explanation": safe_excerpt(str(item.get("explanation") or ""), limit=96),
            }
            for item in feedback_events[: HUM_LIMITS["max_feedback_events"]]
        ]
        return HumFeedbackSummary(counts=ordered_counts, recent=recent)

    def _summarize_membrane(self, membrane_events: list[dict[str, Any]]) -> HumMembraneSummary:
        event_counts = Counter(str(item.get("event_type") or "").upper() for item in membrane_events)
        counts = {event_type: int(event_counts[event_type]) for event_type in sorted(event_counts)}
        recent = [
            {
                "turn_id": str(item.get("turn_id") or ""),
                "event_type": str(item.get("event_type") or "").upper(),
                "detail": safe_excerpt(str(item.get("detail") or ""), limit=96),
            }
            for item in membrane_events[: HUM_LIMITS["max_membrane_events"]]
        ]
        return HumMembraneSummary(counts=counts, recent=recent)

    def _render_surface_lines(
        self,
        *,
        turns: list[dict[str, Any]],
        recurring_items: list[HumRecurringItem],
        overlap: HumOverlap,
        feedback_summary: HumFeedbackSummary,
        membrane_summary: HumMembraneSummary,
    ) -> tuple[list[str], list[str]]:
        lines: list[str] = []
        motif_tokens: list[str] = []
        feedback_tokens = self._summary_tokens_from_feedback(feedback_summary)
        membrane_tokens = self._summary_tokens_from_membrane(membrane_summary)

        for index, turn in enumerate(turns):
            line_tokens = self._turn_motif_tokens(turn)
            if index == len(turns) - 1:
                line_tokens.extend(token for token in feedback_tokens if token not in line_tokens)
                line_tokens.extend(token for token in membrane_tokens if token not in line_tokens)
                if recurring_items:
                    line_tokens.extend(
                        token
                        for item in recurring_items[:2]
                        for token in self._motif_tokens(item.label, max_tokens=1)
                        if token not in line_tokens
                    )
                elif overlap.labels:
                    line_tokens.extend(
                        token
                        for label in overlap.labels[:2]
                        for token in self._motif_tokens(label, max_tokens=1)
                        if token not in line_tokens
                    )
            line_tokens = line_tokens[: HUM_LIMITS["max_line_tokens"]]
            if not line_tokens:
                line_tokens = ["seed", "quiet"] if len(turns) <= 1 else ["carry", "quiet"]
            motif_tokens.extend(line_tokens)
            turn_index = int(turn.get("turn_index", 0) or 0)
            rendered = f"[T{turn_index}] hum: {self._format_hum_line(line_tokens)}"
            lines.append(safe_excerpt(rendered, limit=104))

        if not lines:
            lines = ["[T0] hum: seed quiet"]
            motif_tokens = ["seed", "quiet"]

        bounded_lines = lines[: HUM_LIMITS["max_lines"]]
        while bounded_lines and len("\n".join(bounded_lines)) > HUM_LIMITS["max_text_chars"]:
            bounded_lines.pop()
        if not bounded_lines:
            bounded_lines = [safe_excerpt(lines[0], limit=HUM_LIMITS["max_text_chars"])]
        return bounded_lines, motif_tokens

    def _turn_motif_tokens(self, turn: dict[str, Any]) -> list[str]:
        items = self._sorted_active_set_items(turn)
        tokens: list[str] = []
        for item in items:
            label = str(item.get("label") or item.get("node_id") or "").strip()
            if not label:
                continue
            for token in self._motif_tokens(label, max_tokens=2):
                if token not in tokens:
                    tokens.append(token)
                if len(tokens) >= HUM_LIMITS["max_line_tokens"] - 2:
                    return tokens
        return tokens

    def _sorted_active_set_items(self, turn: dict[str, Any]) -> list[dict[str, Any]]:
        items = json.loads(turn.get("active_set_json") or "[]")
        return sorted(
            items,
            key=lambda item: (
                float(item.get("selection", 0.0)),
                float(item.get("regard", 0.0)),
                float(item.get("activation", 0.0)),
            ),
            reverse=True,
        )

    def _summary_tokens_from_feedback(self, feedback_summary: HumFeedbackSummary) -> list[str]:
        tokens: list[str] = []
        for item in feedback_summary.recent[:2]:
            tokens.extend(self._motif_tokens(str(item.get("verdict") or ""), max_tokens=1))
            tokens.extend(self._motif_tokens(str(item.get("explanation") or ""), max_tokens=2))
        return tokens[:3]

    def _summary_tokens_from_membrane(self, membrane_summary: HumMembraneSummary) -> list[str]:
        tokens: list[str] = []
        for item in membrane_summary.recent[:2]:
            tokens.extend(self._motif_tokens(str(item.get("event_type") or ""), max_tokens=1))
            tokens.extend(self._motif_tokens(str(item.get("detail") or ""), max_tokens=2))
        return tokens[:3]

    def _motif_tokens(self, text: str, *, max_tokens: int) -> list[str]:
        tokens: list[str] = []
        for raw in _TOKEN_RE.findall((text or "").lower()):
            token = raw.strip("'")
            if token.endswith("'s"):
                token = token[:-2]
            token = re.sub(r"[^a-z]", "", token)
            if len(token) < 3 or token in _HUM_STOPWORDS:
                continue
            motif = self._compress_token(token)
            if len(motif) < 2:
                continue
            tokens.append(motif)
            if len(tokens) >= max_tokens:
                break
        return tokens

    def _compress_token(self, token: str) -> str:
        for suffix in ("ingly", "edly", "ment", "ness", "tion", "sion", "ance", "ence", "edly", "edly", "ing", "ers", "ies", "ied", "ed", "es", "ly", "al", "s"):
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                token = token[: -len(suffix)] + ("y" if suffix in {"ies", "ied"} else "")
                break
        if len(token) <= 4:
            return token
        interior = re.sub(r"[aeiou]", "", token[1:-1])
        compressed = token[0] + interior + token[-1]
        compressed = re.sub(r"(.)\1{2,}", r"\1\1", compressed)
        return compressed[:8]

    def _format_hum_line(self, tokens: list[str]) -> str:
        groups = [" ".join(tokens[index : index + 3]) for index in range(0, len(tokens), 3)]
        return " / ".join(group for group in groups if group)

    def _surface_stats(self, surface_lines: list[str], motif_tokens: list[str]) -> HumSurfaceStats:
        counts = Counter(motif_tokens)
        words = len(motif_tokens)
        unique_tokens = len(counts)
        repeated_tokens = sum(1 for count in counts.values() if count >= 2)
        hapax_tokens = sum(1 for count in counts.values() if count == 1)
        chars_total = len("\n".join(surface_lines))
        avg_token_len = round(sum(len(token) for token in motif_tokens) / words, 2) if words else 0.0
        avg_line_words = round(words / max(len(surface_lines), 1), 2) if surface_lines else 0.0
        top10_coverage_pct = round((sum(count for _, count in counts.most_common(10)) / words) * 100, 1) if words else 0.0
        return HumSurfaceStats(
            entries=len(surface_lines),
            lines_total=len(surface_lines),
            words=words,
            unique_tokens=unique_tokens,
            repeated_tokens=repeated_tokens,
            hapax_tokens=hapax_tokens,
            type_token_ratio=round(unique_tokens / words, 3) if words else 0.0,
            avg_token_len=avg_token_len,
            avg_line_words=avg_line_words,
            chars_total=chars_total,
            top10_coverage_pct=top10_coverage_pct,
        )

    def _surface_token_table(self, motif_tokens: list[str]) -> list[HumTokenRow]:
        counts = Counter(motif_tokens)
        total = max(len(motif_tokens), 1)
        return [
            HumTokenRow(
                token=token,
                count=count,
                pct_of_all_tokens=round(count / total, 3),
            )
            for token, count in counts.most_common(HUM_LIMITS["max_table_rows"])
        ]

    def _render_markdown(self, payload: HumPayload, *, markdown_path: Path, json_path: Path) -> str:
        token_rows = payload.token_table or [HumTokenRow(token="seed", count=1, pct_of_all_tokens=1.0)]
        lines = [
            "# Adam Hum",
            "",
            f"- artifact_version: {payload.artifact_version}",
            f"- generated_at: {payload.generated_at}",
            f"- experiment_id: {payload.experiment_id}",
            f"- session_id: {payload.session_id}",
            f"- derived_from: {', '.join(payload.derived_from)}",
            f"- markdown_path: {markdown_path}",
            f"- json_path: {json_path}",
            "",
            *payload.surface_lines,
            "",
            "[HUM_STATS]",
            (
                f"entries={payload.surface_stats.entries} lines_total={payload.surface_stats.lines_total} "
                f"words={payload.surface_stats.words} unique_tokens={payload.surface_stats.unique_tokens} "
                f"repeated_tokens={payload.surface_stats.repeated_tokens} hapax_tokens={payload.surface_stats.hapax_tokens} "
                f"type_token_ratio={payload.surface_stats.type_token_ratio:.3f} avg_token_len={payload.surface_stats.avg_token_len:.2f} "
                f"avg_line_words={payload.surface_stats.avg_line_words:.2f} chars_total={payload.surface_stats.chars_total}"
            ),
            "",
            "[HUM_METRICS]",
            (
                f"turn_window_size={payload.metrics.turn_window_size} recurring_item_count={payload.metrics.recurring_item_count} "
                f"feedback_event_count={payload.metrics.feedback_event_count} membrane_event_count={payload.metrics.membrane_event_count} "
                f"top10_coverage_pct={payload.surface_stats.top10_coverage_pct:.1f} latest_turn_id={payload.latest_turn_id or 'n/a'}"
            ),
            "",
            "[HUM_TABLE]",
            "| rank | token | count | pct_of_all_tokens |",
            "| --- | --- | --- | --- |",
            *[
                f"| {index} | {row.token} | {row.count} | {row.pct_of_all_tokens:.3f} |"
                for index, row in enumerate(token_rows[: HUM_LIMITS["max_table_rows"]], start=1)
            ],
            "[/HUM_TABLE]",
            "",
        ]
        return "\n".join(lines)
