"""WebUI host tests driven by the Action vocabulary.

Keyboard/click/request paths already exist under ``test_web_events`` and
``test_web_request_hooks``. These tests assert that Actions are the
shared object form: matching, ``to_event``, ``WebSession.perform``, and
parity with ``dispatch_*`` helpers.
"""

from __future__ import annotations

from tests.web.grids import ClickableGrid, InteractiveGrid, RequestHookGrid
from xnano.core.actions import Action
from xnano.events import Event, KeyboardEventData, on_action, on_keyboard
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.web import Web
from xnano.web.requests import on_post_request


def test_web_session_perform_keyboard_action() -> None:
    """WebSession inherits host.perform; keyboard Actions fire hooks."""
    grid = InteractiveGrid()
    web = Web()
    web.render_html(grid)
    session = web._ensure_default_session()

    session.perform(Action.keyboard("up"))
    assert grid.count == 10
    session.perform(Action.keyboard("ctrl+k"))
    assert grid.count == 20


def test_web_dispatch_keyboard_matches_action_object() -> None:
    """dispatch_keyboard and Action.keyboard describe the same binding."""
    SAVE = Action.keyboard("ctrl+k")
    event = Event.from_data(KeyboardEventData.from_binding("ctrl+k"))
    assert SAVE.matches(event)

    grid = InteractiveGrid()
    web = Web()
    web.render_html(grid)
    web.dispatch_keyboard("ctrl+k")
    assert grid.count == 10
    # Action.round-trip: same binding via session.perform
    web._ensure_default_session().perform(SAVE)
    assert grid.count == 20


def test_web_shared_action_on_decorator() -> None:
    BUMP = Action.keyboard("b")

    class App(BaseGrid):
        n: int = Field(default=0, state=True)
        label: str = Field(default="0", height=1)

        @on_action(BUMP)
        def bump(self, ctx) -> None:
            self.n += 1
            self.label = str(self.n)

    grid = App()
    web = Web()
    web.render_html(grid)
    session = web._ensure_default_session()
    session.perform(BUMP)
    assert grid.n == 1
    web.dispatch_keyboard("b")
    assert grid.n == 2


def test_web_dispatch_click_uses_action_click_event() -> None:
    """dispatch_click builds Action.click(field).to_event() under the hood."""
    grid = ClickableGrid()
    web = Web()
    web.render_html(grid)
    target_id = next(iter(web._controller.click_targets.keys()))

    click = Action.click("body")
    event = click.to_event()
    assert click.matches(event)
    assert event.is_mouse_event()
    assert event.mouse_event_kind == "press"

    assert grid.count == 0
    html_out = web.dispatch_click(target_id)
    assert grid.count == 1
    assert "Count: 1" in html_out


def test_web_click_action_field_is_metadata_for_matches() -> None:
    """Action.click field does not affect matches — host maps target_id."""
    left = Action.click("body")
    other = Action.click("label")
    event = left.to_event()
    assert left.matches(event)
    assert other.matches(event)  # field ignored by matches


def test_web_request_action_object_form_with_dispatch() -> None:
    """Action.request documents the route; dispatch_request fires hooks."""
    POST = Action.request("POST", "/increment")
    shell = POST.to_event()
    assert POST.matches(shell)
    assert not Action.request("GET", "/increment").matches(shell)

    grid = RequestHookGrid()
    web = Web()
    web.render_html(grid)
    web.dispatch_request("POST", "/increment")
    assert grid.count == 1
    web.dispatch_request("POST", "/increment")
    assert grid.count == 2


def test_web_session_perform_request_does_not_fire_http_hooks() -> None:
    """HTTP hooks live on the request registry, not dispatch_hooks.

    perform(Action.request(...)) synthesizes a request shell but the
    shared pump has no request branch — use dispatch_request / HTTP.
    """
    grid = RequestHookGrid()
    web = Web()
    web.render_html(grid)
    session = web._ensure_default_session()
    session.perform(Action.request("POST", "/increment"))
    assert grid.count == 0
    session.dispatch_request("POST", "/increment")
    assert grid.count == 1


def test_web_action_request_with_custom_grid_hook() -> None:
    """Custom POST path expressed as Action.request + dispatch_request."""
    SAVE = Action.request("POST", "/save")

    class SaveGrid(BaseGrid):
        saved: bool = Field(default=False, state=True)
        label: str = Field(default="no", height=1)

        @on_post_request("/save")
        def save(self) -> None:
            self.saved = True
            self.label = "yes"

    grid = SaveGrid()
    web = Web()
    web.render_html(grid)
    assert SAVE.matches(SAVE.to_event())
    from typing import cast

    from xnano.web.requests import HttpMethod

    web.dispatch_request(cast(HttpMethod, SAVE.method), SAVE.path)
    assert grid.saved is True
    assert "yes" in web.render_html()


def test_web_keyboard_action_unmatched_binding_is_noop() -> None:
    grid = InteractiveGrid()
    web = Web()
    web.render_html(grid)
    session = web._ensure_default_session()
    session.perform(Action.keyboard("x"))
    assert grid.count == 0


def test_web_ctx_actions_press_via_keyboard_hook() -> None:
    class App(BaseGrid):
        n: int = Field(default=0, state=True)
        label: str = Field(default="0", height=1)

        @on_keyboard("z")
        def bump(self, ctx) -> None:
            self.n += 1
            self.label = str(self.n)

        @on_keyboard("p")
        def via_actions(self, ctx) -> None:
            ctx.actions.press("z")

    grid = App()
    web = Web()
    web.render_html(grid)
    session = web._ensure_default_session()
    session.perform(Action.keyboard("p"))
    assert grid.n == 1
