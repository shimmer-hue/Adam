from __future__ import annotations

import time
from pathlib import Path

import pytest

from textual.widgets import Button, Input, Select, Static, TextArea

from eden.browser import BrowserOpenResult
from eden.tui.app import ChatScreen, ConversationAtlasModal, DeckModal, EdenTuiApp, SessionConfigModal


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
            "#response_char_cap_label": "Response Character Cap",
        }
        for selector, expected in expected_labels.items():
            assert modal.query_one(selector, Static).render().plain == expected

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
        modal.query_one("#response_char_cap_input", Input).value = "5000"
        await pilot.pause(0.3)

        summary_panel = modal.query_one("#session_config_summary", Static).render()
        summary_text = summary_panel._renderable.renderable.plain
        assert "temperature=1.50" in summary_text
        assert "top_p=1.00" in summary_text
        assert "repetition_penalty=0.00" in summary_text
        assert "retrieval_depth=32" in summary_text
        assert "max_context_items=4" in summary_text
        assert "max_output_tokens=128" in summary_text
        assert "response_char_cap=3200" in summary_text

        modal.query_one("#session_confirm_btn", Button).press()
        await pilot.pause(0.5)
        assert isinstance(app.screen, ChatScreen)
        assert app.ui_state.session_title == "Fresh Session"


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
        assert any(url.endswith(f"{experiment['id']}/observatory_index.html") for url in opened_urls)
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
        assert opened_urls[0].endswith(f"{app.ui_state.experiment_id}/observatory_index.html")
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
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        menu = app.screen.query_one("#runtime_action_menu", Select)

        menu.value = "observatory"
        await pilot.pause(0.8)

        assert opened_urls
        assert opened_urls[0].endswith(f"{app.ui_state.experiment_id}/observatory_index.html")
        assert "observatory_index.html" in app.ui_state.last_feedback
        assert str(menu.value) == "review"

        menu.value = "observatory"
        await pilot.pause(0.8)

        assert len(opened_urls) == 2

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
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        assert isinstance(app.screen, ChatScreen)
        menu = app.screen.query_one("#runtime_action_menu", Select)

        menu.value = "observatory"
        await pilot.pause(0.1)

        panel = app.screen.main_action_bus_panel()
        assert "action=Open Browser Observatory" in panel.renderable.plain
        assert "phase=Ensuring observatory server" in panel.renderable.plain
        assert "elapsed=" in panel.renderable.plain
        assert "progress=" in panel.renderable.plain
        assert str(menu.value) == "review"

        menu.value = "observatory"
        await pilot.pause(0.1)

        assert start_calls == 1
        assert "already running" in app.ui_state.last_feedback

        await pilot.pause(1.0)

        assert opened_urls
        assert len(opened_urls) == 1

    runtime.stop_observatory()
