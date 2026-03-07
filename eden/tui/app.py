from __future__ import annotations

import asyncio
import math
import webbrowser
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, RichLog, Select, Static, TextArea

from ..runtime import EdenRuntime
from ..utils import safe_excerpt


AMBER = "#ffbf66"
TEXT = "#ffe2af"
MUTED = "#b88646"
BG = "#090603"
PANEL = "#140d05"
SHADE = "#110b06"
SHADE_ALT = "#1a1108"
NEON = "#8df7a8"
ICE = "#a7d8ff"
ROSE = "#ff8fb5"
EMBER = "#ff8d47"

ACTION_MENU_OPTIONS = [
    ("Review Feedback", "review"),
    ("Adjust Profile", "profile"),
    ("New Session", "new_session"),
    ("Resume Latest", "resume"),
    ("Blank Eden", "blank"),
    ("Seeded Eden", "seeded"),
    ("Prepare Qwen", "prepare_mlx"),
    ("Open Observatory", "observatory"),
    ("Export Latest", "export"),
    ("Open Deck", "deck"),
    ("Help", "help"),
]


def _observatory_target_url(runtime: EdenRuntime, status: dict[str, Any], experiment_id: str | None) -> str:
    if not experiment_id:
        return status["url"]
    out_dir = runtime.export_dir_for_experiment(experiment_id)
    for name in ("observatory_index.html", "geometry_lab.html", "graph_knowledge_base.html"):
        if (out_dir / name).exists():
            return status["url"] + f"{experiment_id}/{name}"
    return status["url"]


@dataclass(slots=True)
class UiState:
    experiment_id: str | None = None
    experiment_name: str | None = None
    session_id: str | None = None
    session_title: str | None = None
    model_status: dict[str, Any] | None = None
    last_turn_id: str | None = None
    last_user_text: str = ""
    last_response: str = ""
    last_reasoning: str = ""
    last_active_set: list[dict[str, Any]] | None = None
    last_trace: list[dict[str, Any]] | None = None
    preview_active_set: list[dict[str, Any]] | None = None
    preview_trace: list[dict[str, Any]] | None = None
    last_feedback: str = "No feedback applied yet."
    observatory_status: dict[str, Any] | None = None
    current_budget: dict[str, Any] | None = None
    current_profile: dict[str, Any] | None = None


class HelpModal(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        help_text = Text.from_markup(
            "[bold #ffbf66]EDEN Controls[/]\n\n"
            "EDEN boots directly into a live session cockpit.\n"
            "The top action menu handles review, profile, launch, export, and observatory actions.\n"
            "The left bay is aperture, visible thinking, and feedback.\n"
            "The upper-right bay is the animated cockpit scope, dials, and trace bus.\n"
            "The lower-right deck is the Brian/Adam transcript and live composer.\n"
            "Open Deck for detailed budget, thinking, history, ingest, and launch utilities.\n"
            "Open Review for explicit accept / edit / reject feedback.\n\n"
            "[bold]F1[/] help overlay\n"
            "[bold]Ctrl+S[/] send current input\n"
            "[bold]F2[/] export graph, basin, and geometry artifacts\n"
            "[bold]F3[/] ensure observatory is running and open the current export surface\n"
            "[bold]F4[/] toggle low motion for the current session request\n"
            "[bold]F5[/] open the new-session inference-profile flow\n"
            "[bold]F6[/] open the operator deck\n"
            "[bold]F7[/] open review feedback\n"
            "[bold]Esc[/] close this overlay\n\n"
            "When the backend emits explicit reasoning, EDEN surfaces it as a visible model artifact.\n"
            "That thinking panel shows model-emitted text, not claimed hidden chain-of-thought.\n\n"
            "Inference modes:\n"
            "- MANUAL: operator-specified bounded parameters\n"
            "- RUNTIME_AUTO: deterministic transparent runtime policy\n"
            "- ADAM_AUTO: bounded preset choice; MLX currently falls back to runtime_auto and logs that fact\n\n"
            "Feedback rules:\n"
            "- Accept requires explanation\n"
            "- Reject requires explanation\n"
            "- Edit requires explanation and corrected response\n"
            "- Skip records a lightweight no-op verdict"
        )
        yield Static(Panel(help_text, title="Help", border_style=AMBER), id="help_panel")

    def on_key(self, event) -> None:
        if event.key in {"escape", "f1"}:
            self.dismiss(None)


class SessionConfigModal(ModalScreen[dict[str, Any] | None]):
    def __init__(
        self,
        defaults: dict[str, Any],
        *,
        title_text: str,
        action_label: str,
        show_title_input: bool = True,
    ) -> None:
        super().__init__()
        self.defaults = defaults
        self.title_text = title_text
        self.action_label = action_label
        self.show_title_input = show_title_input

    def compose(self) -> ComposeResult:
        summary = Text.from_markup(
            f"[bold {AMBER}]{self.title_text}[/]\n"
            "Choose the inference-profile mode for this session. EDEN will persist the request at session creation and surface the resolved circumstances on later turns."
        )
        yield Static(Panel(summary, title="Session Start", border_style=AMBER), id="session_config_header")
        with Horizontal(id="session_config_shell"):
            with Vertical(classes="session_config_column"):
                if self.show_title_input:
                    yield Input(value=self.defaults.get("title", "Operator Session"), id="session_title_input", placeholder="session title")
                yield Select(
                    [("MANUAL", "manual"), ("RUNTIME_AUTO", "runtime_auto"), ("ADAM_AUTO", "adam_auto")],
                    value=self.defaults.get("mode", "manual"),
                    allow_blank=False,
                    id="mode_select",
                    prompt="Inference mode",
                )
                yield Select(
                    [("Tight", "tight"), ("Balanced", "balanced"), ("Wide", "wide")],
                    value=self.defaults.get("budget_mode", "balanced"),
                    allow_blank=False,
                    id="budget_mode_select",
                    prompt="Budget mode",
                )
                yield Select(
                    [("Off", "false"), ("On", "true")],
                    value="true" if self.defaults.get("low_motion") else "false",
                    allow_blank=False,
                    id="low_motion_select",
                    prompt="Low motion",
                )
                yield Select(
                    [("Off", "false"), ("On", "true")],
                    value="true" if self.defaults.get("debug", True) else "false",
                    allow_blank=False,
                    id="debug_select",
                    prompt="Debug verbosity",
                )
                yield Static(id="session_config_summary")
            with Vertical(classes="session_config_column"):
                yield Input(value=str(self.defaults.get("temperature", 0.4)), id="temperature_input", placeholder="temperature")
                yield Input(value=str(self.defaults.get("max_output_tokens", 480)), id="max_tokens_input", placeholder="max output tokens")
                yield Input(value=str(self.defaults.get("top_p", 0.9)), id="top_p_input", placeholder="top_p")
                yield Input(value=str(self.defaults.get("repetition_penalty", 1.05)), id="repetition_penalty_input", placeholder="repetition penalty")
                yield Input(value=str(self.defaults.get("retrieval_depth", 12)), id="retrieval_depth_input", placeholder="retrieval depth")
                yield Input(value=str(self.defaults.get("max_context_items", 8)), id="max_context_items_input", placeholder="max context items")
                yield Input(value=str(self.defaults.get("response_char_cap", 1600)), id="response_char_cap_input", placeholder="response char cap")
                with Horizontal():
                    yield Button(self.action_label, id="session_confirm_btn", variant="primary")
                    yield Button("Cancel", id="session_cancel_btn")

    def on_mount(self) -> None:
        self._refresh_summary()

    @on(Button.Pressed, "#session_confirm_btn")
    def handle_confirm(self) -> None:
        self.dismiss(self._payload())

    @on(Button.Pressed, "#session_cancel_btn")
    def handle_cancel(self) -> None:
        self.dismiss(None)

    @on(Select.Changed)
    @on(Input.Changed)
    def handle_field_change(self, _event) -> None:
        self._refresh_summary()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def _payload(self) -> dict[str, Any]:
        return {
            "title": (
                self.query_one("#session_title_input", Input).value.strip()
                if self.show_title_input
                else self.defaults.get("title", "Operator Session")
            )
            or "Operator Session",
            "mode": str(self.query_one("#mode_select", Select).value),
            "budget_mode": str(self.query_one("#budget_mode_select", Select).value),
            "low_motion": str(self.query_one("#low_motion_select", Select).value) == "true",
            "debug": str(self.query_one("#debug_select", Select).value) == "true",
            "temperature": self._float_value("#temperature_input", 0.4),
            "max_output_tokens": self._int_value("#max_tokens_input", 480),
            "top_p": self._float_value("#top_p_input", 0.9),
            "repetition_penalty": self._float_value("#repetition_penalty_input", 1.05),
            "retrieval_depth": self._int_value("#retrieval_depth_input", 12),
            "max_context_items": self._int_value("#max_context_items_input", 8),
            "response_char_cap": self._int_value("#response_char_cap_input", 1600),
        }

    def _refresh_summary(self) -> None:
        payload = self._payload()
        mode = payload["mode"]
        if mode == "manual":
            mode_summary = "Operator-specified values will be clamped and used directly."
        elif mode == "runtime_auto":
            mode_summary = "EDEN will choose a bounded preset each turn from transparent heuristics."
        else:
            mode_summary = "Mock sessions use a bounded Adam-guided preset picker; MLX sessions fall back to runtime_auto and log that."
        text = Text.from_markup(
            f"[bold {AMBER}]Mode[/] {mode.upper()}\n"
            f"{mode_summary}\n\n"
            f"[bold {AMBER}]Budget preset[/] {payload['budget_mode']}\n"
            f"retrieval_depth={payload['retrieval_depth']} max_context_items={payload['max_context_items']}\n"
            f"max_output_tokens={payload['max_output_tokens']} response_char_cap={payload['response_char_cap']}\n"
            f"temperature={payload['temperature']:.2f} top_p={payload['top_p']:.2f} repetition_penalty={payload['repetition_penalty']:.2f}"
        )
        self.query_one("#session_config_summary", Static).update(Panel(text, title="Profile Summary", border_style=AMBER))

    def _float_value(self, selector: str, default: float) -> float:
        raw = self.query_one(selector, Input).value.strip()
        try:
            return float(raw)
        except ValueError:
            return default

    def _int_value(self, selector: str, default: int) -> int:
        raw = self.query_one(selector, Input).value.strip()
        try:
            return int(raw)
        except ValueError:
            return default


class FeedbackModal(ModalScreen[None]):
    def __init__(self, chat_screen: "ChatScreen") -> None:
        super().__init__()
        self.chat_screen = chat_screen

    def compose(self) -> ComposeResult:
        yield Static(id="review_summary")
        yield TextArea(
            id="review_explanation_input",
            soft_wrap=True,
            show_line_numbers=False,
            placeholder="feedback explanation (required for accept / reject / edit)",
        )
        yield TextArea(
            id="review_corrected_input",
            soft_wrap=True,
            show_line_numbers=False,
            placeholder="corrected answer (required for edit)",
        )
        with Horizontal():
            yield Button("Accept", id="review_accept_btn")
            yield Button("Edit", id="review_edit_btn")
            yield Button("Reject", id="review_reject_btn")
            yield Button("Skip", id="review_skip_btn")
            yield Button("Close", id="review_close_btn")
        yield Static(id="review_status")

    def on_mount(self) -> None:
        self._refresh()
        self.query_one("#review_explanation_input", TextArea).focus()

    def _refresh(self) -> None:
        app = self.app
        summary = Text.from_markup(
            f"[bold {AMBER}]Review Last Turn[/]\n"
            f"turn={app.ui_state.last_turn_id or 'none'}\n\n"
            f"[bold {AMBER}]Adam membrane[/]\n"
            f"{safe_excerpt(app.ui_state.last_response or 'No response yet.', limit=900)}"
        )
        self.query_one("#review_summary", Static).update(Panel(summary, title="Feedback Surface", border_style=AMBER))
        self.query_one("#review_status", Static).update(
            Panel(Text(app.ui_state.last_feedback, style=MUTED), title="Feedback Status", border_style=AMBER)
        )

    async def _submit(self, verdict: str) -> None:
        explanation = self.query_one("#review_explanation_input", TextArea).text
        corrected = self.query_one("#review_corrected_input", TextArea).text
        await self.chat_screen.submit_feedback(verdict, explanation=explanation, corrected=corrected)
        self.dismiss(None)

    @on(Button.Pressed, "#review_accept_btn")
    async def handle_accept(self) -> None:
        await self._submit("accept")

    @on(Button.Pressed, "#review_edit_btn")
    async def handle_edit(self) -> None:
        await self._submit("edit")

    @on(Button.Pressed, "#review_reject_btn")
    async def handle_reject(self) -> None:
        await self._submit("reject")

    @on(Button.Pressed, "#review_skip_btn")
    async def handle_skip(self) -> None:
        await self._submit("skip")

    @on(Button.Pressed, "#review_close_btn")
    def handle_close(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class DeckModal(ModalScreen[None]):
    def __init__(self, chat_screen: "ChatScreen") -> None:
        super().__init__()
        self.chat_screen = chat_screen

    def compose(self) -> ComposeResult:
        yield Static(id="deck_summary")
        with Horizontal(id="deck_shell"):
            with Vertical(classes="deck_column"):
                yield Static(id="deck_budget_panel")
                yield Static(id="deck_telemetry_panel")
                yield Static(id="deck_history_panel")
            with Vertical(classes="deck_column"):
                yield Static(id="deck_thinking_panel")
                yield Static(id="deck_active_set_panel")
                yield Static(id="deck_trace_panel")
            with Vertical(classes="deck_column"):
                yield Input(id="deck_ingest_path_input", placeholder="document path (.pdf/.csv/.txt/.md)")
                with Horizontal():
                    yield Button("Ingest", id="deck_ingest_btn", variant="primary")
                    yield Button("Blank Eden", id="deck_blank_btn")
                    yield Button("Seeded Eden", id="deck_seeded_btn")
                with Horizontal():
                    yield Button("Resume Latest", id="deck_resume_btn")
                    yield Button("New Session", id="deck_new_session_btn")
                with Horizontal():
                    yield Button("Low Motion", id="deck_motion_btn")
                    yield Button("Debug", id="deck_debug_btn")
                    yield Button("Close", id="deck_close_btn")
                yield Static(id="deck_status_panel")

    def on_mount(self) -> None:
        self._refresh()
        self.set_interval(1.0, self._refresh)

    def _refresh(self) -> None:
        self.query_one("#deck_summary", Static).update(self.chat_screen.deck_summary_panel())
        self.query_one("#deck_budget_panel", Static).update(self.chat_screen.deck_budget_panel())
        self.query_one("#deck_telemetry_panel", Static).update(self.chat_screen.deck_telemetry_panel())
        self.query_one("#deck_history_panel", Static).update(self.chat_screen.deck_history_panel())
        self.query_one("#deck_thinking_panel", Static).update(self.chat_screen.deck_thinking_panel())
        self.query_one("#deck_active_set_panel", Static).update(self.chat_screen.deck_active_set_panel())
        self.query_one("#deck_trace_panel", Static).update(self.chat_screen.deck_trace_panel())
        self.query_one("#deck_status_panel", Static).update(self.chat_screen.deck_status_panel())

    @on(Button.Pressed, "#deck_ingest_btn")
    async def handle_ingest(self) -> None:
        path = self.query_one("#deck_ingest_path_input", Input).value.strip()
        if not path:
            return
        await self.chat_screen.ingest_path(path)
        self.query_one("#deck_ingest_path_input", Input).value = ""
        self._refresh()

    @on(Button.Pressed, "#deck_blank_btn")
    def handle_blank(self) -> None:
        self.dismiss(None)
        self.chat_screen.begin_surface_launch("blank")

    @on(Button.Pressed, "#deck_seeded_btn")
    def handle_seeded(self) -> None:
        self.dismiss(None)
        self.chat_screen.begin_surface_launch("seeded")

    @on(Button.Pressed, "#deck_resume_btn")
    def handle_resume(self) -> None:
        self.dismiss(None)
        self.chat_screen.begin_surface_launch("resume")

    @on(Button.Pressed, "#deck_new_session_btn")
    def handle_new_session(self) -> None:
        self.dismiss(None)
        self.chat_screen.begin_new_session_flow()

    @on(Button.Pressed, "#deck_motion_btn")
    async def handle_motion(self) -> None:
        await self.chat_screen.toggle_motion()
        self._refresh()

    @on(Button.Pressed, "#deck_debug_btn")
    async def handle_debug(self) -> None:
        await self.chat_screen.toggle_debug()
        self._refresh()

    @on(Button.Pressed, "#deck_close_btn")
    def handle_close(self) -> None:
        self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


class AdamSigil(Static):
    SWEEP = ("|", "/", "-", "\\")
    PULSES = ("..::....::..", ".::==::==::.", ":==####==::", ".::==::==::.")
    LOOP = ("capture", "retrieve", "scope", "trace", "prune", "prompt", "model", "membrane", "feedback")

    def on_mount(self) -> None:
        self.border_title = "Cockpit Scope"
        self._frame = 0
        self.set_interval(0.35, self._tick)
        self._tick()

    def _gauge(self, value: float, *, width: int = 16, fill: str = "#", empty: str = ".") -> str:
        clamped = max(0.0, min(1.0, value))
        lit = int(round(clamped * width))
        return (fill * lit) + (empty * max(0, width - lit))

    def _dial(self, label: str, value: float, *, width: int = 10) -> str:
        clamped = max(0.0, min(1.0, value))
        position = min(width - 1, max(0, int(round(clamped * (width - 1)))))
        ring = ["." for _ in range(width)]
        ring[position] = "o"
        return f"{label:<10} <{''.join(ring)}>"

    def _phase_index(self, app: "EdenTuiApp") -> int:
        base = 0
        if app.ui_state.session_id:
            base = 1
        if app.ui_state.preview_active_set:
            base = 3
        if app.ui_state.last_response:
            base = 6
        if app.runtime.settings.low_motion:
            return min(base, len(self.LOOP) - 1)
        return (base + self._frame) % len(self.LOOP)

    def _tick(self) -> None:
        app = self.app
        if not isinstance(app, EdenTuiApp):
            return
        if not app.runtime.settings.low_motion:
            self._frame = (self._frame + 1) % max(len(self.SWEEP), len(self.PULSES), len(self.LOOP))
        active_items = list((app.ui_state.preview_active_set or app.ui_state.last_active_set or []))
        trace_items = list((app.ui_state.preview_trace or app.ui_state.last_trace or []))
        pressure = str((app.ui_state.current_budget or {}).get("pressure_level", "LOW")).upper()
        response_chars = len(app.ui_state.last_response or "")
        response_cap = max(1, int((app.ui_state.current_profile or {}).get("response_char_cap", 1600) or 1600))
        max_context_items = max(1, int((app.ui_state.current_profile or {}).get("max_context_items", 8) or 8))
        model_status = app.runtime.mlx_model_status()
        behavior_count = sum(1 for item in active_items if item.get("domain") == "behavior")
        memode_count = sum(1 for item in active_items if item.get("node_kind") == "memode")
        behavior_mass = sum(max(0.0, float(item.get("selection", 0.0))) for item in active_items if item.get("domain") == "behavior")
        knowledge_mass = sum(max(0.0, float(item.get("selection", 0.0))) for item in active_items if item.get("domain") != "behavior")
        total_mass = max(behavior_mass + knowledge_mass, 1e-6)
        reasoning = "present" if app.ui_state.last_reasoning else "quiet"
        latest = app.runtime.runtime_log.recent(4)
        event_lines = [
            f"{event.level:<5} {safe_excerpt(event.event, limit=18)} :: {safe_excerpt(event.message, limit=42)}"
            for event in latest[-4:]
        ]
        pressure_value = {"LOW": 0.28, "MEDIUM": 0.56, "HIGH": 0.84}.get(str(pressure).upper(), 0.4)
        selection_peak = max((float(item.get("selection", 0.0)) for item in trace_items), default=0.0)
        regard_peak = max((float(item.get("regard", 0.0)) for item in trace_items), default=0.0)
        membrane_ratio = response_chars / response_cap
        phase_index = self._phase_index(app)
        loop_a = " > ".join(step.upper() if idx == phase_index else step for idx, step in enumerate(self.LOOP[:5]))
        loop_b = " > ".join(
            step.upper() if idx + 5 == phase_index else step for idx, step in enumerate(self.LOOP[5:])
        )
        sweep = self.SWEEP[0 if app.runtime.settings.low_motion else self._frame % len(self.SWEEP)]
        pulse = self.PULSES[0 if app.runtime.settings.low_motion else self._frame % len(self.PULSES)]
        text = Text.from_markup(
            f"[bold {AMBER}]Flight Loop[/]\n"
            f"{loop_a}\n"
            f"{loop_b}\n\n"
            f"[bold {AMBER}]Amber Dials[/]\n"
            f"scanner={sweep} pulse={pulse} model={model_status.get('stage', 'n/a')} reasoning={reasoning}\n"
            f"aperture   {self._gauge(len(active_items) / max_context_items)} {len(active_items)}/{max_context_items}\n"
            f"behavior   {self._gauge(behavior_mass / total_mass, fill='=')} {behavior_count} slots\n"
            f"memodes    {self._gauge(memode_count / max(1, len(active_items)), fill=':')} {memode_count}/{len(active_items) or 1}\n"
            f"membrane   {self._gauge(membrane_ratio, fill='|')} {response_chars}/{response_cap}\n"
            f"pressure   {self._gauge(pressure_value, fill=':')} {pressure}\n"
            f"{self._dial('selection', selection_peak)}\n"
            f"{self._dial('regard', regard_peak)}\n"
            f"{self._dial('knowledge', knowledge_mass / total_mass)}\n\n"
            f"[bold {AMBER}]Recent Signal[/]\n"
            + ("\n".join(event_lines) if event_lines else "No runtime signal yet.")
        )
        self.update(Panel(text, title="Amber Cockpit", border_style=AMBER))


class SignalField(Static):
    MODES = ("mesh", "radial", "matrix", "lattice")

    def on_mount(self) -> None:
        self._frame = 0
        self.set_interval(0.28, self._tick)
        self._tick()

    def _append_cell(self, line: Text, char: str, style: str) -> None:
        line.append(char, style=style)

    def _mesh_char(self, x: int, y: int, frame: int, width: int, height: int) -> tuple[str, str]:
        horizon = int(height * 0.55 + math.sin((frame + y) / 5) * 2)
        wave = int((math.sin((x + frame) / 4) + 1.0) * 2)
        if y == horizon:
            return "_", ICE
        if y > horizon and ((x + frame) % 4 == 0 or (x - y - frame) % 7 == 0):
            return "/" if (x + y + frame) % 2 == 0 else "\\", EMBER
        if y < horizon and (x + y + frame) % 11 == 0:
            return ".", TEXT
        if y == horizon - wave and (x + frame) % 9 == 0:
            return "*", ROSE
        return " ", TEXT

    def _radial_char(self, x: int, y: int, frame: int, width: int, height: int) -> tuple[str, str]:
        cx = width * 0.68
        cy = height * 0.52
        dx = x - cx
        dy = y - cy
        distance = math.sqrt(dx * dx + dy * dy)
        angle = math.atan2(dy, dx)
        spoke = abs(math.sin(angle * 6 + frame / 3))
        pulse = abs(math.sin(frame / 4 + distance / 3))
        if distance < 1.3:
            return "*", TEXT
        if spoke > 0.97 and distance < min(width, height) * 0.42:
            return "|" if abs(dx) < abs(dy) else "-", ICE
        if abs(distance - (6 + (frame % 5))) < 0.65:
            return "o", ROSE
        if pulse > 0.92 and distance < min(width, height) * 0.46:
            return ".", AMBER
        return " ", TEXT

    def _matrix_char(self, x: int, y: int, frame: int, width: int, height: int) -> tuple[str, str]:
        stream = (x * 11 + frame * 3) % 17
        if stream < 2:
            digit = str((x + y + frame) % 10)
            style = NEON if y < height * 0.75 else AMBER
            if (y + frame) % 9 == 0:
                style = TEXT
            return digit, style
        if y == height - 3 and (x + frame) % 5 == 0:
            return "_", EMBER
        if y > height - 4 and (x + frame) % 3 == 0:
            return "=", MUTED
        return " ", TEXT

    def _lattice_char(self, x: int, y: int, frame: int, width: int, height: int) -> tuple[str, str]:
        offset = (y + frame) % 4
        if (x + offset) % 6 == 0:
            return "/", NEON
        if (x - offset) % 6 == 0:
            return "\\", NEON
        if y % 4 == 0 and (x + frame) % 3 == 0:
            return "_", ICE
        if (x * 3 + y + frame) % 19 == 0:
            return ".", ROSE
        return " ", TEXT

    def _field_state(self, app: "EdenTuiApp") -> dict[str, Any]:
        active_items = list((app.ui_state.preview_active_set or app.ui_state.last_active_set or []))
        behavior_count = sum(1 for item in active_items if item.get("domain") == "behavior")
        knowledge_count = sum(1 for item in active_items if item.get("domain") != "behavior")
        memode_count = sum(1 for item in active_items if item.get("node_kind") == "memode")
        reasoning_present = bool(app.ui_state.last_reasoning)
        pressure = str((app.ui_state.current_budget or {}).get("pressure_level", "LOW")).upper()
        recent_feedback = app.runtime.store.recent_feedback(app.ui_state.session_id, limit=3) if app.ui_state.session_id else []
        latest_feedback = recent_feedback[0] if recent_feedback else None
        pending_review = bool(
            app.ui_state.last_turn_id
            and (
                latest_feedback is None
                or latest_feedback.get("turn_id") != app.ui_state.last_turn_id
            )
        )
        if pressure == "HIGH":
            mode = "matrix"
            rationale = "pressure is high, so the field collapses into a dense traffic pattern."
        elif reasoning_present:
            mode = "radial"
            rationale = "visible reasoning is pulling attention toward a central convergence point."
        elif memode_count:
            mode = "lattice"
            rationale = f"{memode_count} memode bundle{'s are' if memode_count != 1 else ' is'} stabilizing the turn."
        else:
            mode = "mesh"
            rationale = "the turn is still exploratory, so the field remains a distributed search mesh."
        return {
            "active_items": active_items,
            "behavior_count": behavior_count,
            "knowledge_count": knowledge_count,
            "memode_count": memode_count,
            "reasoning_present": reasoning_present,
            "pressure": pressure,
            "recent_feedback": recent_feedback,
            "latest_feedback": latest_feedback,
            "pending_review": pending_review,
            "mode": mode,
            "rationale": rationale,
        }

    def _tick(self) -> None:
        app = self.app
        if not isinstance(app, EdenTuiApp):
            return
        if not app.runtime.settings.low_motion:
            self._frame = (self._frame + 1) % 10_000
        state = self._field_state(app)
        mode = state["mode"]
        width = max(54, min((self.size.width or 72) - 6, 88))
        height = max(8, min((self.size.height or 18) - 9, 10))
        visual = Text()
        for y in range(height):
            line = Text()
            for x in range(width):
                if mode == "mesh":
                    char, style = self._mesh_char(x, y, self._frame, width, height)
                elif mode == "radial":
                    char, style = self._radial_char(x, y, self._frame, width, height)
                elif mode == "matrix":
                    char, style = self._matrix_char(x, y, self._frame, width, height)
                else:
                    char, style = self._lattice_char(x, y, self._frame, width, height)
                if state["pending_review"] and (x * 5 + y + self._frame) % 41 == 0:
                    char, style = "•", ROSE
                if state["reasoning_present"] and abs(x - int(width * 0.68)) + abs(y - int(height * 0.48)) < 2:
                    char, style = "*", ICE
                self._append_cell(line, char, style)
            visual.append(line)
            if y < height - 1:
                visual.append("\n")
        reasoning_label = "visible" if state["reasoning_present"] else "quiet"
        pending_label = "pending" if state["pending_review"] else "settled"
        explanation = Text.from_markup(
            f"\n\n[bold {AMBER}]What you're seeing[/]\n"
            f"green scaffold = active-set topology | amber rails = membrane / budget boundary | "
            f"rose sparks = feedback turbulence | ice beacon = reasoning convergence\n"
            f"[bold {AMBER}]why this mode[/] {state['rationale']}\n"
            f"[bold {AMBER}]read it as[/] mode={mode} active={len(state['active_items'])} "
            f"behavior={state['behavior_count']} knowledge={state['knowledge_count']} "
            f"memodes={state['memode_count']} reasoning={reasoning_label} review={pending_label} "
            f"pressure={state['pressure']}\n"
            "This field is an operator metaphor for the turn state, not a claim about hidden activations."
        )
        border = NEON if mode in {"matrix", "lattice"} else ICE if mode == "radial" else AMBER
        self.update(Panel(visual + explanation, title="Signal Field", border_style=border, style=f"on {SHADE}"))


class StartupScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self._seen_log_count = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="startup_frame"):
            with Horizontal(id="startup_topbar"):
                yield Select(
                    [
                        ("Blank Eden", "blank"),
                        ("Seeded Eden", "seeded"),
                        ("Resume Latest", "resume"),
                        ("Prepare Qwen", "prepare_mlx"),
                        ("Refresh Model", "refresh_model"),
                        ("Open Observatory", "observatory"),
                        ("Export Latest", "export"),
                        ("Help", "help"),
                    ],
                    value="blank",
                    allow_blank=False,
                    id="startup_action_menu",
                    prompt="Startup actions",
                )
                yield Static(id="startup_menu_hint")
            with Horizontal(id="startup_shell"):
                with Vertical(id="startup_left"):
                    yield Static(id="startup_aperture_panel")
                    yield Static(id="startup_reasoning_panel")
                with Vertical(id="startup_right"):
                    with Vertical(id="startup_cockpit_stack"):
                        yield AdamSigil(id="startup_cockpit")
                        yield RichLog(id="startup_log", wrap=True, auto_scroll=True, highlight=True)
                    yield Static(id="startup_transcript_panel")
        yield Footer()

    def on_mount(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        app.runtime.update_runtime_launch_profile(backend="mlx", model_path=None)
        app.ui_state.model_status = app.runtime.mlx_model_status()
        self._refresh_panels()
        self.set_interval(0.6, self._poll_logs)
        self.call_after_refresh(lambda: self.query_one("#startup_action_menu", Select).focus())

    def _refresh_panels(self) -> None:
        self.query_one("#startup_aperture_panel", Static).update(self._aperture_panel())
        self.query_one("#startup_reasoning_panel", Static).update(self._thinking_panel())
        self.query_one("#startup_menu_hint", Static).update(self._menu_hint_panel())
        self.query_one("#startup_transcript_panel", Static).update(self._transcript_panel())

    def _latest_snapshot(self) -> dict[str, Any] | None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        latest = app.runtime.store.get_latest_experiment()
        if latest is None:
            return None
        latest_session = app.runtime.store.get_latest_session(latest["id"])
        if latest_session is None:
            return None
        return app.runtime.session_state_snapshot(latest_session["id"])

    def _aperture_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        snapshot = self._latest_snapshot()
        active_items = list((snapshot or {}).get("last_active_set") or [])
        meme_count = sum(1 for item in active_items if item.get("node_kind") == "meme")
        memode_count = sum(1 for item in active_items if item.get("node_kind") == "memode")
        behavior_count = sum(1 for item in active_items if item.get("domain") == "behavior")
        knowledge_count = sum(1 for item in active_items if item.get("domain") != "behavior")
        active_lines = [
            f"{item.get('label', 'untitled')} [{item.get('node_kind', 'node')}:{item.get('domain', 'knowledge')}] "
            f"sel={float(item.get('selection', 0.0)):.2f} reg={float(item.get('regard', 0.0)):.2f}"
            for item in active_items[:6]
        ]
        if not active_lines:
            active_lines = [
                "Aperture = operator-facing trace of the active set.",
                "Active set = bounded memes and memodes surfaced for a turn.",
                "Regard = persistent valuation; attention = turn-local salience.",
                "Loop = capture > retrieve > scope > trace > prune > prompt > membrane > feedback.",
            ]
        content = Text.from_markup(
            f"[bold {AMBER}]Aperture / Active Set[/]\n"
            f"latest_session={(snapshot or {}).get('session_title', 'none')}\n"
            f"items={len(active_items)} memes={meme_count} memodes={memode_count}\n"
            f"behavior={behavior_count} knowledge={knowledge_count}\n\n"
            + "\n".join(active_lines)
        )
        return Panel(content, title="Aperture", border_style=AMBER)

    def _thinking_panel(self) -> Panel:
        snapshot = self._latest_snapshot() or {}
        reasoning_text = snapshot.get("last_reasoning") or ""
        summary = safe_excerpt(reasoning_text, limit=1600) if reasoning_text else "No Qwen reasoning captured yet. Once Adam has generated with visible reasoning, the latest chain-of-thought surface will appear here as an operator-visible model artifact."
        title_suffix = f" :: {snapshot.get('session_title', 'none')}" if snapshot else ""
        style = TEXT if reasoning_text else MUTED
        body = Text.from_markup(
            f"[bold {AMBER}]Qwen Thinking[/]\n"
            "Visible model reasoning artifact; not hidden chain-of-thought claims.\n\n"
        )
        body.append(summary, style=style)
        return Panel(body, title=f"Thinking{title_suffix}", border_style=AMBER)

    def _menu_hint_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        status = app.runtime.mlx_model_status()
        selected = str(self.query_one("#startup_action_menu", Select).value or "blank").replace("_", " ")
        text = Text.from_markup(
            f"[bold {AMBER}]Launch Contract[/]\n"
            "runtime=Adam / Local MLX (locked)\n"
            f"cache={status.get('stage', 'missing')} storage=models/{Path(status['local_dir']).name}\n"
            f"menu={selected}\n"
            "keyboard: up/down opens menu focus, arrows choose, Enter executes, Tab cycles focus\n"
            "chat deck remains keyboard-first once a session is live"
        )
        return Panel(text, title="Action Menu", border_style=AMBER)

    def _transcript_panel(self) -> Panel:
        snapshot = self._latest_snapshot() or {}
        operator_text = safe_excerpt(snapshot.get("last_user_text") or "Awaiting Brian transmission.", limit=260)
        response_text = safe_excerpt(snapshot.get("last_response") or "Awaiting Adam membrane response.", limit=500)
        exchange = Group(
            Panel(
                Text(operator_text, style=TEXT),
                title="Brian / Last Transmission",
                border_style=MUTED,
                style=f"on {SHADE_ALT}",
            ),
            Panel(
                Text(response_text, style=TEXT),
                title="Adam / Last Membrane",
                border_style=AMBER,
                style=f"on {SHADE}",
            ),
        )
        return Panel(exchange, title="Chat Preview", border_style=AMBER)

    def _execute_startup_action(self, action: str) -> None:
        normalized = (action or "blank").strip().lower()
        if normalized == "blank":
            self.begin_launch_session("blank")
        elif normalized == "seeded":
            self.begin_launch_session("seeded")
        elif normalized == "resume":
            self.begin_launch_session("resume")
        elif normalized == "prepare_mlx":
            self.handle_prepare_mlx()
        elif normalized == "refresh_model":
            self.handle_refresh_model()
        elif normalized == "observatory":
            self.handle_startup_observatory()
        elif normalized == "export":
            self.handle_startup_export()
        elif normalized == "help":
            self.run_worker(self.app.push_screen(HelpModal()), exclusive=True, group="startup_help")

    def _poll_logs(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        events = app.runtime.runtime_log.recent(200)
        widget = self.query_one("#startup_log", RichLog)
        for event in events[self._seen_log_count :]:
            widget.write(f"[{event.level}] {event.event} :: {event.message} {event.payload}")
        self._seen_log_count = len(events)

    async def _launch_session_worker(self, action: str) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        app.runtime.update_runtime_launch_profile(backend="mlx", model_path=None)
        status = await self._ensure_local_mlx_model()
        if status is None:
            return
        app.ui_state.model_status = status
        self._refresh_panels()
        if action == "resume":
            latest = app.runtime.store.get_latest_experiment()
            if latest is None:
                self.query_one("#startup_log", RichLog).write("[WARN] No existing experiment. Create one first.")
                return
            latest_session = app.runtime.store.get_latest_session(latest["id"])
            if latest_session is None:
                self.query_one("#startup_log", RichLog).write("[WARN] Latest experiment has no sessions yet.")
                return
            snapshot = await asyncio.to_thread(partial(app.runtime.session_state_snapshot, latest_session["id"]))
            app.apply_session_snapshot(snapshot)
            await app.push_screen(ChatScreen())
            return
        defaults = app.runtime.default_session_profile_request().to_dict()
        payload = await app.push_screen_wait(
            SessionConfigModal(
                defaults,
                title_text="Session Inference Profile",
                action_label="Start Session",
            )
        )
        if payload is None:
            return
        experiment = await asyncio.to_thread(partial(app.runtime.initialize_experiment, action))
        session = await asyncio.to_thread(
            partial(
                app.runtime.start_session,
                experiment["id"],
                title=payload["title"],
                profile_request=payload,
            )
        )
        app.apply_session_snapshot(
            {
                "experiment_id": experiment["id"],
                "experiment_name": experiment["name"],
                "session_id": session["id"],
                "session_title": session["title"],
                "last_turn_id": None,
                "last_user_text": "",
                "last_response": "",
                "last_reasoning": "",
                "last_active_set": [],
                "last_trace": [],
                "current_profile": None,
                "current_budget": None,
            }
        )
        await app.push_screen(ChatScreen())

    def begin_launch_session(self, action: str) -> None:
        self.run_worker(self._launch_session_worker(action), exclusive=True, group="launch")

    async def _ensure_local_mlx_model(self) -> dict[str, Any] | None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        status = await asyncio.to_thread(app.runtime.mlx_model_status)
        if status["ready"]:
            return status
        self.query_one("#startup_log", RichLog).write(
            f"[INFO] Preparing local MLX model :: {status['label']} -> models/{Path(status['local_dir']).name}"
        )
        try:
            status = await asyncio.to_thread(app.runtime.prepare_default_mlx_model)
        except Exception as exc:
            self.query_one("#startup_log", RichLog).write(f"[ERROR] MLX prepare failed :: {exc}")
            return None
        self.query_one("#startup_log", RichLog).write(
            f"[INFO] MLX model ready :: models/{Path(status['local_dir']).name} ({status.get('gib_on_disk', 0)} GiB)"
        )
        return status

    async def _prepare_mlx_worker(self) -> None:
        status = await self._ensure_local_mlx_model()
        if status is not None:
            self.app.ui_state.model_status = status
            self._refresh_panels()

    def handle_prepare_mlx(self) -> None:
        self.run_worker(self._prepare_mlx_worker(), exclusive=True, group="prepare_mlx")

    def handle_refresh_model(self) -> None:
        self._refresh_panels()

    async def _startup_export_worker(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        latest = app.runtime.store.get_latest_experiment()
        if latest is None:
            self.query_one("#startup_log", RichLog).write("[WARN] No experiment available to export.")
            return
        latest_session = app.runtime.store.get_latest_session(latest["id"])
        paths = await asyncio.to_thread(
            partial(
                app.runtime.export_observability,
                experiment_id=latest["id"],
                session_id=latest_session["id"] if latest_session else None,
            )
        )
        names = [Path(paths[key]).name for key in ("graph_html", "basin_html", "geometry_html") if key in paths]
        self.query_one("#startup_log", RichLog).write(f"[INFO] Exported latest surfaces :: {', '.join(names)}")
        self._refresh_panels()

    async def _startup_observatory_worker(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        status = await asyncio.to_thread(partial(app.runtime.start_observatory, reuse_existing=True))
        app.ui_state.observatory_status = status
        latest = app.runtime.store.get_latest_experiment()
        target_url = _observatory_target_url(app.runtime, status, latest["id"] if latest is not None else None)
        webbrowser.open(target_url)
        self.query_one("#startup_log", RichLog).write(
            f"[INFO] Observatory {'reused' if status['reused_existing'] else 'started'} :: {target_url}"
        )
        self._refresh_panels()

    def handle_startup_export(self) -> None:
        self.run_worker(self._startup_export_worker(), exclusive=True, group="startup_export")

    def handle_startup_observatory(self) -> None:
        self.run_worker(self._startup_observatory_worker(), exclusive=True, group="startup_observatory")

    @on(Select.Changed, "#startup_action_menu")
    def handle_startup_action_changed(self, _event: Select.Changed) -> None:
        self.query_one("#startup_menu_hint", Static).update(self._menu_hint_panel())

    def on_key(self, event) -> None:
        if event.key == "enter" and self.app.focused and getattr(self.app.focused, "id", None) == "startup_action_menu":
            action = str(self.query_one("#startup_action_menu", Select).value or "blank")
            self._execute_startup_action(action)
            event.stop()


class ChatScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self._seen_log_count = 0
        self._preview_task: asyncio.Task[None] | None = None
        self._preview_generation = 0
        self._display_frame = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="runtime_frame"):
            with Horizontal(id="runtime_topbar"):
                yield Select(
                    ACTION_MENU_OPTIONS,
                    value="review",
                    allow_blank=False,
                    id="runtime_action_menu",
                    prompt="Action menu",
                )
                yield Static(id="runtime_status_strip")
            with Horizontal(id="chat_shell"):
                with Vertical(id="chat_left"):
                    yield Static(id="active_aperture_panel")
                    yield Static(id="thinking_panel")
                    yield Static(id="feedback_panel")
                with Vertical(id="chat_right"):
                    yield SignalField(id="signal_field")
                    with Horizontal(id="chat_instrument_row"):
                        yield AdamSigil(id="ritual_panel")
                        yield RichLog(id="forensic_log", wrap=True, auto_scroll=True, highlight=True)
                    with Vertical(id="chat_deck"):
                        yield Static(id="chat_exchange_panel")
                        yield Static(id="feedback_loop_panel")
                        yield TextArea(
                            id="composer_input",
                            soft_wrap=True,
                            show_line_numbers=False,
                            placeholder="Brian the operator: direct, question, or correction. Ctrl+S sends.",
                        )
                        yield Static(id="composer_hint_panel")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(0.6, self._poll_logs)
        self.set_interval(0.45, self.refresh_panels)
        self.refresh_panels()
        self.run_worker(self._bootstrap_live_surface(), exclusive=True, group="bootstrap")
        self.call_after_refresh(lambda: self.query_one("#composer_input", TextArea).focus())

    def refresh_panels(self) -> None:
        self._display_frame = (self._display_frame + 1) % 10_000
        self.query_one("#runtime_status_strip", Static).update(self.main_action_status_panel())
        self.query_one("#active_aperture_panel", Static).update(self.main_aperture_panel())
        self.query_one("#thinking_panel", Static).update(self.main_thinking_panel())
        self.query_one("#feedback_panel", Static).update(self.main_feedback_panel())
        self.query_one("#chat_exchange_panel", Static).update(self.main_chat_exchange_panel())
        self.query_one("#feedback_loop_panel", Static).update(self.main_feedback_loop_panel())
        self.query_one("#composer_hint_panel", Static).update(self.main_composer_hint_panel())

    def _model_status(self) -> dict[str, Any]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if app.ui_state.model_status:
            return app.ui_state.model_status
        backend = app.runtime.settings.model_backend.lower()
        if backend == "mlx":
            app.ui_state.model_status = app.runtime.mlx_model_status()
        else:
            app.ui_state.model_status = {
                "label": "Mock Adapter",
                "local_dir": "mock://runtime",
                "stage": "ready",
                "ready": True,
            }
        return app.ui_state.model_status

    def _active_backend_label(self) -> str:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        backend = app.runtime.settings.model_backend.lower()
        return "Adam / Local MLX" if backend == "mlx" else f"Adam / {backend.upper()}"

    def _recent_turns(self, *, limit: int = 2) -> list[dict[str, Any]]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.session_id:
            return []
        return list(reversed(app.runtime.store.list_turns(app.ui_state.session_id, limit=limit)))

    async def _bootstrap_live_surface(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        app.ui_state.model_status = await asyncio.to_thread(self._load_model_status_snapshot)
        model_status = self._model_status()
        self._write_forensic(
            f"[INFO] Live cockpit boot :: backend={app.runtime.settings.model_backend} stage={model_status.get('stage', 'n/a')}"
        )
        if app.runtime.settings.model_backend.lower() == "mlx" and not model_status.get("ready", False):
            app.ui_state.last_feedback = "Local MLX cache is not ready. Choose Prepare Qwen or send once to fetch it."
        latest = await asyncio.to_thread(app.runtime.store.get_latest_experiment)
        experiment: dict[str, Any] | None = latest
        if latest is not None:
            latest_session = await asyncio.to_thread(partial(app.runtime.store.get_latest_session, latest["id"]))
            if latest_session is not None:
                snapshot = await asyncio.to_thread(partial(app.runtime.session_state_snapshot, latest_session["id"]))
                app.apply_session_snapshot(snapshot)
                app.ui_state.last_feedback = f"Resumed {snapshot['session_title']}."
                self._write_forensic(f"[INFO] Resumed session :: {snapshot['session_title']}")
                self.refresh_panels()
                self._schedule_preview_refresh()
                return
        if experiment is None:
            experiment = await asyncio.to_thread(partial(app.runtime.initialize_experiment, "blank", name="Live Eden"))
            self._write_forensic(f"[INFO] Created experiment :: {experiment['name']}")
        defaults = app.runtime.default_session_profile_request().to_dict()
        defaults["title"] = defaults.get("title") or "Live Adam Session"
        session = await asyncio.to_thread(
            partial(
                app.runtime.start_session,
                experiment["id"],
                title=defaults["title"],
                profile_request=defaults,
            )
        )
        snapshot = await asyncio.to_thread(partial(app.runtime.session_state_snapshot, session["id"]))
        app.apply_session_snapshot(snapshot)
        app.ui_state.last_feedback = "Live cockpit armed. Compose and send with Ctrl+S."
        self._write_forensic(f"[INFO] Armed session :: {snapshot['session_title']}")
        self.refresh_panels()
        self._schedule_preview_refresh()

    def _load_model_status_snapshot(self) -> dict[str, Any]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        backend = app.runtime.settings.model_backend.lower()
        if backend == "mlx":
            return app.runtime.mlx_model_status()
        return {
            "label": "Mock Adapter",
            "local_dir": "mock://runtime",
            "stage": "ready",
            "ready": True,
        }

    async def _ensure_backend_ready(self, *, prepare: bool) -> bool:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if app.runtime.settings.model_backend.lower() != "mlx":
            app.ui_state.model_status = self._load_model_status_snapshot()
            return True
        status = await asyncio.to_thread(app.runtime.mlx_model_status)
        app.ui_state.model_status = status
        if status.get("ready", False):
            return True
        if not prepare:
            self.refresh_panels()
            return False
        self._write_forensic(
            f"[INFO] Preparing local MLX model :: {status['label']} -> models/{Path(status['local_dir']).name}"
        )
        app.ui_state.last_feedback = "Preparing local MLX model. This may take a moment."
        self.refresh_panels()
        try:
            status = await asyncio.to_thread(app.runtime.prepare_default_mlx_model)
        except Exception as exc:
            app.ui_state.last_feedback = f"MLX prepare failed: {exc}"
            self._write_forensic(f"[ERROR] MLX prepare failed :: {exc}")
            self.refresh_panels()
            return False
        app.ui_state.model_status = status
        app.ui_state.last_feedback = f"Local MLX model ready: models/{Path(status['local_dir']).name}"
        self._write_forensic(
            f"[INFO] MLX model ready :: models/{Path(status['local_dir']).name} ({status.get('gib_on_disk', 0)} GiB)"
        )
        self.refresh_panels()
        return True

    def _write_forensic(self, line: str) -> None:
        self.query_one("#forensic_log", RichLog).write(line)

    def _health(self) -> dict[str, Any]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.experiment_id:
            return {
                "memes": 0,
                "memodes": 0,
                "edges": 0,
                "turns": 0,
                "feedback": 0,
                "documents": 0,
                "triadic_closure": 0.0,
                "dyad_ratio": 0.0,
                "memode_coverage": 0.0,
                "isolated_count": 0.0,
            }
        return app.runtime.graph_health(app.ui_state.experiment_id)

    def _active_items(self) -> list[dict[str, Any]]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        return list((app.ui_state.preview_active_set if self._composer_text().strip() else app.ui_state.last_active_set) or [])

    def _trace_items(self) -> list[dict[str, Any]]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        return list((app.ui_state.preview_trace if self._composer_text().strip() else app.ui_state.last_trace) or [])

    def _recent_feedback_entries(self, *, limit: int = 3) -> list[dict[str, Any]]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.session_id:
            return []
        return app.runtime.store.recent_feedback(app.ui_state.session_id, limit=limit)

    def _meter_bar(self, value: float, *, scale: float, width: int = 8, fill: str = "■", empty: str = "·") -> str:
        clamped = max(0.0, min(value / max(scale, 1e-6), 1.0))
        lit = int(round(clamped * width))
        return (fill * lit) + (empty * max(0, width - lit))

    def _selection_phrase(self, value: float) -> str:
        if value >= 4.0:
            return "dominant now"
        if value >= 2.0:
            return "strong pull"
        if value >= 1.0:
            return "steady pull"
        return "background pull"

    def _regard_phrase(self, value: float) -> str:
        if value >= 4.0:
            return "deeply anchored"
        if value >= 2.0:
            return "persistent"
        if value >= 1.0:
            return "present in memory"
        return "lightly held"

    def _activation_phrase(self, value: float) -> str:
        if value >= 0.75:
            return "hot"
        if value >= 0.45:
            return "warm"
        if value >= 0.2:
            return "warming"
        return "cool"

    def _active_item_role(self, item: dict[str, Any]) -> str:
        if item.get("node_kind") == "memode":
            return f"{item.get('domain', 'knowledge')} memode"
        return f"{item.get('domain', 'knowledge')} meme"

    def _feedback_loop_state(self) -> tuple[str, dict[str, Any] | None]:
        latest = self._recent_feedback_entries(limit=1)
        latest_entry = latest[0] if latest else None
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.last_turn_id:
            return ("idle", latest_entry)
        if latest_entry is not None and latest_entry.get("turn_id") == app.ui_state.last_turn_id:
            return ("reviewed", latest_entry)
        return ("pending", latest_entry)

    def main_aperture_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        active_items = sorted(
            self._active_items(),
            key=lambda item: (
                float(item.get("selection", 0.0)),
                float(item.get("regard", 0.0)),
                float(item.get("activation", 0.0)),
            ),
            reverse=True,
        )
        previewing = bool(self._composer_text().strip())
        meme_count = sum(1 for item in active_items if item.get("node_kind") == "meme")
        memode_count = sum(1 for item in active_items if item.get("node_kind") == "memode")
        behavior_count = sum(1 for item in active_items if item.get("domain") == "behavior")
        knowledge_count = sum(1 for item in active_items if item.get("domain") != "behavior")
        if not active_items:
            text = Text.from_markup(
                f"[bold {AMBER}]Aperture / Active Set[/]\n"
                "No active set yet. Start a session or type into the chat deck to arm preview."
            )
            return Panel(text, title="Aperture", border_style=AMBER, style=f"on {SHADE}")
        behavior_mass = sum(float(item.get("selection", 0.0)) for item in active_items if item.get("domain") == "behavior")
        knowledge_mass = sum(float(item.get("selection", 0.0)) for item in active_items if item.get("domain") != "behavior")
        lead = "knowledge-led" if knowledge_mass > behavior_mass * 1.15 else "behavior-led" if behavior_mass > knowledge_mass * 1.15 else "balanced"
        focus_index = self._display_frame % len(active_items)
        focus_item = active_items[focus_index]
        pulse = ("▶", "▸", "•", "▹")[0 if app.runtime.settings.low_motion else self._display_frame % 4]
        body = Text.from_markup(
            f"[bold {AMBER}]Readable scan[/]\n"
            f"This turn is {lead} with {knowledge_count} knowledge cue{'s' if knowledge_count != 1 else ''}, "
            f"{behavior_count} behavioral anchor{'s' if behavior_count != 1 else ''}, and "
            f"{memode_count} memode bundle{'s' if memode_count != 1 else ''}.\n"
            f"Scanner is tracking [bold {NEON}]{safe_excerpt(focus_item.get('label', 'untitled'), limit=28)}[/], "
            f"a {self._active_item_role(focus_item)} that feels {self._selection_phrase(float(focus_item.get('selection', 0.0)))}, "
            f"{self._regard_phrase(float(focus_item.get('regard', 0.0)))}, and {self._activation_phrase(float(focus_item.get('activation', 0.0)))}.\n"
            "Read the queue as: NOW = turn pull | MEMORY = persistent regard | HEAT = present activation.\n\n"
            f"[bold {AMBER}]Scan queue[/]\n"
        )
        for index, item in enumerate(active_items[:5]):
            selection = float(item.get("selection", 0.0))
            regard = float(item.get("regard", 0.0))
            activation = float(item.get("activation", 0.0))
            indicator = pulse if index == focus_index % max(1, min(len(active_items), 5)) else " "
            line_style = f"bold {NEON}" if indicator.strip() else TEXT
            body.append(
                f"{indicator} {safe_excerpt(item.get('label', 'untitled'), limit=24):<24} {self._active_item_role(item):<16} "
                f"NOW {self._meter_bar(selection, scale=5.0)} {self._selection_phrase(selection):<14} "
                f"MEM {self._meter_bar(regard, scale=5.0, fill='▣')} {self._regard_phrase(regard):<16} "
                f"HEAT {self._meter_bar(activation, scale=1.0, fill='▤')} {self._activation_phrase(activation)}\n",
                style=line_style,
            )
        body.append(
            f"\n[bold {AMBER}]State[/] session={app.ui_state.session_title or app.ui_state.session_id or 'arming'} "
            f"state={'preview' if previewing else 'persisted'} items={len(active_items)} memes={meme_count} memodes={memode_count}",
            style=MUTED,
        )
        return Panel(body, title="Aperture", border_style=AMBER, style=f"on {SHADE}")

    def main_action_status_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        model_status = self._model_status()
        selected = str(self.query_one("#runtime_action_menu", Select).value or "review").replace("_", " ")
        profile = app.ui_state.current_profile or {}
        focus_id = getattr(self.app.focused, "id", "none") or "none"
        text = Text.from_markup(
            f"[bold {AMBER}]Live Contract[/]\n"
            f"runtime={self._active_backend_label()} stage={model_status.get('stage', 'n/a')} action={selected}\n"
            f"session={app.ui_state.session_title or app.ui_state.session_id or 'arming'} "
            f"profile={profile.get('profile_name', 'pending')} focus={focus_id}\n"
            "keyboard=Tab switch | Enter run action | Ctrl+S send | F6 deck | F7 review"
        )
        return Panel(text, title="Action Bus", border_style=AMBER, style=f"on {SHADE_ALT}")

    def main_thinking_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        profile = app.ui_state.current_profile or {}
        budget = app.ui_state.current_budget or {}
        trace_lines = [
            f">> {item.get('label', 'untitled')} sel={float(item.get('selection', 0.0)):.2f} "
            f"reg={float(item.get('regard', 0.0)):.2f} act={float(item.get('activation', 0.0)):.2f}"
            for item in self._trace_items()[:4]
        ]
        if not trace_lines:
            trace_lines = [">> no active consideration trace yet"]
        state = "draft-armed" if self._composer_text().strip() else "persisted"
        body = Text.from_markup(
            f"[bold {AMBER}]Visible reasoning artifact[/]\n"
            f"state={state} mode={profile.get('requested_mode', 'pending')} -> {profile.get('effective_mode', 'pending')}\n"
            f"pressure={budget.get('pressure_level', 'n/a')} response_cap={profile.get('response_char_cap', 'n/a')}\n\n"
        )
        if app.ui_state.last_reasoning:
            body.append(safe_excerpt(app.ui_state.last_reasoning, limit=780), style=TEXT)
            body.append("\n\n", style=TEXT)
        else:
            body.append(
                "No model-emitted thinking artifact yet. The live trace below shows what the cockpit is weighting before the next turn.\n\n",
                style=MUTED,
            )
        body.append("Consideration trace\n", style=f"bold {NEON}")
        body.append("\n".join(trace_lines), style=ICE if app.ui_state.last_reasoning else TEXT)
        return Panel(body, title="Thinking", border_style=NEON if app.ui_state.last_reasoning else AMBER, style=f"on {SHADE}")

    def main_feedback_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        profile = app.ui_state.current_profile or {}
        health = self._health()
        recent_feedback = self._recent_feedback_entries(limit=3)
        feedback_lines = [
            f"T{item['turn_index']} {str(item['verdict']).upper()} :: {safe_excerpt(item['explanation'] or 'no explanation', limit=78)}"
            for item in reversed(recent_feedback)
        ]
        if not feedback_lines:
            feedback_lines = ["No feedback events yet. Review the last turn from the action menu or F7."]
        text = Text.from_markup(
            f"[bold {AMBER}]Feedback / Session State[/]\n"
            f"experiment={app.ui_state.experiment_name or app.ui_state.experiment_id or 'live-arming'}\n"
            f"observatory={(app.ui_state.observatory_status or {}).get('url', 'offline')}\n"
            f"graph=memes {health['memes']} memodes {health['memodes']} triadic {health['triadic_closure']:.3f}\n"
            f"profile={profile.get('profile_name', 'pending')} low_motion={app.runtime.settings.low_motion} debug={app.runtime.settings.debug}\n\n"
            f"last_status={safe_excerpt(app.ui_state.last_feedback, limit=170)}\n\n"
            "review rules: accept/reject need explanation; edit needs explanation plus corrected text\n"
            "feedback surfaces update regard, reward, risk, and edit channels\n\n"
            + "\n".join(feedback_lines)
        )
        return Panel(text, title="Feedback", border_style=AMBER, style=f"on {SHADE_ALT}")

    def main_chat_exchange_panel(self):
        transcript: list[Panel] = []
        for turn in self._recent_turns(limit=2):
            transcript.append(
                Panel(
                    Text(safe_excerpt(turn["user_text"], limit=180), style=TEXT),
                    title=f"Brian / T{turn['turn_index']}",
                    border_style=MUTED,
                    style=f"on {SHADE_ALT}",
                )
            )
            transcript.append(
                Panel(
                    Text(safe_excerpt(turn["membrane_text"], limit=260), style=TEXT),
                    title=f"Adam / T{turn['turn_index']}",
                    border_style=AMBER,
                    style=f"on {SHADE}",
                )
            )
        operator_live = self._composer_text().strip()
        if operator_live:
            transcript.append(
                Panel(
                    Text(safe_excerpt(operator_live, limit=220), style=TEXT),
                    title="Brian / Draft",
                    border_style=ROSE,
                    style=f"on {SHADE_ALT}",
                )
            )
        if not transcript:
            transcript.append(
                Panel(
                    Text("Live deck armed. No turns yet. Compose in the lower field and send with Ctrl+S.", style=MUTED),
                    title="Chat Deck",
                    border_style=AMBER,
                    style=f"on {SHADE}",
                )
            )
        return Group(*transcript)

    def main_feedback_loop_panel(self) -> Panel:
        state, latest_entry = self._feedback_loop_state()
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if state == "reviewed" and latest_entry is not None:
            verdict = str(latest_entry.get("verdict", "skip")).upper()
            border = NEON if verdict == "ACCEPT" else ROSE if verdict == "EDIT" else EMBER if verdict == "REJECT" else AMBER
            text = Text.from_markup(
                f"[bold {AMBER}]Feedback loop[/]\n"
                f"latest verdict={verdict} for T{latest_entry.get('turn_index', '?')} at {latest_entry.get('created_at', 'n/a')}\n"
                f"explanation={safe_excerpt(latest_entry.get('explanation') or 'none', limit=180)}\n"
                "F7 reopens structured review if you want to reinforce or revise this judgment."
            )
            return Panel(text, title="Chat Feedback", border_style=border, style=f"on {SHADE_ALT}")
        if state == "pending":
            text = Text.from_markup(
                f"[bold {AMBER}]Feedback loop[/]\n"
                f"Adam / T{app.ui_state.last_turn_id or 'latest'} is awaiting operator judgment.\n"
                "Use F7 or the action menu to review this turn.\n"
                "Accept / Reject need explanation. Edit needs explanation plus corrected text."
            )
            return Panel(text, title="Chat Feedback", border_style=ROSE, style=f"on {SHADE_ALT}")
        text = Text.from_markup(
            f"[bold {AMBER}]Feedback loop[/]\n"
            "No turn needs review yet.\n"
            "Once Adam answers, this strip will show whether the turn is pending review or already judged."
        )
        return Panel(text, title="Chat Feedback", border_style=AMBER, style=f"on {SHADE_ALT}")

    def main_composer_hint_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        draft = self._composer_text().strip()
        state = "draft-loaded" if draft else "idle"
        text = Text.from_markup(
            f"[bold {AMBER}]Composer[/]\n"
            f"state={state} chars={len(draft)} backend={self._active_backend_label()}\n"
            "Ctrl+S send | Shift+Tab action menu | F6 deck | F7 review"
        )
        return Panel(text, title="Transmit", border_style=AMBER, style=f"on {SHADE_ALT}")

    def deck_summary_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        model_status = self._model_status()
        text = Text.from_markup(
            f"[bold {AMBER}]Deck / Detailed Surfaces[/]\n"
            "Budget, thinking, history, ingest, and launch controls live here; the prime surface now keeps the aperture visible.\n\n"
            f"runtime={app.runtime.settings.model_backend}\n"
            f"model={model_status.get('label', 'n/a')}\n"
            f"cache={model_status.get('stage', 'n/a')}\n"
            f"session={app.ui_state.session_title or app.ui_state.session_id or 'none'}"
        )
        return Panel(text, title="Operator Deck", border_style=AMBER)

    def deck_budget_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        return Panel(
            self._budget_text(app.ui_state.current_profile or {}, app.ui_state.current_budget or {}),
            title="Inference Circumstances / Budget",
            border_style=AMBER,
        )

    def deck_telemetry_panel(self) -> Panel:
        health = self._health()
        text = Text.from_markup(
            f"[bold {AMBER}]Graph Health[/]\n"
            f"memes={health['memes']} memodes={health['memodes']} edges={health['edges']}\n"
            f"turns={health['turns']} feedback={health['feedback']} docs={health['documents']}\n"
            f"triadic_closure={health['triadic_closure']:.3f}\n"
            f"dyad_ratio={health['dyad_ratio']:.3f}\n"
            f"memode_coverage={health['memode_coverage']:.3f}\n"
            f"isolated_count={health['isolated_count']:.0f}"
        )
        return Panel(text, title="Telemetry / Graph Stats", border_style=AMBER)

    def deck_history_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        history = app.runtime.store.summarize_history(app.ui_state.session_id, limit=6) if app.ui_state.session_id else []
        text = Text.from_markup(f"[bold {AMBER}]Recent Turns[/]\n" + ("\n".join(history) if history else "No turns yet."))
        return Panel(text, title="Bounded History", border_style=AMBER)

    def deck_thinking_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        reasoning_text = safe_excerpt(app.ui_state.last_reasoning, limit=1200) if app.ui_state.last_reasoning else "No model-emitted thinking yet."
        reasoning_style = TEXT if app.ui_state.last_reasoning else MUTED
        return Panel(Text(reasoning_text, style=reasoning_style), title="Qwen Thinking / Reasoning", border_style=AMBER)

    def deck_active_set_panel(self) -> Panel:
        active_lines = []
        for item in self._active_items()[:10]:
            active_lines.append(
                f"{item['label']} [{item['domain']}] sel={item['selection']:.2f} reg={item['regard']:.2f}"
            )
        active_label = "Aperture / Active Set (Preview)" if self._composer_text().strip() else "Aperture / Active Set"
        text = Text.from_markup(f"[bold {AMBER}]Active Set[/]\n" + ("\n".join(active_lines) if active_lines else "No active set yet."))
        return Panel(text, title=active_label, border_style=AMBER)

    def deck_trace_panel(self) -> Panel:
        trace_lines = []
        for item in self._trace_items()[:12]:
            trace_lines.append(
                f"{item['label']} :: sel={item['selection']:.2f} sim={item['semantic_similarity']:.2f} act={item['activation']:.2f}"
            )
        trace_text = Text.from_markup(
            f"[bold {AMBER}]Decision Trace[/]\n"
            "Operator-visible retrieval, regard, budget, and membrane surfaces only.\n\n"
            + ("\n".join(trace_lines) if trace_lines else "No trace yet.")
        )
        return Panel(trace_text, title="Cogitation / Decision Trace", border_style=AMBER)

    def deck_status_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        text = Text.from_markup(
            f"[bold {AMBER}]Deck Status[/]\n"
            f"observatory={(app.ui_state.observatory_status or {}).get('url', 'offline')}\n"
            f"low_motion={app.runtime.settings.low_motion} debug={app.runtime.settings.debug}\n"
            f"feedback={safe_excerpt(app.ui_state.last_feedback, limit=180)}"
        )
        return Panel(text, title="Status", border_style=AMBER)

    def _budget_text(self, profile: dict[str, Any], budget: dict[str, Any]) -> Text:
        if not profile or not budget:
            return Text.from_markup(
                f"[bold {AMBER}]Awaiting budget preview[/]\n"
                "Type in the composer or start a turn preview to see live prompt-budget conditions."
            )
        reasons = budget.get("change_reasons", [])[:4]
        reason_text = "\n".join(f"- {item}" for item in reasons) if reasons else "- No recent change."
        return Text.from_markup(
            f"[bold {AMBER}]profile[/] {profile.get('profile_name', 'n/a')}\n"
            f"mode={profile.get('requested_mode', 'n/a')} -> {profile.get('effective_mode', 'n/a')}\n"
            f"retrieval_depth={profile.get('retrieval_depth', 'n/a')} max_context_items={profile.get('max_context_items', 'n/a')}\n"
            f"reserved_output={budget.get('reserved_output_tokens', 'n/a')} tok response_char_cap={profile.get('response_char_cap', 'n/a')}\n"
            f"prompt_budget={budget.get('prompt_budget_tokens', 'n/a')} tok context_window={budget.get('context_window_tokens', 'n/a')} tok\n"
            f"user={budget.get('user_tokens', 'n/a')} tok / {budget.get('user_chars', 'n/a')} chars\n"
            f"remaining_input={budget.get('remaining_input_tokens', 'n/a')} tok / {budget.get('remaining_input_chars', 'n/a')} chars\n"
            f"count_method={budget.get('count_method', 'n/a')}\n"
            f"active_set={budget.get('active_set_tokens', 'n/a')} tok history={budget.get('history_tokens', 'n/a')} tok feedback={budget.get('feedback_tokens', 'n/a')} tok\n"
            f"pressure={budget.get('pressure_level', 'n/a')} ratio={budget.get('pressure_ratio', 'n/a')}\n\n"
            f"[bold {AMBER}]Allowance changes[/]\n{reason_text}"
        )

    def _poll_logs(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        events = app.runtime.runtime_log.recent(200)
        widget = self.query_one("#forensic_log", RichLog)
        for event in events[self._seen_log_count :]:
            widget.write(f"[{event.level}] {event.event} :: {event.message} {event.payload}")
        self._seen_log_count = len(events)

    def _composer_text(self) -> str:
        return self.query_one("#composer_input", TextArea).text

    def _set_text_area(self, selector: str, value: str) -> None:
        self.query_one(selector, TextArea).load_text(value)

    def _schedule_preview_refresh(self) -> None:
        if not self.app.ui_state.session_id:
            return
        self._preview_generation += 1
        generation = self._preview_generation
        if self._preview_task is not None and not self._preview_task.done():
            self._preview_task.cancel()
        self._preview_task = asyncio.create_task(self._refresh_preview(generation))

    async def _refresh_preview(self, generation: int) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        await asyncio.sleep(0.22)
        if generation != self._preview_generation or not app.ui_state.session_id:
            return
        user_text = self._composer_text().strip()
        preview = await asyncio.to_thread(
            partial(
                app.runtime.preview_turn,
                session_id=app.ui_state.session_id,
                user_text=user_text,
                previous_budget=app.ui_state.current_budget,
            )
        )
        if generation != self._preview_generation:
            return
        app.ui_state.current_profile = preview.profile
        app.ui_state.current_budget = preview.budget
        if user_text:
            app.ui_state.preview_active_set = preview.active_set
            app.ui_state.preview_trace = preview.trace
        else:
            app.ui_state.preview_active_set = app.ui_state.last_active_set
            app.ui_state.preview_trace = app.ui_state.last_trace
        self.refresh_panels()

    @on(TextArea.Changed, "#composer_input")
    def handle_composer_changed(self, _event) -> None:
        self.refresh_panels()
        self._schedule_preview_refresh()

    async def _send_turn(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        text = self._composer_text().strip()
        if not text or not app.ui_state.session_id:
            return
        if not await self._ensure_backend_ready(prepare=True):
            return
        outcome = await asyncio.to_thread(partial(app.runtime.chat, session_id=app.ui_state.session_id, user_text=text))
        app.ui_state.last_turn_id = outcome.turn["id"]
        app.ui_state.last_user_text = text
        app.ui_state.last_response = outcome.turn["membrane_text"]
        app.ui_state.last_reasoning = outcome.reasoning_text
        app.ui_state.last_active_set = outcome.active_set
        app.ui_state.last_trace = outcome.trace
        app.ui_state.preview_active_set = outcome.active_set
        app.ui_state.preview_trace = outcome.trace
        app.ui_state.current_budget = outcome.budget
        app.ui_state.current_profile = outcome.profile
        app.ui_state.last_feedback = f"Saved turn T{outcome.turn['turn_index']} from Brian the operator."
        self._write_forensic(
            f"[INFO] Turn T{outcome.turn['turn_index']} stored :: active_set={len(outcome.active_set)} pressure={outcome.budget.get('pressure_level', 'n/a')}"
        )
        self._set_text_area("#composer_input", "")
        self.refresh_panels()
        self._schedule_preview_refresh()

    async def submit_feedback(self, verdict: str, *, explanation: str, corrected: str) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.last_turn_id or not app.ui_state.session_id:
            app.ui_state.last_feedback = "No turn available for feedback."
            self.refresh_panels()
            return
        try:
            feedback = await asyncio.to_thread(
                partial(
                    app.runtime.apply_feedback,
                    session_id=app.ui_state.session_id,
                    turn_id=app.ui_state.last_turn_id,
                    verdict=verdict,
                    explanation=explanation,
                    corrected_text=corrected,
                )
            )
        except Exception as exc:
            app.ui_state.last_feedback = f"{verdict.upper()} failed: {exc}"
        else:
            app.ui_state.last_feedback = f"{feedback['verdict'].upper()} recorded at {feedback['created_at']}."
            self._schedule_preview_refresh()
        self.refresh_panels()

    async def ingest_path(self, path: str) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.experiment_id:
            return
        if not path:
            return
        await asyncio.to_thread(partial(app.runtime.ingest_document, experiment_id=app.ui_state.experiment_id, path=path))
        app.ui_state.last_feedback = f"Ingested document path: {path}"
        self.refresh_panels()
        self._schedule_preview_refresh()

    async def handle_export(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.experiment_id:
            return
        paths = await asyncio.to_thread(
            partial(app.runtime.export_observability, experiment_id=app.ui_state.experiment_id, session_id=app.ui_state.session_id)
        )
        names = [Path(paths[key]).name for key in ("graph_html", "basin_html", "geometry_html") if key in paths]
        app.ui_state.last_feedback = f"Exports generated: {', '.join(names)}"
        self._write_forensic(f"[INFO] Exports generated :: {', '.join(names)}")
        self.refresh_panels()

    async def handle_observatory(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        status = await asyncio.to_thread(partial(app.runtime.start_observatory, reuse_existing=True))
        app.ui_state.observatory_status = status
        target_url = _observatory_target_url(app.runtime, status, app.ui_state.experiment_id)
        webbrowser.open(target_url)
        app.ui_state.last_feedback = (
            f"Observatory {'reused' if status['reused_existing'] else 'started'} at {target_url}"
        )
        self._write_forensic(
            f"[INFO] Observatory {'reused' if status['reused_existing'] else 'started'} :: {target_url}"
        )
        self.refresh_panels()

    async def handle_review(self) -> None:
        await self.app.push_screen(FeedbackModal(self))

    async def handle_deck(self) -> None:
        await self.app.push_screen(DeckModal(self))

    async def _new_session_worker(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.experiment_id:
            return
        defaults = app.runtime.default_session_profile_request().to_dict()
        if app.ui_state.session_id:
            defaults.update(await asyncio.to_thread(partial(app.runtime.session_profile_request, app.ui_state.session_id)))
        payload = await app.push_screen_wait(
            SessionConfigModal(
                defaults,
                title_text="New Session Inference Profile",
                action_label="Open Session",
            )
        )
        if payload is None:
            return
        session = await asyncio.to_thread(
            partial(
                app.runtime.start_session,
                app.ui_state.experiment_id,
                title=payload["title"],
                profile_request=payload,
            )
        )
        app.apply_session_snapshot(
            {
                "experiment_id": app.ui_state.experiment_id,
                "experiment_name": app.ui_state.experiment_name,
                "session_id": session["id"],
                "session_title": session["title"],
                "last_turn_id": None,
                "last_user_text": "",
                "last_response": "",
                "last_reasoning": "",
                "last_active_set": [],
                "last_trace": [],
                "current_budget": None,
                "current_profile": None,
            }
        )
        app.ui_state.last_feedback = "Opened a new session."
        self._set_text_area("#composer_input", "")
        self.refresh_panels()
        self._schedule_preview_refresh()

    def begin_new_session_flow(self) -> None:
        self.run_worker(self._new_session_worker(), exclusive=True, group="session")

    async def _edit_profile_worker(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.session_id:
            return
        defaults = await asyncio.to_thread(partial(app.runtime.session_profile_request, app.ui_state.session_id))
        defaults["title"] = app.ui_state.session_title or defaults.get("title", "Current Session")
        payload = await app.push_screen_wait(
            SessionConfigModal(
                defaults,
                title_text="Adjust Session Profile",
                action_label="Apply Profile",
                show_title_input=False,
            )
        )
        if payload is None:
            return
        updated = await asyncio.to_thread(
            partial(
                app.runtime.update_session_profile_request,
                app.ui_state.session_id,
                mode=payload["mode"],
                budget_mode=payload["budget_mode"],
                low_motion=payload["low_motion"],
                debug=payload["debug"],
                temperature=payload["temperature"],
                max_output_tokens=payload["max_output_tokens"],
                top_p=payload["top_p"],
                repetition_penalty=payload["repetition_penalty"],
                retrieval_depth=payload["retrieval_depth"],
                max_context_items=payload["max_context_items"],
                response_char_cap=payload["response_char_cap"],
            )
        )
        app.ui_state.last_feedback = (
            f"Updated session profile: {updated['mode']} / {updated['budget_mode']} / low_motion={updated['low_motion']}"
        )
        self.refresh_panels()
        self._schedule_preview_refresh()

    def begin_edit_profile_flow(self) -> None:
        self.run_worker(self._edit_profile_worker(), exclusive=True, group="profile")

    async def _launch_surface_worker(self, action: str) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if action == "resume":
            latest = app.runtime.store.get_latest_experiment()
            if latest is None:
                app.ui_state.last_feedback = "No experiment available to resume."
                self.refresh_panels()
                return
            latest_session = app.runtime.store.get_latest_session(latest["id"])
            if latest_session is None:
                app.ui_state.last_feedback = "Latest experiment has no saved session yet."
                self.refresh_panels()
                return
            snapshot = await asyncio.to_thread(partial(app.runtime.session_state_snapshot, latest_session["id"]))
            app.apply_session_snapshot(snapshot)
            app.ui_state.last_feedback = f"Resumed {snapshot['session_title']}."
            self._write_forensic(f"[INFO] Resumed session :: {snapshot['session_title']}")
            self._set_text_area("#composer_input", "")
            self.refresh_panels()
            self._schedule_preview_refresh()
            return
        defaults = app.runtime.default_session_profile_request().to_dict()
        payload = await app.push_screen_wait(
            SessionConfigModal(
                defaults,
                title_text=f"{action.title()} Experiment Session",
                action_label="Open Session",
            )
        )
        if payload is None:
            return
        experiment = await asyncio.to_thread(partial(app.runtime.initialize_experiment, action))
        session = await asyncio.to_thread(
            partial(
                app.runtime.start_session,
                experiment["id"],
                title=payload["title"],
                profile_request=payload,
            )
        )
        app.apply_session_snapshot(
            {
                "experiment_id": experiment["id"],
                "experiment_name": experiment["name"],
                "session_id": session["id"],
                "session_title": session["title"],
                "last_turn_id": None,
                "last_user_text": "",
                "last_response": "",
                "last_reasoning": "",
                "last_active_set": [],
                "last_trace": [],
                "current_profile": None,
                "current_budget": None,
            }
        )
        app.ui_state.last_feedback = f"Opened a new {action} experiment session."
        self._write_forensic(f"[INFO] Opened {action} experiment :: {session['title']}")
        self._set_text_area("#composer_input", "")
        self.refresh_panels()
        self._schedule_preview_refresh()

    def begin_surface_launch(self, action: str) -> None:
        self.run_worker(self._launch_surface_worker(action), exclusive=True, group=f"surface_{action}")

    async def toggle_motion(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.session_id:
            return
        current = await asyncio.to_thread(partial(app.runtime.session_profile_request, app.ui_state.session_id))
        updated = await asyncio.to_thread(
            partial(app.runtime.update_session_profile_request, app.ui_state.session_id, low_motion=not current.get("low_motion", False))
        )
        app.ui_state.last_feedback = f"low_motion={updated['low_motion']}"
        self._schedule_preview_refresh()
        self.refresh_panels()

    async def toggle_debug(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.session_id:
            return
        current = await asyncio.to_thread(partial(app.runtime.session_profile_request, app.ui_state.session_id))
        updated = await asyncio.to_thread(
            partial(app.runtime.update_session_profile_request, app.ui_state.session_id, debug=not current.get("debug", True))
        )
        app.ui_state.last_feedback = f"debug={updated['debug']}"
        self._schedule_preview_refresh()
        self.refresh_panels()

    async def handle_motion(self) -> None:
        await self.toggle_motion()

    async def handle_debug(self) -> None:
        await self.toggle_debug()

    async def handle_help(self) -> None:
        await self.app.push_screen(HelpModal())

    def handle_prepare_mlx(self) -> None:
        self.run_worker(self._ensure_backend_ready(prepare=True), exclusive=True, group="prepare_mlx")

    def _execute_runtime_action(self, action: str) -> None:
        normalized = (action or "review").strip().lower()
        if normalized in {"blank", "seeded", "resume"}:
            self.begin_surface_launch(normalized)
        elif normalized == "new_session":
            self.begin_new_session_flow()
        elif normalized == "profile":
            self.begin_edit_profile_flow()
        elif normalized == "review":
            self.run_worker(self.handle_review(), exclusive=True, group="review")
        elif normalized == "prepare_mlx":
            self.handle_prepare_mlx()
        elif normalized == "observatory":
            self.run_worker(self.handle_observatory(), exclusive=True, group="observatory")
        elif normalized == "export":
            self.run_worker(self.handle_export(), exclusive=True, group="export")
        elif normalized == "deck":
            self.run_worker(self.handle_deck(), exclusive=True, group="deck")
        elif normalized == "help":
            self.run_worker(self.handle_help(), exclusive=True, group="help")

    @on(Select.Changed, "#runtime_action_menu")
    def handle_runtime_action_changed(self, _event: Select.Changed) -> None:
        self.query_one("#runtime_status_strip", Static).update(self.main_action_status_panel())

    def on_key(self, event) -> None:
        if event.key == "enter" and self.app.focused and getattr(self.app.focused, "id", None) == "runtime_action_menu":
            action = str(self.query_one("#runtime_action_menu", Select).value or "review")
            self._execute_runtime_action(action)
            event.stop()


class EdenTuiApp(App):
    CSS = f"""
    Screen {{
        background: {BG};
        color: {TEXT};
    }}
    #runtime_frame {{
        height: 1fr;
    }}
    #startup_frame {{
        height: 1fr;
    }}
    #runtime_topbar {{
        height: 8;
        padding: 0 1 1 1;
    }}
    #startup_topbar {{
        height: 8;
        padding: 0 1 1 1;
    }}
    #runtime_action_menu, #startup_action_menu {{
        width: 32;
        margin-right: 1;
    }}
    #runtime_status_strip, #startup_menu_hint {{
        width: 1fr;
    }}
    #startup_action_menu {{
        width: 32;
    }}
    #startup_shell, #chat_shell {{
        height: 1fr;
        layout: horizontal;
        padding: 1 1;
    }}
    #startup_left, #chat_left {{
        width: 38%;
        min-width: 44;
        padding-right: 1;
    }}
    #startup_right, #chat_right {{
        width: 62%;
        min-width: 66;
        padding-left: 1;
    }}
    #startup_aperture_panel, #active_aperture_panel {{
        height: 1fr;
        min-height: 16;
    }}
    #thinking_panel {{
        height: 1fr;
        min-height: 16;
    }}
    #feedback_panel, #startup_reasoning_panel {{
        height: 1fr;
        min-height: 13;
    }}
    #chat_deck, #startup_cockpit_stack {{
        border: tall {AMBER};
        background: {PANEL};
        padding: 0 1;
    }}
    #startup_cockpit_stack {{
        height: 1fr;
        min-height: 18;
    }}
    #signal_field {{
        height: 16;
        min-height: 15;
    }}
    #chat_instrument_row {{
        height: 1fr;
        min-height: 13;
        padding: 0 0 1 0;
    }}
    #signal_field {{
        width: 1fr;
        min-width: 32;
    }}
    #ritual_panel {{
        width: 38%;
        min-width: 30;
        margin-right: 1;
    }}
    #startup_cockpit {{
        height: 1fr;
        min-height: 12;
    }}
    #startup_log {{
        height: 10;
    }}
    #startup_transcript_panel {{
        height: 18;
    }}
    #chat_deck {{
        height: 1fr;
        min-height: 22;
    }}
    #chat_exchange_panel {{
        height: 1fr;
        margin-bottom: 1;
    }}
    #feedback_loop_panel {{
        height: 7;
    }}
    #composer_input {{
        height: 6;
        background: #060403;
        border: tall {AMBER};
        color: {TEXT};
    }}
    #composer_hint_panel {{
        height: 5;
    }}
    #review_explanation_input, #review_corrected_input {{
        height: 6;
        background: #060403;
        border: tall {AMBER};
        color: {TEXT};
    }}
    #forensic_log {{
        height: 1fr;
        border: tall {ICE};
        color: {ICE};
        width: 62%;
        min-width: 36;
    }}
    Static, Input, RichLog, Select, TextArea {{
        margin-bottom: 1;
    }}
    Input, Select {{
        background: {PANEL};
        border: tall {AMBER};
        color: {TEXT};
    }}
    Button {{
        margin-right: 1;
        background: #201208;
        color: {TEXT};
    }}
    RichLog {{
        background: #060403;
        border: tall {AMBER};
        color: {TEXT};
    }}
    #deck_shell, #session_config_shell {{
        padding: 1 1;
    }}
    .deck_column, .session_config_column {{
        width: 1fr;
        padding: 0 1;
    }}
    #deck_summary, #review_summary, #session_config_header, #session_config_summary {{
        margin: 1 2;
    }}
    #deck_status_panel {{
        height: 1fr;
    }}
    #session_config_shell {{
        padding: 1 1;
    }}
    """
    BINDINGS = [
        Binding("tab", "focus_next", "", show=False),
        Binding("shift+tab", "focus_previous", "", show=False),
        ("f1", "show_help", "Help"),
        ("ctrl+s", "send_turn", "Send"),
        ("f2", "export_all", "Export"),
        ("f3", "toggle_observatory", "Observatory"),
        ("f4", "toggle_motion", "Motion"),
        ("f5", "new_session", "New Session"),
        ("f6", "show_deck", "Deck"),
        ("f7", "show_review", "Review"),
    ]

    def __init__(self, runtime: EdenRuntime) -> None:
        super().__init__()
        self.runtime = runtime
        self.repo_root = Path(__file__).resolve().parents[2]
        self.ui_state = UiState()

    def apply_session_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.ui_state.experiment_id = snapshot["experiment_id"]
        self.ui_state.experiment_name = snapshot.get("experiment_name")
        self.ui_state.session_id = snapshot["session_id"]
        self.ui_state.session_title = snapshot.get("session_title")
        self.ui_state.last_turn_id = snapshot.get("last_turn_id")
        self.ui_state.last_user_text = snapshot.get("last_user_text", "")
        self.ui_state.last_response = snapshot.get("last_response", "")
        self.ui_state.last_reasoning = snapshot.get("last_reasoning", "")
        self.ui_state.last_active_set = list(snapshot.get("last_active_set") or [])
        self.ui_state.last_trace = list(snapshot.get("last_trace") or [])
        self.ui_state.preview_active_set = list(snapshot.get("last_active_set") or [])
        self.ui_state.preview_trace = list(snapshot.get("last_trace") or [])
        self.ui_state.current_profile = snapshot.get("current_profile")
        self.ui_state.current_budget = snapshot.get("current_budget")

    async def on_mount(self) -> None:
        await self.push_screen(ChatScreen())

    async def action_show_help(self) -> None:
        await self.push_screen(HelpModal())

    async def action_show_deck(self) -> None:
        if isinstance(self.screen, ChatScreen):
            await self.screen.handle_deck()

    async def action_show_review(self) -> None:
        if isinstance(self.screen, ChatScreen):
            await self.screen.handle_review()

    async def action_send_turn(self) -> None:
        if isinstance(self.screen, ChatScreen):
            await self.screen._send_turn()

    async def action_export_all(self) -> None:
        if isinstance(self.screen, ChatScreen):
            await self.screen.handle_export()

    async def action_toggle_observatory(self) -> None:
        if isinstance(self.screen, ChatScreen):
            await self.screen.handle_observatory()

    async def action_toggle_motion(self) -> None:
        if isinstance(self.screen, ChatScreen):
            await self.screen.handle_motion()

    async def action_new_session(self) -> None:
        if isinstance(self.screen, ChatScreen):
            self.screen.begin_new_session_flow()


def run_tui(runtime: EdenRuntime) -> None:
    EdenTuiApp(runtime).run()
