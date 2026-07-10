"""Web host event dispatch: click, keyboard, tick, input, and page extras."""

from __future__ import annotations

import time

from tests.beta.grids import ClickableGrid, InteractiveGrid, SimpleGrid
from xnano.beta.web import Web


def test_dispatch_click_fires_handler() -> None:
    """dispatch_click invokes the handler and re-renders."""
    grid = ClickableGrid()
    web = Web()
    web.render_html(grid)
    target_id = next(iter(web._controller.click_targets.keys()))

    assert grid.count == 0
    html_out = web.dispatch_click(target_id)
    assert grid.count == 1
    assert "Count: 1" in html_out


def test_dispatch_click_increments_state() -> None:
    """Multiple dispatch_click calls increment state."""
    grid = ClickableGrid()
    web = Web()
    web.render_html(grid)
    target_id = next(iter(web._controller.click_targets.keys()))

    web.dispatch_click(target_id)
    assert grid.count == 1
    web.dispatch_click(target_id)
    assert grid.count == 2


def test_dispatch_click_stale_id_idempotent() -> None:
    """dispatch_click with unknown target_id returns html, state unchanged."""
    grid = ClickableGrid()
    web = Web()
    web.render_html(grid)

    html_out = web.dispatch_click("t999")
    assert grid.count == 0
    assert "Count: 0" in html_out


def test_build_page_includes_shell() -> None:
    """build_page includes document shell, Tailwind, htmx, and app root."""
    grid = SimpleGrid()
    web = Web(title="My <App>")
    page = web.build_page(web.render_html(grid))
    assert "<!doctype html>" in page
    assert "cdn.tailwindcss.com" in page
    assert "htmx.org" in page
    assert 'id="xnano-app"' in page
    assert "&lt;App&gt;" in page
    assert "<App>" not in page


def _interactive_web() -> tuple[Web, InteractiveGrid]:
    grid = InteractiveGrid()
    web = Web()
    web.render_html(grid)
    return web, grid


def test_dispatch_keyboard_matches_binding() -> None:
    """dispatch_keyboard fires @on_keyboard hooks matching the binding."""
    web, grid = _interactive_web()
    web.dispatch_keyboard("up")
    assert grid.count == 10
    web.dispatch_keyboard("ctrl+k")
    assert grid.count == 20


def test_dispatch_keyboard_ignores_unmatched() -> None:
    """Unmatched bindings leave state untouched but still re-render."""
    web, grid = _interactive_web()
    html_out = web.dispatch_keyboard("x")
    assert grid.count == 0
    assert "Count: 0" in html_out


def test_on_field_hook_runs_after_events() -> None:
    """@on_field expressions are pumped after each dispatched event."""
    web, grid = _interactive_web()
    web.dispatch_keyboard("up")
    assert grid.note == "double digits"


def test_dispatch_tick_fires_interval_gated_hooks() -> None:
    """dispatch_tick fires @on_tick hooks respecting their interval."""
    web, grid = _interactive_web()
    web.dispatch_tick()
    first = grid.ticks
    assert first >= 1
    web.dispatch_tick()
    assert grid.ticks == first
    time.sleep(0.06)
    web.dispatch_tick()
    assert grid.ticks == first + 1


def test_input_text_renders_as_input_element() -> None:
    """Editable Text renders as a real <input> with htmx sync attrs."""
    web, _grid = _interactive_web()
    html_out = web.render_html()
    assert "<input" in html_out
    assert 'hx-post="/xnano/input/' in html_out
    assert 'placeholder="name…"' in html_out
    assert 'hx-swap="none"' in html_out


def test_dispatch_input_updates_text_content() -> None:
    """dispatch_input writes the edited value back onto the Text."""
    web, grid = _interactive_web()
    target_id = next(iter(web._controller.input_targets))
    web.dispatch_input(target_id, "hammad")
    assert grid.name.content == "hammad"
    assert grid.name.cursor == len("hammad")
    assert 'value="hammad"' in web.render_html()


def test_build_page_wires_keyboard_and_poller() -> None:
    """Page includes keydown capture and the htmx tick poller."""
    web, _grid = _interactive_web()
    page = web.build_page(web.render_html())
    assert "keydown" in page
    assert "/xnano/key" in page
    assert 'hx-post="/xnano/tick"' in page
    assert "every 100ms" in page


def test_build_page_omits_extras_without_hooks() -> None:
    """A hook-less grid gets no keyboard capture or poller."""
    grid = SimpleGrid()
    web = Web()
    page = web.build_page(web.render_html(grid))
    assert "keydown" not in page
    assert "/xnano/tick" not in page
