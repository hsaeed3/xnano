"""
xnano.composition

Compose a buffer, then build it with ``build``.

[`make`][xnano.composition.make] records widgets, attributes, operations and children.
[`Composition.build`][xnano.composition.Composition.build] turns that record into a core
buffer. It does not open a terminal and it does not draw.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeAlias, TypedDict, cast

import xnano_core as _core
from xnano._media import content_buffer
from xnano._optional import is_image
from xnano._values import (
    AttributeValue,
    Axis,
    AxisName,
    Content,
    Number,
    NumericExpression,
)
from xnano_core import TextContent

if TYPE_CHECKING:
    from xnano_image import TerminalImage

__all__ = ['Composition', 'make']

_AXES: tuple[AxisName, ...] = ('x', 'y', 'width', 'height')


class BufferArguments(TypedDict, total=False):
    """
    The arguments a buffer can be constructed with before it is placed.

    Attributes:
        content: Text the buffer starts with.
        width: The width in cells.
        height: The height in cells.
        x: The column.
        y: The row.
        style: The style of the buffer.
    """

    content: TextContent
    """Text the buffer starts with."""
    width: int
    """The width in cells."""
    height: int
    """The height in cells."""
    x: int
    """The column."""
    y: int
    """The row."""
    style: _core.Style
    """The style of the buffer."""


CompositionContent: TypeAlias = (
    'type[_core.Buffer] | _core.Buffer | _core.Operation | TerminalImage | str | None'  # noqa: E501
)
"""What [`make`][xnano.make] starts from: a widget class, a buffer, text, an operation or nothing."""


class Composition:
    """
    A buffer being composed.

    Set any attribute the buffer or widget understands. Position and size keep their usual
    operators, so ``composition.x += 1`` and ``composition.x = ParentWidth // 2`` are
    ordinary assignments. ``composition | operation`` records an operation, including
    an effect, a border or any other [`Operation`][xnano_core.Operation].
    [`add`][xnano.composition.Composition.add] records a child.

    An operation is applied once, to the buffer as it is when it is built, so an operation
    such as a border keeps the size it was given then. A
    [`Block`][xnano_core.Block] draws its border at whatever size it has.

    Nothing here draws. [`build`][xnano.composition.Composition.build] returns the buffer,
    and you render or place that buffer yourself.

    Attributes:
        x: The column of the left edge, as an [`Axis`][xnano.types.Axis].
        y: The row of the top edge, as an [`Axis`][xnano.types.Axis].
        width: The width, as an [`Axis`][xnano.types.Axis].
        height: The height, as an [`Axis`][xnano.types.Axis].

    Examples:
        ```python
        import xnano
        from xnano_core import Border, Buffer

        card = xnano.make(width=12, height=3) | Border('rounded')
        buffer = card.build()
        assert isinstance(buffer, Buffer)
        assert '╭' in buffer.render(format='text')
        ```
    """

    _content: CompositionContent
    _attributes: dict[str, AttributeValue]
    _operations: list[_core.Operation]
    _children: list[tuple[Content | Composition, dict[str, AttributeValue]]]
    _buffer: _core.Buffer | None
    _pending: list[_core.Operation]

    @property
    def x(self) -> Number | NumericExpression:
        """The column of the left edge, as an [`Axis`][xnano.types.Axis]."""
        return self._read_axis('x')

    @x.setter
    def x(self, value: Axis) -> None:
        self._attributes['x'] = value

    @property
    def y(self) -> Number | NumericExpression:
        """The row of the top edge, as an [`Axis`][xnano.types.Axis]."""
        return self._read_axis('y')

    @y.setter
    def y(self, value: Axis) -> None:
        self._attributes['y'] = value

    @property
    def width(self) -> Number | NumericExpression:
        """The width, as an [`Axis`][xnano.types.Axis]."""
        return self._read_axis('width')

    @width.setter
    def width(self, value: Axis) -> None:
        self._attributes['width'] = value

    @property
    def height(self) -> Number | NumericExpression:
        """The height, as an [`Axis`][xnano.types.Axis]."""
        return self._read_axis('height')

    @height.setter
    def height(self, value: Axis) -> None:
        self._attributes['height'] = value

    def _read_axis(self, name: AxisName) -> Number | NumericExpression:
        buffer = self._buffer
        value: object = (
            getattr(buffer, name) if buffer is not None else self._attributes.get(name)
        )
        if isinstance(value, (int, float, _core.NumericValue)):
            return value
        raise AttributeError(
            f'{name} is not set on this composition. Assign composition.{name} before '
            f'reading it, or call build() and read the attribute on the buffer it returns.'
        )

    def __init__(
        self, content: CompositionContent, attributes: dict[str, AttributeValue]
    ) -> None:
        # Created by ``xnano.make``; not constructed directly.
        """
        Record a buffer to build. Use [`make`][xnano.make] instead of calling this.

        Args:
            content: What the buffer is: a widget class, a buffer, text, an image or nothing.
            attributes: Attributes to set on the buffer, such as ``x`` or ``ratio``.
        """
        object.__setattr__(self, '_content', content)
        object.__setattr__(self, '_attributes', dict(attributes))
        object.__setattr__(self, '_operations', [])
        object.__setattr__(self, '_children', [])
        object.__setattr__(self, '_buffer', None)
        object.__setattr__(self, '_pending', [])

    def __setattr__(self, name: str, value: AttributeValue) -> None:
        buffer = self._buffer
        if buffer is not None:
            setattr(buffer, name, value)
            return
        self._attributes[name] = value

    def __getattr__(self, name: str) -> AttributeValue:
        buffer = self._buffer
        if buffer is not None:
            return getattr(buffer, name)
        try:
            return self._attributes[name]
        except KeyError:
            raise AttributeError(
                f'{name} is not set on this composition. Assign composition.{name} before '
                f'reading it, or call build() and read the attribute on the buffer it returns.'
            ) from None

    def __or__(self, operation: _core.Operation) -> Composition:
        self._record_operation(operation)
        return self

    def __ior__(self, operation: _core.Operation) -> Composition:
        self._record_operation(operation)
        return self

    def update(self, *operations: _core.Operation) -> Composition:
        """
        Record operations to apply when the buffer is built.

        Args:
            operations: Any core operation, including effects and widget drawing
                operations.
        """
        for operation in operations:
            self._record_operation(operation)
        return self

    def add(
        self, child: Content | Composition, /, **attributes: AttributeValue
    ) -> Composition:
        """
        Record a child buffer or composition.

        The child is attached when [`build`][xnano.composition.Composition.build] builds
        this buffer. A child composition is built then too. This does not draw.

        Args:
            child: A buffer, a widget, or another composition.
            attributes: Attributes set on the child before it is attached, such as
                ``x`` and ``y``.
        """
        self._children.append((child, attributes))
        buffer = self._buffer
        if buffer is not None:
            _attach(buffer, child, attributes)
        return self

    def build(self) -> _core.Buffer:
        """
        Build the buffer this composition describes.

        The returned buffer is a core [`Buffer`][xnano_core.Buffer] (or a
        widget, which is a buffer). Render it with ``buffer.render()``, or place it on
        a terminal yourself. ``build`` does neither: calling it draws nothing and opens
        nothing.

        Calling ``build`` again returns the same buffer.

        Examples:
            ```python
            import xnano

            thumb = xnano.make('#')
            thumb.x = 1
            thumb.x += 2
            buffer = thumb.build()
            assert buffer.x == 3
            assert buffer.render(format='text') == '#'
            ```
        """
        buffer = self._buffer
        if buffer is not None:
            return buffer
        built = _create(self._content, self._attributes)
        pending = [
            operation
            for operation in self._operations
            if not _apply_now(built, operation)
        ]
        for child, attributes in self._children:
            _attach(built, child, attributes)
        object.__setattr__(self, '_buffer', built)
        object.__setattr__(self, '_pending', pending)
        return built

    def axes(self) -> dict[AxisName, Axis]:
        """Position and size recorded on the composition, including expressions."""
        axes: dict[AxisName, Axis] = {}
        for name in _AXES:
            value = self._attributes.get(name)
            if isinstance(value, (int, float, str, tuple, _core.NumericValue)):
                axes[name] = value
        return axes

    def apply_mounted(self) -> None:
        """
        Apply operations that need a mounted buffer.

        A terminal calls this after it has placed the buffer. ``build`` itself does not.
        """
        buffer = self._buffer
        pending = self._pending
        if buffer is None or not pending:
            return
        buffer.update(*pending)
        object.__setattr__(self, '_pending', [])

    def __xnano_buffer__(self) -> _core.Buffer:
        """Return the built buffer, for a terminal that is asked to show this composition."""
        return self.build()

    def _record_operation(self, operation: _core.Operation) -> None:
        if not isinstance(operation, _core.Operation):
            raise TypeError(
                f'{operation!r} is not an operation, so it cannot be composed onto a buffer. '
                f'Pass an Operation such as a Border or an Effect. To nest a buffer or a '
                f'widget, use composition.add(...).'
            )
        self._operations.append(operation)
        buffer = self._buffer
        if buffer is not None:
            try:
                buffer.update(operation)
            except _core.RuntimeRequiredError:
                self._pending.append(operation)

    def __repr__(self) -> str:
        if self._buffer is not None:
            return f'Composition(made, width={self._buffer.width}, height={self._buffer.height})'
        name = getattr(self._content, '__name__', None)
        content = (
            name if isinstance(self._content, type) else type(self._content).__name__
        )
        return f'Composition({content}, pending)'


def make(
    content: CompositionContent = None, /, **attributes: AttributeValue
) -> Composition:
    """
    Start a buffer composition.

    ``content`` is a widget class, a buffer, text, or nothing for an empty buffer.
    Keyword arguments are attributes of that buffer, such as ``width``, ``ratio`` or
    ``x``. The result is not drawn. Call
    [`build`][xnano.composition.Composition.build] when you want the buffer.

    Args:
        content: What the buffer is. A widget class such as ``Gauge`` is constructed
            from the attributes. A buffer is used as it is. A string becomes text. An
            image (from [`img`][xnano.img] or
            [`TerminalImage`][xnano_image.TerminalImage]) becomes cells at the ``width`` and
            ``height`` given, or at its own size; an animated image shows its first
            frame, and plays when it is added to a terminal. Omit it for an empty
            buffer.
        attributes: Attributes applied to the buffer. Any attribute the buffer accepts,
            including expressions.

    Examples:
        ```python
        import xnano
        from xnano_core import Gauge

        gauge = xnano.make(Gauge, ratio=0.5, width=10, height=1)
        gauge.ratio = 0.75
        assert gauge.build().render(format='text')
        ```
    """
    return Composition(content, attributes)


def _apply_now(buffer: _core.Buffer, operation: _core.Operation) -> bool:
    """Apply an operation now. Return whether it could run without a runtime."""
    try:
        buffer.update(operation)
    except _core.RuntimeRequiredError:
        return False
    return True


def _create(
    content: CompositionContent, attributes: dict[str, AttributeValue]
) -> _core.Buffer:
    if isinstance(content, _core.Buffer):
        for name, value in attributes.items():
            setattr(content, name, value)
        return content
    if isinstance(content, type) and issubclass(content, _core.Buffer):
        return _construct(content, attributes)
    if is_image(content):
        width, height = attributes.get('width'), attributes.get('height')
        buffer, _ = content_buffer(
            cast('Content', content),
            columns=width if isinstance(width, int) else None,
            rows=height if isinstance(height, int) else None,
        )
        for name, value in attributes.items():
            if name not in ('width', 'height') and _is_buffer_value(name, value):
                setattr(buffer, name, value)
        return buffer
    if isinstance(content, str) or content is None:
        return _build_plain(content, attributes)
    if isinstance(content, _core.Operation):
        buffer = _build_plain(None, attributes)
        buffer.update(content)
        return buffer
    raise TypeError(
        f'{content!r} cannot be composed into a buffer. Pass a widget class, a buffer, '
        f'a string, an operation, or no content for an empty buffer.'
    )


def _construct(
    kind: type[_core.Buffer], attributes: dict[str, AttributeValue]
) -> _core.Buffer:
    """Construct a widget, then set any attribute its constructor does not take."""
    geometry = _geometry(attributes)
    remaining = {
        name: value
        for name, value in attributes.items()
        if name not in geometry and _is_buffer_value(name, value)
    }
    factory = cast('Callable[..., _core.Buffer]', kind)
    try:
        return factory(**geometry, **remaining)
    except TypeError:
        pass
    try:
        buffer = factory(**geometry) if geometry else factory()
    except TypeError as error:
        raise TypeError(
            f'{kind.__name__} could not be constructed from {sorted(attributes)}. '
            f'Pass the attributes {kind.__name__} accepts, or construct it yourself and '
            f'pass the instance to make().'
        ) from error
    for name, value in remaining.items():
        _assign_attribute(buffer, kind, name, value)
    return buffer


def _assign_attribute(
    buffer: _core.Buffer, kind: type[_core.Buffer], name: str, value: AttributeValue
) -> None:
    try:
        setattr(buffer, name, value)
    except (AttributeError, TypeError) as error:
        raise TypeError(
            f'{kind.__name__} has no attribute {name} that can be set to {value!r}. '
            f'Check the name against the widget, or pass it to the constructor.'
        ) from error


def _build_plain(
    content: str | None, attributes: dict[str, AttributeValue]
) -> _core.Buffer:
    arguments = _geometry(attributes)
    if isinstance(content, str):
        arguments['content'] = content
    buffer = _core.Buffer(
        arguments.get('content'),
        width=arguments.get('width'),
        height=arguments.get('height'),
        x=arguments.get('x', 0),
        y=arguments.get('y', 0),
        style=arguments.get('style'),
    )
    for name, value in attributes.items():
        if name in arguments or not _is_buffer_value(name, value):
            continue
        setattr(buffer, name, value)
    return buffer


def _is_buffer_value(name: str, value: AttributeValue) -> bool:
    """
    Whether a buffer can take the attribute as it is.

    Position and size may be percentages, ranges or expressions, which are applied when the
    buffer is placed.
    """
    if name in _AXES:
        return isinstance(value, int) and not isinstance(value, bool)
    return not isinstance(value, _core.NumericValue)


def _attach(
    buffer: _core.Buffer,
    child: Content | Composition,
    attributes: dict[str, AttributeValue],
) -> None:
    if isinstance(child, Composition):
        child_buffer = child.build()
    elif isinstance(child, _core.Buffer):
        child_buffer = child
    else:
        child_buffer, _ = content_buffer(child)
    for name, value in attributes.items():
        setattr(child_buffer, name, value)
    buffer.attach(child_buffer)


def _geometry(attributes: dict[str, AttributeValue]) -> BufferArguments:
    """Constructor arguments a buffer can take before it is placed."""
    geometry: BufferArguments = {}
    for name in _AXES:
        value = attributes.get(name)
        if isinstance(value, int) and not isinstance(value, bool):
            geometry[name] = value
    style = attributes.get('style')
    if isinstance(style, _core.Style):
        geometry['style'] = style
    return geometry
