"""
xnano._internal._content

Turn anything a canvas can show into a buffer, and check component methods.
"""

from __future__ import annotations

import inspect
import os
import weakref
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

import xnano_core as _core
from xnano._internal._optional import is_image
from xnano._schema._content import Content
from xnano.art._images import Image, ImageAnimation, image_buffer
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from xnano.hooks._context import Context

__all__ = ['check_context_method', 'content_buffer']


class _NotWritable(TypeError):
    """Raised for content that cannot be shown; remembers the offending object."""

    def __init__(self, message: str, content: object) -> None:
        """Remember the message and the content that cannot be shown."""
        super().__init__(message)
        self.content = content


_MAXIMUM_RENDER_DEPTH = 8
"""How many times a result may itself be something that renders, before it is a cycle."""


def content_buffer(
    content: Content,
    *,
    columns: int | None = None,
    rows: int | None = None,
    limit: _core.Size | None = None,
    elapsed_seconds: float = 0.0,
    context: Context[object, object] | None = None,
) -> tuple[_core.Buffer, ImageAnimation | None]:
    """
    Return the buffer that shows any content, and the animation that moves it, if any.

    Args:
        content: A buffer or widget, text, a region, art, a pixel, an image, an object with an
            ``__xnano_write__`` method, or a sequence of those.
        columns: The width in cells of an image.
        rows: The height in cells of an image.
        limit: The largest area an image may take when neither size is given.
        elapsed_seconds: The clock time at which an animated image starts.
        context: What ``__xnano_write__`` methods are called with.

    Raises:
        TypeError: The content is not something that can be shown.
        TerminalError: An ``__xnano_write__`` method returns itself again and again.
    """
    try:
        return _content_buffer(
            content,
            columns=columns,
            rows=rows,
            limit=limit,
            elapsed_seconds=elapsed_seconds,
            context=context,
            _chain=(),
        )
    except _NotWritable as error:
        raise TypeError(str(error)) from None


_CHECKED_METHODS: weakref.WeakSet[object] = weakref.WeakSet()
"""Functions of methods already found to accept a context, so each is inspected once."""


def check_context_method(content: object, name: str) -> None:
    """
    Refuse an ``__xnano_write__``, ``__xnano_render__`` or ``__xnano_play__`` method that cannot
    take the context.

    A method that passes is remembered, so a component drawn every frame is inspected once.

    Raises:
        TypeError: The method does not accept one argument besides ``self``.
    """
    method = getattr(content, name)
    function = getattr(method, '__func__', None)
    if function is not None and function in _CHECKED_METHODS:
        return
    try:
        inspect.signature(method).bind(None)
    except TypeError:
        kind = type(content).__name__
        produces = {
            '__xnano_play__': 'return what it plays, such as a Note or melody text',
            '__xnano_render__': 'draw on context.screen',
        }.get(name, 'return the content')
        raise TypeError(
            f'{kind}.{name} must take the context, but it cannot be called with one. '
            f'Write def {name}(self, context): ... and {produces}.'
        ) from None
    except ValueError:
        return
    if function is not None:
        try:
            _CHECKED_METHODS.add(function)
        except TypeError:
            pass


def _content_buffer(
    content: Content,
    *,
    columns: int | None,
    rows: int | None,
    limit: _core.Size | None,
    elapsed_seconds: float,
    context: Context[object, object] | None,
    _chain: tuple[type, ...],
) -> tuple[_core.Buffer, ImageAnimation | None]:
    """Do the work of [`content_buffer`][xnano._internal._content.content_buffer], tracking the chain."""
    if isinstance(content, _core.Buffer):
        return content, None
    if isinstance(content, str):
        return _core.Buffer.with_text(content), None
    if isinstance(content, (bytes, bytearray)):
        raise TypeError(
            'write() does not accept raw bytes. Write the cell buffer instead: '
            'canvas.screen.write(Buffer.from_cell_grid(data)), or for picture bytes use '
            'xnano.load_image(data) or xnano.draw(data, width=..., height=...).'
        )
    if isinstance(content, os.PathLike):
        raise TypeError(
            f'{content!r} is a path, and write shows images, not paths. Load it first with '
            f'xnano.load_image(path) and write the result.'
        )
    if isinstance(content, Image):
        return image_buffer(
            content.decoded,
            columns=columns,
            rows=rows,
            limit=limit,
            elapsed_seconds=elapsed_seconds,
            fit=content.fit,
            resampling_filter=content.resampling_filter,
            background=content.background,
        )
    if is_image(content):
        raise TypeError(
            'write() does not accept a TerminalImage directly. Wrap it: '
            'canvas.screen.write(Image(terminal_image)), or load a file with xnano.load_image(path).'
        )
    from xnano.canvas import Canvas

    if isinstance(content, Canvas):
        raise TypeError(
            'A canvas is written with canvas.screen.write(child) directly; a component or a '
            'sequence cannot contain one.'
        )
    if not isinstance(content, type) and hasattr(content, '__xnano_write__'):
        kind = type(content)
        if len(_chain) >= _MAXIMUM_RENDER_DEPTH:
            names = ' -> '.join(item.__name__ for item in (*_chain, kind))
            raise TerminalError(
                f'{kind.__name__}.__xnano_write__ keeps returning something that renders '
                f'again ({names}). Return text, a Region, an Art, a Buffer or another '
                f'finished value instead of an object that renders itself.'
            )
        check_context_method(content, '__xnano_write__')
        result = content.__xnano_write__(context)  # type: ignore[arg-type]
        try:
            return _content_buffer(
                result,
                columns=columns,
                rows=rows,
                limit=limit,
                elapsed_seconds=elapsed_seconds,
                context=context,
                _chain=(*_chain, kind),
            )
        except _NotWritable as error:
            if error.content is not result:
                raise
            raise TypeError(
                f'{kind.__name__}.__xnano_write__ returned {type(result).__name__}, but it '
                f'must return something write() accepts: text, a Region, an Art, a Pixel, an '
                f'Image, a Buffer, an object with __xnano_write__, or a sequence of those.'
            ) from None
    if isinstance(content, Sequence):
        return _stack(
            content,
            columns=columns,
            rows=rows,
            limit=limit,
            elapsed_seconds=elapsed_seconds,
            context=context,
            chain=_chain,
        ), None
    if hasattr(content, '__xnano_render__'):
        missing = (
            ' It is a renderable, which has a screen of its own, so it is written on its '
            'own with canvas.screen.write(), not as part of other content such as a list.'
        )
    elif hasattr(content, '__xnano_play__'):
        missing = (
            ' It has an __xnano_play__ method but no __xnano_write__ method, so it can be '
            'played with canvas.speaker.play() but not written.'
        )
    else:
        missing = ' It has no __xnano_write__ method.'
    raise _NotWritable(
        f'Cannot show a {type(content).__name__}.{missing} Use a string, a Region, an Art, '
        f'a Pixel, an xnano.Image (made with xnano.load_image(path)), a Buffer or widget, '
        f'an object with an __xnano_write__ method, or a sequence of those.',
        content,
    )


def _stack(
    items: Sequence[object],
    *,
    columns: int | None,
    rows: int | None,
    limit: _core.Size | None,
    elapsed_seconds: float,
    context: Context[object, object] | None,
    chain: tuple[type, ...],
) -> _core.Buffer:
    """Draw the items one below the other, as wide as the widest."""
    results = [
        _content_buffer(
            cast('Content', item),
            columns=columns,
            rows=rows,
            limit=limit,
            elapsed_seconds=elapsed_seconds,
            context=context,
            _chain=chain,
        )
        for item in items
    ]
    if any(animation is not None for _, animation in results):
        raise TypeError(
            'An animated image cannot be shown inside a sequence, because only its first '
            'frame would be drawn. Write it on its own with canvas.screen.write(image), or return '
            'it by itself from __xnano_write__ instead of in a list.'
        )
    buffers = [buffer for buffer, _ in results]
    stacked = _core.Buffer(
        width=max((buffer.width for buffer in buffers), default=0),
        height=sum(buffer.height for buffer in buffers),
    )
    offset = 0
    for buffer in buffers:
        stacked.update(_core.Paste(buffer, y=offset, mode='replace'))
        offset += buffer.height
    return stacked
