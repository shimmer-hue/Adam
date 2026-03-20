from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from textual import events
from textual.widgets import Button, Input, Select, Static, TextArea

from eden.browser import BrowserOpenResult
from eden.models.base import ModelResult
from eden.models.mock import MockModelAdapter
from eden.tui.app import ActionStrip, ChatScreen, ConversationAtlasModal, DeckModal, EdenTuiApp, IngestModal, SessionConfigModal


@pytest.mark.asyncio
async def test_tui_boots_single_graph_mode_and_uses_multiline_composer(runtime, sample_files) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        assert isinstance(app.screen, ChatScreen)
        await pilot.pause(1.0)
        assert app.ui_state.session_id is not None
        chat_primary = app.screen.query_one("#chat_primary")
        chat_secondary = app.screen.query_one("#chat_secondary")
        assert app.screen.query_one("#chat_deck").parent is chat_primary
        assert app.screen.query_one("#signal_field").parent is chat_secondary
        assert app.screen.query_one("#aperture_drawer_panel").display is True
        assert app.screen.query_one("#active_aperture_panel").display is False
        assert app.screen.query_one("#context_budget_panel").display is True
        assert app.screen.query_one("#turn_status_panel").display is True
        assert str(app.screen.query_one("#runtime_action_menu", ActionStrip).styles.width) == "50w"
        assert str(app.screen.query_one("#aperture_drawer_panel").styles.width) == "26w"
        assert app.screen.query_one_optional("#hum_panel") is None
        menu = app.screen.query_one("#runtime_action_menu", ActionStrip)
        composer = app.screen.query_one("#composer_input", TextArea)
        assert menu.value == "review"
        assert str(composer.border_title) == ">> Composer"
        rendered_strip = menu.render().plain
        assert "01 Review Last Reply" in rendered_strip
        assert "08 Open Browser Observatory" in rendered_strip
        await pilot.press("tab")
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "runtime_action_menu"
        assert str(menu.border_title) == ">> Actions"
        assert str(composer.border_title) == "Composer"
        await pilot.press("h", "i")
        await pilot.pause(0.2)
        assert composer.text == "hi"
        menu.set_value("toggle_aperture")
        menu.focus()
        await pilot.press("enter")
        await pilot.pause(0.2)
        assert app.ui_state.aperture_drawer_open is True
        assert app.screen.query_one("#aperture_drawer_panel")
        assert str(app.screen.query_one("#runtime_action_menu", ActionStrip).styles.width) == "40w"
        assert str(app.screen.query_one("#aperture_drawer_panel").styles.width) == "37w"
        await app.screen.ingest_path(
            str(sample_files["pdf"]),
            briefing="Treat this PDF as a durable source on EDEN memory and retrieve it aggressively in later turns.",
        )
        await pilot.pause(0.4)
        assert app.ui_state.last_ingest_result is not None
        assert app.ui_state.last_ingest_result["title"] == sample_files["pdf"].name
        assert app.ui_state.last_ingest_result["briefing_indexed"] is True
        composer.load_text("line one\nline two")
        await pilot.pause()
        assert "\n" in composer.text
        draft_group = app.screen.main_chat_exchange_panel()
        draft_panel = draft_group.renderables[-1]
        assert getattr(draft_panel.renderable, "plain", "") == "line one\nline two"
        await app.screen._send_turn()
        await pilot.pause(0.4)
        assert app.ui_state.last_turn_id is not None
        assert app.ui_state.last_response
        assert "Answer:" not in app.ui_state.last_response
        assert "Basis:" not in app.ui_state.last_response
        assert app.screen.query_one("#inline_feedback_surface").display is True
        chat_group = app.screen.main_chat_exchange_panel()
        assert getattr(chat_group.renderables[0], "style", None) == "on #000000"
        assert getattr(chat_group.renderables[1], "style", None) == "on #321221"
        assert app.screen.query_one("#active_aperture_panel")
        assert app.screen.query_one("#thinking_panel")
        assert app.screen.query_one("#chat_tape")
        assert app.screen.query_one("#chat_exchange_panel")
        assert app.screen.query_one("#signal_field")
        assert app.screen.query_one("#runtime_chyron_panel")
        thinking_scroller = app.screen.query_one("#thinking_scroller")
        thinking_scroller.focus()
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "thinking_scroller"
        assert str(thinking_scroller.border_title) == ">> Reasoning / Hum"
        assert app.screen.query_one("#runtime_chyron_panel").display is False
        await pilot.press("f11")
        await pilot.pause(0.3)
        assert app.screen.query_one("#runtime_chyron_panel").display is True
        await pilot.press("f11")
        await pilot.pause(0.3)
        assert app.screen.query_one("#runtime_chyron_panel").display is False
        assert app.ui_state.conversation_log_path is not None
        transcript_path = Path(app.ui_state.conversation_log_path)
        assert transcript_path.exists()
        assert "line one" in transcript_path.read_text(encoding="utf-8")
        assert "Answer:" not in transcript_path.read_text(encoding="utf-8")
        await app.action_show_review()
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "inline_feedback_verdict_input"
        assert "popup" not in app.ui_state.last_feedback.lower()
        assert app.screen.query_one_optional("#inline_feedback_confirm_input") is None
        verdict = app.screen.query_one("#inline_feedback_verdict_input", Input)
        verdict.value = "A"
        await pilot.pause(0.2)
        await pilot.press("enter")
        await pilot.pause(0.2)
        explanation = app.screen.query_one("#inline_feedback_explanation_input", TextArea)
        assert getattr(app.focused, "id", None) == "inline_feedback_explanation_input"
        explanation.load_text("Accepting because the reply matches the session frame.")
        await pilot.pause(0.2)
        await pilot.press("enter")
        await pilot.pause(0.4)
        assert "ACCEPT recorded" in app.ui_state.last_feedback
        assert runtime.graph_health(app.ui_state.experiment_id)["feedback"] == 1
        transcript_text = transcript_path.read_text(encoding="utf-8")
        assert "ACCEPT" in transcript_text
        await app.action_export_all()
        await pilot.pause(0.4)
        assert "Exports generated in" in app.ui_state.last_feedback
        call_count = 0
        original_graph_health = runtime.graph_health

        def counted_graph_health(experiment_id):
            nonlocal call_count
            call_count += 1
            return original_graph_health(experiment_id)

        runtime.graph_health = counted_graph_health
        app.screen._graph_health_dirty = True
        app.screen._health()
        app.screen._health()
        assert call_count == 1


@pytest.mark.asyncio
async def test_inline_feedback_skip_submits_from_verdict_enter(runtime) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)

        composer = app.screen.query_one("#composer_input", TextArea)
        composer.load_text("Quick turn for skip review.")
        await app.screen._send_turn()
        await pilot.pause(0.4)

        await app.action_show_review()
        await pilot.pause(0.2)

        verdict = app.screen.query_one("#inline_feedback_verdict_input", Input)
        verdict.value = "S"
        await pilot.pause(0.2)
        await pilot.press("enter")
        await pilot.pause(0.4)

        assert "SKIP recorded" in app.ui_state.last_feedback
        assert getattr(app.focused, "id", None) == "composer_input"
        assert runtime.graph_health(app.ui_state.experiment_id)["feedback"] == 1
        assert app.screen.query_one("#inline_feedback_command_row").display is False
        assert app.screen.query_one("#inline_feedback_explanation_input", TextArea).display is False
        assert app.screen.query_one("#inline_feedback_corrected_input", TextArea).display is False
        stored_feedback_panel = app.screen.main_inline_feedback_status_panel()
        assert str(stored_feedback_panel.title) == "Stored Feedback Payload"
        assert "verdict=SKIP" in stored_feedback_panel.renderable.plain
        assert "created=" in stored_feedback_panel.renderable.plain
        assert "Awaiting the next Adam reply." in stored_feedback_panel.renderable.plain

        composer.load_text("Second turn re-arms inline review.")
        await app.screen._send_turn()
        await pilot.pause(0.4)

        assert app.screen.query_one("#inline_feedback_command_row").display is True
        assert app.screen.query_one("#inline_feedback_explanation_input", TextArea).display is True
        assert app.screen.query_one("#inline_feedback_corrected_input", TextArea).display is True


@pytest.mark.asyncio
async def test_inline_feedback_edit_walks_explanation_then_corrected_on_enter(runtime) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)

        composer = app.screen.query_one("#composer_input", TextArea)
        composer.load_text("Turn that will be edited.")
        await app.screen._send_turn()
        await pilot.pause(0.4)

        await app.action_show_review()
        await pilot.pause(0.2)

        verdict = app.screen.query_one("#inline_feedback_verdict_input", Input)
        verdict.value = "E"
        await pilot.pause(0.2)
        await pilot.press("enter")
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "inline_feedback_explanation_input"

        explanation = app.screen.query_one("#inline_feedback_explanation_input", TextArea)
        explanation.load_text("The reply should stay tighter to the graph-grounded continuity.")
        await pilot.pause(0.2)
        await pilot.press("enter")
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "inline_feedback_corrected_input"

        corrected = app.screen.query_one("#inline_feedback_corrected_input", TextArea)
        corrected.load_text("Continuity here is grounded in graph state, retrieval, the membrane, and explicit feedback.")
        await pilot.pause(0.2)
        await pilot.press("enter")
        await pilot.pause(0.4)

        assert "EDIT recorded" in app.ui_state.last_feedback
        assert getattr(app.focused, "id", None) == "composer_input"
        assert runtime.graph_health(app.ui_state.experiment_id)["feedback"] == 1


@pytest.mark.asyncio
async def test_composer_rapid_paste_burst_enter_does_not_submit(runtime, monkeypatch) -> None:
    tick = 1_000.0

    def fake_monotonic() -> float:
        return tick

    monkeypatch.setattr("eden.tui.app.monotonic", fake_monotonic)
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)

        composer = app.screen.query_one("#composer_input", TextArea)
        for character in "pastedmemoir":
            await composer._on_key(events.Key(character, character))
            tick += 0.005

        await composer._on_key(events.Key("enter", None))
        await pilot.pause(0.2)

        assert app.ui_state.last_turn_id is None
        assert composer.text == "pastedmemoir\n"


@pytest.mark.asyncio
async def test_composer_bracketed_paste_with_echoed_raw_keys_does_not_duplicate_or_submit(runtime, monkeypatch) -> None:
    tick = 2_000.0

    def fake_monotonic() -> float:
        return tick

    monkeypatch.setattr("eden.tui.app.monotonic", fake_monotonic)
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)

        composer = app.screen.query_one("#composer_input", TextArea)
        pasted = "All right, good morning, Big Sweet!\n"
        await composer._on_paste(events.Paste(pasted))
        tick += 0.01

        for character in "All right, good morning, Big Sweet!":
            await composer._on_key(events.Key(character, character))
            tick += 0.005

        await composer._on_key(events.Key("enter", None))
        await pilot.pause(0.2)

        assert app.ui_state.last_turn_id is None
        assert composer.text == pasted


@pytest.mark.asyncio
async def test_active_set_document_group_count_drives_aperture_and_runtime_docs(runtime) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)

        app.ui_state.last_active_set = [
            {
                "label": "memoir excerpt a",
                "node_kind": "meme",
                "domain": "knowledge",
                "selection": 2.1,
                "regard": 1.7,
                "activation": 0.6,
                "document_id": "doc-memoir",
                "provenance": "/memoir.normalized.md",
            },
            {
                "label": "memoir excerpt b",
                "node_kind": "meme",
                "domain": "knowledge",
                "selection": 1.9,
                "regard": 1.5,
                "activation": 0.5,
                "document_id": "doc-memoir",
                "provenance": "/memoir.normalized.md",
            },
            {
                "label": "whitepaper excerpt",
                "node_kind": "meme",
                "domain": "knowledge",
                "selection": 1.4,
                "regard": 1.3,
                "activation": 0.4,
                "document_id": "doc-whitepaper",
                "provenance": "/eden_whitepaper_v14.pdf",
            },
            {
                "label": "operator greeting norm",
                "node_kind": "meme",
                "domain": "behavior",
                "selection": 0.8,
                "regard": 1.1,
                "activation": 0.3,
                "provenance": "behavior_rule",
            },
        ]
        app.ui_state.last_ingest_result = None

        aperture_text = app.screen.main_aperture_panel().renderable.plain
        runtime_text = app.screen.main_runtime_chyron_panel().renderable.plain

        assert "docs=2 knowledge=3 behavior=1 memodes=0 items=4" in aperture_text
        assert "docs=2 knowledge=3 behavior=1 memodes=0" in runtime_text


@pytest.mark.asyncio
async def test_ingest_modal_returns_cleanly_to_chat(runtime, sample_files) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)

        chat_screen = app.screen
        chat_screen.run_worker(chat_screen.handle_ingest(), exclusive=True, group="ingest_test")
        await pilot.pause(0.2)

        assert isinstance(app.screen, IngestModal)
        modal = app.screen
        prompt = modal.query_one("#ingest_prompt_input", TextArea)
        assert prompt.text == ""
        assert modal.query_one("#ingest_prompt_label", Static).render().plain == "Framing Prompt (Optional)"
        assert "persistent document-conditioning material" in modal.query_one("#ingest_prompt_help", Static).render().plain
        modal.query_one("#ingest_path_input", Input).value = str(sample_files["pdf"])
        await pilot.press("tab")
        await pilot.pause(0.1)
        assert getattr(app.focused, "id", None) == "ingest_prompt_input"
        await pilot.press("N", "o", "t", "e")
        await pilot.pause(0.1)
        assert prompt.text == "Note"
        prompt.load_text("Treat this as a durable source for the current session and keep the framing prompt in recall.")
        modal.handle_ingest_confirm()
        await pilot.pause(0.6)

        assert isinstance(app.screen, ChatScreen)
        assert app.ui_state.last_ingest_result is not None
        assert app.ui_state.last_ingest_result["title"] == sample_files["pdf"].name
        assert app.ui_state.last_ingest_result["briefing"].startswith("Treat this as a durable source")
        assert getattr(app.focused, "id", None) == "composer_input"


@pytest.mark.asyncio
async def test_ingest_path_recovers_primary_experiment_when_ui_state_is_cold(runtime, sample_files) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)

        app.ui_state.experiment_id = None
        app.ui_state.experiment_name = None

        await app.screen.ingest_path(
            str(sample_files["pdf"]),
            briefing="Recover experiment context before ingest.",
        )
        await pilot.pause(0.2)

        assert app.ui_state.experiment_id == runtime.primary_experiment()["id"]
        assert app.ui_state.last_ingest_result is not None
        assert app.ui_state.last_ingest_result["title"] == sample_files["pdf"].name
        assert app.ui_state.last_ingest_result["briefing"] == "Recover experiment context before ingest."


@pytest.mark.asyncio
async def test_tui_hum_live_pane_scrolls_when_focused(runtime) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(1.0)
        assert app.ui_state.session_id is not None

        long_hum = "\n".join(
            f"continuity beat {index} with enough detail to force wrapping through the right telemetry rail"
            for index in range(1, 26)
        )

        def hum_snapshot(_session_id: str) -> dict[str, object]:
            return {
                "present": True,
                "generated_at": "2026-03-13T21:10:00Z",
                "latest_turn_id": "turn-scroll",
                "turn_window_size": 3,
                "cross_turn_recurrence_present": True,
                "text_surface": long_hum,
            }

        runtime.hum_snapshot = hum_snapshot  # type: ignore[method-assign]
        app.ui_state.reasoning_mode = "hum_live"
        app.screen.refresh_panels()
        await pilot.pause(0.3)

        thinking_scroller = app.screen.query_one("#thinking_scroller")
        assert thinking_scroller.max_scroll_y > 0

        thinking_scroller.focus()
        await pilot.pause(0.1)
        assert getattr(app.focused, "id", None) == "thinking_scroller"

        await pilot.press("pagedown")
        await pilot.pause(0.1)
        assert thinking_scroller.scroll_y > 0

        await pilot.press("end")
        await pilot.pause(0.1)
        assert thinking_scroller.scroll_y == thinking_scroller.max_scroll_y

        await pilot.press("home")
        await pilot.pause(0.1)
        assert thinking_scroller.scroll_y == 0


@pytest.mark.asyncio
async def test_dialogue_tape_recovers_long_answer_beyond_turn_membrane_cap(runtime, monkeypatch) -> None:
    class LongMockAdapter(MockModelAdapter):
        def generate(
            self,
            *,
            system_prompt: str,
            conversation_prompt: str,
            max_tokens: int = 420,
            temperature: float = 0.0,
            top_p: float = 0.0,
            repetition_penalty: float = 0.0,
            progress_callback=None,
        ) -> ModelResult:
            answer = ("Long-form tape recovery paragraph. " * 120) + "TAIL MARKER 7319"
            return ModelResult(
                backend=self.backend_name,
                text=answer,
                tokens_estimate=min(max_tokens, max(64, len(answer.split()))),
                metadata={},
                answer_text=answer,
                reasoning_text="",
                raw_text=answer,
            )

    monkeypatch.setattr(runtime, "_get_model_adapter", lambda: LongMockAdapter())
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(
        experiment["id"],
        title="Tape Recovery",
        profile_request={
            "mode": "manual",
            "budget_mode": "balanced",
            "max_output_tokens": 2400,
            "response_char_cap": 1600,
        },
    )

    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        app.apply_session_snapshot(runtime.session_state_snapshot(session["id"]))
        app.screen.refresh_panels()
        await pilot.pause(0.2)
        composer = app.screen.query_one("#composer_input", TextArea)
        composer.load_text("Give me the long version.")
        await pilot.pause(0.2)
        await app.screen._send_turn()
        await pilot.pause(0.4)

        latest_turn = runtime.store.list_turns(session["id"], limit=1)[0]
        assert len(latest_turn["membrane_text"]) <= 1600
        assert "TAIL MARKER 7319" in app.ui_state.last_response

        chat_group = app.screen.main_chat_exchange_panel()
        adam_panel = chat_group.renderables[1]
        assert "TAIL MARKER 7319" in getattr(adam_panel.renderable, "plain", "")


@pytest.mark.asyncio
async def test_reasoning_mode_buttons_switch_feed_titles(runtime, tmp_path) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(140, 44)) as pilot:
        await pilot.pause(1.0)
        app.ui_state.last_reasoning = (
            "Thinking Process:\n"
            "1. **Analyze the Request:**\n"
            "**User:** Brian the operator.\n"
            "**Context:** Brian is starting Adam's curriculum.\n"
            "**Constraints:** Return one clean operator-facing reply."
        )
        app.ui_state.last_response = (
            "Greetings, Brian.\n"
            "I am ready to begin the first module.\n"
            "We can start with Austin and Butler today."
        )
        app.ui_state.last_active_set = [
            {"label": "language philosophy", "selection": 4.2, "regard": 3.8, "activation": 0.81, "domain": "knowledge", "node_kind": "meme"},
            {"label": "curriculum start", "selection": 3.6, "regard": 3.2, "activation": 0.81, "domain": "behavior", "node_kind": "meme"},
            {"label": "teaching plan", "selection": 2.7, "regard": 2.1, "activation": 0.66, "domain": "behavior", "node_kind": "memode"},
        ]
        app.ui_state.last_trace = list(app.ui_state.last_active_set)
        app.ui_state.current_profile = {
            "profile_name": "manual-balanced",
            "requested_mode": "manual",
            "effective_mode": "manual",
            "response_char_cap": 1600,
            "retrieval_depth": 8,
            "max_context_items": 12,
        }
        app.ui_state.current_budget = {
            "pressure_level": "LOW",
            "prompt_budget_tokens": 1200,
            "remaining_input_tokens": 900,
            "count_method": "heuristic",
        }
        hum_json = tmp_path / "hum.json"
        hum_json.write_text(
            json.dumps(
                {
                    "surface_lines": [
                        "[T0] hum: lngg phlsph / crrclm strt / pssthrgh",
                        "[T1] hum: tchg pln / lngg phlsph / mmbrn stdy",
                    ],
                    "surface_stats": {
                        "entries": 2,
                        "lines_total": 2,
                        "words": 6,
                        "unique_tokens": 5,
                        "repeated_tokens": 1,
                        "hapax_tokens": 4,
                        "type_token_ratio": 0.833,
                        "avg_token_len": 5.17,
                        "avg_line_words": 3.0,
                        "chars_total": 78,
                        "top10_coverage_pct": 100.0,
                    },
                    "token_table": [
                        {"token": "lngg", "count": 2, "pct_of_all_tokens": 0.333},
                        {"token": "phlsph", "count": 1, "pct_of_all_tokens": 0.167},
                        {"token": "crrclm", "count": 1, "pct_of_all_tokens": 0.167},
                    ],
                    "continuity": {
                        "recurring_items": [],
                        "active_set_overlap": {"labels": []},
                        "feedback_summary": {"recent": []},
                        "membrane_summary": {
                            "recent": [
                                {
                                    "event_type": "PASSTHROUGH",
                                    "detail": "Response passed the membrane unchanged.",
                                }
                            ]
                        },
                    }
                }
            ),
            encoding="utf-8",
        )

        def hum_snapshot(_session_id: str) -> dict[str, object]:
            return {
                "present": True,
                "artifact_version": "hum.v1",
                "generated_at": "2026-03-13T21:10:00Z",
                "json_path": str(hum_json),
                "latest_turn_id": "turn-hum",
                "turn_window_size": 3,
                "cross_turn_recurrence_present": True,
                "text_surface": "[T0] hum: lngg phlsph / crrclm strt / pssthrgh\n[T1] hum: tchg pln / lngg phlsph / mmbrn stdy",
            }

        runtime.hum_snapshot = hum_snapshot  # type: ignore[method-assign]
        app.screen._recent_membrane_events = lambda limit=4: [  # type: ignore[method-assign]
            {
                "event_type": "PASSTHROUGH",
                "detail": "Response passed the membrane unchanged.",
            }
        ]
        app.screen.refresh_panels()
        await pilot.pause(0.2)

        assert str(app.screen.main_thinking_panel().title) == "Reasoning"
        assert "Response material" in app.screen.main_thinking_panel().renderable.plain
        assert "Greetings, Brian." in app.screen.main_thinking_panel().renderable.plain
        assert "prompt scaffolding" in app.screen.main_thinking_panel().renderable.plain
        assert "Analyze the Request" not in app.screen.main_thinking_panel().renderable.plain
        assert "Membrane record" in app.screen.main_thinking_panel().renderable.plain

        app.screen.query_one("#reasoning_mode_chain_btn", Button).press()
        await pilot.pause(0.2)
        assert app.ui_state.reasoning_mode == "chain_like"
        assert str(app.screen.main_thinking_panel().title) == "Chain-Like Trace"
        assert "Response beats" in app.screen.main_thinking_panel().renderable.plain
        assert "1. Greetings, Brian." in app.screen.main_thinking_panel().renderable.plain
        assert "Analyze the Request" not in app.screen.main_thinking_panel().renderable.plain

        app.screen.query_one("#reasoning_mode_hum_btn", Button).press()
        await pilot.pause(0.2)
        assert app.ui_state.reasoning_mode == "hum_live"
        assert str(app.screen.main_thinking_panel().title) == "Hum Live Trace"
        hum_panel = app.screen.main_thinking_panel().renderable.plain
        assert "Hum entries" in hum_panel
        assert "[HUM_STATS]" in hum_panel
        assert "[HUM_TABLE]" in hum_panel
        assert "[T0] hum:" in hum_panel
        assert "1. lngg x2" in hum_panel

        app.screen.query_one("#reasoning_mode_reasoning_btn", Button).press()
        await pilot.pause(0.2)
        assert app.ui_state.reasoning_mode == "reasoning"
        assert str(app.screen.main_thinking_panel().title) == "Reasoning"


@pytest.mark.asyncio
async def test_reasoning_panel_surfaces_live_visible_reasoning_during_turn(runtime, monkeypatch) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(140, 44)) as pilot:
        await pilot.pause(1.0)
        composer = app.screen.query_one("#composer_input", TextArea)
        composer.load_text("Show the live reasoning stream.")

        original_chat = runtime.chat

        def live_chat(*, session_id: str, user_text: str, progress_callback=None):
            if progress_callback is not None:
                progress_callback(
                    {
                        "backend": "mock",
                        "phase": "reasoning",
                        "reasoning_text": "1. Inspect the active set.\n2. Check recent feedback.",
                        "answer_text": "",
                        "generation_tokens": 12,
                    }
                )
                time.sleep(0.15)
                progress_callback(
                    {
                        "backend": "mock",
                        "phase": "reasoning",
                        "reasoning_text": "1. Inspect the active set.\n2. Check recent feedback.\n3. Draft the answer.",
                        "answer_text": "",
                        "generation_tokens": 18,
                    }
                )
                time.sleep(0.15)
            return original_chat(session_id=session_id, user_text=user_text)

        monkeypatch.setattr(runtime, "chat", live_chat)

        send_task = asyncio.create_task(app.screen._send_turn())
        await pilot.pause(0.2)

        live_panel = app.screen.main_thinking_panel()
        assert str(live_panel.title) == "Reasoning [LIVE]"
        assert "Inspect the active set." in live_panel.renderable.plain
        assert "Draft the answer." in live_panel.renderable.plain
        assert "live_phase=reasoning" in live_panel.renderable.plain

        await send_task
        await pilot.pause(0.2)

        assert app.ui_state.turn_progress is None
        assert str(app.screen.main_thinking_panel().title) == "Reasoning"


@pytest.mark.asyncio
async def test_context_budget_panel_reports_used_and_remaining(runtime) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(140, 44)) as pilot:
        await pilot.pause(1.0)
        app.ui_state.current_budget = {
            "pressure_level": "MEDIUM",
            "prompt_budget_tokens": 1200,
            "remaining_input_tokens": 900,
        }
        app.screen.refresh_panels()
        await pilot.pause(0.2)

        panel_text = app.screen.main_context_budget_panel().renderable.plain
        assert "used 300/1200" in panel_text
        assert "left 900 | MEDIUM" in panel_text


@pytest.mark.asyncio
async def test_turn_status_panel_tracks_live_turn_progress(runtime) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(140, 44)) as pilot:
        await pilot.pause(1.0)
        app.ui_state.turn_progress = {
            "phase": "assembling",
            "detail": "assembling active set and prompt context",
            "started_at": time.monotonic() - 1.2,
        }
        app.screen.refresh_panels()
        await pilot.pause(0.2)

        panel_text = app.screen.main_turn_status_panel().renderable.plain
        assert "assembling" in panel_text
        assert "elapsed=" in panel_text

        runtime.runtime_log.emit(
            "INFO",
            "generation_start",
            "Generating Adam response.",
            backend="mock",
            profile_name="manual-balanced",
            effective_mode="manual",
        )
        app.screen._poll_logs()

        panel_text = app.screen.main_turn_status_panel().renderable.plain
        assert "generating" in panel_text
        assert "mock composing" in panel_text


@pytest.mark.asyncio
async def test_tui_deck_can_switch_to_typewriter_light_look(runtime) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)

        await app.action_show_deck()
        await pilot.pause(0.3)
        assert isinstance(app.screen, DeckModal)

        look_select = app.screen.query_one("#deck_look_select", Select)
        look_select.value = "typewriter_light"
        await pilot.pause(0.3)

        assert app.current_ui_look() == "typewriter_light"
        assert runtime.settings.ui_look == "typewriter_light"
        assert runtime.ui_appearance()["look"] == "typewriter_light"
        assert runtime.store.read_config("tui_appearance") == {"look": "typewriter_light"}
        assert app.ui_state.last_feedback == "look=Typewriter Light"

        deck_status = app.screen.chat_screen.deck_status_panel().renderable
        assert "look=Typewriter Light" in deck_status.plain


@pytest.mark.asyncio
async def test_session_config_modal_labels_history_and_clamped_summary(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    runtime.start_session(experiment["id"], title="Operator Session")
    runtime.start_session(experiment["id"], title="Field Notes")
    runtime.start_session(experiment["id"], title="FIELD NOTES")
    runtime.start_session(experiment["id"], title="Atlas Draft")

    app = EdenTuiApp(runtime)
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)

        await app.action_new_session()
        await pilot.pause(0.5)
        assert isinstance(app.screen, SessionConfigModal)
        modal = app.screen

        expected_labels = {
            "#session_title_label": "Operator Session",
            "#session_mode_label": "Mode",
            "#session_budget_mode_label": "Budget Mode",
            "#session_low_motion_label": "Low Motion",
            "#session_debug_label": "Debug",
            "#temperature_label": "Temperature",
            "#max_tokens_label": "Max Output Tokens",
            "#top_p_label": "Top-P",
            "#repetition_penalty_label": "Repetition Penalty",
            "#retrieval_depth_label": "Retrieval Depth",
            "#max_context_items_label": "Max Context Items",
            "#history_turns_label": "Conversation History Turns",
            "#response_char_cap_label": "Response Character Cap",
        }
        for selector, expected in expected_labels.items():
            assert modal.query_one(selector, Static).render().plain == expected

        expected_help_snippets = {
            "#session_mode_help": "MANUAL uses your bounded numbers directly after clamping.",
            "#session_budget_mode_help": "Sets the prompt-budget envelope.",
            "#session_low_motion_help": "ON reduces motion for steadier reading and lower terminal churn",
            "#session_debug_help": "The current MLX path does not switch sampler or retrieval behavior on this flag yet.",
            "#temperature_help": "Controls sampling randomness on the model side.",
            "#max_tokens_help": "Hard token cap for the generated answer.",
            "#top_p_help": "Nucleus-sampling cutoff for candidate tokens.",
            "#repetition_penalty_help": "Higher values discourage loops and reused phrasing",
            "#retrieval_depth_help": "How many recall candidates EDEN inspects before building the prompt.",
            "#max_context_items_help": "How many retrieved items EDEN can carry into the active prompt.",
            "#history_turns_help": "How many recent Brian/Adam turns EDEN carries into the prompt history.",
            "#response_char_cap_help": "Character cap for the operator-facing answer after membrane cleanup.",
        }
        for selector, expected in expected_help_snippets.items():
            assert expected in modal.query_one(selector, Static).render().plain

        history_select = modal.query_one("#session_title_history_select", Select)
        history_values = [value for _, value in history_select._options if value != Select.NULL]
        assert history_values == ["Atlas Draft", "FIELD NOTES", "Operator Session"]

        history_select.value = "FIELD NOTES"
        await pilot.pause(0.2)
        title_input = modal.query_one("#session_title_input", Input)
        assert title_input.value == "FIELD NOTES"

        title_input.value = "Fresh Session"
        await pilot.pause(0.2)
        assert history_select.value == Select.NULL

        modal.query_one("#temperature_input", Input).value = "3.7"
        modal.query_one("#max_tokens_input", Input).value = "10"
        modal.query_one("#top_p_input", Input).value = "2.4"
        modal.query_one("#repetition_penalty_input", Input).value = "-4"
        modal.query_one("#retrieval_depth_input", Input).value = "99"
        modal.query_one("#max_context_items_input", Input).value = "2"
        modal.query_one("#history_turns_input", Input).value = "999"
        modal.query_one("#response_char_cap_input", Input).value = "5000"
        await pilot.pause(0.3)

        summary_panel = modal.query_one("#session_config_summary", Static).render()
        summary_text = summary_panel._renderable.renderable.plain
        assert "temperature=1.50" in summary_text
        assert "top_p=1.00" in summary_text
        assert "repetition_penalty=0.00" in summary_text
        assert "retrieval_depth=32" in summary_text
        assert "max_context_items=4" in summary_text
        assert "history_turns=256" in summary_text
        assert "max_output_tokens=128" in summary_text
        assert "response_char_cap=5000" in summary_text

        modal.query_one("#max_tokens_input", Input).value = "99999"
        modal.query_one("#response_char_cap_input", Input).value = "99999"
        await pilot.pause(0.3)

        summary_panel = modal.query_one("#session_config_summary", Static).render()
        summary_text = summary_panel._renderable.renderable.plain
        assert "max_output_tokens=4096" in summary_text
        assert "response_char_cap=12000" in summary_text

        modal.query_one("#session_confirm_btn", Button).press()
        await pilot.pause(0.5)
        assert isinstance(app.screen, ChatScreen)
        assert app.ui_state.session_title == "Fresh Session"


@pytest.mark.asyncio
async def test_new_session_flow_wins_over_inflight_bootstrap_resume(runtime, monkeypatch) -> None:
    experiment = runtime.initialize_experiment("blank")
    resumed_session = runtime.start_session(
        experiment["id"],
        title="June Session",
        profile_request={"mode": "manual", "budget_mode": "balanced", "history_turns": 3},
    )
    runtime.chat(session_id=resumed_session["id"], user_text="Keep this prior session distinct from any fresh one.")

    snapshot_started = threading.Event()
    release_snapshot = threading.Event()
    original_snapshot = runtime.session_state_snapshot

    def delayed_snapshot(session_id: str):
        if session_id == resumed_session["id"]:
            snapshot_started.set()
            assert release_snapshot.wait(timeout=2.0)
        return original_snapshot(session_id)

    monkeypatch.setattr(runtime, "session_state_snapshot", delayed_snapshot)

    app = EdenTuiApp(runtime)
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        assert snapshot_started.wait(timeout=1.0)

        await app.action_new_session()
        await pilot.pause(0.5)
        assert isinstance(app.screen, SessionConfigModal)
        modal = app.screen

        modal.query_one("#session_title_input", Input).value = "Fresh Session"
        modal.query_one("#history_turns_input", Input).value = "64"
        modal.query_one("#max_tokens_input", Input).value = "2400"
        modal.query_one("#session_confirm_btn", Button).press()
        await pilot.pause(0.4)

        assert isinstance(app.screen, ChatScreen)
        fresh_session_id = app.ui_state.session_id
        assert fresh_session_id is not None
        assert fresh_session_id != resumed_session["id"]
        assert app.ui_state.session_title == "Fresh Session"
        assert app.ui_state.last_turn_id is None
        assert runtime.session_profile_request(fresh_session_id)["history_turns"] == 64
        assert runtime.session_profile_request(fresh_session_id)["max_output_tokens"] == 2400

        release_snapshot.set()
        await pilot.pause(0.5)

        assert app.ui_state.session_id == fresh_session_id
        assert app.ui_state.session_title == "Fresh Session"
        assert app.ui_state.last_turn_id is None


@pytest.mark.asyncio
async def test_tune_session_modal_restores_title_edit_and_recent_titles(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    runtime.start_session(experiment["id"], title="Atlas Draft")
    runtime.start_session(experiment["id"], title="Field Notes")
    current_session = runtime.start_session(experiment["id"], title="June Session")

    app = EdenTuiApp(runtime)
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        app.apply_session_snapshot(runtime.session_state_snapshot(current_session["id"]))
        app.screen.refresh_panels()
        await pilot.pause(0.2)
        assert app.ui_state.session_id == current_session["id"]
        assert app.ui_state.session_title == "June Session"

        app.screen.begin_edit_profile_flow()
        await pilot.pause(0.5)
        assert isinstance(app.screen, SessionConfigModal)
        modal = app.screen

        title_input = modal.query_one("#session_title_input", Input)
        assert title_input.value == "June Session"

        history_select = modal.query_one("#session_title_history_select", Select)
        history_values = [value for _, value in history_select._options if value != Select.NULL]
        assert history_values == ["June Session", "Field Notes", "Atlas Draft"]

        history_select.value = "Field Notes"
        await pilot.pause(0.2)
        assert title_input.value == "Field Notes"

        title_input.value = "June Session Revised"
        modal.query_one("#history_turns_input", Input).value = "64"
        modal.query_one("#max_tokens_input", Input).value = "2400"
        modal.query_one("#response_char_cap_input", Input).value = "7200"
        await pilot.pause(0.2)
        assert history_select.value == Select.NULL

        modal.query_one("#session_confirm_btn", Button).press()
        await pilot.pause(0.5)

        assert isinstance(app.screen, ChatScreen)
        assert app.ui_state.session_title == "June Session Revised"
        assert runtime.store.get_session(current_session["id"])["title"] == "June Session Revised"
        assert runtime.session_profile_request(current_session["id"])["title"] == "June Session Revised"
        assert runtime.session_profile_request(current_session["id"])["history_turns"] == 64
        assert runtime.session_profile_request(current_session["id"])["max_output_tokens"] == 2400
        assert runtime.session_profile_request(current_session["id"])["response_char_cap"] == 7200
        assert "Updated session profile: June Session Revised" in app.ui_state.last_feedback
        assert "history_turns=64" in app.ui_state.last_feedback
        assert "max_output_tokens=2400" in app.ui_state.last_feedback
        assert "response_char_cap=7200" in app.ui_state.last_feedback
        assert app.ui_state.current_profile is not None
        assert app.ui_state.current_profile["history_turns"] == 64
        assert app.ui_state.current_profile["max_output_tokens"] == 2400
        assert app.ui_state.current_profile["response_char_cap"] == 7200
        assert app.ui_state.current_profile["profile_name"] == "manual:balanced"
        assert app.ui_state.current_budget is not None
        assert app.ui_state.current_budget["prompt_budget_tokens"] == app.ui_state.current_profile["prompt_budget_tokens"]

        app.screen.begin_edit_profile_flow()
        await pilot.pause(0.5)
        assert isinstance(app.screen, SessionConfigModal)
        reopened_modal = app.screen
        assert reopened_modal.query_one("#history_turns_input", Input).value == "64"
        assert reopened_modal.query_one("#max_tokens_input", Input).value == "2400"
        assert reopened_modal.query_one("#response_char_cap_input", Input).value == "7200"


@pytest.mark.asyncio
async def test_tui_conversation_atlas_saves_taxonomy_and_resumes_session(runtime, monkeypatch) -> None:
    experiment = runtime.initialize_experiment("blank")
    first_session = runtime.start_session(experiment["id"], title="Atlas One")
    runtime.chat(session_id=first_session["id"], user_text="Describe conversation atlas one.")
    second_session = runtime.start_session(experiment["id"], title="Atlas Two")
    runtime.chat(session_id=second_session["id"], user_text="Describe conversation atlas two.")
    opened_urls: list[str] = []
    export_calls: list[tuple[str, str | None]] = []
    original_export = runtime.export_observability

    def capture_open(url: str) -> BrowserOpenResult:
        opened_urls.append(url)
        return BrowserOpenResult(ok=True, method="mock")

    def capture_export(*, experiment_id: str, session_id: str | None = None):
        export_calls.append((experiment_id, session_id))
        return original_export(experiment_id=experiment_id, session_id=session_id)

    monkeypatch.setattr("eden.tui.app.open_browser_url", capture_open)
    monkeypatch.setattr(runtime, "export_observability", capture_export)

    app = EdenTuiApp(runtime)
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        await app.action_show_archive()
        await pilot.pause(0.5)
        assert isinstance(app.screen, ConversationAtlasModal)
        modal = app.screen
        center_ids = [child.id for child in modal.query_one("#atlas_main_column").children if child.id]
        assert center_ids == ["atlas_records_table", "atlas_detail_row"]
        detail_ids = [child.id for child in modal.query_one("#atlas_detail_row").children if child.id]
        assert detail_ids == ["atlas_metadata_column", "atlas_preview_column"]
        metadata_ids = [child.id for child in modal.query_one("#atlas_metadata_column").children if child.id]
        assert metadata_ids == ["atlas_folder_field", "atlas_tags_field", "atlas_taxonomy_actions"]
        preview_ids = [child.id for child in modal.query_one("#atlas_preview_column").children if child.id]
        assert preview_ids == ["atlas_preview_scroller", "atlas_observatory_actions", "atlas_session_actions"]
        assert modal.query_one_optional("#atlas_projection_panel") is None
        assert modal.query_one_optional("#atlas_editor_hint") is None
        search = modal.query_one("#atlas_search_input", Input)
        search.value = "Atlas One"
        await pilot.pause(0.3)
        assert len(modal._filtered_records) == 1
        assert modal._selected_record()["id"] == first_session["id"]
        assert modal._selected_preview is not None
        assert modal._selected_preview["session_title"] == "Atlas One"
        preview_panel = modal.query_one("#atlas_preview_panel", Static).render()
        preview_text = preview_panel._renderable.renderable.plain
        assert "Browser Observatory" in preview_text
        assert "transcript_path=" in preview_text
        modal.query_one("#atlas_folder_input", Input).value = "library/notes"
        modal.query_one("#atlas_tags_input", TextArea).load_text("research, archive, research")
        await modal._save_metadata_worker()
        await pilot.pause(0.3)
        record = next(item for item in runtime.conversation_archive_records() if item["id"] == first_session["id"])
        assert record["folder"] == "library/notes"
        assert record["tags"] == ["research", "archive"]
        modal.query_one("#atlas_open_btn", Button).press()
        await pilot.pause(0.3)
        assert opened_urls
        refreshed_record = next(item for item in runtime.conversation_archive_records() if item["id"] == first_session["id"])
        assert refreshed_record["conversation_log_exists"] is True
        transcript_path = Path(refreshed_record["conversation_log_path"])
        assert transcript_path.exists()
        modal.query_one("#atlas_observatory_btn", Button).press()
        await pilot.pause(0.8)
        assert export_calls == [(experiment["id"], first_session["id"])]
        assert any(
            urlparse(url).path.endswith(f"{experiment['id']}/observatory_index.html")
            and parse_qs(urlparse(url).query).get("session_id") == [first_session["id"]]
            for url in opened_urls
        )
        modal.query_one("#atlas_turns_api_btn", Button).press()
        await pilot.pause(0.3)
        assert opened_urls[-1].endswith(f"api/sessions/{first_session['id']}/turns")
        modal.query_one("#atlas_active_set_api_btn", Button).press()
        await pilot.pause(0.3)
        assert opened_urls[-1].endswith(f"api/sessions/{first_session['id']}/active-set")
        modal.query_one("#atlas_refresh_btn", Button).press()
        await pilot.pause(0.3)
        assert len(modal._filtered_records) == 1
        assert modal._selected_record()["id"] == first_session["id"]
        modal.query_one("#atlas_resume_btn", Button).press()
        await pilot.pause(0.5)
        assert isinstance(app.screen, ChatScreen)
        assert app.ui_state.session_id == first_session["id"]
        assert app.ui_state.session_title == "Atlas One"

    runtime.stop_observatory()


@pytest.mark.asyncio
async def test_tui_compact_layout_keeps_first_action_and_escape_recovery(runtime) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        assert app.screen._is_compact_layout() is True
        assert getattr(app.focused, "id", None) == "composer_input"
        assert app.screen.query_one("#runtime_action_menu").display is True
        assert app.screen.query_one("#chat_secondary").display is False

        chyron = app.screen.query_one("#runtime_chyron_panel")
        assert chyron.display is False
        await pilot.press("f11")
        await pilot.pause(0.2)
        assert chyron.display is True
        await pilot.press("f11")
        await pilot.pause(0.2)
        assert chyron.display is False

        await pilot.press("tab")
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "runtime_action_menu"
        await pilot.press("enter")
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "composer_input"
        assert "No Adam reply is available to review yet" in app.ui_state.last_feedback
        await pilot.press("tab")
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "runtime_action_menu"
        await pilot.press("escape")
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "composer_input"

        app.screen.toggle_aperture_drawer()
        await pilot.pause(0.2)
        assert app.ui_state.aperture_drawer_open is True
        assert app.screen.query_one("#chat_primary").display is False
        assert app.screen.query_one("#chat_secondary").display is True

        await pilot.press("escape")
        await pilot.pause(0.2)
        assert app.ui_state.aperture_drawer_open is False
        assert app.screen.query_one("#chat_primary").display is True
        assert app.screen.query_one("#chat_secondary").display is False
        assert getattr(app.focused, "id", None) == "composer_input"

        await app.action_show_review()
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "composer_input"
        assert "No Adam reply is available to review yet" in app.ui_state.last_feedback


@pytest.mark.asyncio
async def test_open_browser_observatory_refreshes_current_export_and_targets_index(runtime, monkeypatch) -> None:
    opened_urls: list[str] = []
    export_calls: list[tuple[str, str | None]] = []
    original_export = runtime.export_observability

    def capture_open(url: str) -> BrowserOpenResult:
        opened_urls.append(url)
        return BrowserOpenResult(ok=True, method="mock")

    def capture_export(*, experiment_id: str, session_id: str | None = None):
        export_calls.append((experiment_id, session_id))
        return original_export(experiment_id=experiment_id, session_id=session_id)

    monkeypatch.setattr("eden.tui.app.open_browser_url", capture_open)
    monkeypatch.setattr(runtime, "export_observability", capture_export)

    app = EdenTuiApp(runtime)
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        assert app.ui_state.experiment_id is not None
        assert app.ui_state.session_id is not None

        await app.screen.handle_observatory()
        await pilot.pause(0.8)

        assert export_calls == [(app.ui_state.experiment_id, app.ui_state.session_id)]
        assert opened_urls
        assert urlparse(opened_urls[0]).path.endswith(f"{app.ui_state.experiment_id}/observatory_index.html")
        assert parse_qs(urlparse(opened_urls[0]).query).get("session_id") == [app.ui_state.session_id]
        assert "observatory_index.html" in app.ui_state.last_feedback

    runtime.stop_observatory()


@pytest.mark.asyncio
async def test_open_browser_observatory_reports_launch_failure(runtime, monkeypatch) -> None:
    original_export = runtime.export_observability

    def capture_export(*, experiment_id: str, session_id: str | None = None):
        return original_export(experiment_id=experiment_id, session_id=session_id)

    def fail_open(url: str) -> BrowserOpenResult:
        return BrowserOpenResult(ok=False, method="mock", detail=f"launcher unavailable for {url}")

    monkeypatch.setattr("eden.tui.app.open_browser_url", fail_open)
    monkeypatch.setattr(runtime, "export_observability", capture_export)

    app = EdenTuiApp(runtime)
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        assert app.ui_state.experiment_id is not None

        await app.screen.handle_observatory()
        await pilot.pause(0.8)

        assert "browser launch failed" in app.ui_state.last_feedback
        assert "observatory_index.html" in app.ui_state.last_feedback

    runtime.stop_observatory()


@pytest.mark.asyncio
async def test_runtime_action_menu_selection_executes_observatory(runtime, monkeypatch) -> None:
    opened_urls: list[str] = []

    def capture_open(url: str) -> BrowserOpenResult:
        opened_urls.append(url)
        return BrowserOpenResult(ok=True, method="mock")

    monkeypatch.setattr("eden.tui.app.open_browser_url", capture_open)

    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        menu = app.screen.query_one("#runtime_action_menu", ActionStrip)
        menu.focus()
        menu.set_value("observatory", notify=True)
        await pilot.press("enter")
        await pilot.pause(0.8)

        assert opened_urls
        assert urlparse(opened_urls[0]).path.endswith(f"{app.ui_state.experiment_id}/observatory_index.html")
        assert parse_qs(urlparse(opened_urls[0]).query).get("session_id") == [app.ui_state.session_id]
        assert "observatory_index.html" in app.ui_state.last_feedback
        assert menu.value == "observatory"

        await pilot.press("enter")
        await pilot.pause(0.8)

        assert len(opened_urls) == 2

    runtime.stop_observatory()


@pytest.mark.asyncio
async def test_runtime_action_menu_digit_shortcut_opens_existing_observatory_shell_before_slow_export(runtime, monkeypatch) -> None:
    opened_urls: list[str] = []
    export_started = threading.Event()
    export_can_finish = threading.Event()
    original_export = runtime.export_observability

    # Seed an existing shell so the browser can open immediately before the refresh completes.
    original_export(experiment_id=runtime.primary_experiment()["id"], session_id=None)

    def slow_export(*, experiment_id: str, session_id: str | None = None):
        export_started.set()
        export_can_finish.wait(timeout=5.0)
        return original_export(experiment_id=experiment_id, session_id=session_id)

    def capture_open(url: str) -> BrowserOpenResult:
        opened_urls.append(url)
        return BrowserOpenResult(ok=True, method="mock")

    monkeypatch.setattr(runtime, "export_observability", slow_export)
    monkeypatch.setattr("eden.tui.app.open_browser_url", capture_open)

    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        menu = app.screen.query_one("#runtime_action_menu", ActionStrip)
        menu.focus()
        await pilot.press("8")
        await pilot.press("enter")
        await pilot.pause(0.3)

        assert export_started.is_set()
        assert opened_urls
        assert urlparse(opened_urls[0]).path.endswith(f"{app.ui_state.experiment_id}/observatory_index.html")
        assert parse_qs(urlparse(opened_urls[0]).query).get("session_id") == [app.ui_state.session_id]

        export_can_finish.set()
        await pilot.pause(1.0)

    runtime.stop_observatory()


@pytest.mark.asyncio
async def test_runtime_action_menu_observatory_progress_and_duplicate_guard(runtime, monkeypatch) -> None:
    opened_urls: list[str] = []
    start_calls = 0
    original_start = runtime.start_observatory

    def slow_start(*, reuse_existing: bool = True):
        nonlocal start_calls
        start_calls += 1
        time.sleep(0.35)
        return original_start(reuse_existing=reuse_existing)

    def capture_open(url: str) -> BrowserOpenResult:
        opened_urls.append(url)
        return BrowserOpenResult(ok=True, method="mock")

    monkeypatch.setattr(runtime, "start_observatory", slow_start)
    monkeypatch.setattr("eden.tui.app.open_browser_url", capture_open)

    app = EdenTuiApp(runtime)
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        menu = app.screen.query_one("#runtime_action_menu", ActionStrip)
        menu.focus()
        menu.set_value("observatory", notify=True)
        await pilot.press("enter")
        await pilot.pause(0.1)

        rendered_strip = menu.render().plain
        assert "action=Open Browser Observatory" in rendered_strip
        assert "phase=Ensuring observatory server" in rendered_strip
        assert "elapsed=" in rendered_strip
        assert "progress=" in rendered_strip
        assert menu.value == "observatory"

        await pilot.press("enter")
        await pilot.pause(0.1)

        assert start_calls == 1

        await pilot.pause(1.0)

        assert opened_urls
        assert len(opened_urls) == 1

    runtime.stop_observatory()
