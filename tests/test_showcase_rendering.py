"""tests.test_showcase_rendering

---

Rendering-quality tests for the showcase demo. These guard the traits
that make the animation look smooth on a live terminal: stable geometry across
frames (no layout jump), full paint every frame, animation that actually
progresses, and — the reason it stays fast — the identity cache hit on an
unchanged ``CellCanvas``. A real animated GIF is rendered from the demo's own
plasma frames into ``tests/assets`` and re-opened to prove it is well-formed.
"""

from __future__ import annotations

import pathlib

import pytest

import xnano.core.demo as demo
from xnano.actions import Action
from xnano.core import Runtime
from xnano.core.demo import (
    Demo,
    IntroSplash,
    Showcase,
    build_plasma_frame,
    build_sin_table,
    build_title_frame,
)

_ASSETS = pathlib.Path(__file__).parent.parent / "assets"


@pytest.fixture(autouse=True)
def _reset_pause():
    """Keep the module-level pause flag from leaking between tests."""
    demo._PAUSED = False
    yield
    demo._PAUSED = False


def _drive(width: int, height: int, ticks: int) -> list[str]:
    """Render the showcase across ``ticks`` frames, returning frame text."""
    runtime = Runtime.offscreen(width, height)
    frames: list[str] = []
    try:
        app = Showcase()
        runtime.set_root(app)
        frames.append(runtime.render().text)
        for _ in range(ticks):
            runtime.perform(Action.tick(66))
            frames.append(runtime.render().text)
    finally:
        runtime.close()
    return frames


def _render_showcase_tick(runtime: Runtime) -> object:
    """Advance and render one showcase frame."""
    runtime.perform(Action.tick(80))
    return runtime.render()


def _paint_showcase_tick(runtime: Runtime) -> None:
    """Advance and paint one live-style showcase frame."""
    runtime.perform(Action.tick(80))
    runtime._render()


# ── Cheap gradient math ─────────────────────────────────────────────────────


def test_sin_table_length_matches_count() -> None:
    assert len(build_sin_table(37, 0.2, 1.0)) == 37


def test_plasma_frame_math_is_per_axis_not_per_cell(monkeypatch) -> None:
    """The plasma gradient must cost ``width + height`` trig calls, not
    ``width * height`` — the property that keeps a full-screen animated
    canvas affordable to rebuild."""
    calls = {"count": 0}
    original = demo.math.sin

    def counting(value: float) -> float:
        calls["count"] += 1
        return original(value)

    monkeypatch.setattr(demo.math, "sin", counting)
    build_plasma_frame(80, 24, 1.0)
    assert calls["count"] == 80 + 24


def test_plasma_frame_dimensions() -> None:
    canvas = build_plasma_frame(50, 12, 0.5)
    assert canvas.width == 50
    assert canvas.height == 12
    assert len(canvas.rows) == 12
    assert all(
        sum(len(span.text) for span in row) == 50 for row in canvas.rows
    )


# ── Frame invariants ────────────────────────────────────────────────────────


def test_frames_keep_stable_geometry() -> None:
    """Every rendered frame is the full viewport with no ragged rows — a
    layout jump mid-animation is exactly the 'stacked rows' glitch."""
    frames = _drive(120, 40, ticks=20)
    for frame in frames:
        lines = frame.split("\n")
        # Row count is fixed to the viewport height every frame; a mid-motion
        # layout jump would change this and read as stacked/torn rows. (Buffer
        # lines are right-trimmed, so widths legitimately vary — only the
        # ceiling matters.)
        assert len(lines) == 40
        assert max(len(line) for line in lines) <= 120


def test_animation_progresses_over_ticks() -> None:
    """Ticks must actually change the picture, or nothing is animating."""
    frames = _drive(120, 40, ticks=12)
    assert len(set(frames)) > 1


def test_paused_animation_is_frozen() -> None:
    frames_before = _drive(120, 40, ticks=1)[0]
    runtime = Runtime.offscreen(120, 40)
    try:
        app = Showcase()
        runtime.set_root(app)
        runtime.render()
        runtime.perform(Action.keyboard("space"))
        assert demo._PAUSED is True
        stage = app.body.center.stage
        canvas_id = id(stage.view._canvas)
        runtime.perform(Action.tick(66))
        runtime.render()
        assert id(stage.view._canvas) == canvas_id
    finally:
        runtime.close()
    assert frames_before  # sanity: the unpaused baseline rendered


# ── Identity cache (the speed guarantee) ────────────────────────────────────


def test_unchanged_canvas_is_reused_across_renders() -> None:
    """Between ticks the stage returns the same ``CellCanvas`` object so the
    renderer's identity cache stays warm (a cache miss here means every frame
    re-lowers the whole canvas)."""
    runtime = Runtime.offscreen(120, 40)
    try:
        app = Showcase()
        runtime.set_root(app)
        runtime.render()
        stage = app.body.center.stage
        first = id(stage.view._canvas)
        runtime.render()
        assert id(stage.view._canvas) == first
        runtime.perform(Action.tick(200))
        runtime.render()
        assert id(stage.view._canvas) != first
    finally:
        runtime.close()


# ── Keybinds ────────────────────────────────────────────────────────────────


def test_tab_keybind_cycles_focused_box() -> None:
    runtime = Runtime.offscreen(120, 40)
    try:
        app = Showcase()
        runtime.set_root(app)
        runtime.render()
        stage = app.body.center.stage
        assert runtime.focused_group == "stage"
        start = stage.tab_index
        runtime.perform(Action.keyboard("]"))
        assert stage.tab_index == (start + 1) % 3
        runtime.perform(Action.keyboard("["))
        assert stage.tab_index == start
    finally:
        runtime.close()


def test_number_keys_select_focused_box_tab() -> None:
    runtime = Runtime.offscreen(120, 40)
    try:
        app = Showcase()
        runtime.set_root(app)
        runtime.render()
        runtime.focus("stage")
        runtime.perform(Action.keyboard("3"))
        assert app.body.center.stage.tab_index == 2
        runtime.perform(Action.keyboard("1"))
        assert app.body.center.stage.tab_index == 0
    finally:
        runtime.close()


def test_effects_target_every_focusable_box() -> None:
    """A field whose value is a nested grid must still register an effect
    area — otherwise effects only fire on leaf-component boxes."""
    runtime = Runtime.offscreen(120, 40)
    try:
        app = Showcase()
        runtime.set_root(app)
        runtime.render()
        for parent, field_name in app._effect_targets.values():
            assert parent.grid_effect(
                "fade", duration_ms=200, fields=[field_name]
            )
    finally:
        runtime.close()


def test_quit_keybind_requests_exit() -> None:
    runtime = Runtime.offscreen(120, 40)
    try:
        app = Showcase()
        runtime.set_root(app)
        runtime.render()
        runtime.perform(Action.keyboard("q"))
        assert runtime._should_exit is True
    finally:
        runtime.close()


# ── Compute stays bounded ───────────────────────────────────────────────────


# Spanning the real range xnano runs in: the classic 80x24 VT minimum, an
# 80-col laptop split, a full-screen laptop, a wide external monitor, and an
# ultrawide / tmux-fullscreen 4K terminal. Frame cost scales with cell count,
# so the big sizes are where the paint budget actually bites.
_BENCH_SIZES = (
    pytest.param(80, 24, id="80x24"),
    pytest.param(120, 40, id="120x40"),
    pytest.param(200, 50, id="200x50"),
    pytest.param(280, 70, id="280x70"),
    pytest.param(400, 100, id="400x100"),
)


@pytest.mark.parametrize("width, height", _BENCH_SIZES)
def test_bench_showcase_tick_and_render(benchmark, width, height) -> None:
    """Benchmark one animated frame including offscreen serialization."""
    runtime = Runtime.offscreen(width, height)
    app = Showcase()
    runtime.set_root(app)
    runtime.render()
    try:
        frame = benchmark(_render_showcase_tick, runtime)
        assert frame.width == width
        assert frame.height == height
    finally:
        runtime.close()


@pytest.mark.parametrize("width, height", _BENCH_SIZES)
def test_bench_showcase_live_paint(benchmark, width, height) -> None:
    """Benchmark the live path without unused frame serialization."""
    runtime = Runtime.offscreen(width, height)
    runtime.set_root(Showcase())
    runtime._render()
    try:
        benchmark(_paint_showcase_tick, runtime)
    finally:
        runtime.close()


def test_paint_interval_backs_off_with_terminal_size() -> None:
    """Small terminals get a smooth cadence; huge ones back off to protect the
    paint budget. Cadence must be monotonic in cell count."""
    small = demo._paint_interval_ms(80, 24)
    medium = demo._paint_interval_ms(280, 70)
    large = demo._paint_interval_ms(400, 100)
    assert small == 66
    assert large == 100
    assert small <= medium <= large


def test_canvas_ir_cache_stays_bounded_under_animation() -> None:
    """Driving the animated demo must not grow the lowered-IR cache without
    bound — the demo rebuilds canvases every tick, so an unbounded cache would
    be a steady memory leak on a long-running session."""
    from xnano.core import rendering

    runtime = Runtime.offscreen(120, 40)
    try:
        app = Showcase()
        runtime.set_root(app)
        for _ in range(300):
            runtime.perform(Action.tick(66))
            runtime.render()
        assert (
            len(rendering._cell_canvas_ir_cache)
            <= rendering._CELL_CANVAS_IR_CACHE_CAPACITY
        )
    finally:
        runtime.close()


# ── Intro splash ────────────────────────────────────────────────────────────


def test_title_frame_has_full_dimensions() -> None:
    canvas = build_title_frame(80, 24, 0.5)
    assert canvas.width == 80
    assert len(canvas.rows) == 24


def test_intro_splash_transitions_on_key() -> None:
    runtime = Runtime.offscreen(120, 40)
    try:
        app = Demo()
        runtime.set_root(app)
        runtime.render()
        assert isinstance(app.view, IntroSplash)
        runtime.perform(Action.keyboard("space"))
        assert isinstance(app.view, Showcase)
    finally:
        runtime.close()


def test_intro_splash_transitions_after_timeout() -> None:
    runtime = Runtime.offscreen(120, 40)
    try:
        app = Demo()
        runtime.set_root(app)
        runtime.render()
        # Drive just past the wall-clock splash duration (66ms synthetic ticks).
        ticks = int(Demo._INTRO_SECONDS * 1000 / 66) + 2
        for _ in range(ticks):
            runtime.perform(Action.tick(66))
        assert isinstance(app.view, Showcase)
    finally:
        runtime.close()


# ── Multi-tab boxes ─────────────────────────────────────────────────────────


def test_orbit_box_cycles_three_motion_tabs() -> None:
    runtime = Runtime.offscreen(120, 40)
    try:
        app = Showcase()
        runtime.set_root(app)
        runtime.render()
        orbit = app.body.center.strip.orbit
        seen = set()
        for _ in range(3):
            seen.add(orbit.view.mode)
            orbit.cycle_tab(1)
        assert seen == {"Orbit", "Spiral", "Ripple"}
    finally:
        runtime.close()


def test_signal_box_has_three_distinct_tabs() -> None:
    runtime = Runtime.offscreen(120, 40)
    try:
        app = Showcase()
        runtime.set_root(app)
        runtime.render()
        signal = app.body.center.strip.signal
        assert signal._TABS == ("Wave", "Bars", "Spark")
        kinds = set()
        for _ in range(3):
            runtime.render()
            kinds.add(type(signal.view).__name__)
            signal.cycle_tab(1)
        assert len(kinds) >= 2
    finally:
        runtime.close()


# ── Rendered GIF asset ──────────────────────────────────────────────────────


def _canvas_to_image(canvas, cell: int):
    """Rasterize one plasma ``CellCanvas`` to a PIL RGB image."""
    from PIL import Image

    image = Image.new("RGB", (canvas.width * cell, canvas.height * cell))
    pixels = image.load()
    assert pixels is not None
    for row_index, row in enumerate(canvas.rows):
        column_index = 0
        for span in row:
            hex_color = (span.color or "#000000").lstrip("#")
            rgb = (
                int(hex_color[0:2], 16),
                int(hex_color[2:4], 16),
                int(hex_color[4:6], 16),
            )
            for _ in span.text:
                for dy in range(cell):
                    for dx in range(cell):
                        pixels[
                            column_index * cell + dx,
                            row_index * cell + dy,
                        ] = rgb
                column_index += 1
    return image


def test_plasma_gif_asset_is_wellformed() -> None:
    """Render the demo's plasma frames to a real animated GIF and re-open it
    to confirm frame count and geometry. The committed asset doubles as a
    visual reference for the animation."""
    pytest.importorskip("PIL")
    from PIL import Image

    width, height, cell, frame_count = 64, 24, 4, 24
    images = [
        _canvas_to_image(build_plasma_frame(width, height, index * 0.09), cell)
        for index in range(frame_count)
    ]
    _ASSETS.mkdir(parents=True, exist_ok=True)
    target = _ASSETS / "showcase_plasma.gif"
    images[0].save(
        target,
        save_all=True,
        append_images=images[1:],
        duration=66,
        loop=0,
        optimize=False,
    )
    assert target.exists() and target.stat().st_size > 0
    with Image.open(target) as reopened:
        # Pillow coalesces frames that are identical after palette conversion,
        # so the stored count can be below the source count — assert it stayed
        # a well-formed, genuinely animated GIF at the expected geometry.
        assert getattr(reopened, "is_animated", False)
        assert 1 < getattr(reopened, "n_frames", 0) <= frame_count
        assert reopened.size == (width * cell, height * cell)
