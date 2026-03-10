from __future__ import annotations

from pathlib import Path

import pytest

from textual.widgets import Button, Input, Select, TextArea

from eden.tui.app import ChatScreen, ConversationAtlasModal, EdenTuiApp


@pytest.mark.asyncio
async def test_tui_boots_blank_mode_and_uses_multiline_composer(runtime, sample_files) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test() as pilot:
        assert isinstance(app.screen, ChatScreen)
        await pilot.pause(1.0)
        assert app.ui_state.session_id is not None
        chat_primary = app.screen.query_one("#chat_primary")
        chat_secondary = app.screen.query_one("#chat_secondary")
        assert app.screen.query_one("#chat_deck").parent is chat_primary
        assert app.screen.query_one("#signal_field").parent is chat_secondary
        assert app.screen.query_one("#action_bus_panel")
        assert app.screen.query_one("#header_ingest_btn", Button)
        aperture_button = app.screen.query_one("#header_aperture_btn", Button)
        menu = app.screen.query_one("#runtime_action_menu", Select)
        assert str(menu.value) == "review"
        await pilot.press("tab")
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "runtime_action_menu"
        await pilot.press("h", "i")
        await pilot.pause(0.2)
        composer = app.screen.query_one("#composer_input", TextArea)
        assert composer.text == "hi"
        aperture_button.press()
        await pilot.pause(0.2)
        assert app.ui_state.aperture_drawer_open is True
        assert app.screen.query_one("#aperture_drawer_panel")
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
        assert app.screen.query_one("#active_aperture_panel")
        assert app.screen.query_one("#thinking_panel")
        assert app.screen.query_one("#chat_tape")
        assert app.screen.query_one("#chat_exchange_panel")
        assert app.screen.query_one("#feedback_loop_panel")
        assert app.screen.query_one("#signal_field")
        assert app.screen.query_one("#runtime_chyron_panel")
        assert app.ui_state.conversation_log_path is not None
        transcript_path = Path(app.ui_state.conversation_log_path)
        assert transcript_path.exists()
        assert "line one" in transcript_path.read_text(encoding="utf-8")
        assert "Answer:" not in transcript_path.read_text(encoding="utf-8")
        await app.action_show_review()
        await pilot.pause(0.2)
        assert getattr(app.focused, "id", None) == "inline_feedback_verdict_input"
        verdict = app.screen.query_one("#inline_feedback_verdict_input", Input)
        verdict.value = "A"
        await pilot.pause(0.2)
        explanation = app.screen.query_one("#inline_feedback_explanation_input", TextArea)
        explanation.load_text("Accepting because the reply matches the session frame.")
        confirm = app.screen.query_one("#inline_feedback_confirm_input", Input)
        confirm.value = "Y"
        await app.screen._submit_inline_feedback_from_fields()
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
async def test_tui_conversation_atlas_saves_taxonomy_and_resumes_session(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    first_session = runtime.start_session(experiment["id"], title="Atlas One")
    runtime.chat(session_id=first_session["id"], user_text="Describe conversation atlas one.")
    second_session = runtime.start_session(experiment["id"], title="Atlas Two")
    runtime.chat(session_id=second_session["id"], user_text="Describe conversation atlas two.")

    app = EdenTuiApp(runtime)
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        await app.action_show_archive()
        await pilot.pause(0.5)
        assert isinstance(app.screen, ConversationAtlasModal)
        modal = app.screen
        search = modal.query_one("#atlas_search_input", Input)
        search.value = "Atlas One"
        await pilot.pause(0.3)
        assert len(modal._filtered_records) == 1
        assert modal._selected_record()["id"] == first_session["id"]
        modal.query_one("#atlas_folder_input", Input).value = "library/notes"
        modal.query_one("#atlas_tags_input", Input).value = "research, archive, research"
        await modal._save_metadata_worker()
        await pilot.pause(0.3)
        record = next(item for item in runtime.conversation_archive_records() if item["id"] == first_session["id"])
        assert record["folder"] == "library/notes"
        assert record["tags"] == ["research", "archive"]
        modal.query_one("#atlas_resume_btn", Button).press()
        await pilot.pause(0.5)
        assert isinstance(app.screen, ChatScreen)
        assert app.ui_state.session_id == first_session["id"]
        assert app.ui_state.session_title == "Atlas One"


@pytest.mark.asyncio
async def test_tui_compact_layout_keeps_first_action_and_escape_recovery(runtime) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        assert app.screen._is_compact_layout() is True
        assert getattr(app.focused, "id", None) == "composer_input"
        assert app.screen.query_one("#action_bus_panel").display is False
        assert app.screen.query_one("#runtime_status_strip").display is False
        assert app.screen.query_one("#chat_secondary").display is False

        hint = app.screen.main_composer_hint_panel().renderable
        assert "Start here:" in hint.plain
        assert "Ctrl+S" in hint.plain
        assert "F10 atlas" in hint.plain

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
