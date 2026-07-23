"""tests.experimental.images.test_images

---

Focused coverage for the optional, experimental image surface. This directory
is excluded from default pytest discovery and must be run explicitly.
"""

from __future__ import annotations

import io
import pathlib
import types
from typing import Any, Callable, cast

import pytest
from PIL import Image as pillow_image  # ty: ignore[unresolved-import]

from xnano import _demo as demo_module
from xnano._demo import (
    _LOGO_HOLD_FRAMES,
    _TRANSITION_FRAMES,
    DemoSequence,
    GifSplash,
    MonochromeLogoSplash,
    XnanoDemo,
    _build_gif_splash,
)
from xnano._types import Area
from xnano.components.abstract import ComponentRenderContext
from xnano.images import Image, ImageData, ImageFrame
from xnano.terminal import Terminal


def _get_gif_bytes() -> bytes:
    """Build a two-frame in-memory GIF with distinct source timings."""
    first = pillow_image.new("RGB", (2, 2), (255, 0, 0))
    second = pillow_image.new("RGB", (2, 2), (0, 0, 255))
    stream = io.BytesIO()
    first.save(
        stream,
        format="GIF",
        save_all=True,
        append_images=[second],
        duration=[40, 90],
        loop=0,
    )
    return stream.getvalue()


def _get_png_bytes() -> bytes:
    """Build a four-column image whose center crop is unambiguous."""
    image = pillow_image.new("RGB", (4, 2))
    pixels = image.load()
    assert pixels is not None
    colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))
    for column, color in enumerate(colors):
        for row in range(2):
            pixels[column, row] = color
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def test_animation_uses_source_frame_timings() -> None:
    image = Image(_get_gif_bytes())

    assert image.frame_count == 2
    assert image.duration_ms == 130
    assert image.get_frame_index(0) == 0
    assert image.get_frame_index(39) == 0
    assert image.get_frame_index(40) == 1
    assert image.get_frame_index(129) == 1
    assert image.get_frame_index(130) == 0


def test_animation_supports_exact_thirty_fps_cadence() -> None:
    durations = (33, 34, 33) * 10
    frames = tuple(
        ImageFrame(bytes((frame_index, 0, 0, frame_index, 0, 0)), duration)
        for frame_index, duration in enumerate(durations)
    )
    image = Image(ImageData(width=1, height=2, frames=frames), loop=False)

    assert image.frame_count == 30
    assert image.duration_ms == 1000
    assert image.get_frame_index(32) == 0
    assert image.get_frame_index(33) == 1
    assert image.get_frame_index(999) == 29


def test_animation_seek_updates_the_next_composed_frame() -> None:
    image = Image(_get_gif_bytes())
    image.seek(40)

    canvas = image.compose(
        ComponentRenderContext(area=Area(x=0, y=0, width=2, height=1))
    )

    assert canvas.rows[0][0].color == "#0000ff"


def test_non_looping_animation_reports_source_time_completion() -> None:
    image = Image(_get_gif_bytes(), loop=False)
    assert image.finished is False

    image.seek(image.duration_ms)

    assert image.finished is True


def test_bundled_animation_decodes_without_pillow_file_io() -> None:
    expectations = {
        "luffy": ((165, 128), 25, 2500),
        "luffy_deck": ((165, 94), 71, 2367),
    }
    for image_name, (size, frame_count, duration_ms) in expectations.items():
        source = demo_module._DEMO_IMAGE_SOURCE_DIRECTORY / f"{image_name}.xni"
        data = ImageData.from_bytes(source.read_bytes())
        image = Image(data)

        assert (data.width, data.height) == size
        assert image.frame_count == frame_count
        assert image.duration_ms == duration_ms


def test_demo_image_uses_local_source_and_populates_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    cache_directory = tmp_path / "xnano"
    cache_directory.mkdir()
    cache = cache_directory / "luffy.xni"
    monkeypatch.setattr(
        demo_module,
        "_DEMO_IMAGE_CACHE_DIRECTORY",
        cache_directory,
    )
    monkeypatch.setattr(
        demo_module.urllib.request,
        "urlopen",
        lambda *args, **kwargs: pytest.fail("unexpected network request"),
    )
    demo_module._get_demo_image_data.cache_clear()

    data = demo_module._get_demo_image_data("luffy")

    assert data.frames
    assert (
        cache.read_bytes()
        == (
            demo_module._DEMO_IMAGE_SOURCE_DIRECTORY / "luffy.xni"
        ).read_bytes()
    )
    demo_module._get_demo_image_data.cache_clear()


def test_demo_image_cache_never_pulls_remote_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    cache = tmp_path / "luffy.xni"
    cache.write_bytes(
        (demo_module._DEMO_IMAGE_SOURCE_DIRECTORY / "luffy.xni").read_bytes()
    )
    monkeypatch.setattr(
        demo_module,
        "_DEMO_IMAGE_CACHE_DIRECTORY",
        tmp_path,
    )
    monkeypatch.setattr(
        demo_module,
        "_DEMO_IMAGE_SOURCE_DIRECTORY",
        tmp_path / "missing",
    )
    monkeypatch.setattr(
        demo_module.urllib.request,
        "urlopen",
        lambda *args, **kwargs: pytest.fail("unexpected network request"),
    )
    demo_module._get_demo_image_data.cache_clear()

    data = demo_module._get_demo_image_data("luffy")

    assert data.frames
    demo_module._get_demo_image_data.cache_clear()


def test_demo_image_downloads_only_once_across_startups(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    payload = (
        demo_module._DEMO_IMAGE_SOURCE_DIRECTORY / "luffy.xni"
    ).read_bytes()
    cache = tmp_path / "luffy.xni"
    calls = 0

    def _open_remote(*args: Any, **kwargs: Any) -> io.BytesIO:
        nonlocal calls
        calls += 1
        return io.BytesIO(payload)

    monkeypatch.setattr(
        demo_module,
        "_DEMO_IMAGE_CACHE_DIRECTORY",
        tmp_path,
    )
    monkeypatch.setattr(
        demo_module,
        "_DEMO_IMAGE_SOURCE_DIRECTORY",
        tmp_path / "missing",
    )
    monkeypatch.setattr(
        demo_module.urllib.request,
        "urlopen",
        _open_remote,
    )
    demo_module._get_demo_image_data.cache_clear()

    first = demo_module._get_demo_image_data("luffy")
    demo_module._get_demo_image_data.cache_clear()
    second = demo_module._get_demo_image_data("luffy")

    assert first.frames == second.frames
    assert calls == 1
    assert cache.read_bytes() == payload
    demo_module._get_demo_image_data.cache_clear()


def test_demo_image_failure_names_the_selected_asset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    def _raise_network_error(*args: Any, **kwargs: Any) -> Any:
        raise OSError("offline")

    monkeypatch.setattr(
        demo_module,
        "_DEMO_IMAGE_CACHE_DIRECTORY",
        tmp_path / "cache",
    )
    monkeypatch.setattr(
        demo_module,
        "_DEMO_IMAGE_SOURCE_DIRECTORY",
        tmp_path / "source",
    )
    monkeypatch.setattr(
        demo_module.urllib.request,
        "urlopen",
        _raise_network_error,
    )
    demo_module._get_demo_image_data.cache_clear()

    with pytest.raises(RuntimeError, match="luffy.xni"):
        demo_module._get_demo_image_data("luffy")

    demo_module._get_demo_image_data.cache_clear()


def test_demo_sequence_loads_only_the_randomly_selected_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_data = ImageData.from_bytes(
        (demo_module._DEMO_IMAGE_SOURCE_DIRECTORY / "luffy.xni").read_bytes()
    )
    loaded_names: list[str] = []

    def _load_selected_image(image_name: str) -> ImageData:
        loaded_names.append(image_name)
        return image_data

    monkeypatch.setattr(
        demo_module.random,
        "getrandbits",
        lambda bit_count: 1,
    )
    monkeypatch.setattr(
        demo_module.random,
        "choice",
        lambda choices: "luffy",
    )
    monkeypatch.setattr(
        demo_module,
        "_get_demo_image_data",
        _load_selected_image,
    )

    sequence = DemoSequence()

    assert sequence.demo_image_name == "luffy"
    assert loaded_names == ["luffy"]


def test_demo_sequence_falls_back_when_pillow_import_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_pillow_import(image_name: str) -> GifSplash:
        raise ImportError("Pillow is unavailable")

    monkeypatch.setattr(
        demo_module.random,
        "getrandbits",
        lambda bit_count: 1,
    )
    monkeypatch.setattr(
        demo_module,
        "_get_demo_image_data",
        lambda image_name: pytest.fail("XNI must not need Pillow"),
    )
    monkeypatch.setattr(
        demo_module,
        "_build_gif_splash",
        _raise_pillow_import,
    )

    sequence = DemoSequence()

    assert sequence.use_gif is False
    assert sequence.demo_image_name == ""


def test_default_fit_centers_and_crops_without_resizing() -> None:
    image = Image(_get_png_bytes())
    canvas = image.compose(
        ComponentRenderContext(area=Area(x=0, y=0, width=2, height=1))
    )

    assert canvas.width == 2
    assert canvas.height == 1
    assert [span.color for span in canvas.rows[0]] == [
        "#00ff00",
        "#0000ff",
    ]


def test_native_crop_centers_smaller_image_with_background() -> None:
    image = Image(_get_png_bytes(), background=(1, 2, 3))
    canvas = image.compose(
        ComponentRenderContext(area=Area(x=0, y=0, width=6, height=2))
    )

    assert canvas.width == 6
    assert canvas.height == 2
    assert canvas.rows[0][0].color == "#010203"


def test_smart_fit_adapts_between_cover_and_contain() -> None:
    close_ratio = Image(_get_png_bytes(), fit="smart").compose(
        ComponentRenderContext(area=Area(x=0, y=0, width=4, height=1))
    )
    tall_viewport = Image(_get_png_bytes(), fit="smart").compose(
        ComponentRenderContext(area=Area(x=0, y=0, width=2, height=2))
    )

    assert close_ratio.rows[0][0].color == "#ff0000"
    assert close_ratio.rows[0][-1].color == "#ffff00"
    assert tall_viewport.rows[-1][0].color == "#000000"


def test_xni_adaptive_resize_does_not_require_pillow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_pillow_import() -> Any:
        raise ImportError("Pillow unavailable")

    source = demo_module._DEMO_IMAGE_SOURCE_DIRECTORY / "luffy.xni"
    image = Image(ImageData.from_bytes(source.read_bytes()), fit="smart")
    monkeypatch.setattr(
        "xnano.images._get_pillow_image_module",
        _raise_pillow_import,
    )

    canvas = image.compose(
        ComponentRenderContext(area=Area(x=0, y=0, width=40, height=12))
    )

    assert canvas.width == 40
    assert canvas.height == 12


def test_two_by_two_mapping_uses_one_terminal_cell_per_pixel_block() -> None:
    image = Image(_get_png_bytes(), horizontal_pixels_per_cell=2)
    canvas = image.compose(
        ComponentRenderContext(area=Area(x=0, y=0, width=2, height=1))
    )

    assert canvas.width == 2
    assert canvas.height == 1
    assert [span.color for span in canvas.rows[0]] == [
        "#808000",
        "#808080",
    ]


def test_two_by_two_mapping_can_correct_terminal_cell_aspect() -> None:
    image = Image(
        _get_png_bytes(),
        horizontal_pixels_per_cell=2,
        correct_terminal_aspect=True,
    )
    canvas = image.compose(
        ComponentRenderContext(area=Area(x=0, y=0, width=4, height=1))
    )

    assert canvas.width == 4
    assert canvas.height == 1


def test_buffer_backed_render_preserves_half_block_truecolor(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        Terminal,
        "_supports_live_terminal",
        staticmethod(lambda: False),
    )

    Terminal(width=2, height=1).render(Image(_get_png_bytes()))

    output = capsys.readouterr().out
    assert output.count("▀") == 2
    assert "38;2;0;255;0" in output
    assert "48;2;0;255;0" in output


def test_demo_clip_runs_through_logo_before_panels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        DemoSequence, "grid_play_effect", lambda *args, **kwargs: None
    )
    sequence = DemoSequence()
    sequence.use_gif = True
    sequence.content = _build_gif_splash("luffy")
    assert isinstance(sequence.content, GifSplash)
    assert set(sequence.content._grid_fields) == {"image"}
    assert isinstance(sequence.content.image, Image)
    assert sequence.content.image.horizontal_pixels_per_cell == 2
    assert sequence.content.image.correct_terminal_aspect is True
    assert sequence.content.image.loop is False
    assert sequence.content.image.get_frame_index(100_000) == 24
    sequence.sequence_stage = "splash"
    sequence.frame_count = 0
    advance_sequence = cast(Callable[[], Any], sequence._advance_sequence)

    sequence.content.image.seek(sequence.content.image.duration_ms)
    advance_sequence()
    assert sequence.sequence_stage == "logo"
    assert isinstance(sequence.content, MonochromeLogoSplash)

    for _ in range(_LOGO_HOLD_FRAMES):
        advance_sequence()
    assert sequence.sequence_stage == "fade_to_panels"

    for _ in range(_TRANSITION_FRAMES):
        advance_sequence()
    assert sequence.sequence_stage == "panels"
    assert isinstance(sequence.content, XnanoDemo)


@pytest.mark.parametrize(
    ("key", "effect_name", "native_effect"),
    (
        ("c", "coalesce", "coalesce"),
        ("F", "fade", "fade"),
        ("d", "dissolve", "dissolve"),
        ("S", "sweep_in", "sweep_in"),
    ),
)
def test_effect_lab_keys_trigger_panel_effects(
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    effect_name: str,
    native_effect: str,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def _record_effect(
        self: XnanoDemo,
        effect: str,
        **kwargs: Any,
    ) -> None:
        calls.append((effect, kwargs))

    monkeypatch.setattr(XnanoDemo, "grid_play_effect", _record_effect)
    app = XnanoDemo()
    handler = cast(Callable[[Any], Any], app._handle_keyboard)
    context = types.SimpleNamespace(
        keyboard=types.SimpleNamespace(key=key),
    )

    handler(context)

    assert app.active_effect == effect_name
    assert calls[-1][0] == native_effect
    assert calls[-1][1]["fields"] == ["panels"]


def test_effect_lab_space_shuffles_and_triggers_an_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        XnanoDemo,
        "grid_play_effect",
        lambda self, effect, **kwargs: calls.append(effect),
    )
    monkeypatch.setattr(demo_module.random, "choice", lambda choices: "d")
    app = XnanoDemo()
    handler = cast(Callable[[Any], Any], app._handle_keyboard)
    context = types.SimpleNamespace(
        keyboard=types.SimpleNamespace(key="space"),
    )

    handler(context)

    assert app.active_effect == "dissolve"
    assert calls == ["dissolve"]
