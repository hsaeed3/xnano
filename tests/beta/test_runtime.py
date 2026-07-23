"""tests.beta.test_runtime"""

from __future__ import annotations

import signal

from xnano.beta.core import Frame, Runtime
from xnano.beta.core.runtime import (
    _ACTIVE_RUNTIME,
    _EXIT_SIGNALS,
    _atexit_restore_active_runtime,
)


def test_offscreen_runtime_render_text() -> None:
    runtime = Runtime.offscreen(40, 10)
    try:
        frame = runtime.render("hello beta")
        assert isinstance(frame, Frame)
        assert frame.width == 40
        assert frame.height == 10
        assert frame.contains("hello beta")
        assert frame.revision == 1
        frame2 = runtime.render("second")
        assert frame2.revision == 2
    finally:
        runtime.close()


def test_runtime_uses_complete_grid_rendering_and_default_exit() -> None:
    from xnano.beta.actions import Action
    from xnano.beta.fields import Field
    from xnano.beta.grids import BaseGrid

    class App(BaseGrid):
        name: str = Field(default="John Doe", border="rounded")

        def grid_render(self) -> None:
            self.name = "Jane Doe"

    runtime = Runtime.offscreen(20, 4)
    try:
        app = App()
        runtime.set_root(app)
        frame = runtime.render()
        assert "╭──────────────────╮" in frame.text
        assert "│Jane Doe" in frame.text
        assert runtime.stage.get_area("name") is not None
        runtime.perform(Action.keyboard("ctrl+c"))
        assert runtime.pump() is False
    finally:
        runtime.close()


def test_runtime_resolves_mouse_field_for_click_hooks() -> None:
    from xnano.beta import hooks
    from xnano.beta.actions import Action
    from xnano.beta.fields import Field
    from xnano.beta.grids import BaseGrid

    class App(BaseGrid):
        button: str = Field(default="Click", group="action")
        clicked: bool = Field(default=False, state=True)

        @hooks.on_click("button")
        def click(self) -> None:
            self.clicked = True

    runtime = Runtime.offscreen(20, 4)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        runtime.perform(Action.mouse("left", kind="press"))
        assert app.clicked is True
    finally:
        runtime.close()


def test_runtime_honors_focus_filters_and_tick_intervals() -> None:
    from xnano.beta import hooks
    from xnano.beta.actions import Action
    from xnano.beta.components.input import Input
    from xnano.beta.fields import Field
    from xnano.beta.grids import BaseGrid

    class App(BaseGrid):
        name: Input = Field(default_factory=Input, group="name")
        focus_count: int = Field(default=0, state=True)
        tick_count: int = Field(default=0, state=True)

        @hooks.on_focus(group="name", kind="gained")
        def focused(self) -> None:
            self.focus_count += 1

        @hooks.on_tick(100)
        def ticked(self) -> None:
            self.tick_count += 1

    runtime = Runtime.offscreen(20, 4)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        runtime.blur()
        runtime.focus("name")
        assert app.focus_count == 1
        runtime.perform(Action.tick(50))
        runtime.perform(Action.tick(49))
        assert app.tick_count == 0
        runtime.perform(Action.tick(1))
        assert app.tick_count == 1
    finally:
        runtime.close()


def test_runtime_focus_api() -> None:
    from xnano.beta.components.text import Text
    from xnano.beta.fields import Field
    from xnano.beta.grids import BaseGrid

    class Form(BaseGrid):
        name: Text = Field(
            default=Text("", input=True, placeholder="Name"),
            group="name",
        )

    runtime = Runtime.offscreen(40, 8)
    try:
        form = Form()
        runtime.set_root(form)
        runtime.render(form)
        assert runtime.focus("name") is True
        assert runtime.focused_group == "name"
        runtime.blur()
        assert runtime.focused_group is None
    finally:
        runtime.close()


def test_keyboard_action_edits_focused_input() -> None:
    from xnano.beta.actions import Action
    from xnano.beta.components.input import Input
    from xnano.beta.fields import Field
    from xnano.beta.grids import BaseGrid

    class Form(BaseGrid):
        name: Input = Field(
            default_factory=Input, group="name", autofocus=True
        )

    runtime = Runtime.offscreen(30, 4)
    try:
        form = Form()
        runtime.set_root(form)
        runtime.render()
        runtime.perform(Action.keyboard("a"))
        assert form.name.value == "a"
    finally:
        runtime.close()


def test_device_and_cursor_proxies() -> None:
    runtime = Runtime.offscreen(20, 6)
    try:
        assert runtime.device.size.width >= 0
        runtime.cursor.visible = False
        frame = runtime.render("x")
        assert isinstance(frame.text, str)
    finally:
        runtime.close()


def test_cursor_move_updates_position_and_frame() -> None:
    """``runtime.cursor`` is beta's own decoupled tracker (xnano.beta.cursor),
    not a proxy over the stable terminal's cursor — moving it updates its
    own position and the next ``Frame`` snapshot, independent of
    ``runtime.terminal.cursor`` (see test_context.py for the split)."""
    runtime = Runtime.offscreen(20, 6)
    try:
        runtime.cursor.move(7, 3)
        assert runtime.cursor.position == (7, 3)
        frame = runtime.render("x")
        assert frame.cursor_position == (7, 3)
    finally:
        runtime.close()


def test_cursor_position_setter_updates_position() -> None:
    runtime = Runtime.offscreen(20, 6)
    try:
        runtime.cursor.position = (2, 5)
        assert runtime.cursor.position == (2, 5)
    finally:
        runtime.close()


def test_cursor_save_and_restore_round_trip() -> None:
    """Regression: save()/restore() used to be silent no-ops because the
    underlying stable cursor exposes ``save_position``/``restore_position``,
    not ``save``/``restore``."""
    runtime = Runtime.offscreen(20, 6)
    try:
        runtime.cursor.move(4, 4)
        runtime.cursor.save()
        runtime.cursor.move(0, 0)
        assert runtime.cursor.position == (0, 0)
        runtime.cursor.restore()
        assert runtime.cursor.position == (4, 4)
    finally:
        runtime.close()


def test_frame_cursor_position_reflects_real_cursor_state() -> None:
    """Regression: frame_from_terminal() read a nonexistent ``.position``
    attribute off the stable cursor, so ``Frame.cursor_position`` was
    always ``None`` regardless of where the cursor actually was — which
    meant a moved, visible cursor never reached the browser frame."""
    runtime = Runtime.offscreen(20, 6)
    try:
        runtime.cursor.move(5, 2)
        runtime.cursor.visible = True
        frame = runtime.render("x")
        assert frame.cursor_position == (5, 2)
        assert frame.cursor_visible is True
    finally:
        runtime.close()


def test_native_chart_canvas_and_bars_render() -> None:
    from xnano.beta.core.content import (
        Bar,
        BarGroup,
        Bars,
        Canvas,
        CanvasLine,
        Plot,
        PlotAxis,
        PlotDataset,
        Stack,
    )

    content = Stack(
        children=(
            Bars(
                groups=(BarGroup(bars=(Bar(value=4, label="A"),)),),
            ),
            Canvas(
                shapes=(CanvasLine(x1=0, y1=0, x2=1, y2=1),),
            ),
            Plot(
                datasets=(PlotDataset(data=((0, 0), (1, 1)), name="series"),),
                x_axis=PlotAxis(bounds=(0, 1)),
                y_axis=PlotAxis(bounds=(0, 1)),
            ),
        ),
    )
    runtime = Runtime.offscreen(40, 18)
    try:
        frame = runtime.render(content)
        assert frame.text.strip()
    finally:
        runtime.close()


def test_grid_effect_uses_recorded_field_area() -> None:
    from xnano.beta.effects import FadeEffect
    from xnano.beta.fields import Field
    from xnano.beta.grids import BaseGrid

    class App(BaseGrid):
        body: str = Field(default="hello")

    runtime = Runtime.offscreen(20, 4)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        assert app.grid_play_effect(FadeEffect(), fields=["body"])
        runtime.render()
    finally:
        runtime.close()


def _live_runtime_over_offscreen_session() -> Runtime:
    """Build a runtime flagged live but backed by an in-memory session.

    Signal-handler wiring is independent of whether a real TTY exists, so
    this exercises the restore-on-exit path without needing a terminal.
    The session is built directly (not via ``Runtime.offscreen``) so no
    extra runtime is entered and bound as the active one.
    """
    from xnano_core.core import CoreSession

    session = CoreSession.offscreen(20, 4)
    return Runtime(session, live=True, surface="terminal")


def test_offscreen_runtime_installs_no_signal_handlers() -> None:
    before = signal.getsignal(signal.SIGINT)
    runtime = Runtime.offscreen(20, 4)
    try:
        assert runtime._signals_installed is False
        assert signal.getsignal(signal.SIGINT) is before
    finally:
        runtime.close()


def test_live_runtime_installs_and_restores_signal_handlers() -> None:
    before = signal.getsignal(signal.SIGINT)
    runtime = _live_runtime_over_offscreen_session()
    runtime.enter()
    try:
        assert runtime._signals_installed is True
        handler = signal.getsignal(signal.SIGINT)
        assert getattr(handler, "__func__", None) is Runtime._on_exit_signal
        assert getattr(handler, "__self__", None) is runtime
    finally:
        runtime.close()
    assert runtime._signals_installed is False
    assert signal.getsignal(signal.SIGINT) is before


def test_exit_signal_set_excludes_sighup_when_unavailable() -> None:
    # SIGINT and SIGTERM exist on every supported platform; SIGHUP is
    # POSIX-only and must simply be absent (never crash) elsewhere.
    assert signal.SIGINT in _EXIT_SIGNALS
    assert signal.SIGTERM in _EXIT_SIGNALS
    if not hasattr(signal, "SIGHUP"):
        assert all(sig.name != "SIGHUP" for sig in _EXIT_SIGNALS)


def test_on_exit_signal_requests_exit_and_raises() -> None:
    runtime = _live_runtime_over_offscreen_session()
    runtime.enter()
    try:
        try:
            runtime._on_exit_signal(int(signal.SIGTERM), None)
        except SystemExit as exit_error:
            assert exit_error.code == 128 + int(signal.SIGTERM)
        else:  # pragma: no cover - the handler must raise
            raise AssertionError("expected SystemExit")
        assert runtime._should_exit is True
    finally:
        runtime.close()


def test_atexit_restore_closes_active_live_runtime() -> None:
    runtime = _live_runtime_over_offscreen_session()
    runtime.enter()
    assert _ACTIVE_RUNTIME.get() is runtime
    # Simulate interpreter shutdown skipping the normal close path.
    _atexit_restore_active_runtime()
    # The active live runtime is closed and unbound (the contextvar is
    # reset to whatever it held before this runtime entered, which is not
    # this runtime).
    assert runtime._closed is True
    assert _ACTIVE_RUNTIME.get() is not runtime
