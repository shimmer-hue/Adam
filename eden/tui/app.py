from __future__ import annotations

import asyncio
import json
import math
import re
from time import monotonic
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, RichLog, Select, Static, TextArea

from ..browser import open_browser_url
from ..inference import request_from_dict
from ..runtime import EdenRuntime
from ..utils import safe_excerpt


@dataclass(frozen=True, slots=True)
class LookPalette:
    label: str
    amber: str
    text: str
    muted: str
    bg: str
    panel: str
    shade: str
    shade_alt: str
    neon: str
    ice: str
    rose: str
    ember: str
    violet: str
    marble_dark: str
    marble_light: str
    chiaro_shadow: str
    chiaro_bronze: str
    chiaro_wine: str
    chiaro_slate: str


LOOK_PALETTES: dict[str, LookPalette] = {
    "amber_dark": LookPalette(
        label="Amber Dark",
        amber="#ffd98a",
        text="#fff1d2",
        muted="#e6ab5a",
        bg="#12080a",
        panel="#211014",
        shade="#1a0d12",
        shade_alt="#27121c",
        neon="#84ffd0",
        ice="#8ddcff",
        rose="#ff7ad7",
        ember="#ffae57",
        violet="#a890ff",
        marble_dark="#160a14",
        marble_light="#351629",
        chiaro_shadow="#10070a",
        chiaro_bronze="#21100f",
        chiaro_wine="#22101a",
        chiaro_slate="#101622",
    ),
    "typewriter_light": LookPalette(
        label="Typewriter Light",
        amber="#6f5335",
        text="#2b2217",
        muted="#756451",
        bg="#f4eddc",
        panel="#eadfc7",
        shade="#efe4cf",
        shade_alt="#e5d8c1",
        neon="#2f6d5e",
        ice="#486276",
        rose="#9a4e47",
        ember="#8d5d2c",
        violet="#6b608f",
        marble_dark="#d8ccb5",
        marble_light="#fbf7ef",
        chiaro_shadow="#f7f0e1",
        chiaro_bronze="#ede0ca",
        chiaro_wine="#ead8cd",
        chiaro_slate="#dde4e7",
    ),
}

LOOK_OPTIONS = [(palette.label, key) for key, palette in LOOK_PALETTES.items()]
LOOK_LABELS = {key: palette.label for key, palette in LOOK_PALETTES.items()}
LOOK_CLASSES = {key: f"look-{key.replace('_', '-')}" for key in LOOK_PALETTES}


def _normalize_ui_look(value: Any) -> str:
    normalized = str(value or "amber_dark").strip().lower()
    return normalized if normalized in LOOK_PALETTES else "amber_dark"


def _apply_look_palette(look: str) -> LookPalette:
    palette = LOOK_PALETTES[_normalize_ui_look(look)]
    globals().update(
        {
            "AMBER": palette.amber,
            "TEXT": palette.text,
            "MUTED": palette.muted,
            "BG": palette.bg,
            "PANEL": palette.panel,
            "SHADE": palette.shade,
            "SHADE_ALT": palette.shade_alt,
            "NEON": palette.neon,
            "ICE": palette.ice,
            "ROSE": palette.rose,
            "EMBER": palette.ember,
            "VIOLET": palette.violet,
            "MARBLE_DARK": palette.marble_dark,
            "MARBLE_LIGHT": palette.marble_light,
            "CHIARO_SHADOW": palette.chiaro_shadow,
            "CHIARO_BRONZE": palette.chiaro_bronze,
            "CHIARO_WINE": palette.chiaro_wine,
            "CHIARO_SLATE": palette.chiaro_slate,
        }
    )
    return palette


_apply_look_palette("amber_dark")
TYPEWRITER_LIGHT = LOOK_PALETTES["typewriter_light"]

ACTION_MENU_OPTIONS = [
    ("Toggle Aperture Drawer", "toggle_aperture"),
    ("Toggle Runtime Chyron", "toggle_chyron"),
    ("Ingest PDF / Doc", "ingest_pdf"),
    ("Review Last Reply", "review"),
    ("Open Conversation Log", "conversation_log"),
    ("Open Conversation Atlas", "archive"),
    ("Tune Session", "profile"),
    ("Start New Session", "new_session"),
    ("Continue Latest", "resume"),
    ("Start Blank Eden", "blank"),
    ("Start Seeded Eden", "seeded"),
    ("Prepare Local Model", "prepare_mlx"),
    ("Open Browser Observatory", "observatory"),
    ("Export Artifacts", "export"),
    ("Open Utilities Deck", "deck"),
    ("Help", "help"),
]

ACTION_MENU_LABELS = {value: label for label, value in ACTION_MENU_OPTIONS}
ACTION_STRIP_OPTIONS = [
    ("Review Last Reply", "review"),
    ("Open Conversation Log", "conversation_log"),
    ("Open Conversation Atlas", "archive"),
    ("Tune Session", "profile"),
    ("Start New Session", "new_session"),
    ("Continue Latest", "resume"),
    ("Start Blank Eden", "blank"),
    ("Start Seeded Eden", "seeded"),
    ("Prepare Local Model", "prepare_mlx"),
    ("Open Browser Observatory", "observatory"),
    ("Export Artifacts", "export"),
    ("Open Utilities Deck", "deck"),
    ("Help", "help"),
    ("Ingest PDF / Doc", "ingest_pdf"),
    ("Toggle Aperture Drawer", "toggle_aperture"),
    ("Toggle Runtime Chyron", "toggle_chyron"),
]
ACTION_STRIP_INDEX = {value: index for index, (_, value) in enumerate(ACTION_STRIP_OPTIONS)}
ACTION_STRIP_NUMBER = {value: index + 1 for index, (_, value) in enumerate(ACTION_STRIP_OPTIONS)}

ARCHIVE_SORT_OPTIONS = [
    ("Recently Updated", "updated_desc"),
    ("Oldest Updated", "updated_asc"),
    ("Title A-Z", "title_asc"),
    ("Most Turns", "turns_desc"),
    ("Folder A-Z", "folder_asc"),
    ("Experiment A-Z", "experiment_asc"),
]

ARCHIVE_GROUP_OPTIONS = [
    ("All Texts", "all_texts"),
    ("Folders", "folder"),
    ("Tags", "tag"),
    ("Experiments", "experiment"),
    ("Modes", "mode"),
]


def _observatory_target_url(runtime: EdenRuntime, status: dict[str, Any], experiment_id: str | None) -> str:
    if not experiment_id:
        return status["url"]
    return status["url"] + f"{experiment_id}/observatory_index.html"


@dataclass(slots=True)
class UiState:
    experiment_id: str | None = None
    experiment_name: str | None = None
    session_id: str | None = None
    session_title: str | None = None
    aperture_drawer_open: bool = False
    runtime_chyron_open: bool = False
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
    last_ingest_result: dict[str, Any] | None = None
    observatory_status: dict[str, Any] | None = None
    current_budget: dict[str, Any] | None = None
    current_profile: dict[str, Any] | None = None
    current_graph_health: dict[str, Any] | None = None
    conversation_log_path: str | None = None
    action_progress: dict[str, Any] | None = None
    last_action_summary: str | None = None
    reasoning_mode: str = "reasoning"
    turn_progress: dict[str, Any] | None = None


class ReviewTextArea(TextArea):
    @dataclass
    class Submitted(Message):
        textarea: "ReviewTextArea"
        value: str

        @property
        def control(self) -> "ReviewTextArea":
            return self.textarea

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            self.post_message(self.Submitted(self, self.text))
            return
        if event.key == "shift+enter":
            event.stop()
            event.prevent_default()
            self._replace_via_keyboard("\n", *self.selection)
            return
        await super()._on_key(event)


class ComposerTextArea(TextArea):
    @dataclass
    class Submitted(Message):
        textarea: "ComposerTextArea"
        value: str

        @property
        def control(self) -> "ComposerTextArea":
            return self.textarea

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            event.prevent_default()
            self.post_message(self.Submitted(self, self.text))
            return
        if event.key == "shift+enter":
            event.stop()
            event.prevent_default()
            self._replace_via_keyboard("\n", *self.selection)
            return
        await super()._on_key(event)


class ActionStrip(Static):
    can_focus = True

    @dataclass
    class Changed(Message):
        strip: "ActionStrip"
        action: str

        @property
        def control(self) -> "ActionStrip":
            return self.strip

    @dataclass
    class Submitted(Message):
        strip: "ActionStrip"
        action: str

        @property
        def control(self) -> "ActionStrip":
            return self.strip

    def __init__(self, *, value: str = "review", id: str | None = None) -> None:
        super().__init__("", id=id)
        self._value = value if value in ACTION_STRIP_INDEX else ACTION_STRIP_OPTIONS[0][1]
        self._pending_digits = ""
        self._pending_digits_at = 0.0
        self._hitboxes: list[tuple[int, int, int, str]] = []
        self._status_line_count = 2

    @property
    def value(self) -> str:
        return self._value

    def on_mount(self) -> None:
        _sync_node_look(self)

    def on_focus(self, _event: events.Focus) -> None:
        self.refresh()

    def on_blur(self, _event: events.Blur) -> None:
        self._pending_digits = ""
        self.refresh()

    def set_value(self, value: str, *, notify: bool = False) -> None:
        normalized = (value or ACTION_STRIP_OPTIONS[0][1]).strip().lower()
        if normalized not in ACTION_STRIP_INDEX:
            return
        changed = normalized != self._value
        self._value = normalized
        self.refresh()
        if changed and notify:
            self.post_message(self.Changed(self, normalized))

    def _button_style(self, value: str) -> str:
        if value == self._value:
            return "bold #04161b on #98f4ff"
        return "bold #bff9ff on #103445"

    def _available_width(self) -> int:
        local_width = getattr(getattr(self, "size", None), "width", 0) or 0
        app_width = getattr(getattr(self, "app", None), "size", None)
        return max(32, local_width or getattr(app_width, "width", 120) or 120)

    def _button_label(self, value: str) -> str:
        label = ACTION_MENU_LABELS.get(value, value.replace("_", " "))
        return f"{ACTION_STRIP_NUMBER[value]:02d} {label}"

    def _button_width(self) -> int:
        return max(len(self._button_label(value)) for _, value in ACTION_STRIP_OPTIONS) + 2

    def _column_count(self, available_width: int) -> int:
        if available_width >= 132:
            return 3
        if available_width >= 82:
            return 2
        return 1

    def _button_rows(self, available_width: int) -> list[list[str]]:
        columns = self._column_count(available_width)
        values = [value for _, value in ACTION_STRIP_OPTIONS]
        return [values[index : index + columns] for index in range(0, len(values), columns)]

    def preferred_height(self, available_width: int) -> int:
        return len(self._button_rows(available_width)) + self._status_line_count + 1

    def _status_lines(self, available_width: int) -> list[tuple[str, str]]:
        app = getattr(self, "app", None)
        if app is None:
            return [
                ("digits jump | left/right move | Enter runs | click runs", ICE),
                ("runtime surface arming...", MUTED),
            ]
        screen = getattr(app, "screen", None)
        if screen and hasattr(screen, "action_strip_status_lines"):
            return screen.action_strip_status_lines(available_width)
        return [
            ("digits jump | left/right move | Enter runs | click runs", ICE if self.has_focus else TEXT),
            ("runtime surface arming...", MUTED),
        ]

    def _render_row(self, row_index: int, values: list[str], *, button_width: int) -> tuple[Text, list[tuple[int, int, int, str]]]:
        row = Text()
        hitboxes: list[tuple[int, int, int, str]] = []
        cursor = 0
        for index, value in enumerate(values):
            if index:
                separator = "  "
                row.append(separator, style=MUTED)
                cursor += len(separator)
            chip = f"[  {self._button_label(value):<{button_width}}  ]"
            start = cursor
            row.append(chip, style=self._button_style(value))
            cursor += len(chip)
            hitboxes.append((row_index, start, cursor, value))
        return row, hitboxes

    def render(self) -> Text:
        available_width = max(28, self._available_width() - 2)
        rows = self._button_rows(available_width)
        button_width = self._button_width()
        body = Text()
        self._hitboxes = []
        for row_index, row_values in enumerate(rows):
            row, hitboxes = self._render_row(row_index, row_values, button_width=button_width)
            if row_index:
                body.append("\n")
            body.append(row)
            self._hitboxes.extend(hitboxes)
        body.append("\n\n")
        for index, (line, style) in enumerate(self._status_lines(available_width)):
            if index:
                body.append("\n")
            body.append(line, style=style)
        return body

    def _select_relative(self, delta: int) -> None:
        current_index = ACTION_STRIP_INDEX.get(self._value, 0)
        next_index = (current_index + delta) % len(ACTION_STRIP_OPTIONS)
        self._pending_digits = ""
        self.set_value(ACTION_STRIP_OPTIONS[next_index][1], notify=True)

    def _accept_digit(self, digit: str) -> None:
        if not digit.isdigit():
            return
        now = monotonic()
        if (now - self._pending_digits_at) >= 1.2:
            self._pending_digits = ""
        candidate = f"{self._pending_digits}{digit}".lstrip("0")
        if not candidate:
            return
        number = int(candidate)
        if number < 1 or number > len(ACTION_STRIP_OPTIONS):
            candidate = digit
            number = int(candidate)
            if number < 1 or number > len(ACTION_STRIP_OPTIONS):
                return
        self._pending_digits = candidate
        self._pending_digits_at = now
        self.set_value(ACTION_STRIP_OPTIONS[number - 1][1], notify=True)

    def on_key(self, event: events.Key) -> None:
        if event.key == "left":
            self._select_relative(-1)
            event.stop()
            return
        if event.key == "right":
            self._select_relative(1)
            event.stop()
            return
        if event.key == "home":
            self._pending_digits = ""
            self.set_value(ACTION_STRIP_OPTIONS[0][1], notify=True)
            event.stop()
            return
        if event.key == "end":
            self._pending_digits = ""
            self.set_value(ACTION_STRIP_OPTIONS[-1][1], notify=True)
            event.stop()
            return
        if event.key == "backspace":
            self._pending_digits = ""
            self.refresh()
            event.stop()
            return
        if event.key == "enter":
            self._pending_digits = ""
            self.refresh()
            self.post_message(self.Submitted(self, self._value))
            event.stop()
            return
        if event.character and event.character.isdigit():
            self._accept_digit(event.character)
            event.stop()

    def on_click(self, event: events.Click) -> None:
        for row, start, end, value in self._hitboxes:
            if event.y == row and start <= event.x < end:
                self._pending_digits = ""
                self.set_value(value, notify=True)
                self.post_message(self.Submitted(self, value))
                event.stop()
                return


def _sync_node_look(node: Any) -> str:
    app = getattr(node, "app", None)
    runtime = getattr(app, "runtime", None)
    look = _normalize_ui_look(getattr(getattr(runtime, "settings", None), "ui_look", "amber_dark"))
    for class_name in LOOK_CLASSES.values():
        node.remove_class(class_name)
    node.add_class(LOOK_CLASSES[look])
    return look


def _format_elapsed(seconds: float) -> str:
    bounded = max(0.0, seconds)
    if bounded < 60:
        return f"{bounded:.1f}s"
    total_seconds = int(bounded)
    minutes, secs = divmod(total_seconds, 60)
    hours, mins = divmod(minutes, 60)
    if hours:
        return f"{hours}h{mins:02d}m{secs:02d}s"
    return f"{mins}m{secs:02d}s"


def _progress_bar(step: int, total: int, *, width: int = 12) -> str:
    bounded_total = max(total, 1)
    bounded_step = max(0, min(step, bounded_total))
    filled = min(width, math.floor((bounded_step / bounded_total) * width))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


class HelpModal(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        help_text = Text.from_markup(
            f"[bold {AMBER}]EDEN Controls[/]\n\n"
            "EDEN boots directly into a live dialogue surface.\n"
            "The top action strip keeps the runtime actions compact and always visible.\n"
            "Focus it with Tab, move with Left/Right, jump by typing the action number, and press Enter to run.\n"
            "F8 opens a full-width aperture drawer for a wider active-set scan.\n"
            "F9 opens the ingest bay so you can load a PDF or other document with a framing prompt.\n"
            "The large left column is the Adam dialogue: longer scrolling transcript tape and live composer.\n"
            "The right column stacks the memgraph bus, the aperture/active-set read, and a lower reasoning surface with chain-like and hum-live lenses.\n"
            "The runtime loop and session/event state live in a bottom-docked runtime/event chyron drawer that is hidden until pulled up.\n"
            "Use the action strip -> Open Conversation Log to open the saved markdown transcript for the live session.\n"
            "Use the action strip -> Open Conversation Atlas to browse saved sessions through folder and tag projections.\n"
            "Open Utilities Deck for detailed budget, thinking, history, ingest, launch utilities, and the UI look selector.\n"
            "Review Last Reply focuses the inline explicit-feedback controls inside the chat column.\n\n"
            "[bold]F1[/] help overlay\n"
            "[bold]Enter[/] send current input (or [bold]Ctrl+S[/] as a shortcut)\n"
            "[bold]F2[/] export graph, basin, and geometry artifacts\n"
            "[bold]F3[/] ensure observatory is running and open the current export surface\n"
            "[bold]F4[/] toggle low motion for the current session request\n"
            "[bold]F5[/] open the new-session inference-profile flow\n"
            "[bold]F6[/] open the operator deck\n"
            "[bold]F7[/] focus inline review for Adam's latest reply\n"
            "[bold]F8[/] toggle the narrower top-band aperture drawer\n"
            "[bold]F9[/] open document ingest with framing prompt\n"
            "[bold]F10[/] open the conversation atlas\n"
            "[bold]F11[/] toggle the runtime/event chyron drawer\n"
            "[bold]Esc[/] focus the composer on the main chat screen\n"
            "[bold]Esc[/] close this overlay\n\n"
            "Printable keys typed outside editable widgets are routed back into the composer automatically.\n"
            "When the backend emits explicit reasoning, EDEN surfaces it as a visible model artifact.\n"
            "That reasoning surface can render direct text, chain-like steps, or hum-live continuity, but it still does not claim hidden chain-of-thought.\n\n"
            "Inference modes:\n"
            "- MANUAL: operator-specified bounded parameters\n"
            "- RUNTIME_AUTO: deterministic transparent runtime policy\n"
            "- ADAM_AUTO: bounded preset choice; MLX currently falls back to runtime_auto and logs that fact\n\n"
            "Feedback rules:\n"
            "- Type A to accept, R to reject, E to edit, S to skip\n"
            "- Press Enter to advance or submit once the required fields are filled\n"
            "- Use Shift+Enter for a newline inside explanation or corrected-response fields\n"
            "- Accept and reject require explanation\n"
            "- Edit requires explanation and corrected response\n"
            "- Skip records a lightweight no-op verdict"
        )
        yield Static(Panel(help_text, title="Help", border_style=AMBER), id="help_panel")

    def on_mount(self) -> None:
        _sync_node_look(self)

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
        session_title_history: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.defaults = defaults
        self.title_text = title_text
        self.action_label = action_label
        self.show_title_input = show_title_input
        self.session_title_history = session_title_history or []

    def compose(self) -> ComposeResult:
        summary = Text.from_markup(
            f"[bold {AMBER}]{self.title_text}[/]\n"
            "Choose the inference-profile mode for this session. EDEN will persist the request at session creation and surface the resolved circumstances on later turns."
        )
        yield Static(Panel(summary, title="Session Start", border_style=AMBER), id="session_config_header")
        with Horizontal(id="session_config_shell"):
            with Vertical(classes="session_config_column"):
                if self.show_title_input:
                    with Vertical(classes="field_stack", id="session_title_field"):
                        yield Static("Operator Session", classes="field_label", id="session_title_label")
                        with Horizontal(id="session_title_row"):
                            yield Input(
                                value=self.defaults.get("title", "Operator Session"),
                                id="session_title_input",
                                placeholder="Type a session title",
                            )
                            yield Select(
                                [(title, title) for title in self.session_title_history],
                                value=Select.NULL,
                                allow_blank=True,
                                id="session_title_history_select",
                                prompt="Recent titles",
                                disabled=not self.session_title_history,
                            )
                with Vertical(classes="field_stack", id="session_mode_field"):
                    yield Static("Mode", classes="field_label", id="session_mode_label")
                    yield Select(
                        [("MANUAL", "manual"), ("RUNTIME_AUTO", "runtime_auto"), ("ADAM_AUTO", "adam_auto")],
                        value=self.defaults.get("mode", "manual"),
                        allow_blank=False,
                        id="mode_select",
                        prompt="Inference mode",
                    )
                with Vertical(classes="field_stack", id="session_budget_mode_field"):
                    yield Static("Budget Mode", classes="field_label", id="session_budget_mode_label")
                    yield Select(
                        [("Tight", "tight"), ("Balanced", "balanced"), ("Wide", "wide")],
                        value=self.defaults.get("budget_mode", "balanced"),
                        allow_blank=False,
                        id="budget_mode_select",
                        prompt="Budget mode",
                    )
                with Vertical(classes="field_stack", id="session_low_motion_field"):
                    yield Static("Low Motion", classes="field_label", id="session_low_motion_label")
                    yield Select(
                        [("Off", "false"), ("On", "true")],
                        value="true" if self.defaults.get("low_motion") else "false",
                        allow_blank=False,
                        id="low_motion_select",
                        prompt="Low motion",
                    )
                with Vertical(classes="field_stack", id="session_debug_field"):
                    yield Static("Debug", classes="field_label", id="session_debug_label")
                    yield Select(
                        [("Off", "false"), ("On", "true")],
                        value="true" if self.defaults.get("debug", True) else "false",
                        allow_blank=False,
                        id="debug_select",
                        prompt="Debug verbosity",
                    )
                yield Static(id="session_config_summary")
            with Vertical(classes="session_config_column"):
                with Vertical(classes="field_stack", id="temperature_field"):
                    yield Static("Temperature", classes="field_label", id="temperature_label")
                    yield Input(value=str(self.defaults.get("temperature", 0.4)), id="temperature_input", placeholder="temperature")
                with Vertical(classes="field_stack", id="max_tokens_field"):
                    yield Static("Max Output Tokens", classes="field_label", id="max_tokens_label")
                    yield Input(value=str(self.defaults.get("max_output_tokens", 480)), id="max_tokens_input", placeholder="max output tokens")
                with Vertical(classes="field_stack", id="top_p_field"):
                    yield Static("Top-P", classes="field_label", id="top_p_label")
                    yield Input(value=str(self.defaults.get("top_p", 0.9)), id="top_p_input", placeholder="top_p")
                with Vertical(classes="field_stack", id="repetition_penalty_field"):
                    yield Static("Repetition Penalty", classes="field_label", id="repetition_penalty_label")
                    yield Input(
                        value=str(self.defaults.get("repetition_penalty", 1.05)),
                        id="repetition_penalty_input",
                        placeholder="repetition penalty",
                    )
                with Vertical(classes="field_stack", id="retrieval_depth_field"):
                    yield Static("Retrieval Depth", classes="field_label", id="retrieval_depth_label")
                    yield Input(value=str(self.defaults.get("retrieval_depth", 12)), id="retrieval_depth_input", placeholder="retrieval depth")
                with Vertical(classes="field_stack", id="max_context_items_field"):
                    yield Static("Max Context Items", classes="field_label", id="max_context_items_label")
                    yield Input(
                        value=str(self.defaults.get("max_context_items", 8)),
                        id="max_context_items_input",
                        placeholder="max context items",
                    )
                with Vertical(classes="field_stack", id="response_char_cap_field"):
                    yield Static("Response Character Cap", classes="field_label", id="response_char_cap_label")
                    yield Input(
                        value=str(self.defaults.get("response_char_cap", 1600)),
                        id="response_char_cap_input",
                        placeholder="response char cap",
                    )
                with Horizontal(id="session_action_row"):
                    yield Button(self.action_label, id="session_confirm_btn", variant="primary")
                    yield Button("Cancel", id="session_cancel_btn")

    def on_mount(self) -> None:
        _sync_node_look(self)
        self._refresh_summary()

    @on(Button.Pressed, "#session_confirm_btn")
    def handle_confirm(self) -> None:
        self.dismiss(self._payload())

    @on(Button.Pressed, "#session_cancel_btn")
    def handle_cancel(self) -> None:
        self.dismiss(None)

    @on(Select.Changed, "#session_title_history_select")
    def handle_title_history_select(self, event: Select.Changed) -> None:
        if not self.show_title_input or event.value == Select.NULL:
            return
        title = str(event.value or "").strip()
        title_input = self.query_one("#session_title_input", Input)
        if title and title_input.value != title:
            title_input.value = title

    @on(Input.Changed, "#session_title_input")
    def handle_title_input_change(self, event: Input.Changed) -> None:
        if not self.show_title_input:
            return
        history = self.query_one("#session_title_history_select", Select)
        current = history.value
        if current != Select.NULL and str(current) != event.value:
            history.value = Select.NULL

    @on(Select.Changed)
    @on(Input.Changed)
    def handle_field_change(self, _event) -> None:
        self._refresh_summary()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

    def _payload(self) -> dict[str, Any]:
        raw_payload = {
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
        app = self.app
        assert isinstance(app, EdenTuiApp)
        return request_from_dict(raw_payload, app.runtime.settings).to_dict()

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
        _sync_node_look(self)
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


class ConversationAtlasModal(ModalScreen[dict[str, str] | None]):
    def __init__(self, *, preferred_session_id: str | None = None) -> None:
        super().__init__()
        self.preferred_session_id = preferred_session_id
        self._records: list[dict[str, Any]] = []
        self._filtered_records: list[dict[str, Any]] = []
        self._selected_session_id: str | None = preferred_session_id
        self._selected_preview: dict[str, Any] | None = None
        self._status_message = "Atlas root = all_texts. Folder and tag lenses are relational overlays over saved session transcripts."

    def compose(self) -> ComposeResult:
        yield Static(id="atlas_summary")
        with Horizontal(id="atlas_shell"):
            with Vertical(classes="atlas_column", id="atlas_filter_column"):
                yield Input(placeholder="Search title, experiment, folder, tag, or excerpt", id="atlas_search_input")
                yield Select(
                    ARCHIVE_SORT_OPTIONS,
                    value="updated_desc",
                    allow_blank=False,
                    id="atlas_sort_select",
                    prompt="Sort order",
                )
                yield Select(
                    ARCHIVE_GROUP_OPTIONS,
                    value="all_texts",
                    allow_blank=False,
                    id="atlas_group_select",
                    prompt="Lens",
                )
                yield Input(placeholder="Optional facet filter for the current lens", id="atlas_filter_input")
                yield Static(id="atlas_taxonomy_panel")
                yield Static(id="atlas_status_panel")
            with Vertical(classes="atlas_column", id="atlas_main_column"):
                yield DataTable(zebra_stripes=True, cursor_type="row", id="atlas_records_table")
                with Horizontal(id="atlas_detail_row"):
                    with Vertical(classes="atlas_detail_column", id="atlas_metadata_column"):
                        with Vertical(classes="field_stack", id="atlas_folder_field"):
                            yield Static("Folder", classes="field_label", id="atlas_folder_label")
                            yield Input(placeholder="Folder path, e.g. projects/atlas", id="atlas_folder_input")
                        with Vertical(classes="field_stack", id="atlas_tags_field"):
                            yield Static("Tags", classes="field_label", id="atlas_tags_label")
                            yield TextArea("", id="atlas_tags_input")
                        with Horizontal(id="atlas_taxonomy_actions"):
                            yield Button("Save Taxonomy", id="atlas_save_btn", variant="primary")
                            yield Button("Open Transcript", id="atlas_open_btn")
                    with Vertical(classes="atlas_detail_column", id="atlas_preview_column"):
                        with VerticalScroll(id="atlas_preview_scroller"):
                            yield Static(id="atlas_preview_panel")
                        with Horizontal(id="atlas_observatory_actions"):
                            yield Button("Open Observatory", id="atlas_observatory_btn")
                            yield Button("Turns API", id="atlas_turns_api_btn")
                            yield Button("Active Set API", id="atlas_active_set_api_btn")
                        with Horizontal(id="atlas_session_actions"):
                            yield Button("Resume Session", id="atlas_resume_btn")
                            yield Button("Refresh", id="atlas_refresh_btn")
                            yield Button("Close", id="atlas_close_btn")

    def on_mount(self) -> None:
        _sync_node_look(self)
        table = self.query_one("#atlas_records_table", DataTable)
        table.add_columns("Session", "Experiment", "Mode", "Turns", "Folder", "Tags", "Updated")
        self._refresh_panels()
        self.run_worker(self._load_records_worker(), exclusive=True, group="atlas_load")
        self.call_after_refresh(lambda: self.query_one("#atlas_search_input", Input).focus())

    async def _load_records_worker(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        self._records = await asyncio.to_thread(app.runtime.conversation_archive_records)
        self._refresh_table()

    async def _load_preview_worker(self, session_id: str) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        try:
            preview = await asyncio.to_thread(partial(app.runtime.conversation_archive_preview, session_id))
        except KeyError:
            self._status_message = "Atlas detected a stale session pointer and refreshed its index."
            self._records = await asyncio.to_thread(app.runtime.conversation_archive_records)
            if session_id == self._selected_session_id:
                self._selected_session_id = None
            self._refresh_table()
            return
        if session_id != self._selected_session_id:
            return
        self._selected_preview = preview
        self._refresh_panels()

    def _selected_record(self) -> dict[str, Any] | None:
        if not self._selected_session_id:
            return None
        for record in self._filtered_records:
            if record["id"] == self._selected_session_id:
                return record
        for record in self._records:
            if record["id"] == self._selected_session_id:
                return record
        return None

    def _current_lens(self) -> str:
        return str(self.query_one("#atlas_group_select", Select).value or "all_texts")

    def _current_filter(self) -> str:
        return self.query_one("#atlas_filter_input", Input).value.strip().lower()

    def _current_search(self) -> str:
        return self.query_one("#atlas_search_input", Input).value.strip().lower()

    def _record_matches(self, record: dict[str, Any], *, search: str, lens: str, facet: str) -> bool:
        if search and search not in record["search_text"]:
            return False
        if not facet:
            return True
        if lens == "folder":
            return facet in record["folder"].lower()
        if lens == "tag":
            return any(facet in tag.lower() for tag in record["tags"])
        if lens == "experiment":
            return facet in str(record["experiment_name"]).lower()
        if lens == "mode":
            return facet in str(record.get("experiment_mode") or "").lower()
        return facet in record["search_text"]

    def _sort_key(self, record: dict[str, Any]) -> tuple[Any, ...]:
        sort_mode = str(self.query_one("#atlas_sort_select", Select).value or "updated_desc")
        if sort_mode == "updated_asc":
            return (str(record.get("updated_at") or ""), str(record["title"]).lower())
        if sort_mode == "title_asc":
            return (str(record["title"]).lower(), str(record.get("updated_at") or ""))
        if sort_mode == "turns_desc":
            return (int(record.get("turn_count") or 0), str(record.get("updated_at") or ""))
        if sort_mode == "folder_asc":
            return (str(record["folder"]).lower(), str(record["title"]).lower())
        if sort_mode == "experiment_asc":
            return (str(record["experiment_name"]).lower(), str(record["title"]).lower())
        return (str(record.get("updated_at") or ""), int(record.get("turn_count") or 0))

    def _sort_reverse(self) -> bool:
        sort_mode = str(self.query_one("#atlas_sort_select", Select).value or "updated_desc")
        return sort_mode in {"updated_desc", "turns_desc"}

    def _sync_editor_fields(self) -> None:
        record = self._selected_record()
        folder_input = self.query_one("#atlas_folder_input", Input)
        tags_input = self.query_one("#atlas_tags_input", TextArea)
        if record is None:
            folder_input.value = ""
            tags_input.load_text("")
            return
        folder_input.value = record["folder"]
        tags_input.load_text(", ".join(record["tags"]))

    def _counts_for_lens(self, lens: str) -> list[tuple[str, int]]:
        counts: dict[str, int] = {}
        for record in self._records:
            if lens == "folder":
                values = [record["folder"]]
            elif lens == "tag":
                values = record["tags"] or ["untagged"]
            elif lens == "experiment":
                values = [record["experiment_name"]]
            elif lens == "mode":
                values = [str(record.get("experiment_mode") or "blank")]
            else:
                values = ["all_texts"]
            for value in values:
                counts[value] = counts.get(value, 0) + 1
        return sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))

    def _refresh_table(self) -> None:
        table = self.query_one("#atlas_records_table", DataTable)
        search = self._current_search()
        lens = self._current_lens()
        facet = self._current_filter()
        filtered = [record for record in self._records if self._record_matches(record, search=search, lens=lens, facet=facet)]
        filtered.sort(key=self._sort_key, reverse=self._sort_reverse())
        self._filtered_records = filtered
        table.clear(columns=False)
        for record in filtered:
            table.add_row(
                safe_excerpt(record["title"], limit=26),
                safe_excerpt(record["experiment_name"], limit=20),
                str(record.get("experiment_mode") or "blank"),
                str(record.get("turn_count") or 0),
                safe_excerpt(record["folder"], limit=18),
                safe_excerpt(record["tag_display"], limit=22),
                safe_excerpt(str(record.get("updated_at") or ""), limit=19),
                key=record["id"],
            )
        if not filtered:
            self._selected_session_id = None
            self._selected_preview = None
            self.query_one("#atlas_folder_input", Input).value = ""
            self.query_one("#atlas_tags_input", TextArea).load_text("")
            self._refresh_panels()
            return
        selected_ids = {record["id"] for record in filtered}
        target_id = self._selected_session_id if self._selected_session_id in selected_ids else None
        if target_id is None and self.preferred_session_id in selected_ids:
            target_id = self.preferred_session_id
        if target_id is None:
            target_id = filtered[0]["id"]
        target_index = next(index for index, record in enumerate(filtered) if record["id"] == target_id)
        self._selected_session_id = target_id
        self._sync_editor_fields()
        table.move_cursor(row=target_index, column=0)
        self.run_worker(self._load_preview_worker(target_id), exclusive=True, group="atlas_preview")
        self._refresh_panels()

    def _summary_panel(self) -> Panel:
        lens = self._current_lens()
        selected = self._selected_record()
        body = Text.from_markup(
            "[bold #ffbf66]Conversation Atlas[/]\n"
            "all_texts is the root shelf. Folders and tags are relational projections over persisted sessions, not duplicate transcript files.\n\n"
            f"records={len(self._records)} filtered={len(self._filtered_records)} lens={lens}\n"
            f"selected={(selected or {}).get('title', 'none')}"
        )
        return Panel(body, title="Atlas Root", border_style=AMBER)

    def _taxonomy_panel(self) -> Panel:
        folder_counts = self._counts_for_lens("folder")[:5]
        tag_counts = self._counts_for_lens("tag")[:6]
        lines = ["[bold #ffbf66]Folder Projections[/]"]
        lines.extend(f"{name} :: {count}" for name, count in folder_counts)
        lines.append("")
        lines.append("[bold #ffbf66]Tag Projections[/]")
        lines.extend(f"#{name} :: {count}" for name, count in tag_counts)
        return Panel(Text.from_markup("\n".join(lines)), title="Taxonomy", border_style=ROSE)

    def _status_panel(self) -> Panel:
        record = self._selected_record()
        transcript_state = "ready" if record and record.get("conversation_log_exists") else "derived-on-open"
        facet = self._current_filter() or "none"
        body = Text.from_markup(
            f"[bold {AMBER}]Lens[/] {self._current_lens()} / facet={facet}\n"
            f"[bold {AMBER}]Search[/] {self._current_search() or 'none'}\n"
            f"[bold {AMBER}]Transcript[/] {transcript_state}\n\n"
            + safe_excerpt(self._status_message, limit=220)
        )
        return Panel(body, title="Atlas Status", border_style=ICE)

    def _observatory_context(self) -> dict[str, str] | None:
        record = self._selected_record()
        if record is None:
            return None
        app = self.app
        assert isinstance(app, EdenTuiApp)
        experiment_id = str(record.get("experiment_id") or "").strip()
        session_id = str(record["id"])
        export_dir = app.runtime.export_dir_for_experiment(experiment_id) if experiment_id else None
        export_path = str((export_dir / "observatory_index.html").resolve()) if export_dir is not None else ""
        status = app.ui_state.observatory_status or app.runtime.observatory_status()
        if not status or not experiment_id:
            return {
                "state": "stopped",
                "export_path": export_path,
            }
        base_url = str(status["url"])
        return {
            "state": "ready",
            "export_path": export_path,
            "gui_url": _observatory_target_url(app.runtime, status, experiment_id),
            "overview_url": f"{base_url}api/experiments/{experiment_id}/overview?session_id={session_id}",
            "turns_url": f"{base_url}api/sessions/{session_id}/turns",
            "active_set_url": f"{base_url}api/sessions/{session_id}/active-set",
        }

    def _preview_panel(self) -> Panel:
        record = self._selected_record()
        preview = self._selected_preview
        if record is None:
            return Panel(Text("No saved conversations yet.", style=MUTED), title="Session Preview", border_style=AMBER)
        observatory = self._observatory_context() or {}
        profile_request = (preview or {}).get("profile_request") or {}
        projection = " / ".join(["all_texts", record["folder"], *[f"#{tag}" for tag in record["tags"]]])
        recent_turn_lines = []
        feedback_lines = []
        if preview:
            for turn in preview.get("recent_turns", []):
                recent_turn_lines.append(f"T{turn['turn_index']} Brian :: {turn['user_excerpt']}")
                recent_turn_lines.append(f"T{turn['turn_index']} Adam  :: {turn['response_excerpt']}")
            feedback_lines = [
                f"{str(item.get('verdict', 'skip')).upper()} :: {safe_excerpt(item.get('explanation') or 'no explanation', limit=72)}"
                for item in preview.get("recent_feedback", [])
            ]
        else:
            recent_turn_lines = ["Loading preview surface..."]
        observatory_lines = [
            f"state={observatory.get('state', 'stopped')}",
            f"export={observatory.get('export_path') or 'n/a'}",
        ]
        if observatory.get("state") == "ready":
            observatory_lines.extend(
                [
                    f"gui={observatory.get('gui_url', 'n/a')}",
                    f"overview_api={observatory.get('overview_url', 'n/a')}",
                    f"turns_api={observatory.get('turns_url', 'n/a')}",
                    f"active_set_api={observatory.get('active_set_url', 'n/a')}",
                ]
            )
        else:
            observatory_lines.append("Open Session Observatory to start the browser surface and refresh a session-scoped export.")
        body = Text.from_markup(
            f"[bold {AMBER}]Session[/] {record['title']}\n"
            f"session_id={record['id']}\n"
            f"experiment={record['experiment_name']} ({record.get('experiment_id', 'n/a')}) mode={record.get('experiment_mode', 'blank')}\n"
            f"requested={record.get('requested_mode', 'manual')} budget={record.get('budget_mode', 'balanced')} low_motion={bool(profile_request.get('low_motion', False))} debug={bool(profile_request.get('debug', True))}\n"
            f"turns={record.get('turn_count', 0)} feedback={record.get('feedback_count', 0)}\n"
            f"created={record.get('created_at', 'n/a')}\n"
            f"updated={record.get('updated_at', 'n/a')}\n"
            f"path={projection or 'all_texts'}\n"
            f"tags={record.get('tag_display', 'untagged')}\n"
            f"transcript_ready={bool(preview and preview.get('conversation_log_exists'))}\n"
            f"transcript_path={(preview or {}).get('conversation_log_path') or record.get('conversation_log_path', 'n/a')}\n\n"
            f"[bold {AMBER}]Latest Brian[/] {record['last_user_excerpt']}\n"
            f"[bold {AMBER}]Latest Adam[/] {record['last_response_excerpt']}\n\n"
            f"[bold {AMBER}]Recent Turns[/]\n"
            + ("\n".join(recent_turn_lines) if recent_turn_lines else "No recent turns.")
            + (
                "\n\n[bold #ffbf66]Recent Feedback[/]\n" + "\n".join(feedback_lines)
                if feedback_lines
                else ""
            )
            + "\n\n[bold #ffbf66]Browser Observatory[/]\n"
            + "\n".join(observatory_lines)
        )
        return Panel(body, title="Session Preview", border_style=AMBER)

    def _refresh_panels(self) -> None:
        self.query_one("#atlas_summary", Static).update(self._summary_panel())
        self.query_one("#atlas_taxonomy_panel", Static).update(self._taxonomy_panel())
        self.query_one("#atlas_status_panel", Static).update(self._status_panel())
        self.query_one("#atlas_preview_panel", Static).update(self._preview_panel())

    @on(Input.Changed, "#atlas_search_input")
    @on(Input.Changed, "#atlas_filter_input")
    @on(Select.Changed, "#atlas_sort_select")
    @on(Select.Changed, "#atlas_group_select")
    def handle_query_change(self, _event) -> None:
        if self.is_mounted:
            self._refresh_table()

    @on(DataTable.RowHighlighted, "#atlas_records_table")
    def handle_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        session_id = str(event.row_key.value)
        if session_id == self._selected_session_id and self._selected_preview is not None:
            return
        self._selected_session_id = session_id
        self._selected_preview = None
        self._sync_editor_fields()
        self._refresh_panels()
        self.run_worker(self._load_preview_worker(session_id), exclusive=True, group="atlas_preview")

    @on(Button.Pressed, "#atlas_save_btn")
    def handle_save_metadata(self) -> None:
        self.run_worker(self._save_metadata_worker(), exclusive=True, group="atlas_save")

    async def _save_metadata_worker(self) -> None:
        if not self._selected_session_id:
            self._status_message = "No session selected."
            self._refresh_panels()
            return
        app = self.app
        assert isinstance(app, EdenTuiApp)
        record = self._selected_record()
        folder = self.query_one("#atlas_folder_input", Input).value
        tags = self.query_one("#atlas_tags_input", TextArea).text
        updated = await asyncio.to_thread(
            partial(app.runtime.update_conversation_archive, self._selected_session_id, folder=folder, tags=tags)
        )
        title = record["title"] if record else self._selected_session_id
        self._status_message = (
            f"Saved taxonomy for {title}: "
            f"{updated['archive']['folder']} / "
            f"{', '.join('#' + tag for tag in updated['archive']['tags']) or 'untagged'}"
        )
        self._records = await asyncio.to_thread(app.runtime.conversation_archive_records)
        self._refresh_table()

    async def _open_observatory_target_worker(self, target: str) -> None:
        record = self._selected_record()
        if record is None:
            self._status_message = "No session selected."
            self._refresh_panels()
            return
        app = self.app
        assert isinstance(app, EdenTuiApp)
        experiment_id = str(record.get("experiment_id") or "").strip()
        session_id = str(record["id"])
        if not experiment_id:
            self._status_message = "The selected session does not have an experiment anchor."
            self._refresh_panels()
            return
        status = await asyncio.to_thread(partial(app.runtime.start_observatory, reuse_existing=True))
        app.ui_state.observatory_status = status
        if target == "gui":
            await asyncio.to_thread(partial(app.runtime.export_observability, experiment_id=experiment_id, session_id=session_id))
            target_url = _observatory_target_url(app.runtime, status, experiment_id)
            label = "session observatory"
        elif target == "turns":
            target_url = f"{status['url']}api/sessions/{session_id}/turns"
            label = "session turns API"
        elif target == "active_set":
            target_url = f"{status['url']}api/sessions/{session_id}/active-set"
            label = "session active-set API"
        else:
            self._status_message = f"Unknown observatory target: {target}"
            self._refresh_panels()
            return
        launch = await asyncio.to_thread(partial(open_browser_url, target_url))
        if launch.ok:
            self._status_message = f"Opened {label} for {record['title']}."
        else:
            self._status_message = f"{label} ready for {record['title']}, but browser launch failed: {launch.detail}"
        self._refresh_panels()

    @on(Button.Pressed, "#atlas_open_btn")
    def handle_open_transcript(self) -> None:
        self.run_worker(self._open_transcript_worker(), exclusive=True, group="atlas_open")

    async def _open_transcript_worker(self) -> None:
        if not self._selected_session_id:
            self._status_message = "No session selected."
            self._refresh_panels()
            return
        app = self.app
        assert isinstance(app, EdenTuiApp)
        path = await asyncio.to_thread(partial(app.runtime.write_conversation_log, self._selected_session_id))
        open_browser_url(path.as_uri())
        self._status_message = f"Opened transcript {path.name}."
        self._records = await asyncio.to_thread(app.runtime.conversation_archive_records)
        self._selected_preview = await asyncio.to_thread(partial(app.runtime.conversation_archive_preview, self._selected_session_id))
        self._refresh_panels()

    @on(Button.Pressed, "#atlas_observatory_btn")
    def handle_open_session_observatory(self) -> None:
        self.run_worker(self._open_observatory_target_worker("gui"), exclusive=True, group="atlas_observatory")

    @on(Button.Pressed, "#atlas_turns_api_btn")
    def handle_open_session_turns_api(self) -> None:
        self.run_worker(self._open_observatory_target_worker("turns"), exclusive=True, group="atlas_observatory")

    @on(Button.Pressed, "#atlas_active_set_api_btn")
    def handle_open_session_active_set_api(self) -> None:
        self.run_worker(self._open_observatory_target_worker("active_set"), exclusive=True, group="atlas_observatory")

    @on(Button.Pressed, "#atlas_resume_btn")
    def handle_resume_session(self) -> None:
        if not self._selected_session_id:
            self._status_message = "No session selected."
            self._refresh_panels()
            return
        self.dismiss({"action": "resume", "session_id": self._selected_session_id})

    @on(Button.Pressed, "#atlas_refresh_btn")
    def handle_refresh(self) -> None:
        self._status_message = "Refreshing atlas index."
        self._refresh_panels()
        self.run_worker(self._load_records_worker(), exclusive=True, group="atlas_refresh")

    @on(Button.Pressed, "#atlas_close_btn")
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
                yield Static(id="deck_ingest_help_panel")
                with Horizontal():
                    yield Button("Ingest PDF / Doc", id="deck_ingest_modal_btn", variant="primary")
                    yield Button("Blank Eden", id="deck_blank_btn")
                    yield Button("Seeded Eden", id="deck_seeded_btn")
                with Horizontal():
                    yield Button("Resume Latest", id="deck_resume_btn")
                    yield Button("New Session", id="deck_new_session_btn")
                    yield Button("Conversation Atlas", id="deck_archive_btn")
                with Horizontal():
                    yield Select(
                        LOOK_OPTIONS,
                        value=self.chat_screen.current_ui_look(),
                        allow_blank=False,
                        id="deck_look_select",
                        prompt="Look",
                    )
                with Horizontal():
                    yield Button("Low Motion", id="deck_motion_btn")
                    yield Button("Debug", id="deck_debug_btn")
                    yield Button("Close", id="deck_close_btn")
                yield Static(id="deck_status_panel")

    def on_mount(self) -> None:
        _sync_node_look(self)
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
        self.query_one("#deck_ingest_help_panel", Static).update(self.chat_screen.deck_ingest_help_panel())
        self.query_one("#deck_status_panel", Static).update(self.chat_screen.deck_status_panel())

    @on(Button.Pressed, "#deck_ingest_modal_btn")
    def handle_ingest_modal(self) -> None:
        self.dismiss(None)
        self.chat_screen.run_worker(self.chat_screen.handle_ingest(), exclusive=True, group="ingest_modal")

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

    @on(Button.Pressed, "#deck_archive_btn")
    def handle_archive(self) -> None:
        self.dismiss(None)
        self.chat_screen.run_worker(self.chat_screen.handle_archive(), exclusive=True, group="archive")

    @on(Button.Pressed, "#deck_motion_btn")
    async def handle_motion(self) -> None:
        await self.chat_screen.toggle_motion()
        self._refresh()

    @on(Select.Changed, "#deck_look_select")
    async def handle_look(self, event: Select.Changed) -> None:
        await self.chat_screen.set_ui_look(str(event.value or "amber_dark"), active_modal=self)
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


class IngestModal(ModalScreen[None]):
    def __init__(self, chat_screen: "ChatScreen") -> None:
        super().__init__()
        self.chat_screen = chat_screen

    def compose(self) -> ComposeResult:
        summary = Text.from_markup(
            f"[bold {AMBER}]Corpus Intake[/]\n"
            "Load a PDF or other supported document into the experiment memgraph.\n"
            "Use the framing prompt to tell Adam how to read the work before ingest: "
            "what it is, why it matters, and what interpretive lens or task should persist across turns.\n\n"
            "After ingest, stay in the same session and ask Adam about the work directly."
        )
        guidance = Text.from_markup(
            f"[bold {AMBER}]Framing prompt examples[/]\n"
            "- Treat this as a core primary source on institutional critique.\n"
            "- Ingest this as operator background for the current session and retrieve it aggressively.\n"
            "- Read this as constitutional guidance, not as casual reference.\n\n"
            "[bold {AMBER}]Keyboard[/]\n"
            "Tab moves focus | Enter on the button ingests | Esc closes"
        )
        yield Static(Panel(summary, title="Ingest Bay", border_style=AMBER), id="ingest_summary")
        with Horizontal(id="ingest_shell"):
            with Vertical(classes="ingest_column"):
                yield Input(id="ingest_path_input", placeholder="/absolute/path/to/document.pdf")
                yield TextArea(
                    id="ingest_prompt_input",
                    soft_wrap=True,
                    show_line_numbers=False,
                    text="",
                )
                with Horizontal():
                    yield Button("Ingest Into Memgraph", id="ingest_confirm_btn", variant="primary")
                    yield Button("Cancel", id="ingest_cancel_btn")
            with Vertical(classes="ingest_column"):
                yield Static(Panel(guidance, title="Guidance", border_style=AMBER), id="ingest_guidance_panel")

    def on_mount(self) -> None:
        _sync_node_look(self)
        prompt = self.query_one("#ingest_prompt_input", TextArea)
        prompt.load_text(
            "Brief Adam before ingest: what is this document, how should it be read, and what should persist in recall?"
        )
        self.call_after_refresh(lambda: self.query_one("#ingest_path_input", Input).focus())

    @on(Button.Pressed, "#ingest_confirm_btn")
    async def handle_ingest_confirm(self) -> None:
        path = self.query_one("#ingest_path_input", Input).value.strip()
        prompt = self.query_one("#ingest_prompt_input", TextArea).text.strip()
        if not path:
            return
        await self.chat_screen.ingest_path(path, briefing=prompt)
        self.dismiss(None)

    @on(Button.Pressed, "#ingest_cancel_btn")
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
        _sync_node_look(self)
        self.border_title = "Runtime Loop"
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
            f"[bold {AMBER}]Turn Loop[/]\n"
            f"{loop_a}\n"
            f"{loop_b}\n\n"
            f"[bold {AMBER}]Live Dials[/]\n"
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
        self.update(Panel(text, title="Runtime Loop", border_style=AMBER))


class SignalField(Static):
    def on_mount(self) -> None:
        _sync_node_look(self)
        self._frame = 0
        self.set_interval(0.55, self._tick)
        self._tick()

    def _trace_payload(self, event: dict[str, Any]) -> dict[str, Any]:
        try:
            return json.loads(event.get("payload_json") or "{}")
        except json.JSONDecodeError:
            return {}

    def _stable_number(self, text: str) -> int:
        return sum((index + 1) * ord(char) for index, char in enumerate(text))

    def _line_points(self, x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
        points: list[tuple[int, int]] = []
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        for step in range(1, steps):
            x = x0 + round(dx * step / steps)
            y = y0 + round(dy * step / steps)
            points.append((x, y))
        return points

    def _draw(self, canvas: list[list[tuple[str, str]]], x: int, y: int, char: str, style: str) -> None:
        if 0 <= y < len(canvas) and 0 <= x < len(canvas[y]):
            canvas[y][x] = (char, style)

    def _active_item_position(
        self,
        *,
        item: dict[str, Any],
        index: int,
        width: int,
        height: int,
        center_x: int,
        center_y: int,
        frame: int,
        low_motion: bool,
    ) -> tuple[int, int]:
        seed = self._stable_number(str(item.get("node_id") or item.get("label") or index))
        phase = 0 if low_motion else (frame + seed) % 7
        spread_x = max(8, width // 3)
        knowledge_lane = max(2, center_y - max(3, height // 4))
        behavior_lane = min(height - 3, center_y + max(3, height // 4))
        memode_lane = center_y + ((seed % 3) - 1)
        base_x = center_x - spread_x + ((seed + index * 7) % max(12, width - 18))
        wobble = 0 if low_motion else int(round(math.sin((frame + index + seed % 5) / 3) * 1))
        if item.get("node_kind") == "memode":
            return max(4, min(width - 8, base_x)), max(2, min(height - 3, memode_lane + wobble))
        if item.get("domain") == "behavior":
            return max(4, min(width - 8, base_x)), max(2, min(height - 3, behavior_lane + wobble))
        return max(4, min(width - 8, base_x)), max(2, min(height - 3, knowledge_lane + wobble))

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
        trace_events = (
            app.runtime.store.list_trace_events(app.ui_state.experiment_id, limit=6, session_id=app.ui_state.session_id)
            if app.ui_state.experiment_id
            else []
        )
        latest_event = trace_events[0] if trace_events else None
        health = app.ui_state.current_graph_health or {
            "memes": 0,
            "memodes": 0,
            "edges": 0,
            "turns": 0,
            "feedback": 0,
            "documents": 0,
        }
        anchors = sorted(active_items, key=lambda item: float(item.get("regard", 0.0)), reverse=True)[:3]
        return {
            "active_items": active_items[:8],
            "anchors": anchors,
            "behavior_count": behavior_count,
            "knowledge_count": knowledge_count,
            "memode_count": memode_count,
            "reasoning_present": reasoning_present,
            "pressure": pressure,
            "pending_review": pending_review,
            "trace_events": trace_events,
            "latest_event": latest_event,
            "latest_payload": self._trace_payload(latest_event) if latest_event else {},
            "health": health,
            "last_ingest": app.ui_state.last_ingest_result or {},
        }

    def _event_summary(self, event: dict[str, Any]) -> str:
        payload = self._trace_payload(event)
        event_type = str(event.get("event_type", "TRACE")).upper()
        if event_type == "TURN":
            return (
                f"turn pulse + active_set {payload.get('active_set_size', '?')} "
                f"reasoning={'yes' if payload.get('reasoning_present') else 'no'}"
            )
        if event_type == "FEEDBACK":
            return (
                f"feedback retuned regard on {payload.get('affected_memes', '?')} memes / "
                f"{payload.get('affected_memodes', '?')} memodes"
            )
        if event_type == "INGEST":
            return (
                f"ingest added {payload.get('meme_count', '?')} memes / "
                f"{payload.get('memode_count', '?')} memodes"
            )
        if event_type == "INGEST_BRIEF":
            return (
                f"brief lens anchored {payload.get('brief_meme_count', '?')} memes / "
                f"{payload.get('brief_memode_count', '?')} memodes"
            )
        return safe_excerpt(str(event.get("message") or event_type).lower(), limit=64)

    def _tick(self) -> None:
        app = self.app
        if not isinstance(app, EdenTuiApp):
            return
        if not app.runtime.settings.low_motion:
            self._frame = (self._frame + 1) % 10_000
        state = self._field_state(app)
        width = max(64, min((self.size.width or 92) - 6, 140))
        height = max(12, min((self.size.height or 22) - 9, 16))
        center_x = width // 2
        center_y = height // 2
        canvas = [[(" ", TEXT) for _ in range(width)] for _ in range(height)]

        nebula_palette = (MUTED, EMBER, ROSE, VIOLET, ICE, NEON)
        for y in range(0, height, 4):
            for x in range(width):
                if (x + self._frame) % 9 == 0:
                    self._draw(canvas, x, y, ".", nebula_palette[(x + y + self._frame) % len(nebula_palette)])
        for x in range(0, width, 10):
            for y in range(height):
                if (y + self._frame) % 5 == 0:
                    self._draw(canvas, x, y, ":", nebula_palette[(x + y + 2 * self._frame) % len(nebula_palette)])

        session_x = center_x
        session_y = center_y
        self._draw(canvas, session_x, session_y, "@", ICE)

        doc_node: tuple[int, int] | None = None
        if state["last_ingest"]:
            doc_node = (5, max(2, min(height - 3, center_y - 1)))
            self._draw(canvas, doc_node[0], doc_node[1], "D", AMBER)
            for point_x, point_y in self._line_points(doc_node[0], doc_node[1], session_x - 2, session_y):
                rail = "=" if point_y == doc_node[1] else "/" if point_y < session_y else "\\"
                self._draw(canvas, point_x, point_y, rail, EMBER)

        active_positions: list[tuple[dict[str, Any], int, int, str, str]] = []
        for index, item in enumerate(state["active_items"]):
            pos_x, pos_y = self._active_item_position(
                item=item,
                index=index,
                width=width,
                height=height,
                center_x=center_x,
                center_y=center_y,
                frame=self._frame,
                low_motion=app.runtime.settings.low_motion,
            )
            if item.get("node_kind") == "memode":
                glyph, style = "M", ICE
                rail_style = VIOLET
            elif item.get("domain") == "behavior":
                glyph, style = "^", ROSE
                rail_style = ROSE
            else:
                glyph, style = "o", NEON
                rail_style = NEON
            active_positions.append((item, pos_x, pos_y, glyph, style))
            for point_x, point_y in self._line_points(session_x, session_y, pos_x, pos_y):
                rail = "|" if point_x == session_x else "-" if point_y == session_y else "/" if point_y < session_y else "\\"
                self._draw(canvas, point_x, point_y, rail, rail_style)
            self._draw(canvas, pos_x, pos_y, glyph, style)

        for anchor_index, anchor in enumerate(state["anchors"]):
            match = next((entry for entry in active_positions if entry[0].get("node_id") == anchor.get("node_id")), None)
            if match is None:
                continue
            _, anchor_x, anchor_y, _, _ = match
            bank_x = width - 5
            bank_y = min(height - 2, 2 + anchor_index * 3)
            for point_x, point_y in self._line_points(anchor_x, anchor_y, bank_x - 1, bank_y):
                self._draw(canvas, point_x, point_y, ".", VIOLET if anchor_index % 2 else ICE)
            self._draw(canvas, bank_x, bank_y, "R", ICE)

        latest_event = state["latest_event"]
        if latest_event is not None:
            event_type = str(latest_event.get("event_type", "")).upper()
            if event_type == "TURN":
                pulse_radius = 2 + (0 if app.runtime.settings.low_motion else self._frame % 4)
                for point_x, point_y in (
                    (session_x - pulse_radius, session_y),
                    (session_x + pulse_radius, session_y),
                    (session_x, session_y - pulse_radius),
                    (session_x, session_y + pulse_radius),
                ):
                    self._draw(canvas, point_x, point_y, "*", AMBER)
            elif event_type == "FEEDBACK":
                for _, pos_x, pos_y, _, _ in active_positions[:3]:
                    self._draw(canvas, pos_x + 1, pos_y, "!", ROSE)
            elif event_type == "INGEST" and doc_node is not None:
                ring = 1 + (0 if app.runtime.settings.low_motion else self._frame % 3)
                for point_x, point_y in (
                    (doc_node[0] + ring, doc_node[1]),
                    (doc_node[0], doc_node[1] + ring),
                    (doc_node[0], doc_node[1] - ring),
                ):
                    self._draw(canvas, point_x, point_y, "o", EMBER)
            elif event_type == "INGEST_BRIEF" and doc_node is not None:
                self._draw(canvas, doc_node[0] + 2, doc_node[1] - 1, "?", ROSE)

        if state["reasoning_present"]:
            for delta in (-1, 1):
                self._draw(canvas, session_x + delta, session_y, "*", ICE)
                self._draw(canvas, session_x, session_y + delta, "*", ICE)
        if state["pending_review"]:
            for spark_x in range(8, width - 8, 17):
                spark_y = 1 + ((spark_x + self._frame) % max(3, height - 2))
                self._draw(canvas, spark_x, spark_y, ".", ROSE)

        visual = Text()
        for y, row in enumerate(canvas):
            line = Text()
            for char, style in row:
                line.append(char, style=style)
            visual.append(line)
            if y < height - 1:
                visual.append("\n")

        update_lines = [self._event_summary(event) for event in state["trace_events"][:3]]
        latest_update = update_lines[0] if update_lines else "no recent memgraph mutation yet"
        health = state["health"]
        last_ingest = state["last_ingest"]
        knowledge_labels = [
            safe_excerpt(item.get("label", "untitled"), limit=18)
            for item in state["active_items"]
            if item.get("node_kind") != "memode" and item.get("domain") != "behavior"
        ][:3]
        behavior_labels = [
            safe_excerpt(item.get("label", "untitled"), limit=18)
            for item in state["active_items"]
            if item.get("node_kind") != "memode" and item.get("domain") == "behavior"
        ][:3]
        memode_labels = [
            safe_excerpt(item.get("label", "untitled"), limit=18)
            for item in state["active_items"]
            if item.get("node_kind") == "memode"
        ][:2]
        focus_label = (
            safe_excerpt(state["active_items"][0].get("label", "untitled"), limit=24)
            if state["active_items"]
            else "no hot node"
        )
        explanation = Text.from_markup(
            f"\n\n[bold {AMBER}]Legend[/] D doc | o knowledge meme | ^ behavior meme | M memode | @ session anchor | R recall bank | * turn pulse | ! feedback spark | ? framing brief\n"
            f"[bold {AMBER}]Live read[/] update={latest_update}\n"
            f"graph=memes {health.get('memes', 0)} memodes {health.get('memodes', 0)} "
            f"edges {health.get('edges', 0)} docs {health.get('documents', 0)} turns {health.get('turns', 0)} "
            f"review={'pending' if state['pending_review'] else 'settled'} pressure={state['pressure']}\n"
            f"[bold {AMBER}]Bus -> Aperture[/] docs={safe_excerpt(last_ingest.get('title', 'none yet'), limit=24)} | "
            f"knowledge={', '.join(knowledge_labels) or 'quiet'} | "
            f"behavior={', '.join(behavior_labels) or 'quiet'} | "
            f"memodes={', '.join(memode_labels) or 'quiet'}\n"
            f"[bold {AMBER}]Relation read[/] D -> @ -> {focus_label} -> R | "
            f"knowledge={state['knowledge_count']} behavior={state['behavior_count']} memodes={state['memode_count']}\n"
            + (
                f"latest corpus root={safe_excerpt(last_ingest.get('title', ''), limit=54)} | brief={'yes' if last_ingest.get('briefing') else 'no'}"
                if last_ingest
                else "latest corpus root=none yet"
            )
        )
        border = ROSE if state["pending_review"] else ICE if state["reasoning_present"] else AMBER
        self.update(Panel(visual + explanation, title="Memgraph Bus", border_style=border, style=f"on {SHADE}"))


class StartupScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self._seen_log_count = 0
        self._last_startup_action_dispatch: tuple[str, float] | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="startup_frame"):
            with Horizontal(id="startup_topbar"):
                yield Select(
                    [
                        ("Start Blank Eden", "blank"),
                        ("Start Seeded Eden", "seeded"),
                        ("Continue Latest", "resume"),
                        ("Prepare Local Model", "prepare_mlx"),
                        ("Refresh Model", "refresh_model"),
                        ("Open Browser Observatory", "observatory"),
                        ("Export Artifacts", "export"),
                        ("Open Conversation Atlas", "archive"),
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
        _sync_node_look(self)
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
        operator_text = (snapshot.get("last_user_text") or "Awaiting Brian transmission.").strip()
        if operator_text.lower().startswith("brian the operator:"):
            operator_text = operator_text.split(":", 1)[1].strip()
        operator_text = safe_excerpt(operator_text, limit=260)
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
        self._last_startup_action_dispatch = (normalized, monotonic())
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
        elif normalized == "archive":
            self.handle_startup_archive()
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
        session_title_history = await asyncio.to_thread(partial(app.runtime.recent_session_titles, limit=20))
        payload = await app.push_screen_wait(
            SessionConfigModal(
                defaults,
                title_text="Session Inference Profile",
                action_label="Start Session",
                session_title_history=session_title_history,
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
        latest_experiment_id = latest["id"] if latest is not None else None
        if latest_experiment_id:
            await asyncio.to_thread(partial(app.runtime.export_observability, experiment_id=latest_experiment_id, session_id=None))
        target_url = _observatory_target_url(app.runtime, status, latest_experiment_id)
        launch = await asyncio.to_thread(partial(open_browser_url, target_url))
        if launch.ok:
            self.query_one("#startup_log", RichLog).write(
                f"[INFO] Observatory {'reused' if status['reused_existing'] else 'started'} :: {target_url} via {launch.method}"
            )
        else:
            self.query_one("#startup_log", RichLog).write(
                f"[WARN] Observatory ready but browser launch failed :: {target_url} :: {launch.detail}"
            )
        self._refresh_panels()

    def handle_startup_export(self) -> None:
        self.run_worker(self._startup_export_worker(), exclusive=True, group="startup_export")

    async def _startup_archive_worker(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        payload = await app.push_screen_wait(ConversationAtlasModal(preferred_session_id=app.ui_state.session_id))
        if not payload or payload.get("action") != "resume" or not payload.get("session_id"):
            return
        snapshot = await asyncio.to_thread(partial(app.runtime.session_state_snapshot, payload["session_id"]))
        app.apply_session_snapshot(snapshot)
        self.query_one("#startup_log", RichLog).write(f"[INFO] Atlas resumed :: {snapshot['session_title']}")
        await app.push_screen(ChatScreen())

    def handle_startup_archive(self) -> None:
        self.run_worker(self._startup_archive_worker(), exclusive=True, group="startup_archive")

    def handle_startup_observatory(self) -> None:
        self.run_worker(self._startup_observatory_worker(), exclusive=True, group="startup_observatory")

    @on(Select.Changed, "#startup_action_menu")
    def handle_startup_action_changed(self, _event: Select.Changed) -> None:
        self.query_one("#startup_menu_hint", Static).update(self._menu_hint_panel())
        action = str(self.query_one("#startup_action_menu", Select).value or "blank")
        if self._recent_startup_action_dispatch(action):
            return
        self._execute_startup_action(action)

    def _recent_startup_action_dispatch(self, action: str) -> bool:
        normalized = (action or "blank").strip().lower()
        if self._last_startup_action_dispatch is None:
            return False
        last_action, dispatched_at = self._last_startup_action_dispatch
        return last_action == normalized and (monotonic() - dispatched_at) < 0.6

    def on_key(self, event) -> None:
        if event.key == "enter" and self.app.focused and getattr(self.app.focused, "id", None) == "startup_action_menu":
            action = str(self.query_one("#startup_action_menu", Select).value or "blank")
            if not self._recent_startup_action_dispatch(action):
                self._execute_startup_action(action)
            event.stop()


class ChatScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self._seen_log_count = 0
        self._preview_task: asyncio.Task[None] | None = None
        self._preview_generation = 0
        self._preview_running = False
        self._preview_rerun_requested = False
        self._transcript_cache_session_id: str | None = None
        self._transcript_cache_panels: tuple[Panel, ...] = ()
        self._graph_health_dirty = True
        self._event_lines: list[str] = []
        self._last_runtime_action_dispatch: tuple[str, float] | None = None
        self._last_feedback_signature: tuple[str, str] | None = None
        self._last_hum_signature: tuple[str, str] | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="runtime_frame"):
            with Horizontal(id="runtime_topbar"):
                yield ActionStrip(value="review", id="runtime_action_menu")
                yield Static(id="turn_status_panel")
                yield Static(id="aperture_drawer_panel")
            with Horizontal(id="chat_shell"):
                with Vertical(id="chat_primary"):
                    with Vertical(id="chat_deck"):
                        with VerticalScroll(id="chat_tape", can_focus=True):
                            yield Static(id="chat_exchange_panel")
                        with Vertical(id="inline_feedback_surface"):
                            with Horizontal(id="inline_feedback_command_row"):
                                yield Input(placeholder="Verdict code: A / E / R / S", id="inline_feedback_verdict_input")
                            yield Static(id="inline_feedback_status_panel")
                            yield ReviewTextArea(
                                id="inline_feedback_explanation_input",
                                soft_wrap=True,
                                show_line_numbers=False,
                                placeholder="Explain the review decision. Press Enter to submit. Shift+Enter adds a newline.",
                            )
                            yield ReviewTextArea(
                                id="inline_feedback_corrected_input",
                                soft_wrap=True,
                                show_line_numbers=False,
                                placeholder="Corrected text for EDIT. Press Enter to submit. Shift+Enter adds a newline.",
                            )
                        yield ComposerTextArea(
                            id="composer_input",
                            soft_wrap=True,
                            show_line_numbers=False,
                            placeholder="Message Adam here. Ask a question, continue the session, or correct the draft. Enter sends. F9 ingests a document first if needed.",
                        )
                with Vertical(id="chat_secondary"):
                    yield SignalField(id="signal_field")
                    yield Static(id="active_aperture_panel")
                    with Horizontal(id="reasoning_mode_row"):
                        yield Button("Reasoning", id="reasoning_mode_reasoning_btn")
                        yield Button("Chain-Like", id="reasoning_mode_chain_btn")
                        yield Button("Hum Live", id="reasoning_mode_hum_btn")
                    with VerticalScroll(id="thinking_scroller", can_focus=True):
                        yield Static(id="thinking_panel")
            with Vertical(id="runtime_chyron_drawer"):
                yield Static(id="runtime_chyron_panel")
        yield Footer()

    def on_mount(self) -> None:
        _sync_node_look(self)
        self.set_interval(0.6, self._poll_logs)
        self.refresh_panels()
        self.run_worker(self._bootstrap_live_surface(), exclusive=True, group="bootstrap")
        self.call_after_refresh(self.focus_composer)

    def refresh_panels(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._sync_responsive_layout()
            self._health()
            self._sync_aperture_drawer()
            self._sync_runtime_chyron_drawer()
            self._sync_header_controls()
            self.query_one("#turn_status_panel", Static).update(self.main_turn_status_panel())
            top_aperture = self.main_aperture_drawer_panel() if self.app.ui_state.aperture_drawer_open else self.main_aperture_panel()
            self.query_one("#aperture_drawer_panel", Static).update(top_aperture)
            self.query_one("#active_aperture_panel", Static).update(top_aperture)
            self._sync_reasoning_mode_controls()
            self.query_one("#thinking_panel", Static).update(self.main_thinking_panel())
            self.query_one("#chat_exchange_panel", Static).update(self.main_chat_exchange_panel())
            self._sync_inline_feedback_surface()
            self.query_one("#inline_feedback_status_panel", Static).update(self.main_inline_feedback_status_panel())
            self.query_one("#runtime_chyron_panel", Static).update(self.main_runtime_chyron_panel())
        except NoMatches:
            return

    def _refresh_composer_surfaces(self) -> None:
        if not self.is_mounted:
            return
        try:
            self.query_one("#runtime_action_menu", ActionStrip).refresh()
            self.query_one("#turn_status_panel", Static).update(self.main_turn_status_panel())
            self.query_one("#chat_exchange_panel", Static).update(self.main_chat_exchange_panel())
        except NoMatches:
            return

    def _is_compact_layout(self) -> bool:
        return (self.size.width or 0) < 100 or (self.size.height or 0) < 30

    def _sync_responsive_layout(self) -> None:
        compact = self._is_compact_layout()
        app = self.app
        assert isinstance(app, EdenTuiApp)
        topbar = self.query_one("#runtime_topbar", Horizontal)
        action_strip = self.query_one("#runtime_action_menu", ActionStrip)
        turn_status = self.query_one("#turn_status_panel", Static)
        aperture_drawer = self.query_one("#aperture_drawer_panel", Static)
        chat_primary = self.query_one("#chat_primary", Vertical)
        chat_secondary = self.query_one("#chat_secondary", Vertical)
        chat_deck = self.query_one("#chat_deck", Vertical)
        chat_tape = self.query_one("#chat_tape", VerticalScroll)
        composer = self.query_one("#composer_input", TextArea)
        signal_field = self.query_one("#signal_field", SignalField)
        aperture_panel = self.query_one("#active_aperture_panel", Static)
        reasoning_mode_row = self.query_one("#reasoning_mode_row", Horizontal)
        thinking_scroller = self.query_one("#thinking_scroller", VerticalScroll)

        if compact:
            action_strip.styles.width = "1fr"
            action_strip.styles.min_width = 0
            turn_status.display = False
            turn_status.styles.width = 0
            aperture_drawer.styles.width = 0
            topbar.styles.height = action_strip.preferred_height(max(32, (self.size.width or 80) - 4))
            chat_deck.styles.min_height = 0
            chat_primary.styles.width = "1fr"
            chat_primary.styles.min_width = 0
            chat_secondary.styles.width = "1fr"
            chat_secondary.styles.min_width = 0
            chat_tape.styles.min_height = 3
            chat_tape.styles.margin_bottom = 0
            composer.styles.height = 4
            aperture_panel.styles.min_height = 0
            if app.ui_state.aperture_drawer_open:
                chat_primary.display = False
                chat_secondary.display = True
                signal_field.display = False
                aperture_panel.display = True
                reasoning_mode_row.display = False
                thinking_scroller.display = False
                aperture_panel.styles.height = "1fr"
            else:
                chat_primary.display = True
                chat_secondary.display = False
                signal_field.display = True
                aperture_panel.display = False
                reasoning_mode_row.display = True
                thinking_scroller.display = True
                aperture_panel.styles.height = 0
        else:
            chat_primary.display = True
            chat_secondary.display = True
            signal_field.display = True
            aperture_panel.display = False
            reasoning_mode_row.display = True
            thinking_scroller.display = True
            if app.ui_state.aperture_drawer_open:
                action_strip.styles.width = "44%"
                action_strip.styles.min_width = 42
                turn_status.display = True
                turn_status.styles.width = "14%"
                aperture_drawer.styles.width = "42%"
                action_width = max(42, int((self.size.width or 120) * 0.44) - 4)
                drawer_height = max(13, int((self.size.height or 40) * 0.30))
                topbar.styles.height = max(action_strip.preferred_height(action_width), drawer_height)
            else:
                action_strip.styles.width = "57%"
                action_strip.styles.min_width = 57
                turn_status.display = True
                turn_status.styles.width = "13%"
                aperture_drawer.styles.width = "30%"
                action_width = max(42, int((self.size.width or 120) * 0.57) - 4)
                topbar.styles.height = max(action_strip.preferred_height(action_width), 11)
            chat_deck.styles.min_height = 28
            chat_primary.styles.width = "60%"
            chat_primary.styles.min_width = 76
            chat_secondary.styles.width = "40%"
            chat_secondary.styles.min_width = 50
            chat_tape.styles.min_height = 22
            chat_tape.styles.margin_bottom = 1
            composer.styles.height = 5
            aperture_panel.styles.height = 0
            thinking_scroller.styles.height = "1fr"
            thinking_scroller.styles.min_height = 16

    def on_resize(self, _event: events.Resize) -> None:
        if self.is_mounted:
            self.refresh_panels()

    def _invalidate_transcript_cache(self) -> None:
        self._transcript_cache_session_id = None
        self._transcript_cache_panels = ()

    def _mark_graph_dirty(self) -> None:
        self._graph_health_dirty = True
        self._invalidate_transcript_cache()
        self._preview_generation += 1
        self._preview_rerun_requested = False
        if self._preview_task is not None and not self._preview_task.done() and not self._preview_running:
            self._preview_task.cancel()

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

    def _all_turns(self) -> list[dict[str, Any]]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.session_id:
            return []
        return app.runtime.store.list_all_turns(app.ui_state.session_id)

    async def _sync_conversation_log(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.session_id:
            app.ui_state.conversation_log_path = None
            return
        path = app.runtime.write_conversation_log(app.ui_state.session_id)
        app.ui_state.conversation_log_path = str(path)

    def _scroll_chat_to_end(self) -> None:
        if not self.is_mounted:
            return

        def _scroll() -> None:
            if not self.is_mounted:
                return
            self.query_one("#chat_tape", VerticalScroll).scroll_end(animate=False)

        self.call_after_refresh(_scroll)

    async def _bootstrap_live_surface(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        app.ui_state.model_status = await asyncio.to_thread(self._load_model_status_snapshot)
        model_status = self._model_status()
        self._write_forensic(
            f"[INFO] Live cockpit boot :: backend={app.runtime.settings.model_backend} stage={model_status.get('stage', 'n/a')}"
        )
        if app.runtime.settings.model_backend.lower() == "mlx" and not model_status.get("ready", False):
            app.ui_state.last_feedback = "Local MLX cache is not ready. Choose Prepare Local Model or send once to fetch it."
        latest = await asyncio.to_thread(app.runtime.store.get_latest_experiment)
        experiment: dict[str, Any] | None = latest
        if latest is not None:
            latest_session = await asyncio.to_thread(partial(app.runtime.store.get_latest_session, latest["id"]))
            if latest_session is not None:
                snapshot = await asyncio.to_thread(partial(app.runtime.session_state_snapshot, latest_session["id"]))
                app.apply_session_snapshot(snapshot)
                self._mark_graph_dirty()
                app.ui_state.last_feedback = f"Resumed {snapshot['session_title']}."
                self._write_forensic(f"[INFO] Resumed session :: {snapshot['session_title']}")
                self.refresh_panels()
                self.focus_composer()
                self._scroll_chat_to_end()
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
        self._mark_graph_dirty()
        app.ui_state.last_feedback = "Live dialogue surface armed. Ask a question with Enter (or Ctrl+S) or ingest a document with F9."
        self._write_forensic(f"[INFO] Armed session :: {snapshot['session_title']}")
        self.refresh_panels()
        self.focus_composer()
        self._scroll_chat_to_end()
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
        self._record_event_line(line)

    def _record_event_line(self, line: str) -> None:
        self._event_lines.append(line)
        if len(self._event_lines) > 80:
            self._event_lines = self._event_lines[-80:]

    def _health(self) -> dict[str, Any]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not self._graph_health_dirty and app.ui_state.current_graph_health is not None:
            return app.ui_state.current_graph_health
        if not app.ui_state.experiment_id:
            health = {
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
            app.ui_state.current_graph_health = health
            self._graph_health_dirty = False
            return health
        health = app.runtime.graph_health(app.ui_state.experiment_id)
        app.ui_state.current_graph_health = health
        self._graph_health_dirty = False
        return health

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

    def _recent_trace_events(self, *, limit: int = 6) -> list[dict[str, Any]]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.experiment_id:
            return []
        return app.runtime.store.list_trace_events(
            app.ui_state.experiment_id,
            limit=limit,
            session_id=app.ui_state.session_id,
        )

    def _current_hum_snapshot(self) -> dict[str, Any]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.session_id:
            return {
                "present": False,
                "generated_at": None,
                "latest_turn_id": None,
                "turn_window_size": 0,
                "cross_turn_recurrence_present": False,
                "text_surface": "",
            }
        return app.runtime.hum_snapshot(app.ui_state.session_id)

    def _current_hum_payload(self) -> dict[str, Any]:
        hum = self._current_hum_snapshot()
        json_path = str(hum.get("json_path") or "").strip()
        if not hum.get("present") or not json_path:
            return {}
        try:
            return json.loads(Path(json_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _recent_membrane_events(self, *, limit: int = 4) -> list[dict[str, Any]]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.experiment_id:
            return []
        return app.runtime.store.list_membrane_events(
            app.ui_state.experiment_id,
            limit=limit,
            session_id=app.ui_state.session_id,
        )

    def _chain_like_lines(self, text: str, *, limit: int = 6, line_limit: int = 96) -> list[str]:
        segments = [segment.strip(" -") for segment in str(text or "").replace("\r", "\n").splitlines() if segment.strip()]
        if not segments and text.strip():
            segments = [segment.strip() for segment in text.split(". ") if segment.strip()]
        return [f"{index + 1}. {safe_excerpt(segment, limit=line_limit)}" for index, segment in enumerate(segments[:limit])]

    def _artifact_excerpt_lines(self, text: str, *, limit: int = 8, line_limit: int = 108) -> list[str]:
        normalized = str(text or "").replace("\r", "\n").strip()
        if not normalized:
            return []
        segments = [segment.strip() for segment in normalized.splitlines() if segment.strip()]
        if len(segments) <= 1:
            segments = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", normalized) if segment.strip()]
        return [safe_excerpt(segment, limit=line_limit) for segment in segments[:limit]]

    def _normalize_reasoning_line(self, text: str) -> str:
        normalized = re.sub(r"\*\*", "", str(text or "").strip()).lower()
        normalized = re.sub(r"^[\-\*\d\.\)\s:]+", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _is_prompt_mirror_line(self, text: str) -> bool:
        normalized = self._normalize_reasoning_line(text)
        if not normalized:
            return True
        mirror_prefixes = (
            "thinking process",
            "analyze the request",
            "user:",
            "context:",
            "role:",
            "constraints:",
            "constraint:",
            "input data:",
            "tone/persona:",
            "tone persona:",
        )
        if any(normalized.startswith(prefix) for prefix in mirror_prefixes):
            return True
        mirror_fragments = (
            "return one clean operator-facing reply",
            "no headings",
            "brian the operator",
            "adam, the first graph-conditioned agent",
            "active set memes show",
        )
        return any(fragment in normalized for fragment in mirror_fragments)

    def _useful_reasoning_lines(self, reasoning_text: str, *, limit: int = 6, line_limit: int = 108) -> list[str]:
        raw_lines = self._artifact_excerpt_lines(reasoning_text, limit=limit * 3, line_limit=line_limit)
        useful = [line for line in raw_lines if not self._is_prompt_mirror_line(line)]
        return useful[:limit]

    def _dominant_active_lane(self, active_items: list[dict[str, Any]]) -> str:
        if not active_items:
            return "quiet"
        behavior_mass = sum(float(item.get("selection", 0.0)) for item in active_items if item.get("domain") == "behavior")
        knowledge_mass = sum(float(item.get("selection", 0.0)) for item in active_items if item.get("domain") != "behavior")
        if knowledge_mass > behavior_mass * 1.15:
            return "knowledge-led"
        if behavior_mass > knowledge_mass * 1.15:
            return "behavior-led"
        return "balanced"

    def _feedback_status_phrase(self, latest_feedback: dict[str, Any] | None) -> str:
        feedback_state, _ = self._feedback_loop_state()
        if latest_feedback is not None:
            return (
                f"{str(latest_feedback.get('verdict', 'skip')).upper()} on "
                f"T{latest_feedback.get('turn_index', '?')}: "
                f"{safe_excerpt(str(latest_feedback.get('explanation') or 'no explanation'), limit=52)}"
            )
        if feedback_state == "pending":
            return "reply pending review"
        return "no explicit feedback yet"

    def _membrane_record_lines(self, membrane_events: list[dict[str, Any]], *, limit: int = 3, line_limit: int = 88) -> list[str]:
        if not membrane_events:
            return ["No membrane events recorded yet. The next Adam reply will log the operator-facing cleanup path."]
        lines: list[str] = []
        for event in membrane_events[:limit]:
            event_type = str(event.get("event_type") or "UNKNOWN").upper()
            detail = safe_excerpt(str(event.get("detail") or "no detail"), limit=line_limit)
            lines.append(f"{event_type} :: {detail}")
        return lines

    def _hum_surface_lines(self, hum_payload: dict[str, Any], hum_snapshot: dict[str, Any]) -> list[str]:
        lines = [safe_excerpt(str(line), limit=112) for line in hum_payload.get("surface_lines") or [] if str(line).strip()]
        if lines:
            return lines
        return self._artifact_excerpt_lines(str(hum_snapshot.get("text_surface") or ""), limit=4, line_limit=112)

    def _hum_table_lines(self, hum_payload: dict[str, Any]) -> list[str]:
        rows = list(hum_payload.get("token_table") or [])
        if not rows:
            return []
        lines: list[str] = []
        for index, row in enumerate(rows[:6], start=1):
            token = safe_excerpt(str(row.get("token") or "seed"), limit=20)
            count = int(row.get("count", 0) or 0)
            pct = float(row.get("pct_of_all_tokens", 0.0) or 0.0) * 100
            lines.append(f"{index}. {token} x{count} ({pct:.1f}%)")
        return lines

    def _sync_runtime_chyron_drawer(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        drawer = self.query_one("#runtime_chyron_drawer", Vertical)
        chyron = self.query_one("#runtime_chyron_panel", Static)
        if app.ui_state.runtime_chyron_open:
            drawer.styles.display = "block"
            chyron.styles.display = "block"
            chyron.styles.height = 5 if self._is_compact_layout() else 6
            chyron.styles.min_height = chyron.styles.height
            drawer.styles.height = chyron.styles.height
            drawer.styles.min_height = chyron.styles.height
        else:
            drawer.styles.display = "none"
            chyron.styles.display = "none"
            drawer.styles.height = 0
            drawer.styles.min_height = 0
            chyron.styles.height = 0
            chyron.styles.min_height = 0

    def _sync_reasoning_mode_controls(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        controls = {
            "reasoning": ("#reasoning_mode_reasoning_btn", "Reasoning"),
            "chain_like": ("#reasoning_mode_chain_btn", "Chain-Like"),
            "hum_live": ("#reasoning_mode_hum_btn", "Hum Live"),
        }
        for mode, (selector, label) in controls.items():
            button = self.query_one(selector, Button)
            active = app.ui_state.reasoning_mode == mode
            button.label = f"● {label}" if active else label
            button.variant = "primary" if active else "default"

    def _sync_aperture_drawer(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        drawer = self.query_one("#aperture_drawer_panel", Static)
        if self._is_compact_layout():
            drawer.display = False
            drawer.styles.height = 0
            return
        drawer.display = True
        drawer.styles.height = "1fr"

    def _sync_header_controls(self) -> None:
        self.query_one("#runtime_action_menu", ActionStrip).refresh()

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

    def _sync_inline_feedback_surface(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        surface = self.query_one("#inline_feedback_surface", Vertical)
        has_reply = bool(app.ui_state.last_turn_id)
        if not has_reply:
            surface.display = False
            surface.styles.height = 0
            surface.styles.min_height = 0
            return
        surface.display = True
        surface.styles.height = "auto"
        surface.styles.min_height = 11

    def _inline_feedback_intent(self) -> tuple[str | None, str]:
        raw_code = self.query_one("#inline_feedback_verdict_input", Input).value.strip().upper()
        verdict_map = {
            "A": "accept",
            "E": "edit",
            "R": "reject",
            "S": "skip",
        }
        return verdict_map.get(raw_code), raw_code

    def _inline_feedback_form_state(self) -> dict[str, Any]:
        verdict, raw_code = self._inline_feedback_intent()
        explanation = self.query_one("#inline_feedback_explanation_input", TextArea).text.strip()
        corrected = self.query_one("#inline_feedback_corrected_input", TextArea).text.strip()
        needs_explanation = verdict in {"accept", "edit", "reject"}
        needs_corrected = verdict == "edit"
        ready = verdict is not None
        if needs_explanation:
            ready = ready and bool(explanation)
        if needs_corrected:
            ready = ready and bool(corrected)
        return {
            "verdict": verdict,
            "raw_code": raw_code,
            "explanation": explanation,
            "corrected": corrected,
            "needs_explanation": needs_explanation,
            "needs_corrected": needs_corrected,
            "ready": ready,
        }

    def _conversation_stage(self) -> tuple[str, str]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        draft = self._composer_text().strip()
        turns = self._recent_turns(limit=1)
        feedback_state, _ = self._feedback_loop_state()
        if not turns and not draft:
            if app.ui_state.last_ingest_result:
                return (
                    "start",
                    f"Document armed: {safe_excerpt(app.ui_state.last_ingest_result.get('title', 'recent ingest'), limit=32)}. Ask below or press F9 to ingest again.",
                )
            return ("start", "Start here: type below, press Enter to send, or press F9 to ingest first.")
        if draft:
            return ("ask", "Draft ready. Press Enter to send.")
        if feedback_state == "pending":
            return ("review", "Adam replied. Inline review is armed in chat; press F7 to focus it if needed.")
        if turns:
            return ("continue", "Conversation active. Keep typing below, or press F5 for a clean session.")
        return ("start", "Session is armed. Begin when ready.")

    def _display_operator_text(self, text: str) -> str:
        cleaned = (text or "").strip()
        prefix = "Brian the operator:"
        if cleaned.lower().startswith(prefix.lower()):
            return cleaned.split(":", 1)[1].strip()
        return cleaned

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
                f"[bold {AMBER}]Aperture snapshot[/]\n"
                "No active set yet. Type in the composer or ingest a document to arm the scan.\n"
                "Press F8 for the wide aperture drawer once the loop is live."
            )
            return Panel(text, title="Aperture / Active Set", border_style=AMBER, style=f"on {SHADE}")
        behavior_mass = sum(float(item.get("selection", 0.0)) for item in active_items if item.get("domain") == "behavior")
        knowledge_mass = sum(float(item.get("selection", 0.0)) for item in active_items if item.get("domain") != "behavior")
        lead = "knowledge-led" if knowledge_mass > behavior_mass * 1.15 else "behavior-led" if behavior_mass > knowledge_mass * 1.15 else "balanced"
        focus_index = 0
        focus_item = active_items[focus_index]
        pulse = "▶"
        ingest = app.ui_state.last_ingest_result or {}
        knowledge_memes = [item for item in active_items if item.get("node_kind") != "memode" and item.get("domain") != "behavior"]
        behavior_memes = [item for item in active_items if item.get("node_kind") != "memode" and item.get("domain") == "behavior"]
        memodes = [item for item in active_items if item.get("node_kind") == "memode"]
        anchors = sorted(active_items, key=lambda item: float(item.get("regard", 0.0)), reverse=True)[:3]
        body = Text.from_markup(
            f"[bold {AMBER}]Bus-to-aperture read[/]\n"
            f"{lead} turn | docs={1 if ingest else 0} knowledge={knowledge_count} behavior={behavior_count} memodes={memode_count} items={len(active_items)}\n"
            f"Focus {pulse} [bold {NEON}]{safe_excerpt(focus_item.get('label', 'untitled'), limit=28)}[/] "
            f"({self._active_item_role(focus_item)})\n"
            f"NOW={self._selection_phrase(float(focus_item.get('selection', 0.0)))} | "
            f"MEM={self._regard_phrase(float(focus_item.get('regard', 0.0)))} | "
            f"HEAT={self._activation_phrase(float(focus_item.get('activation', 0.0)))}\n\n"
            f"[bold {AMBER}]Field dialogue[/]\n"
        )
        body.append(
            f"DOC ROOT   {safe_excerpt(ingest.get('title', 'none yet'), limit=48)}\n",
            style=EMBER,
        )
        body.append(
            "KNOWLEDGE  " + (" | ".join(safe_excerpt(item.get("label", "untitled"), limit=18) for item in knowledge_memes[:4]) or "quiet")
            + "\n",
            style=NEON,
        )
        body.append(
            "BEHAVIOR   " + (" | ".join(safe_excerpt(item.get("label", "untitled"), limit=18) for item in behavior_memes[:4]) or "quiet")
            + "\n",
            style=ROSE,
        )
        body.append(
            "MEMODES    " + (" | ".join(safe_excerpt(item.get("label", "untitled"), limit=18) for item in memodes[:3]) or "quiet")
            + "\n",
            style=ICE,
        )
        body.append(
            "\nRelation read\n",
            style=f"bold {AMBER}",
        )
        body.append(
            f"D -> @ -> {safe_excerpt(focus_item.get('label', 'untitled'), limit=30)} -> R\n",
            style=TEXT,
        )
        if knowledge_memes and behavior_memes:
            body.append(
                f"{safe_excerpt(knowledge_memes[0].get('label', 'untitled'), limit=26)} braids with "
                f"{safe_excerpt(behavior_memes[0].get('label', 'untitled'), limit=26)}\n",
                style=VIOLET,
            )
        if memodes:
            body.append(
                f"{safe_excerpt(memodes[0].get('label', 'untitled'), limit=30)} is bundling the current lane.\n\n",
                style=ICE,
            )
        body.append("Ranked pulls\n", style=f"bold {AMBER}")
        for index, item in enumerate(active_items[:5]):
            selection = float(item.get("selection", 0.0))
            regard = float(item.get("regard", 0.0))
            activation = float(item.get("activation", 0.0))
            indicator = pulse if index == focus_index else " "
            line_style = f"bold {NEON}" if indicator.strip() else TEXT
            body.append(
                f"{indicator} {safe_excerpt(item.get('label', 'untitled'), limit=28):<28} "
                f"{self._active_item_role(item):<18} "
                f"NOW {self._meter_bar(selection, scale=5.0, width=8)} "
                f"MEM {self._meter_bar(regard, scale=5.0, width=8, fill='=')} "
                f"HEAT {self._meter_bar(activation, scale=1.0, width=8, fill=':')}\n",
                style=line_style,
            )
        body.append(
            f"\n[bold {AMBER}]Recall anchors[/] "
            + (" | ".join(safe_excerpt(item.get("label", "untitled"), limit=18) for item in anchors) or "quiet")
            + "\n",
            style=ICE,
        )
        body.append(
            f"[bold {AMBER}]State[/] session={app.ui_state.session_title or app.ui_state.session_id or 'arming'} "
            f"state={'preview' if previewing else 'persisted'} items={len(active_items)} memes={meme_count} memodes={memode_count}\n"
            "This surface is the readable, pre-speech companion to the memgraph bus above. Press F8 for the full-width drawer.",
            style=MUTED,
        )
        return Panel(body, title="Aperture / Active Set", border_style=AMBER, style=f"on {SHADE}")

    def main_aperture_drawer_panel(self) -> Panel:
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
        if not active_items:
            text = Text.from_markup(
                f"[bold {AMBER}]Wide aperture drawer[/]\n"
                "The drawer opens a wider human-readable scan of the active set.\n"
                "No active set yet. Start with a prompt or ingest a document."
            )
            return Panel(text, title="Aperture Drawer", border_style=AMBER, style=f"on {SHADE}")
        behavior_items = [item for item in active_items if item.get("domain") == "behavior"]
        knowledge_items = [item for item in active_items if item.get("domain") != "behavior"]
        memode_items = [item for item in active_items if item.get("node_kind") == "memode"]
        focus_item = active_items[0]
        scan_width = max(18, min(52, (self.size.width or 120) - 26))
        sweep = scan_width // 2
        rail = "".join("█" if index == sweep else "▓" if abs(index - sweep) < 2 else "▒" if index % 3 == 0 else "░" for index in range(scan_width))
        anchors = sorted(active_items, key=lambda item: float(item.get("regard", 0.0)), reverse=True)[:3]
        hottest = sorted(active_items, key=lambda item: float(item.get("activation", 0.0)), reverse=True)[:3]
        body = Text.from_markup(
            f"[bold {AMBER}]Readable pull-down[/]\n"
            f"{rail}\n"
            f"This turn is reading as {'knowledge-led' if len(knowledge_items) >= len(behavior_items) else 'behavior-led'} with "
            f"{len(knowledge_items)} knowledge cues, {len(behavior_items)} behavioral anchors, and {len(memode_items)} memode bundle{'s' if len(memode_items) != 1 else ''}.\n"
            f"Current scan focus: [bold {NEON}]{safe_excerpt(focus_item.get('label', 'untitled'), limit=40)}[/] "
            f"({self._active_item_role(focus_item)}). It feels {self._selection_phrase(float(focus_item.get('selection', 0.0)))}, "
            f"{self._regard_phrase(float(focus_item.get('regard', 0.0)))}, and {self._activation_phrase(float(focus_item.get('activation', 0.0)))}.\n\n"
            f"[bold {AMBER}]Natural-language queue[/]\n"
        )
        for index, item in enumerate(active_items[:8]):
            prefix = "NOW" if index < 2 else "MEM" if item in anchors else "HEAT" if item in hottest else "SCAN"
            body.append(
                f"{prefix:<5} {safe_excerpt(item.get('label', 'untitled'), limit=36):<36} "
                f"is a {self._active_item_role(item)} with NOW {self._meter_bar(float(item.get('selection', 0.0)), scale=5.0, width=10)} "
                f"{self._selection_phrase(float(item.get('selection', 0.0))):<14} "
                f"MEM {self._meter_bar(float(item.get('regard', 0.0)), scale=5.0, width=10, fill='=')} "
                f"{self._regard_phrase(float(item.get('regard', 0.0))):<18} "
                f"HEAT {self._meter_bar(float(item.get('activation', 0.0)), scale=1.0, width=10, fill=':')} "
                f"{self._activation_phrase(float(item.get('activation', 0.0)))}\n",
                style=f"bold {NEON}" if item.get("node_id") == focus_item.get("node_id") else TEXT,
            )
        body.append(
            "\n[bold "
            + AMBER
            + "]Persistent recall anchors[/]\n"
            + "\n".join(
                f"- {safe_excerpt(item.get('label', 'untitled'), limit=58)} stays available because regard={float(item.get('regard', 0.0)):.2f}."
                for item in anchors
            ),
            style=ICE,
        )
        body.append(
            "\n\n[bold "
            + AMBER
            + "]Turn assembly[/]\n"
            + f"knowledge lane={len(knowledge_items)} | behavior lane={len(behavior_items)} | memode lane={len(memode_items)} | "
            + f"session={app.ui_state.session_title or app.ui_state.session_id or 'arming'}\n"
            + "Collapse with F8 when you want the compact telemetry stack back.",
            style=MUTED,
        )
        return Panel(body, title="Aperture Drawer", border_style=AMBER, style=f"on {SHADE_ALT}")

    def _selected_runtime_action(self) -> str:
        return self.query_one("#runtime_action_menu", ActionStrip).value or "review"

    def _set_turn_progress(self, *, phase: str, detail: str, feedback: str | None = None) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        current = app.ui_state.turn_progress or {}
        app.ui_state.turn_progress = {
            "phase": phase,
            "detail": detail,
            "started_at": current.get("started_at", monotonic()),
        }
        if feedback:
            app.ui_state.last_feedback = feedback
        if self.is_mounted:
            self.refresh_panels()

    def _clear_turn_progress(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        app.ui_state.turn_progress = None
        if self.is_mounted:
            self.refresh_panels()

    def _sync_turn_progress_from_log_event(self, event: Any) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if app.ui_state.turn_progress is None:
            return
        payload = getattr(event, "payload", {}) or {}
        event_name = str(getattr(event, "event", "") or "").lower()
        if event_name == "turn_preview_ready":
            self._set_turn_progress(
                phase="prompt ready",
                detail=(
                    f"active_set={payload.get('active_set_size', '?')} "
                    f"profile={payload.get('profile_name', 'pending')} "
                    f"pressure={payload.get('budget_pressure', 'n/a')}"
                ),
            )
        elif event_name == "generation_start":
            self._set_turn_progress(
                phase="generating",
                detail=(
                    f"{payload.get('backend', 'backend')} composing "
                    f"profile={payload.get('profile_name', 'pending')} "
                    f"mode={payload.get('effective_mode', 'n/a')}"
                ),
            )
        elif event_name == "generation_complete":
            self._set_turn_progress(
                phase="finalizing",
                detail=(
                    f"turn={safe_excerpt(str(payload.get('turn_id') or 'pending'), limit=18)} "
                    f"active_set={payload.get('active_set_size', '?')} "
                    f"pressure={payload.get('budget_pressure', 'n/a')}"
                ),
            )
        elif event_name == "hum_refreshed":
            self._set_turn_progress(
                phase="continuity",
                detail=(
                    f"hum refreshed recurring={payload.get('recurring_item_count', 0)} "
                    f"membrane={payload.get('membrane_event_count', 0)}"
                ),
            )

    def _set_runtime_action_progress(
        self,
        *,
        action: str,
        label: str,
        phase: str,
        step: int,
        total: int,
        detail: str,
        feedback: str | None = None,
    ) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        current = app.ui_state.action_progress or {}
        started_at = current.get("started_at", monotonic()) if current.get("action") == action else monotonic()
        app.ui_state.action_progress = {
            "action": action,
            "label": label,
            "phase": phase,
            "step": step,
            "total": total,
            "detail": detail,
            "started_at": started_at,
        }
        if feedback:
            app.ui_state.last_feedback = feedback
        self.refresh_panels()

    def _clear_runtime_action_progress(self, *, summary: str | None = None) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        app.ui_state.action_progress = None
        if summary:
            app.ui_state.last_action_summary = summary
        self.refresh_panels()

    def _runtime_action_running(self, action: str) -> bool:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        progress = app.ui_state.action_progress or {}
        return progress.get("action") == action

    def action_strip_status_lines(self, max_width: int) -> list[tuple[str, str]]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        model_status = self._model_status()
        profile = app.ui_state.current_profile or {}
        focus_id = getattr(self.app.focused, "id", "none") or "none"
        stage, _stage_note = self._conversation_stage()
        selected_value = self._selected_runtime_action()
        selected = ACTION_MENU_LABELS.get(selected_value, selected_value.replace("_", " "))
        log_state = "ready" if app.ui_state.conversation_log_path else "pending"
        action_progress = app.ui_state.action_progress or {}
        turn_progress = app.ui_state.turn_progress or {}
        runtime_line = (
            f"runtime={self._active_backend_label()} stage={model_status.get('stage', 'n/a')} "
            f"session={safe_excerpt(str(app.ui_state.session_title or app.ui_state.session_id or 'arming'), limit=28)} "
            f"profile={safe_excerpt(str(profile.get('profile_name', 'pending')), limit=24)} "
            f"focus={focus_id} convo={stage}"
        )
        if action_progress:
            started_at = float(action_progress.get("started_at", monotonic()))
            elapsed = _format_elapsed(monotonic() - started_at)
            step = int(action_progress.get("step", 0))
            total = int(action_progress.get("total", 1))
            detail_limit = max(18, max_width - 58)
            return [
                (safe_excerpt(runtime_line, limit=max_width), TEXT),
                (
                    safe_excerpt(
                        f"action={action_progress.get('label', 'unknown')} | phase={action_progress.get('phase', 'running')} | "
                        f"elapsed={elapsed} | progress={_progress_bar(step, total)} {step}/{total} | "
                        f"{safe_excerpt(str(action_progress.get('detail', 'working')), limit=detail_limit)}",
                        limit=max_width,
                    ),
                    ICE,
                ),
            ]
        if turn_progress:
            started_at = float(turn_progress.get("started_at", monotonic()))
            elapsed = _format_elapsed(monotonic() - started_at)
            detail_limit = max(18, max_width - 48)
            return [
                (safe_excerpt(runtime_line, limit=max_width), TEXT),
                (
                    safe_excerpt(
                        f"turn=Adam reply | phase={turn_progress.get('phase', 'working')} | elapsed={elapsed} | "
                        f"{safe_excerpt(str(turn_progress.get('detail', 'working')), limit=detail_limit)}",
                        limit=max_width,
                    ),
                    ICE,
                ),
            ]
        last_summary = app.ui_state.last_action_summary or app.ui_state.last_feedback or "No action has run yet."
        summary_limit = max(24, max_width - 62)
        action_line = (
            f"selected={ACTION_STRIP_NUMBER.get(selected_value, 1):02d} {selected} | aperture={'open' if app.ui_state.aperture_drawer_open else 'closed'} "
            f"| review={'armed' if self._feedback_loop_state()[0] == 'pending' else 'clear'} | transcript={log_state} "
            f"| last={safe_excerpt(str(last_summary), limit=summary_limit)}"
        )
        return [
            (safe_excerpt(runtime_line, limit=max_width), TEXT),
            (safe_excerpt(action_line, limit=max_width), ICE if focus_id == "runtime_action_menu" else MUTED),
        ]

    def main_turn_status_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        progress = app.ui_state.turn_progress or {}
        active_items = self._active_items()
        phase, stage_note = self._conversation_stage()
        model_status = self._model_status()
        if progress:
            started_at = float(progress.get("started_at", monotonic()))
            spinner = "|/-\\"[int(monotonic() * 4) % 4]
            text = Text.from_markup(
                f"[bold {ICE}]Adam status[/]\n"
                f"{spinner} {safe_excerpt(str(progress.get('phase', 'working')), limit=18)}\n"
                f"elapsed={_format_elapsed(monotonic() - started_at)}\n"
                f"{safe_excerpt(str(progress.get('detail', 'working')), limit=72)}\n"
                f"items={len(active_items)} review={'armed' if self._feedback_loop_state()[0] == 'pending' else 'clear'}"
            )
            return Panel(text, title="Live Turn Status", border_style=ICE, style=f"on {SHADE_ALT}")
        reasoning_state = "present" if app.ui_state.last_reasoning else "quiet"
        text = Text.from_markup(
            f"[bold {AMBER}]Adam status[/]\n"
            f"phase={phase}\n"
            f"{safe_excerpt(stage_note, limit=72)}\n"
            f"model={model_status.get('stage', 'n/a')} reasoning={reasoning_state}\n"
            f"items={len(active_items)} review={'armed' if self._feedback_loop_state()[0] == 'pending' else 'clear'}"
        )
        return Panel(text, title="Live Turn Status", border_style=AMBER, style=f"on {SHADE_ALT}")

    def main_thinking_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        profile = app.ui_state.current_profile or {}
        budget = app.ui_state.current_budget or {}
        hum = self._current_hum_snapshot()
        hum_payload = self._current_hum_payload()
        reasoning_mode = app.ui_state.reasoning_mode
        active_items = self._active_items()
        membrane_events = self._recent_membrane_events(limit=4)
        latest_feedback = self._recent_feedback_entries(limit=1)
        latest_feedback_entry = latest_feedback[0] if latest_feedback else None
        feedback_phrase = self._feedback_status_phrase(latest_feedback_entry)
        reasoning_text = (app.ui_state.last_reasoning or "").strip()
        answer_text = (app.ui_state.last_response or "").strip()
        reasoning_chars = len(reasoning_text)
        dominant_lane = self._dominant_active_lane(active_items)
        focus_item = (
            max(active_items, key=lambda item: float(item.get("selection", 0.0)))
            if active_items
            else {"label": "none yet", "selection": 0.0, "regard": 0.0, "activation": 0.0}
        )
        reasoning_lines = self._useful_reasoning_lines(reasoning_text, limit=6, line_limit=118)
        answer_lines = self._artifact_excerpt_lines(answer_text, limit=5, line_limit=118)
        answer_beats = self._chain_like_lines(answer_text, limit=8, line_limit=112)
        trace_lines = [
            f">> {item.get('label', 'untitled')} sel={float(item.get('selection', 0.0)):.2f} "
            f"reg={float(item.get('regard', 0.0)):.2f} act={float(item.get('activation', 0.0)):.2f}"
            for item in self._trace_items()[:3]
        ]
        if not trace_lines:
            trace_lines = [">> no active consideration trace yet"]
        state = "draft-armed" if self._composer_text().strip() else "persisted"
        body = Text()
        if reasoning_mode == "hum_live":
            continuity = hum_payload.get("continuity", {}) if isinstance(hum_payload, dict) else {}
            recurring_items = list(continuity.get("recurring_items") or [])
            overlap = continuity.get("active_set_overlap") or {}
            feedback_recent = list(((continuity.get("feedback_summary") or {}).get("recent")) or [])
            membrane_recent = list(((continuity.get("membrane_summary") or {}).get("recent")) or [])
            surface_stats = dict(hum_payload.get("surface_stats") or {})
            surface_lines = self._hum_surface_lines(hum_payload, hum)
            token_lines = self._hum_table_lines(hum_payload)
            body.append("Hum entries\n", style=f"bold {ICE}")
            if surface_lines:
                body.append("\n".join(surface_lines), style=ICE)
            else:
                body.append(
                    "No bounded hum artifact yet. Persist another turn or explicit feedback to create one.",
                    style=MUTED,
                )
            body.append("\n\n", style=TEXT)
            body.append("[HUM_STATS]\n", style=f"bold {NEON}")
            if surface_stats:
                body.append(
                    f"entries={surface_stats.get('entries', 0)} lines_total={surface_stats.get('lines_total', 0)} "
                    f"words={surface_stats.get('words', 0)} unique_tokens={surface_stats.get('unique_tokens', 0)} "
                    f"repeated_tokens={surface_stats.get('repeated_tokens', 0)} hapax_tokens={surface_stats.get('hapax_tokens', 0)}\n"
                    f"type_token_ratio={float(surface_stats.get('type_token_ratio', 0.0) or 0.0):.3f} "
                    f"avg_token_len={float(surface_stats.get('avg_token_len', 0.0) or 0.0):.2f} "
                    f"avg_line_words={float(surface_stats.get('avg_line_words', 0.0) or 0.0):.2f} "
                    f"chars_total={surface_stats.get('chars_total', 0)}",
                    style=TEXT,
                )
            else:
                body.append("Hum stats are not available yet.", style=MUTED)
            body.append("\n\n", style=TEXT)
            body.append("[HUM_METRICS]\n", style=f"bold {AMBER}")
            body.append(
                f"window={hum.get('turn_window_size', 0)} recurring={len(recurring_items)} overlap={int(overlap.get('count', 0) or 0)} "
                f"feedback={len(feedback_recent)} membrane={len(membrane_recent)}\n"
                f"feedback_state={feedback_phrase}",
                style=TEXT,
            )
            body.append("\n\n", style=TEXT)
            body.append("[HUM_TABLE]\n", style=f"bold {ICE}")
            if token_lines:
                body.append("\n".join(token_lines), style=TEXT)
            else:
                body.append("No motif counts are recorded yet.", style=MUTED)
            body.append("\n\n", style=TEXT)
            body.append("Carryover anchors\n", style=f"bold {NEON}")
            if recurring_items:
                body.append(
                    "\n".join(
                        f"- {safe_excerpt(str(item.get('label') or 'untitled'), limit=52)} across T{', '.join(str(value) for value in item.get('turn_indices', [])[:3])}"
                        for item in recurring_items[:3]
                    ),
                    style=TEXT,
                )
            elif overlap.get("labels"):
                body.append(
                    "- latest overlap: " + " | ".join(safe_excerpt(str(label), limit=24) for label in overlap.get("labels", [])[:3]),
                    style=TEXT,
                )
            else:
                body.append(
                    f"- seed-state only; focus={safe_excerpt(str(focus_item.get('label', 'none yet')), limit=44)}\n"
                    f"- lane={dominant_lane} items={len(active_items)}",
                    style=TEXT,
                )
            body.append("\n\n", style=TEXT)
            body.append("Membrane / feedback\n", style=f"bold {AMBER}")
            memory_lines: list[str] = []
            if feedback_recent:
                memory_lines.extend(
                    f"- T{item.get('turn_index', '?')} {str(item.get('verdict') or 'skip').upper()} :: {safe_excerpt(str(item.get('explanation') or 'no explanation'), limit=88)}"
                    for item in feedback_recent[:2]
                )
            else:
                memory_lines.append(f"- {feedback_phrase}")
            if membrane_recent:
                memory_lines.extend(
                    f"- {str(item.get('event_type') or 'UNKNOWN').upper()} :: {safe_excerpt(str(item.get('detail') or 'no detail'), limit=88)}"
                    for item in membrane_recent[:2]
                )
            else:
                memory_lines.extend(f"- {line}" for line in self._membrane_record_lines(membrane_events, limit=2))
            body.append("\n".join(memory_lines), style=TEXT)
            body.append("\n\n", style=TEXT)
        elif reasoning_mode == "chain_like":
            body.append("Response beats\n", style=f"bold {NEON}")
            if answer_beats:
                body.append("\n".join(answer_beats), style=TEXT)
            else:
                body.append("No operator-facing answer is available for beat reduction yet.", style=MUTED)
            body.append("\n\n", style=TEXT)
            if reasoning_lines:
                body.append("Reasoning signal\n", style=f"bold {ICE}")
                body.append("\n".join(f"- {line}" for line in reasoning_lines[:3]), style=TEXT)
                body.append("\n\n", style=TEXT)
            body.append("Assembly anchors\n", style=f"bold {AMBER}")
            body.append(
                f"- focus={safe_excerpt(str(focus_item.get('label', 'none yet')), limit=44)} lane={dominant_lane} items={len(active_items)}\n"
                f"- pressure={budget.get('pressure_level', 'n/a')} remaining_input={budget.get('remaining_input_tokens', 'n/a')} count_method={budget.get('count_method', 'n/a')}\n"
                f"- feedback={feedback_phrase}\n"
                f"- membrane={', '.join(str(event.get('event_type') or 'UNKNOWN').upper() for event in membrane_events[:3]) or 'no events yet'}",
                style=TEXT,
            )
            body.append("\n\n", style=TEXT)
        else:
            body.append("Response material\n", style=f"bold {NEON}")
            if answer_lines:
                body.append("\n".join(answer_lines), style=TEXT)
            else:
                body.append("No operator-facing answer is persisted yet.", style=MUTED)
            body.append("\n\n", style=TEXT)
            body.append("Reasoning signal\n", style=f"bold {AMBER}")
            if reasoning_lines:
                body.append("\n".join(reasoning_lines), style=TEXT)
            elif reasoning_text:
                body.append(
                    "Visible reasoning was captured, but it mostly echoed prompt scaffolding for this turn, so it is suppressed here.",
                    style=MUTED,
                )
            else:
                body.append(
                    "No model-emitted reasoning artifact was captured for this turn.",
                    style=MUTED,
                )
            body.append("\n\n", style=TEXT)
            body.append("Runtime condition\n", style=f"bold {ICE}")
            body.append(
                f"- state={state} profile={profile.get('profile_name', 'pending')} mode={profile.get('requested_mode', 'pending')} -> {profile.get('effective_mode', 'pending')}\n"
                f"- pressure={budget.get('pressure_level', 'n/a')} response_cap={profile.get('response_char_cap', 'n/a')} retrieval_depth={profile.get('retrieval_depth', 'n/a')}\n"
                f"- lane={dominant_lane} focus={safe_excerpt(str(focus_item.get('label', 'none yet')), limit=40)} reasoning_chars={reasoning_chars}\n"
                f"- feedback={feedback_phrase}",
                style=TEXT,
            )
            body.append("\n\n", style=TEXT)
            body.append("Membrane record\n", style=f"bold {ICE}")
            body.append("\n".join(f"- {line}" for line in self._membrane_record_lines(membrane_events, limit=3)), style=TEXT)
            body.append("\n\n", style=TEXT)
        body.append("Consideration trace\n", style=f"bold {NEON}")
        body.append("\n".join(trace_lines), style=ICE if active_items else TEXT)
        panel_title = {
            "reasoning": "Reasoning",
            "chain_like": "Chain-Like Trace",
            "hum_live": "Hum Live Trace",
        }.get(reasoning_mode, "Reasoning")
        border = ICE if reasoning_mode == "hum_live" and hum.get("present") else NEON if active_items or membrane_events else AMBER
        return Panel(body, title=panel_title, border_style=border, style=f"on {SHADE}")

    def main_hum_panel(self) -> Panel:
        hum = self._current_hum_snapshot()
        if hum.get("present"):
            recurrence = "yes" if hum.get("cross_turn_recurrence_present") else "seed-state"
            body = Text.from_markup(
                f"[bold {AMBER}]Hum fact surface[/]\n"
                f"generated={hum.get('generated_at') or 'n/a'}\n"
                f"window={hum.get('turn_window_size', 0)} recurrence={recurrence}\n"
                f"turn={hum.get('latest_turn_id') or 'n/a'}\n\n"
            )
            body.append(safe_excerpt(hum.get("text_surface") or "", limit=260), style=TEXT)
            return Panel(body, title="Hum / Continuity", border_style=ICE, style=f"on {SHADE_ALT}")
        body = Text.from_markup(
            f"[bold {AMBER}]Hum fact surface[/]\n"
            "No bounded hum artifact yet.\n"
            "After persisted turns or explicit feedback exist, this panel reports the current continuity artifact as a matter of fact."
        )
        return Panel(body, title="Hum / Continuity", border_style=AMBER, style=f"on {SHADE_ALT}")

    def main_event_bus_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        profile = app.ui_state.current_profile or {}
        health = self._health()
        transcript_path = app.ui_state.conversation_log_path or "pending"
        recent_feedback = self._recent_feedback_entries(limit=2)
        feedback_lines = [
            f"T{item['turn_index']} {str(item['verdict']).upper()} :: {safe_excerpt(item['explanation'] or 'no explanation', limit=64)}"
            for item in reversed(recent_feedback)
        ]
        if not feedback_lines:
            feedback_lines = ["No feedback events yet. Press F7 to focus the inline review fields in chat."]
        recent_events = self._event_lines[-6:]
        if not recent_events:
            recent_events = ["[INFO] Event bus is quiet. Start a turn or ingest a document to populate it."]
        body = Text.from_markup(
            f"[bold {AMBER}]Session state[/]\n"
            f"experiment={app.ui_state.experiment_name or app.ui_state.experiment_id or 'live-arming'} "
            f"profile={profile.get('profile_name', 'pending')} "
            f"observatory={(app.ui_state.observatory_status or {}).get('url', 'offline')}\n"
            f"graph=memes {health['memes']} memodes {health['memodes']} triadic {health['triadic_closure']:.3f}\n"
            f"transcript={transcript_path}\n"
            "open transcript via the action strip -> Open Conversation Log\n"
            f"last_status={safe_excerpt(app.ui_state.last_feedback, limit=108)}\n\n"
            f"[bold {AMBER}]Feedback state[/]\n"
            + "\n".join(feedback_lines)
            + "\n\n"
        )
        body.append("Recent event flow\n", style=f"bold {ICE}")
        for line in recent_events:
            style = ROSE if "[ERROR]" in line else ICE if "[WARN]" in line else TEXT
            body.append(f"{safe_excerpt(line, limit=140)}\n", style=style)
        return Panel(body, title="Event Bus", border_style=ICE, style=f"on {SHADE_ALT}")

    def main_runtime_chyron_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        profile = app.ui_state.current_profile or {}
        budget = app.ui_state.current_budget or {}
        active_items = self._active_items()
        trace_items = self._trace_items()
        recent_feedback = self._recent_feedback_entries(limit=1)
        latest_feedback = recent_feedback[0] if recent_feedback else None
        transcript_name = Path(app.ui_state.conversation_log_path).name if app.ui_state.conversation_log_path else "pending"
        ingest = app.ui_state.last_ingest_result or {}
        phase_index = 0
        if app.ui_state.session_id:
            phase_index = 1
        if app.ui_state.preview_active_set:
            phase_index = 3
        if app.ui_state.last_response:
            phase_index = 6
        rendered_steps = " > ".join(
            step.upper() if index == phase_index else step for index, step in enumerate(AdamSigil.LOOP)
        )
        selection_peak = max((float(item.get("selection", 0.0)) for item in trace_items), default=0.0)
        regard_peak = max((float(item.get("regard", 0.0)) for item in trace_items), default=0.0)
        behavior_count = sum(1 for item in active_items if item.get("domain") == "behavior" and item.get("node_kind") != "memode")
        knowledge_count = sum(1 for item in active_items if item.get("domain") != "behavior" and item.get("node_kind") != "memode")
        memode_count = sum(1 for item in active_items if item.get("node_kind") == "memode")
        feedback_state = (
            f"{str(latest_feedback.get('verdict', 'pending')).upper()} T{latest_feedback.get('turn_index', '?')}"
            if latest_feedback
            else ("PENDING_REVIEW" if self._feedback_loop_state()[0] == "pending" else "QUIET")
        )
        event_summary = safe_excerpt(self._event_lines[-1] if self._event_lines else "No recent event flow.", limit=132)
        text = Text.from_markup(
            f"[bold {AMBER}]Runtime Loop[/] {rendered_steps}\n"
            f"docs={1 if ingest else 0} knowledge={knowledge_count} behavior={behavior_count} memodes={memode_count} "
            f"active={len(active_items)}/{profile.get('max_context_items', 'n/a')} "
            f"pressure={budget.get('pressure_level', 'n/a')} reasoning={'present' if app.ui_state.last_reasoning else 'quiet'}\n"
            f"selection={selection_peak:.2f} regard={regard_peak:.2f} feedback={feedback_state} transcript={transcript_name}\n"
            f"event={event_summary}"
        )
        return Panel(text, title="Runtime / Event Chyron", border_style=AMBER, style=f"on {SHADE_ALT}")

    def _dialogue_card_backgrounds(self) -> tuple[str, str]:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if app.current_ui_look() == "typewriter_light":
            return ("#fbf7f0", "#efd1de")
        return ("#000000", "#321221")

    def main_chat_exchange_panel(self):
        app = self.app
        assert isinstance(app, EdenTuiApp)
        brian_background, adam_background = self._dialogue_card_backgrounds()
        turns = self._all_turns()
        if self._transcript_cache_session_id != app.ui_state.session_id:
            self._invalidate_transcript_cache()
        if not self._transcript_cache_panels:
            transcript: list[Panel] = []
            for turn in turns:
                feedback_entries = app.runtime.store.list_feedback_for_turn(turn["id"])
                latest_feedback = feedback_entries[-1] if feedback_entries else None
                if latest_feedback is not None:
                    verdict = str(latest_feedback.get("verdict", "skip")).upper()
                    adam_title = f"Adam / T{turn['turn_index']} / {verdict}"
                    adam_border = NEON if verdict == "ACCEPT" else ICE if verdict == "EDIT" else EMBER if verdict == "REJECT" else AMBER
                elif turn["id"] == app.ui_state.last_turn_id:
                    adam_title = f"Adam / T{turn['turn_index']} / AWAITING REVIEW"
                    adam_border = ROSE
                else:
                    adam_title = f"Adam / T{turn['turn_index']}"
                    adam_border = AMBER
                brian_text = self._display_operator_text(turn.get("user_text") or "") or " "
                adam_text, _ = app.runtime.sanitize_operator_response(
                    turn.get("membrane_text") or turn.get("response_text") or "",
                    response_char_cap=1600,
                )
                adam_text = adam_text or " "
                transcript.append(
                    Panel(
                        Text(brian_text, style=TEXT),
                        title=f"Brian / T{turn['turn_index']}",
                        border_style=MUTED,
                        style=f"on {brian_background}",
                    )
                )
                transcript.append(
                    Panel(
                        Text(adam_text, style=TEXT),
                        title=adam_title,
                        border_style=adam_border,
                        style=f"on {adam_background}",
                    )
                )
            self._transcript_cache_session_id = app.ui_state.session_id
            self._transcript_cache_panels = tuple(transcript)
        transcript = list(self._transcript_cache_panels)
        operator_live = self._composer_text().strip()
        if operator_live:
            transcript.append(
                Panel(
                    Text(operator_live, style=TEXT),
                    title="Brian / Draft",
                    border_style=ROSE,
                    style=f"on {brian_background}",
                )
            )
        if not transcript:
            transcript.append(
                Panel(
                    Text(
                        "Start here: type in the composer below and press Enter to send. Press F9 first if you want to ingest a document with a framing note.",
                        style=MUTED,
                    ),
                    title="Adam Dialogue",
                    border_style=AMBER,
                    style=f"on {SHADE}",
                )
            )
        return Group(*transcript)

    def main_inline_feedback_status_panel(self) -> Panel:
        state, latest_entry = self._feedback_loop_state()
        form = self._inline_feedback_form_state()
        if state == "pending":
            text = Text.from_markup(
                "code="
                + (form["raw_code"] or "·")
                + " -> "
                + str(form["verdict"] or "pending")
                + " | enter="
                + ("submits" if form["ready"] else "awaiting fields")
                + " | explanation="
                + ("ready" if form["explanation"] else ("needed" if form["needs_explanation"] else "n/a"))
                + " | corrected="
                + ("ready" if form["corrected"] else ("needed" if form["needs_corrected"] else "n/a"))
                + " | submit="
                + ("armed" if form["ready"] else "waiting")
            )
            border = NEON if form["ready"] else ROSE
        elif state == "reviewed" and latest_entry is not None:
            text = Text.from_markup(
                f"Latest stored verdict={str(latest_entry.get('verdict', 'skip')).upper()} | "
                f"turn=T{latest_entry.get('turn_index', '?')} | "
                f"{safe_excerpt(latest_entry.get('explanation') or 'no explanation', limit=96)} | "
                "edit fields below to append another review event if needed"
            )
            border = NEON if str(latest_entry.get("verdict", "")).lower() == "accept" else AMBER
        else:
            text = Text.from_markup("Reply review unlocks after Adam answers.")
            border = AMBER
        return Panel(text, title="Explicit Feedback", border_style=border, style=f"on {SHADE_ALT}")

    def deck_summary_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        model_status = self._model_status()
        text = Text.from_markup(
            f"[bold {AMBER}]Deck / Detailed Surfaces[/]\n"
            "Budget, deeper reasoning, history, ingest, launch controls, and TUI look selection live here; the prime surface keeps dialogue first while telemetry stays visible.\n\n"
            f"runtime={app.runtime.settings.model_backend}\n"
            f"model={model_status.get('label', 'n/a')}\n"
            f"cache={model_status.get('stage', 'n/a')}\n"
            f"look={LOOK_LABELS.get(self.current_ui_look(), 'Amber Dark')}\n"
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
            f"look={LOOK_LABELS.get(self.current_ui_look(), 'Amber Dark')}\n"
            f"low_motion={app.runtime.settings.low_motion} debug={app.runtime.settings.debug}\n"
            f"feedback={safe_excerpt(app.ui_state.last_feedback, limit=180)}"
        )
        return Panel(text, title="Status", border_style=AMBER)

    def deck_ingest_help_panel(self) -> Panel:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        ingest = app.ui_state.last_ingest_result
        text = Text.from_markup(
            f"[bold {AMBER}]Corpus Intake[/]\n"
            "Use the ingest bay to load a PDF or other supported document with a framing prompt.\n"
            "The framing prompt becomes graph-conditioning material so Adam can retrieve the work more intentionally later.\n\n"
            + (
                f"latest={safe_excerpt(ingest.get('title', 'document'), limit=44)} "
                f"brief={'yes' if ingest.get('briefing') else 'no'} "
                f"meme+memode={ingest.get('meme_count', 0)}/{ingest.get('memode_count', 0)}"
                if ingest
                else "latest=none yet"
            )
        )
        return Panel(text, title="Intake Guidance", border_style=AMBER)

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
        for event in events[self._seen_log_count :]:
            payload = safe_excerpt(str(event.payload or ""), limit=68)
            line = f"[{event.level}] {event.event} :: {safe_excerpt(event.message, limit=78)}"
            if payload and payload != "{}":
                line += f" | {payload}"
            self._record_event_line(line)
            self._sync_turn_progress_from_log_event(event)
        self._seen_log_count = len(events)
        latest_feedback = self._recent_feedback_entries(limit=1)
        feedback_signature = None
        if latest_feedback:
            feedback_signature = (
                str(latest_feedback[0].get("id") or ""),
                str(latest_feedback[0].get("created_at") or ""),
            )
        hum = self._current_hum_snapshot()
        hum_signature = (
            str(hum.get("generated_at") or ""),
            str(hum.get("latest_turn_id") or ""),
        )
        if feedback_signature != self._last_feedback_signature or hum_signature != self._last_hum_signature:
            self._last_feedback_signature = feedback_signature
            self._last_hum_signature = hum_signature
            if latest_feedback:
                latest = latest_feedback[0]
                latest_summary = (
                    f"Popup review stored {str(latest.get('verdict', 'skip')).upper()} for "
                    f"T{latest.get('turn_index', '?')}."
                )
                if " recorded at " not in str(app.ui_state.last_feedback or ""):
                    app.ui_state.last_feedback = latest_summary
            self._invalidate_transcript_cache()
            self._mark_graph_dirty()
            if self.is_mounted:
                self.refresh_panels()
        if app.ui_state.action_progress is not None and self.is_mounted:
            self.query_one("#runtime_action_menu", ActionStrip).refresh()
        if app.ui_state.turn_progress is not None and self.is_mounted:
            self.query_one("#turn_status_panel", Static).update(self.main_turn_status_panel())
            self.query_one("#runtime_action_menu", ActionStrip).refresh()

    def _composer_text(self) -> str:
        return self.query_one("#composer_input", TextArea).text

    def _set_text_area(self, selector: str, value: str) -> None:
        self.query_one(selector, TextArea).load_text(value)

    def _reset_inline_feedback_inputs(self) -> None:
        try:
            self.query_one("#inline_feedback_verdict_input", Input).value = ""
            self._set_text_area("#inline_feedback_explanation_input", "")
            self._set_text_area("#inline_feedback_corrected_input", "")
        except Exception:
            return

    def focus_composer(self) -> TextArea:
        composer = self.query_one("#composer_input", TextArea)
        composer.focus()
        return composer

    def _schedule_preview_refresh(self) -> None:
        if not self.app.ui_state.session_id:
            return
        self._preview_generation += 1
        generation = self._preview_generation
        if self._preview_running:
            self._preview_rerun_requested = True
            return
        if self._preview_task is not None and not self._preview_task.done():
            self._preview_task.cancel()
        self._preview_task = asyncio.create_task(self._refresh_preview(generation))

    async def _refresh_preview(self, generation: int) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        await asyncio.sleep(0.55)
        if generation != self._preview_generation or not app.ui_state.session_id:
            return
        self._preview_running = True
        try:
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
            if not self.is_mounted:
                return
            self.query_one("#runtime_action_menu", ActionStrip).refresh()
            top_aperture = self.main_aperture_drawer_panel() if app.ui_state.aperture_drawer_open else self.main_aperture_panel()
            self.query_one("#aperture_drawer_panel", Static).update(top_aperture)
            self.query_one("#active_aperture_panel", Static).update(top_aperture)
            self.query_one("#thinking_panel", Static).update(self.main_thinking_panel())
            self.query_one("#runtime_chyron_panel", Static).update(self.main_runtime_chyron_panel())
        finally:
            self._preview_running = False
            if self._preview_rerun_requested and generation != self._preview_generation:
                self._preview_rerun_requested = False
                self._preview_task = asyncio.create_task(self._refresh_preview(self._preview_generation))

    @on(TextArea.Changed, "#composer_input")
    def handle_composer_changed(self, _event) -> None:
        self._refresh_composer_surfaces()
        self._schedule_preview_refresh()

    async def _submit_inline_feedback_from_fields(self) -> None:
        form = self._inline_feedback_form_state()
        verdict = form["verdict"]
        if verdict is None:
            self.app.ui_state.last_feedback = "Review code must be A, E, R, or S."
            self.refresh_panels()
            return
        await self.submit_feedback(
            verdict,
            explanation=form["explanation"],
            corrected=form["corrected"],
        )

    @on(Input.Changed, "#inline_feedback_verdict_input")
    def handle_inline_feedback_input_changed(self, _event: Input.Changed) -> None:
        self._sync_inline_feedback_surface()
        self.query_one("#inline_feedback_status_panel", Static).update(self.main_inline_feedback_status_panel())

    @on(TextArea.Changed, "#inline_feedback_explanation_input")
    @on(TextArea.Changed, "#inline_feedback_corrected_input")
    def handle_inline_feedback_text_changed(self, _event: TextArea.Changed) -> None:
        self.query_one("#inline_feedback_status_panel", Static).update(self.main_inline_feedback_status_panel())

    @on(Input.Submitted, "#inline_feedback_verdict_input")
    async def handle_inline_feedback_verdict_submitted(self, _event: Input.Submitted) -> None:
        verdict, _ = self._inline_feedback_intent()
        if verdict == "skip":
            await self._submit_inline_feedback_from_fields()
            return
        if verdict in {"accept", "edit", "reject"}:
            self.query_one("#inline_feedback_explanation_input", TextArea).focus()
            return
        self.app.ui_state.last_feedback = "Review code must be A, E, R, or S."
        self.refresh_panels()
        self.query_one("#inline_feedback_verdict_input", Input).focus()

    @on(ReviewTextArea.Submitted, "#inline_feedback_explanation_input")
    async def handle_inline_feedback_explanation_submitted(self, _event: ReviewTextArea.Submitted) -> None:
        verdict, _ = self._inline_feedback_intent()
        if verdict == "edit":
            self.query_one("#inline_feedback_corrected_input", TextArea).focus()
            return
        await self._submit_inline_feedback_from_fields()

    @on(ReviewTextArea.Submitted, "#inline_feedback_corrected_input")
    async def handle_inline_feedback_corrected_submitted(self, _event: ReviewTextArea.Submitted) -> None:
        await self._submit_inline_feedback_from_fields()

    async def _send_turn(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        text = self._composer_text().strip()
        if not text or not app.ui_state.session_id:
            return
        self._set_turn_progress(
            phase="preflight",
            detail="binding current draft and checking backend readiness",
            feedback="Dispatching Adam reply...",
        )
        try:
            if not await self._ensure_backend_ready(prepare=True):
                self._clear_turn_progress()
                return
            self._set_turn_progress(
                phase="assembling",
                detail="assembling active set and prompt context",
            )
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
            self._mark_graph_dirty()
            self._set_turn_progress(
                phase="review",
                detail=f"T{outcome.turn['turn_index']} stored; arming inline review",
            )
            app.ui_state.last_feedback = (
                f"Saved turn T{outcome.turn['turn_index']} from Brian. "
                "Inline review is armed in chat."
            )
            self._write_forensic(
                f"[INFO] Turn T{outcome.turn['turn_index']} stored :: active_set={len(outcome.active_set)} pressure={outcome.budget.get('pressure_level', 'n/a')}"
            )
            self._set_text_area("#composer_input", "")
            await self._sync_conversation_log()
            self.refresh_panels()
            await self.handle_review()
            self.focus_composer()
            self._scroll_chat_to_end()
            self._schedule_preview_refresh()
        except Exception as exc:
            app.ui_state.last_feedback = f"Turn failed: {exc}"
            self._write_forensic(f"[ERROR] Turn failed :: {type(exc).__name__}: {exc}")
            self.refresh_panels()
            return
        finally:
            self._clear_turn_progress()

    @on(ComposerTextArea.Submitted, "#composer_input")
    async def handle_composer_submitted(self, _event: ComposerTextArea.Submitted) -> None:
        await self._send_turn()

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
            self._reset_inline_feedback_inputs()
            self._mark_graph_dirty()
            await self._sync_conversation_log()
            self._schedule_preview_refresh()
            self.focus_composer()
            self._scroll_chat_to_end()
        self.refresh_panels()

    async def ingest_path(self, path: str, *, briefing: str = "") -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.experiment_id:
            return
        if not path:
            return
        result = await asyncio.to_thread(
            partial(
                app.runtime.ingest_document,
                experiment_id=app.ui_state.experiment_id,
                path=path,
                briefing=briefing,
                session_id=app.ui_state.session_id,
            )
        )
        app.ui_state.last_ingest_result = result
        self._mark_graph_dirty()
        app.ui_state.last_feedback = (
            f"Ingested {result['title']} into the memgraph with "
            f"{result['meme_count']} memes / {result['memode_count']} memodes"
            + (f" plus briefing lens {result['brief_meme_count']}/{result['brief_memode_count']}." if result["briefing"] else ".")
        )
        self._write_forensic(
            f"[INFO] Ingested corpus root :: {result['title']} "
            f"(memes={result['meme_count']} memodes={result['memode_count']} brief={bool(result['briefing'])})"
        )
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
        export_dir = Path(next(iter(paths.values()))).parent if paths else app.runtime.export_dir_for_experiment(app.ui_state.experiment_id)
        names = [Path(paths[key]).name for key in ("graph_html", "basin_html", "geometry_html") if key in paths]
        app.ui_state.last_feedback = f"Exports generated in {export_dir}: {', '.join(names)}"
        self._write_forensic(f"[INFO] Exports generated :: {export_dir}")
        self.refresh_panels()

    async def handle_observatory(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        summary = "Observatory action cancelled before completion."
        try:
            self._set_runtime_action_progress(
                action="observatory",
                label="Open Browser Observatory",
                phase="Ensuring observatory server",
                step=1,
                total=3,
                detail="Checking for a reusable local observatory server.",
                feedback="Observatory: ensuring the local server is available.",
            )
            status = await asyncio.to_thread(partial(app.runtime.start_observatory, reuse_existing=True))
            app.ui_state.observatory_status = status

            experiment_id = app.ui_state.experiment_id
            session_id = app.ui_state.session_id
            if experiment_id is None:
                latest = app.runtime.store.get_latest_experiment()
                experiment_id = latest["id"] if latest is not None else None
                session_id = None

            export_detail = (
                f"Refreshing observability artifacts for experiment {safe_excerpt(experiment_id, limit=20)}."
                if experiment_id is not None
                else "No active experiment; skipping export and using the server root."
            )
            self._set_runtime_action_progress(
                action="observatory",
                label="Open Browser Observatory",
                phase="Exporting observatory payloads",
                step=2,
                total=3,
                detail=export_detail,
                feedback=(
                    f"Observatory: exporting payloads for {safe_excerpt(experiment_id, limit=20)}."
                    if experiment_id is not None
                    else "Observatory: no active experiment, opening the server root."
                ),
            )
            if experiment_id is not None:
                await asyncio.to_thread(
                    partial(app.runtime.export_observability, experiment_id=experiment_id, session_id=session_id)
                )

            target_url = _observatory_target_url(app.runtime, status, experiment_id)
            self._set_runtime_action_progress(
                action="observatory",
                label="Open Browser Observatory",
                phase="Opening browser",
                step=3,
                total=3,
                detail=f"Launching the system browser for {safe_excerpt(target_url, limit=88)}.",
                feedback="Observatory: launching the browser.",
            )
            launch = await asyncio.to_thread(partial(open_browser_url, target_url))
            if launch.ok:
                summary = f"Observatory {'reused' if status['reused_existing'] else 'started'} at {target_url}"
                app.ui_state.last_feedback = summary
                self._write_forensic(
                    f"[INFO] Observatory {'reused' if status['reused_existing'] else 'started'} :: {target_url} via {launch.method}"
                )
            else:
                summary = f"Observatory ready at {target_url}, but browser launch failed: {launch.detail}"
                app.ui_state.last_feedback = summary
                self._write_forensic(
                    f"[WARN] Observatory ready but browser launch failed :: {target_url} :: {launch.detail}"
                )
        except asyncio.CancelledError:
            app.ui_state.last_feedback = summary
            self._write_forensic("[WARN] Observatory action cancelled.")
            raise
        except Exception as exc:
            summary = f"Observatory failed: {exc}"
            app.ui_state.last_feedback = summary
            self._write_forensic(f"[WARN] Observatory action failed :: {exc}")
        finally:
            self._clear_runtime_action_progress(summary=summary)

    async def handle_conversation_log(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.session_id:
            app.ui_state.last_feedback = "No session is active yet, so there is no transcript to open."
            self.refresh_panels()
            return
        path = await asyncio.to_thread(partial(app.runtime.write_conversation_log, app.ui_state.session_id))
        app.ui_state.conversation_log_path = str(path)
        open_browser_url(path.as_uri())
        app.ui_state.last_feedback = f"Opened transcript log at {path}"
        self.refresh_panels()

    def focus_inline_feedback(self) -> None:
        try:
            self.query_one("#inline_feedback_verdict_input", Input).focus()
        except Exception:
            self.focus_composer()

    async def handle_review(self, *, open_inline_feedback: bool = True) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.last_turn_id:
            self.focus_composer()
            app.ui_state.last_feedback = "No Adam reply is available to review yet. Send a turn first."
            self.refresh_panels()
            return
        state, latest_entry = self._feedback_loop_state()
        if state == "pending":
            app.ui_state.last_feedback = (
                "Inline review focused in chat. Type A, E, R, or S; explanation is required for A/E/R, "
                "and corrected text is required for E."
            )
        elif latest_entry is not None:
            app.ui_state.last_feedback = (
                f"Latest review stays inline in chat. Current verdict={str(latest_entry.get('verdict', 'skip')).upper()} "
                f"for T{latest_entry.get('turn_index', '?')}."
            )
        else:
            app.ui_state.last_feedback = "Inline review is available in chat for Adam's latest reply."
        self._write_forensic(
            f"[INFO] Inline review focus :: turn={app.ui_state.last_turn_id} state={state}"
        )
        self.refresh_panels()
        if open_inline_feedback:
            self.call_after_refresh(self.focus_inline_feedback)

    async def handle_deck(self) -> None:
        await self.app.push_screen(DeckModal(self))

    async def handle_archive(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        payload = await self.app.push_screen_wait(ConversationAtlasModal(preferred_session_id=app.ui_state.session_id))
        if not payload or payload.get("action") != "resume" or not payload.get("session_id"):
            return
        snapshot = await asyncio.to_thread(partial(app.runtime.session_state_snapshot, payload["session_id"]))
        app.apply_session_snapshot(snapshot)
        self._mark_graph_dirty()
        app.ui_state.last_feedback = f"Atlas resumed {snapshot['session_title']}."
        self._write_forensic(f"[INFO] Atlas resumed session :: {snapshot['session_title']}")
        self._set_text_area("#composer_input", "")
        self._reset_inline_feedback_inputs()
        self.refresh_panels()
        self.focus_composer()
        self._scroll_chat_to_end()
        self._schedule_preview_refresh()

    async def handle_ingest(self) -> None:
        await self.app.push_screen(IngestModal(self))

    @on(Button.Pressed, "#reasoning_mode_reasoning_btn")
    def handle_reasoning_mode_reasoning(self) -> None:
        self.app.ui_state.reasoning_mode = "reasoning"
        self.refresh_panels()

    @on(Button.Pressed, "#reasoning_mode_chain_btn")
    def handle_reasoning_mode_chain(self) -> None:
        self.app.ui_state.reasoning_mode = "chain_like"
        self.refresh_panels()

    @on(Button.Pressed, "#reasoning_mode_hum_btn")
    def handle_reasoning_mode_hum(self) -> None:
        self.app.ui_state.reasoning_mode = "hum_live"
        self.refresh_panels()

    def toggle_runtime_chyron(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        app.ui_state.runtime_chyron_open = not app.ui_state.runtime_chyron_open
        app.ui_state.last_feedback = (
            "Runtime event chyron opened from the bottom."
            if app.ui_state.runtime_chyron_open
            else "Runtime event chyron closed."
        )
        self.refresh_panels()

    def toggle_aperture_drawer(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        app.ui_state.aperture_drawer_open = not app.ui_state.aperture_drawer_open
        if self._is_compact_layout():
            app.ui_state.last_feedback = (
                "Compact aperture view opened. Press F8 or Esc to return to dialogue."
                if app.ui_state.aperture_drawer_open
                else "Returned to dialogue view."
            )
        else:
            app.ui_state.last_feedback = (
                "Aperture drawer opened for a wide scan."
                if app.ui_state.aperture_drawer_open
                else "Aperture drawer collapsed back to the compact dialogue view."
            )
        self.refresh_panels()
        if self._is_compact_layout() and app.ui_state.aperture_drawer_open:
            self.query_one("#runtime_action_menu", ActionStrip).focus()
        elif not app.ui_state.aperture_drawer_open and not app.ui_state.runtime_chyron_open:
            self.focus_composer()

    def _route_printable_to_composer(self, event) -> bool:
        character = getattr(event, "character", None)
        if not character or not character.isprintable():
            return False
        if getattr(event, "is_control", False) or getattr(event, "ctrl", False) or getattr(event, "meta", False):
            return False
        focused = self.app.focused
        if isinstance(focused, TextArea):
            return False
        if isinstance(focused, Input):
            return False
        composer = self.focus_composer()
        composer.insert(character)
        event.stop()
        return True

    async def _new_session_worker(self) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        if not app.ui_state.experiment_id:
            return
        defaults = app.runtime.default_session_profile_request().to_dict()
        if app.ui_state.session_id:
            defaults.update(await asyncio.to_thread(partial(app.runtime.session_profile_request, app.ui_state.session_id)))
        session_title_history = await asyncio.to_thread(partial(app.runtime.recent_session_titles, limit=20))
        payload = await app.push_screen_wait(
            SessionConfigModal(
                defaults,
                title_text="New Session Inference Profile",
                action_label="Open Session",
                session_title_history=session_title_history,
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
        snapshot = await asyncio.to_thread(partial(app.runtime.session_state_snapshot, session["id"]))
        app.apply_session_snapshot(snapshot)
        self._mark_graph_dirty()
        app.ui_state.last_feedback = "Opened a new session."
        self._set_text_area("#composer_input", "")
        self._reset_inline_feedback_inputs()
        self.refresh_panels()
        self.focus_composer()
        self._scroll_chat_to_end()
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
            self._mark_graph_dirty()
            app.ui_state.last_feedback = f"Resumed {snapshot['session_title']}."
            self._write_forensic(f"[INFO] Resumed session :: {snapshot['session_title']}")
            self._set_text_area("#composer_input", "")
            self._reset_inline_feedback_inputs()
            self.refresh_panels()
            self.focus_composer()
            self._scroll_chat_to_end()
            self._schedule_preview_refresh()
            return
        defaults = app.runtime.default_session_profile_request().to_dict()
        session_title_history = await asyncio.to_thread(partial(app.runtime.recent_session_titles, limit=20))
        payload = await app.push_screen_wait(
            SessionConfigModal(
                defaults,
                title_text=f"{action.title()} Experiment Session",
                action_label="Open Session",
                session_title_history=session_title_history,
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
        snapshot = await asyncio.to_thread(partial(app.runtime.session_state_snapshot, session["id"]))
        app.apply_session_snapshot(snapshot)
        self._mark_graph_dirty()
        app.ui_state.last_feedback = f"Opened a new {action} experiment session."
        self._write_forensic(f"[INFO] Opened {action} experiment :: {session['title']}")
        self._set_text_area("#composer_input", "")
        self._reset_inline_feedback_inputs()
        self.refresh_panels()
        self.focus_composer()
        self._scroll_chat_to_end()
        self._schedule_preview_refresh()

    def begin_surface_launch(self, action: str) -> None:
        self.run_worker(self._launch_surface_worker(action), exclusive=True, group=f"surface_{action}")

    def current_ui_look(self) -> str:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        return app.current_ui_look()

    async def set_ui_look(self, look: str, *, active_modal: ModalScreen[Any] | None = None) -> None:
        app = self.app
        assert isinstance(app, EdenTuiApp)
        updated = await asyncio.to_thread(partial(app.runtime.update_ui_appearance, look=look))
        normalized = _normalize_ui_look(updated.get("look"))
        app.apply_ui_look(normalized, extra_nodes=[self, active_modal] if active_modal is not None else [self])
        app.ui_state.last_feedback = f"look={LOOK_LABELS.get(normalized, normalized)}"
        self.refresh_panels()

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
        app = self.app
        assert isinstance(app, EdenTuiApp)
        normalized = (action or "review").strip().lower()
        self._last_runtime_action_dispatch = (normalized, monotonic())
        if normalized in {"blank", "seeded", "resume"}:
            self.begin_surface_launch(normalized)
        elif normalized == "new_session":
            self.begin_new_session_flow()
        elif normalized == "profile":
            self.begin_edit_profile_flow()
        elif normalized == "review":
            self.run_worker(self.handle_review(), exclusive=True, group="review")
        elif normalized == "conversation_log":
            self.run_worker(self.handle_conversation_log(), exclusive=True, group="conversation_log")
        elif normalized == "toggle_aperture":
            self.toggle_aperture_drawer()
        elif normalized == "toggle_chyron":
            self.toggle_runtime_chyron()
        elif normalized == "ingest_pdf":
            self.run_worker(self.handle_ingest(), exclusive=True, group="ingest")
        elif normalized == "prepare_mlx":
            self.handle_prepare_mlx()
        elif normalized == "observatory":
            if self._runtime_action_running("observatory"):
                progress = app.ui_state.action_progress or {}
                elapsed = _format_elapsed(monotonic() - float(progress.get("started_at", monotonic())))
                app.ui_state.last_feedback = (
                    f"Observatory action already running: {progress.get('phase', 'working')} ({elapsed} elapsed)."
                )
                self.refresh_panels()
                return
            self._set_runtime_action_progress(
                action="observatory",
                label="Open Browser Observatory",
                phase="Queued launch",
                step=0,
                total=3,
                detail="Waiting for the observatory worker to begin.",
                feedback="Observatory queued: preparing browser observability surfaces.",
            )
            self.run_worker(self.handle_observatory(), exclusive=True, group="observatory")
        elif normalized == "export":
            self.run_worker(self.handle_export(), exclusive=True, group="export")
        elif normalized == "archive":
            self.run_worker(self.handle_archive(), exclusive=True, group="archive")
        elif normalized == "deck":
            self.run_worker(self.handle_deck(), exclusive=True, group="deck")
        elif normalized == "help":
            self.run_worker(self.handle_help(), exclusive=True, group="help")

    @on(ActionStrip.Changed, "#runtime_action_menu")
    def handle_runtime_action_changed(self, _event: ActionStrip.Changed) -> None:
        self.query_one("#runtime_action_menu", ActionStrip).refresh()

    @on(ActionStrip.Submitted, "#runtime_action_menu")
    def handle_runtime_action_submitted(self, event: ActionStrip.Submitted) -> None:
        if self._recent_runtime_action_dispatch(event.action):
            return
        self._execute_runtime_action(event.action)

    def _recent_runtime_action_dispatch(self, action: str) -> bool:
        normalized = (action or "review").strip().lower()
        if self._runtime_action_running(normalized):
            return False
        if self._last_runtime_action_dispatch is None:
            return False
        last_action, dispatched_at = self._last_runtime_action_dispatch
        return last_action == normalized and (monotonic() - dispatched_at) < 0.6

    @on(events.DescendantFocus)
    @on(events.DescendantBlur)
    def handle_focus_surface_change(self, _event: events.Event) -> None:
        if not self.is_mounted:
            return
        self.query_one("#runtime_action_menu", ActionStrip).refresh()

    def _handle_scroll_keys(self, event: events.Key) -> bool:
        focused_id = getattr(self.app.focused, "id", None)
        if focused_id not in {"chat_tape", "thinking_scroller"}:
            return False
        viewport = self.query_one(f"#{focused_id}", VerticalScroll)
        action = {
            "up": viewport.scroll_up,
            "down": viewport.scroll_down,
            "pageup": viewport.scroll_page_up,
            "pagedown": viewport.scroll_page_down,
            "home": viewport.scroll_home,
            "end": viewport.scroll_end,
        }.get(event.key)
        if action is None:
            return False
        action(animate=False)
        event.stop()
        return True

    def on_key(self, event) -> None:
        if event.key == "escape" and self.app.ui_state.runtime_chyron_open:
            self.app.ui_state.runtime_chyron_open = False
            self.app.ui_state.last_feedback = "Runtime chyron closed."
            self.refresh_panels()
            event.stop()
            return
        if event.key == "escape":
            message = "Composer focused."
            if self._is_compact_layout() and self.app.ui_state.aperture_drawer_open:
                self.app.ui_state.aperture_drawer_open = False
                message = "Returned to dialogue view."
            self.focus_composer()
            self.app.ui_state.last_feedback = message
            self.refresh_panels()
            event.stop()
            return
        if self._handle_scroll_keys(event):
            return
        if self._route_printable_to_composer(event):
            return


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
        height: 11;
        padding: 0 1 1 1;
    }}
    #aperture_drawer_panel {{
        display: none;
        margin: 0 0 1 1;
        min-width: 34;
    }}
    #turn_status_panel {{
        display: none;
        margin: 0 0 1 1;
        min-width: 24;
    }}
    #startup_topbar {{
        height: 8;
        padding: 0 1 1 1;
    }}
    #runtime_action_menu, #startup_action_menu {{
        width: 1fr;
        min-width: 32;
    }}
    #runtime_action_menu {{
        min-width: 72;
        padding: 0 1;
        background: #07232d;
        border: tall #8ef3ff;
        color: #c3fbff;
    }}
    #startup_menu_hint {{
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
    #startup_left, #chat_primary {{
        width: 38%;
        min-width: 44;
        padding-right: 1;
    }}
    #chat_primary {{
        width: 62%;
        min-width: 78;
    }}
    #startup_right, #chat_secondary {{
        width: 62%;
        min-width: 66;
        padding-left: 1;
    }}
    #chat_secondary {{
        width: 38%;
        min-width: 46;
    }}
    #startup_aperture_panel {{
        height: 1fr;
        min-height: 16;
    }}
    #startup_reasoning_panel {{
        height: 1fr;
        min-height: 13;
    }}
    #chat_deck, #startup_cockpit_stack {{
        border: tall {AMBER};
        background: {CHIARO_SHADOW};
        padding: 0 1;
    }}
    #startup_cockpit_stack {{
        height: 1fr;
        min-height: 18;
    }}
    #signal_field {{
        width: 1fr;
        min-width: 32;
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
        min-height: 28;
    }}
    #chat_tape {{
        height: 1fr;
        min-height: 20;
        margin-bottom: 1;
        border: tall {ROSE};
        background: {CHIARO_SHADOW};
        padding: 0 1;
        scrollbar-gutter: stable;
        scrollbar-size-vertical: 2;
        scrollbar-color: {AMBER};
        scrollbar-color-hover: {ICE};
        scrollbar-color-active: {TEXT};
        scrollbar-background: #17101a;
        scrollbar-background-hover: #1d1420;
        scrollbar-background-active: #231b27;
        scrollbar-corner-color: {CHIARO_SHADOW};
    }}
    #chat_tape:focus {{
        border: tall {ICE};
    }}
    #chat_exchange_panel {{
        width: 100%;
    }}
    #signal_field {{
        height: 14;
        min-height: 12;
    }}
    #active_aperture_panel {{
        display: none;
        height: 0;
        min-height: 0;
    }}
    #reasoning_mode_row {{
        height: 3;
    }}
    #reasoning_mode_row Button {{
        width: 1fr;
        margin-bottom: 0;
    }}
    #thinking_scroller {{
        height: 1fr;
        min-height: 16;
        background: {CHIARO_SHADOW};
        scrollbar-gutter: stable;
        scrollbar-size-vertical: 2;
        scrollbar-color: {AMBER};
        scrollbar-color-hover: {ICE};
        scrollbar-color-active: {TEXT};
        scrollbar-background: #17101a;
        scrollbar-background-hover: #1d1420;
        scrollbar-background-active: #231b27;
        scrollbar-corner-color: {CHIARO_SHADOW};
    }}
    #thinking_scroller:focus {{
        background: #14090d;
    }}
    #thinking_panel {{
        width: 100%;
        min-height: 100%;
        margin-bottom: 0;
    }}
    #runtime_chyron_panel {{
        height: 0;
        min-height: 0;
        margin: 0 1 1 1;
    }}
    #runtime_chyron_drawer {{
        height: 0;
        min-height: 0;
        width: 100%;
        dock: bottom;
        margin: 0 1 1 1;
    }}
    #inline_feedback_surface {{
        display: none;
        height: 0;
    }}
    #inline_feedback_command_row {{
        height: 3;
    }}
    #inline_feedback_explanation_input,
    #inline_feedback_corrected_input {{
        height: 4;
        min-height: 4;
        background: #11070d;
        border: tall {AMBER};
        color: {TEXT};
    }}
    #composer_input {{
        height: 5;
        background: {CHIARO_SHADOW};
        border: tall {AMBER};
        color: {TEXT};
        scrollbar-gutter: stable;
        scrollbar-size-vertical: 2;
        scrollbar-color: {AMBER};
        scrollbar-color-hover: {ICE};
        scrollbar-color-active: {TEXT};
        scrollbar-background: #181015;
        scrollbar-background-hover: #20161c;
        scrollbar-background-active: #281d24;
    }}
    #composer_input:focus {{
        border: tall {NEON};
        background: #14090d;
    }}
    #runtime_action_menu:focus {{
        background: #0b2f3b;
        border: tall #d9ffff;
    }}
    #review_explanation_input, #review_corrected_input, #ingest_prompt_input {{
        height: 6;
        background: #11070d;
        border: tall {AMBER};
        color: {TEXT};
    }}
    Static, Input, RichLog, Select, TextArea {{
        margin-bottom: 1;
    }}
    .field_label {{
        margin-bottom: 0;
        color: {MUTED};
        text-style: bold;
    }}
    .field_stack Input,
    .field_stack Select {{
        margin-bottom: 0;
    }}
    #deck_look_select {{
        width: 1fr;
        margin-bottom: 0;
    }}
    #session_title_row {{
        height: 3;
    }}
    #session_action_row {{
        height: 3;
    }}
    #session_title_input {{
        width: 1fr;
    }}
    #session_title_history_select {{
        width: 24;
        min-width: 20;
        margin-bottom: 0;
    }}
    #session_title_row Input,
    #session_title_row Select,
    #session_action_row Button,
    #atlas_taxonomy_actions Button,
    #atlas_observatory_actions Button,
    #atlas_session_actions Button {{
        margin-bottom: 0;
    }}
    #session_title_row Input {{
        margin-right: 1;
    }}
    #session_title_row Select,
    #session_action_row Button:last-child,
    #atlas_taxonomy_actions Button:last-child,
    #atlas_observatory_actions Button:last-child,
    #atlas_session_actions Button:last-child {{
        margin-right: 0;
    }}
    Input, Select {{
        background: #261219;
        border: tall {AMBER};
        color: {TEXT};
    }}
    Button {{
        margin-right: 1;
        background: #32160f;
        color: {TEXT};
    }}
    RichLog {{
        background: #060403;
        border: tall {AMBER};
        color: {TEXT};
    }}
    #deck_shell, #session_config_shell, #ingest_shell, #atlas_shell {{
        padding: 1 1;
    }}
    .deck_column, .session_config_column, .ingest_column, .atlas_column {{
        width: 1fr;
        padding: 0 1;
    }}
    #atlas_filter_column {{
        width: 30;
        min-width: 30;
    }}
    #atlas_main_column {{
        width: 1fr;
        min-width: 70;
    }}
    #atlas_detail_row {{
        height: 22;
        min-height: 20;
    }}
    .atlas_detail_column {{
        padding: 0 1;
        height: 1fr;
    }}
    #atlas_metadata_column {{
        width: 34;
        min-width: 32;
        max-width: 38;
    }}
    #atlas_preview_column {{
        width: 1fr;
        min-width: 36;
    }}
    #atlas_preview_scroller {{
        height: 1fr;
        min-height: 14;
        margin-bottom: 0;
        scrollbar-gutter: stable;
        scrollbar-size-vertical: 2;
        scrollbar-color: {AMBER};
        scrollbar-color-hover: {ICE};
        scrollbar-color-active: {TEXT};
        scrollbar-background: #181015;
        scrollbar-background-hover: #20161c;
        scrollbar-background-active: #281d24;
    }}
    #deck_summary, #review_summary, #session_config_header, #session_config_summary, #ingest_summary, #atlas_summary {{
        margin: 1 2;
    }}
    #deck_status_panel {{
        height: 1fr;
    }}
    #session_config_shell, #ingest_shell, #atlas_shell {{
        padding: 1 1;
    }}
    #atlas_records_table {{
        height: 1fr;
        min-height: 18;
        background: #0c070a;
        border: tall {AMBER};
        color: {TEXT};
    }}
    #atlas_preview_panel {{
        height: auto;
        min-height: 0;
        margin-bottom: 0;
    }}
    #atlas_taxonomy_panel, #atlas_status_panel {{
        height: 1fr;
        min-height: 8;
    }}
    #atlas_folder_field {{
        height: 5;
    }}
    #atlas_tags_field {{
        height: 11;
    }}
    #atlas_tags_input {{
        height: 1fr;
        min-height: 7;
        background: #11070d;
        border: tall {AMBER};
        color: {TEXT};
        scrollbar-gutter: stable;
        scrollbar-size-vertical: 2;
        scrollbar-color: {AMBER};
        scrollbar-color-hover: {ICE};
        scrollbar-color-active: {TEXT};
        scrollbar-background: #181015;
        scrollbar-background-hover: #20161c;
        scrollbar-background-active: #281d24;
    }}
    #atlas_tags_input:focus {{
        border: tall {ICE};
        background: #14090d;
    }}
    #atlas_taxonomy_actions,
    #atlas_observatory_actions,
    #atlas_session_actions {{
        height: 3;
    }}
    #atlas_taxonomy_actions Button,
    #atlas_observatory_actions Button,
    #atlas_session_actions Button {{
        width: 1fr;
    }}
    .look-typewriter-light {{
        background: {TYPEWRITER_LIGHT.bg};
        color: {TYPEWRITER_LIGHT.text};
    }}
    .look-typewriter-light Header, .look-typewriter-light Footer {{
        background: {TYPEWRITER_LIGHT.shade_alt};
        color: {TYPEWRITER_LIGHT.text};
    }}
    .look-typewriter-light #runtime_frame,
    .look-typewriter-light #startup_frame,
    .look-typewriter-light #startup_shell,
    .look-typewriter-light #chat_shell {{
        background: {TYPEWRITER_LIGHT.bg};
        color: {TYPEWRITER_LIGHT.text};
    }}
    .look-typewriter-light #chat_deck,
    .look-typewriter-light #startup_cockpit_stack {{
        border: tall {TYPEWRITER_LIGHT.amber};
        background: {TYPEWRITER_LIGHT.chiaro_shadow};
    }}
    .look-typewriter-light #chat_tape {{
        border: tall {TYPEWRITER_LIGHT.rose};
        background: {TYPEWRITER_LIGHT.marble_light};
        scrollbar-color: {TYPEWRITER_LIGHT.amber};
        scrollbar-color-hover: {TYPEWRITER_LIGHT.ice};
        scrollbar-color-active: {TYPEWRITER_LIGHT.text};
        scrollbar-background: #ece2d2;
        scrollbar-background-hover: #e4d8c5;
        scrollbar-background-active: #dbceb7;
        scrollbar-corner-color: {TYPEWRITER_LIGHT.marble_light};
    }}
    .look-typewriter-light #chat_tape:focus {{
        border: tall {TYPEWRITER_LIGHT.ice};
    }}
    .look-typewriter-light #thinking_scroller {{
        background: {TYPEWRITER_LIGHT.marble_light};
        scrollbar-color: {TYPEWRITER_LIGHT.amber};
        scrollbar-color-hover: {TYPEWRITER_LIGHT.ice};
        scrollbar-color-active: {TYPEWRITER_LIGHT.text};
        scrollbar-background: #e8dece;
        scrollbar-background-hover: #dfd3c0;
        scrollbar-background-active: #d5c6b1;
        scrollbar-corner-color: {TYPEWRITER_LIGHT.marble_light};
    }}
    .look-typewriter-light #thinking_scroller:focus {{
        background: {TYPEWRITER_LIGHT.shade};
    }}
    .look-typewriter-light #composer_input {{
        background: {TYPEWRITER_LIGHT.marble_light};
        border: tall {TYPEWRITER_LIGHT.amber};
        color: {TYPEWRITER_LIGHT.text};
        scrollbar-color: {TYPEWRITER_LIGHT.amber};
        scrollbar-color-hover: {TYPEWRITER_LIGHT.ice};
        scrollbar-color-active: {TYPEWRITER_LIGHT.text};
        scrollbar-background: #e8dece;
        scrollbar-background-hover: #dfd3c0;
        scrollbar-background-active: #d5c6b1;
    }}
    .look-typewriter-light #composer_input:focus {{
        border: tall {TYPEWRITER_LIGHT.neon};
        background: {TYPEWRITER_LIGHT.shade};
    }}
    .look-typewriter-light #runtime_action_menu {{
        background: #d8f5f7;
        border: tall #4fa4b8;
        color: #173944;
    }}
    .look-typewriter-light #runtime_action_menu:focus {{
        background: #eafcfd;
        border: tall #2b8195;
    }}
    .look-typewriter-light #review_explanation_input,
    .look-typewriter-light #review_corrected_input,
    .look-typewriter-light #ingest_prompt_input,
    .look-typewriter-light TextArea,
    .look-typewriter-light Input,
    .look-typewriter-light Select {{
        background: {TYPEWRITER_LIGHT.marble_light};
        border: tall {TYPEWRITER_LIGHT.amber};
        color: {TYPEWRITER_LIGHT.text};
    }}
    .look-typewriter-light #atlas_tags_input {{
        scrollbar-color: {TYPEWRITER_LIGHT.amber};
        scrollbar-color-hover: {TYPEWRITER_LIGHT.ice};
        scrollbar-color-active: {TYPEWRITER_LIGHT.text};
        scrollbar-background: #e8dece;
        scrollbar-background-hover: #dfd3c0;
        scrollbar-background-active: #d5c6b1;
    }}
    .look-typewriter-light #atlas_preview_scroller {{
        scrollbar-color: {TYPEWRITER_LIGHT.amber};
        scrollbar-color-hover: {TYPEWRITER_LIGHT.ice};
        scrollbar-color-active: {TYPEWRITER_LIGHT.text};
        scrollbar-background: #e8dece;
        scrollbar-background-hover: #dfd3c0;
        scrollbar-background-active: #d5c6b1;
    }}
    .look-typewriter-light .field_label {{
        color: {TYPEWRITER_LIGHT.muted};
    }}
    .look-typewriter-light Button {{
        background: {TYPEWRITER_LIGHT.panel};
        color: {TYPEWRITER_LIGHT.text};
        border: tall {TYPEWRITER_LIGHT.amber};
    }}
    .look-typewriter-light RichLog {{
        background: {TYPEWRITER_LIGHT.marble_light};
        border: tall {TYPEWRITER_LIGHT.amber};
        color: {TYPEWRITER_LIGHT.text};
    }}
    .look-typewriter-light #atlas_records_table {{
        background: {TYPEWRITER_LIGHT.marble_light};
        border: tall {TYPEWRITER_LIGHT.amber};
        color: {TYPEWRITER_LIGHT.text};
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
        ("f8", "toggle_aperture", "Aperture"),
        ("f9", "open_ingest", "Ingest"),
        ("f10", "show_archive", "Archive"),
        ("f11", "toggle_runtime_chyron", "Runtime Chyron"),
    ]

    def __init__(self, runtime: EdenRuntime) -> None:
        super().__init__()
        self.runtime = runtime
        self.repo_root = Path(__file__).resolve().parents[2]
        self.ui_state = UiState()

    def current_ui_look(self) -> str:
        return _normalize_ui_look(self.runtime.settings.ui_look)

    def apply_ui_look(self, look: str | None = None, *, extra_nodes: list[Any] | None = None) -> None:
        normalized = _normalize_ui_look(look or self.runtime.settings.ui_look)
        self.runtime.settings.ui_look = normalized
        _apply_look_palette(normalized)
        for class_name in LOOK_CLASSES.values():
            self.remove_class(class_name)
        self.add_class(LOOK_CLASSES[normalized])
        for node in extra_nodes or []:
            if node is not None:
                _sync_node_look(node)
        self.refresh(layout=True)

    def _focus_chain(self) -> list[Any]:
        chain = list(self.screen.focus_chain)
        if not isinstance(self.screen, ChatScreen):
            return chain
        try:
            action_strip = self.screen.query_one("#runtime_action_menu", ActionStrip)
            composer = self.screen.query_one("#composer_input", TextArea)
        except NoMatches:
            return chain
        if action_strip not in chain or composer not in chain:
            return chain
        chain.remove(action_strip)
        chain.insert(chain.index(composer) + 1, action_strip)
        return chain

    def action_focus_next(self) -> None:
        chain = self._focus_chain()
        if not chain:
            return
        focused = self.focused
        if focused in chain:
            chain[(chain.index(focused) + 1) % len(chain)].focus()
            return
        chain[0].focus()

    def action_focus_previous(self) -> None:
        chain = self._focus_chain()
        if not chain:
            return
        focused = self.focused
        if focused in chain:
            chain[(chain.index(focused) - 1) % len(chain)].focus()
            return
        chain[-1].focus()

    def apply_session_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.ui_state.experiment_id = snapshot["experiment_id"]
        self.ui_state.experiment_name = snapshot.get("experiment_name")
        self.ui_state.session_id = snapshot["session_id"]
        self.ui_state.session_title = snapshot.get("session_title")
        self.ui_state.conversation_log_path = snapshot.get("conversation_log_path")
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
        self.ui_state.current_graph_health = None
        self.ui_state.last_ingest_result = None
        self.ui_state.turn_progress = None

    async def on_mount(self) -> None:
        self.apply_ui_look(self.runtime.ui_appearance().get("look"))
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

    async def action_toggle_runtime_chyron(self) -> None:
        if isinstance(self.screen, ChatScreen):
            self.screen.toggle_runtime_chyron()

    async def action_toggle_aperture(self) -> None:
        if isinstance(self.screen, ChatScreen):
            self.screen.toggle_aperture_drawer()

    async def action_open_ingest(self) -> None:
        if isinstance(self.screen, ChatScreen):
            await self.screen.handle_ingest()

    async def action_show_archive(self) -> None:
        if isinstance(self.screen, ChatScreen):
            self.screen.run_worker(self.screen.handle_archive(), exclusive=True, group="archive")
        elif isinstance(self.screen, StartupScreen):
            self.screen.handle_startup_archive()


def run_tui(runtime: EdenRuntime) -> None:
    EdenTuiApp(runtime).run()
