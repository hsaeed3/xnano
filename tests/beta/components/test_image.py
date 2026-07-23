"""Tests for beta ``Image``."""

from __future__ import annotations

import io
from typing import Any, cast

import pytest

from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.components.image import Image, ImageData, ImageFit, ImageFrame
from xnano.beta.core import Runtime
from xnano.beta.core.content import CellCanvas
from xnano.beta.types import Area


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
    assert canvas.rows[0][0].color == "#0000ff"


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
    assert canvas.rows[0][0].color == "#0000ff"
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
    assert canvas.rows[0][0].color == "#0000ff"


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
