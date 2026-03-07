from __future__ import annotations

import pytest

from textual.widgets import Select, TextArea

from eden.tui.app import ChatScreen, EdenTuiApp


@pytest.mark.asyncio
async def test_tui_boots_blank_mode_and_uses_multiline_composer(runtime) -> None:
    app = EdenTuiApp(runtime)
    async with app.run_test() as pilot:
        assert isinstance(app.screen, ChatScreen)
        await pilot.pause(1.0)
        assert app.ui_state.session_id is not None
        menu = app.screen.query_one("#runtime_action_menu", Select)
        assert str(menu.value) == "review"
        composer = app.screen.query_one("#composer_input", TextArea)
        composer.load_text("line one\nline two")
        await pilot.pause()
        assert "\n" in composer.text
        await app.screen._send_turn()
        await pilot.pause(0.4)
        assert app.ui_state.last_turn_id is not None
        assert app.ui_state.last_response
        assert app.screen.query_one("#active_aperture_panel")
        assert app.screen.query_one("#thinking_panel")
        assert app.screen.query_one("#feedback_panel")
        assert app.screen.query_one("#chat_exchange_panel")
        assert app.screen.query_one("#feedback_loop_panel")
        assert app.screen.query_one("#signal_field")
        assert app.screen.query_one("#ritual_panel")
        assert app.screen.query_one("#forensic_log")
        await app.screen.submit_feedback("skip", explanation="", corrected="")
        await pilot.pause(0.2)
        assert "SKIP recorded" in app.ui_state.last_feedback
