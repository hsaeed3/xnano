"""Tests for ``Image``."""

from __future__ import annotations

import io
import struct
import zlib
from typing import Any, cast

import pytest

import xnano.components.image as image_module
from xnano.area import Area
from xnano.components.component import ComponentRenderContext
from xnano.components.image import Image, ImageData, ImageFit, ImageFrame
from xnano.core import Runtime
from xnano.core.content import CellCanvas


def _ctx(width: int = 4, height: int = 2) -> ComponentRenderContext[Any]:
    return ComponentRenderContext(
        area=Area(x=0, y=0, width=width, height=height)
    )


def _require_pillow():
    return pytest.importorskip("PIL.Image")


def _get_gif_bytes() -> bytes:
    pillow_image = _require_pillow()
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
    pillow_image = _require_pillow()
    image = pillow_image.new("RGB", (4, 2), (0, 255, 0))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _get_xni_bytes() -> bytes:
    palette = bytes((255, 0, 0, 0, 255, 0))
    indexes = zlib.compress(bytes((0, 1)))
    return (
        b"XNI1"
        + struct.pack(">HHH", 2, 1, 1)
        + struct.pack(">HHI", 25, 2, len(indexes))
        + palette
        + indexes
    )


def test_compact_image_decodes_and_resizes_for_terminal_cells() -> None:
    data = ImageData.from_bytes(_get_xni_bytes())
    assert (data.width, data.height) == (2, 1)
    assert data.frames[0].duration_ms == 25

    image = Image(source=data, fit="contain", background=(0, 0, 255))
    canvas = image.compose(_ctx(4, 2))
    assert isinstance(canvas, CellCanvas)
    assert len(canvas.rows) == 2
    assert len(canvas.rows[0]) == 4
    assert {cell.foreground for row in canvas.rows for cell in row} >= {
        "#ff0000",
        "#00ff00",
    }


def test_compact_image_rejects_invalid_boundaries() -> None:
    with pytest.raises(ValueError, match="positive dimensions"):
        ImageData(width=0, height=1, frames=())
    with pytest.raises(ValueError, match="does not match"):
        ImageData(
            width=2,
            height=1,
            frames=(ImageFrame(bytes((0, 0, 0)), 10),),
        )
    with pytest.raises(ValueError, match="XNI1 header"):
        ImageData.from_bytes(b"PNG")
    with pytest.raises(ValueError, match="trailing bytes"):
        ImageData.from_bytes(_get_xni_bytes() + b"x")

    compressed = zlib.compress(bytes((0,)))
    wrong_pixel_count = (
        b"XNI1"
        + struct.pack(">HHH", 2, 1, 1)
        + struct.pack(">HHI", 25, 1, len(compressed))
        + bytes((255, 0, 0))
        + compressed
    )
    with pytest.raises(ValueError, match="invalid pixel count"):
        ImageData.from_bytes(wrong_pixel_count)

    corrupt = (
        b"XNI1"
        + struct.pack(">HHH", 1, 1, 1)
        + struct.pack(">HHI", 25, 1, 3)
        + bytes((255, 0, 0))
        + b"bad"
    )
    with pytest.raises(ValueError, match="truncated or corrupt"):
        ImageData.from_bytes(corrupt)


def test_dependency_free_resize_preserves_nearest_colors(monkeypatch) -> None:
    frame = image_module._RasterFrame(
        pixels=bytes((255, 0, 0, 0, 255, 0)),
        width=2,
        height=1,
        duration_ms=40,
    )

    def unavailable():
        raise ImportError

    monkeypatch.setattr(image_module, "_get_pillow_image_module", unavailable)
    resized = image_module._resize_frame(frame, 4, 2)
    assert (resized.width, resized.height) == (4, 2)
    assert resized.pixels[:6] == bytes((255, 0, 0, 255, 0, 0))
    assert resized.pixels[6:12] == bytes((0, 255, 0, 0, 255, 0))
    assert image_module._resize_frame(frame, 2, 1) is frame


@pytest.mark.parametrize("fit", ("crop", "cover", "stretch", "smart"))
def test_fit_modes_fill_requested_terminal_area(fit: ImageFit) -> None:
    pixels = bytes((255, 0, 0) * 2 + (0, 255, 0) * 2)
    image = Image(
        source=ImageData(
            width=2,
            height=2,
            frames=(ImageFrame(pixels, 40),),
        ),
        fit=fit,
    )
    canvas = image.compose(_ctx(3, 2))
    assert isinstance(canvas, CellCanvas)
    assert canvas.width == 3
    assert canvas.height == 2


def test_image_data_without_pillow_file_io() -> None:
    frames = (
        ImageFrame(bytes((255, 0, 0, 0, 255, 0)), 50),
        ImageFrame(bytes((0, 0, 255, 255, 255, 0)), 50),
    )
    data = ImageData(width=1, height=2, frames=frames)
    image = Image(source=data)
    assert image.frame_count == 2
    assert image.duration_ms == 100
    canvas = image.compose(_ctx(1, 1))
    assert isinstance(canvas, CellCanvas)


def test_image_data_frame_index_and_seek() -> None:
    frames = (
        ImageFrame(bytes((255, 0, 0, 0, 0, 0)), 40),
        ImageFrame(bytes((0, 0, 255, 0, 0, 0)), 90),
    )
    image = Image(source=ImageData(width=1, height=2, frames=frames))
    assert image.get_frame_index(0) == 0
    assert image.get_frame_index(39) == 0
    assert image.get_frame_index(40) == 1
    image.seek(40)
    canvas = image.compose(_ctx(1, 1))
    assert canvas.rows[0][0].foreground == "#0000ff"


def test_play_pause_preserves_position() -> None:
    frames = (
        ImageFrame(bytes((255, 0, 0, 0, 0, 0)), 40),
        ImageFrame(bytes((0, 0, 255, 0, 0, 0)), 90),
    )
    image = Image(source=ImageData(width=1, height=2, frames=frames))
    image.seek(40)
    image.pause()
    assert image.playing is False
    canvas = image.compose(_ctx(1, 1))
    assert canvas.rows[0][0].foreground == "#0000ff"
    image.play()
    assert image.playing is True


def test_non_looping_finished() -> None:
    frames = (ImageFrame(bytes((255, 0, 0, 0, 0, 0)), 100),)
    image = Image(
        source=ImageData(width=1, height=2, frames=frames),
        loop=False,
    )
    assert image.finished is False
    image.seek(image.duration_ms)
    assert image.finished is True


def test_restart_resets_playback() -> None:
    frames = (
        ImageFrame(bytes((255, 0, 0, 0, 0, 0)), 40),
        ImageFrame(bytes((0, 0, 255, 0, 0, 0)), 90),
    )
    image = Image(source=ImageData(width=1, height=2, frames=frames))
    image.seek(100)
    image.restart()
    assert image.get_frame_index(0) == 0


def test_invalid_fit_rejected() -> None:
    frames = (ImageFrame(bytes((0, 0, 0, 0, 0, 0)), 100),)
    with pytest.raises(ValueError, match="Unsupported image fit"):
        Image(
            source=ImageData(width=1, height=2, frames=frames),
            fit=cast(ImageFit, "nope"),
        )


def test_invalid_speed_rejected() -> None:
    frames = (ImageFrame(bytes((0, 0, 0, 0, 0, 0)), 100),)
    with pytest.raises(ValueError, match="greater than zero"):
        Image(
            source=ImageData(width=1, height=2, frames=frames),
            speed=0,
        )


def test_terminal_geometry_configuration_is_validated() -> None:
    data = ImageData(
        width=1,
        height=2,
        frames=(ImageFrame(bytes((0, 0, 0) * 2), 100),),
    )
    with pytest.raises(ValueError, match="Horizontal pixels"):
        Image(
            source=data,
            horizontal_pixels_per_cell=cast(Any, 3),
        )
    with pytest.raises(ValueError, match="three RGB"):
        Image(source=data, background=(0, 0, 999))


def test_get_size_native_cells() -> None:
    # 4x2 pixels → 4 cells wide, 1 cell tall with half-blocks.
    pixels = bytes([0, 255, 0] * 8)
    image = Image(
        source=ImageData(
            width=4,
            height=2,
            frames=(ImageFrame(pixels, 100),),
        )
    )
    size = image.get_size(_ctx())
    assert size.width == 4
    assert size.height == 1


def test_position_ms_override() -> None:
    frames = (
        ImageFrame(bytes((255, 0, 0, 0, 0, 0)), 40),
        ImageFrame(bytes((0, 0, 255, 0, 0, 0)), 90),
    )
    image = Image(
        source=ImageData(width=1, height=2, frames=frames),
        position_ms=40,
    )
    canvas = image.compose(_ctx(1, 1))
    assert canvas.rows[0][0].foreground == "#0000ff"


def test_source_change_resets_playback_and_canvas_cache() -> None:
    red = ImageData(
        width=1,
        height=2,
        frames=(ImageFrame(bytes((255, 0, 0) * 2), 40),),
    )
    green = ImageData(
        width=1,
        height=2,
        frames=(ImageFrame(bytes((0, 255, 0) * 2), 40),),
    )
    image = Image(source=red)
    first = image.compose(_ctx(1, 1))
    assert image.compose(_ctx(1, 1)) is first
    image.seek(20)
    image.source = green
    second = image.compose(_ctx(1, 1))
    assert second is not first
    assert second.rows[0][0].foreground == "#00ff00"
    assert image._paused_elapsed_ms == 0.0


def test_playback_idempotence_and_nonlooping_clamp() -> None:
    frames = (
        ImageFrame(bytes((255, 0, 0) * 2), 40),
        ImageFrame(bytes((0, 0, 255) * 2), 90),
    )
    image = Image(
        source=ImageData(width=1, height=2, frames=frames),
        loop=False,
    )
    image.play()
    assert image.playing is True
    image.pause()
    frozen = image._paused_elapsed_ms
    image.pause()
    assert image._paused_elapsed_ms == frozen
    image.seek(10_000)
    assert image._started_at_ns is None
    assert image.get_frame_index(10_000) == 1
    image.play()
    started = image._started_at_ns
    image.play()
    assert image._started_at_ns == started

    looping = Image(source=image.source, loop=True)
    assert looping.finished is False


def test_terminal_aspect_mode_uses_source_width() -> None:
    image = Image(
        source=ImageData(
            width=4,
            height=2,
            frames=(ImageFrame(bytes((0, 255, 0) * 8), 40),),
        ),
        horizontal_pixels_per_cell=2,
        correct_terminal_aspect=True,
    )
    assert image.get_size(_ctx()).width == 4
    canvas = image.compose(_ctx(4, 1))
    assert canvas.width == 4


def test_runtime_offscreen_render_smoke() -> None:
    pixels = bytes([0, 255, 0] * 8)
    image = Image(
        source=ImageData(
            width=4,
            height=2,
            frames=(ImageFrame(pixels, 100),),
        )
    )
    runtime = Runtime.offscreen(8, 4)
    try:
        frame = runtime.render(image)
        assert isinstance(frame.text, str)
        assert len(frame.text) > 0
    finally:
        runtime.close()


def test_animation_uses_source_frame_timings_with_pillow() -> None:
    _require_pillow()
    image = Image(source=_get_gif_bytes())
    assert image.frame_count == 2
    assert image.duration_ms == 130
    assert image.get_frame_index(0) == 0
    assert image.get_frame_index(40) == 1


def test_runtime_png_with_pillow() -> None:
    _require_pillow()
    runtime = Runtime.offscreen(8, 4)
    try:
        frame = runtime.render(Image(source=_get_png_bytes()))
        assert isinstance(frame.text, str)
        assert len(frame.text) > 0
    finally:
        runtime.close()


def test_transparent_stream_composites_over_configured_background() -> None:
    pillow_image = _require_pillow()
    source = pillow_image.new("RGBA", (1, 2), (0, 255, 0, 0))
    stream = io.BytesIO()
    source.save(stream, format="PNG")
    stream.seek(0)

    image = Image(source=stream, background=(255, 0, 0))
    canvas = image.compose(_ctx(1, 1))
    assert canvas.rows[0][0].foreground == "#ff0000"
