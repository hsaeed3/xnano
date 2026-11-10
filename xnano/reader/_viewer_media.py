"""
xnano.reader._viewer_media

The images and the sound of the viewer: images load in the background, and a sound plays.
"""

from __future__ import annotations

import pathlib
import threading
from typing import TYPE_CHECKING

from xnano._internal._optional import is_installed
from xnano.reader._documents import audio_lines, load_audio_of
from xnano.reader._images import cells_for, load_image_in_cells, pixel_size
from xnano.reader._lines import Line, Run, content_lines, line_of
from xnano_core import LineGauge

if TYPE_CHECKING:
    from xnano.reader._viewer import _Viewer


def image_of(
    viewer: _Viewer, path: pathlib.Path, columns: int, rows: int
) -> object | None:
    """
    The image of ``path``, or ``None`` while it loads or when it cannot be read.

    An image is decoded on another thread the first time that it comes into view, so a
    large image never stops the scrolling. The window is drawn again when it is ready.
    """
    with viewer.images_lock:
        if path in viewer.images:
            return viewer.images[path]
        if path in viewer.is_loading:
            return None
        viewer.is_loading.add(path)
    is_still = viewer.document.kind != 'image'

    def load() -> None:
        image = load_image_in_cells(path, columns, rows, is_still=is_still)
        with viewer.images_lock:
            viewer.images[path] = image
            viewer.is_loading.discard(path)

    threading.Thread(target=load, name='xnano-reader-image', daemon=True).start()
    return None


def image_lines(viewer: _Viewer) -> list[Line]:
    """An image file as large as the window allows, in the middle of it."""
    document = viewer.document
    pixels = pixel_size(document.path) if is_installed('image') else None
    if pixels is None:
        words = (
            'This file is not an image that xnano can read.'
            if is_installed('image')
            else 'Images need an extra: pip install "xnano[image]"'
        )
        return [
            line_of([Run(document.path.name, bold=True)]),
            Line(),
            line_of([Run(words)]),
        ]
    columns, rows = cells_for(pixels, viewer.width, height=viewer.height)
    if not viewer.message:
        viewer.message = f'{pixels[0]} × {pixels[1]} pixels'
    return [Line() for _ in range((viewer.height - rows) // 2)] + content_lines(
        document.path,
        columns=columns,
        rows=rows,
        column=(viewer.width - columns) // 2,
        description=document.path.name,
    )


def audio_document_lines(viewer: _Viewer) -> list[Line]:
    """What a sound file holds, and a gauge that follows how far it has played."""
    if viewer.audio is None:
        viewer.audio = load_audio_of(viewer.document)
    lines = audio_lines(viewer.document, viewer.audio)
    if viewer.audio is None:
        return lines
    if not viewer.terminal.speaker.is_available:
        lines.append(Line())
        lines.append(line_of([Run('× This computer has no sound output.')]))
        return lines
    viewer.gauge = LineGauge(
        0.0,
        label='■ 0:00',
        filled_style=viewer.theme.style(role='accent'),
        unfilled_style=viewer.theme.style(role='border'),
        style=viewer.theme.style(),
    )
    lines.append(Line())
    lines.extend(content_lines(viewer.gauge, columns=min(viewer.width - 2, 60), rows=1))
    return lines


def toggle_audio(viewer: _Viewer) -> None:
    """Play the sound from its start, or stop it."""
    if viewer.audio is None or viewer.gauge is None:
        return
    if viewer.audio_started is not None:
        stop_audio(viewer)
    else:
        viewer.audio_handle = viewer.terminal.speaker.play(viewer.audio)  # type: ignore[arg-type]
        viewer.audio_started = viewer.terminal.clock.elapsed_seconds
    follow_audio(viewer)


def stop_audio(viewer: _Viewer) -> None:
    """Stop the sound if it plays."""
    handle, viewer.audio_handle, viewer.audio_started = viewer.audio_handle, None, None
    if handle is not None:
        handle.remove()  # type: ignore[attr-defined]


def follow_audio(viewer: _Viewer) -> None:
    """Move the gauge to where the sound is, and notice when it has ended."""
    if viewer.audio is None or viewer.gauge is None:
        return
    seconds = viewer.audio.duration_milliseconds / 1000  # type: ignore[attr-defined]
    played = 0.0
    if viewer.audio_started is not None:
        played = viewer.terminal.clock.elapsed_seconds - viewer.audio_started
        if played >= seconds:
            stop_audio(viewer)
            played = 0.0
    mark = '▶' if viewer.audio_started is not None else '■'
    viewer.gauge.ratio = min(played / seconds, 1.0) if seconds else 0.0
    viewer.gauge.label = f'{mark} {_minutes(played)} of {_minutes(seconds)}'


def _minutes(seconds: float) -> str:
    """Seconds as minutes and seconds, such as ``1:05``."""
    whole = int(seconds)
    return f'{whole // 60}:{whole % 60:02d}'
