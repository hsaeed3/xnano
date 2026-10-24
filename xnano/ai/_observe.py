"""
xnano.ai._observe

The canvas as a model reads it: ``observe(target)`` and the evidence every task model takes.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel

import xnano_core as _core
from xnano.art._worlds import Art
from xnano.canvas import Canvas
from xnano.errors import TerminalError
from xnano.hooks._context import Context, Frame, Update
from xnano.layout._placement import Placement

if TYPE_CHECKING:
    from xnano_core import JSONValue

__all__ = [
    'Evidence',
    'Observation',
    'evidence_for',
    'evidence_prompt',
    'evidence_value',
    'observe',
    'snapshot',
]

Evidence = object
"""
What a decision or judgement is about.

A [`Context`][xnano.hooks.Context], [`Canvas`][xnano.canvas.Canvas],
[`Placement`][xnano.layout.Placement], [`Frame`][xnano.hooks.Frame] or
[`Art`][xnano.art.Art] (each read as an [`Observation`][xnano.ai.Observation]), an
``Observation``, a string, a Pydantic model or dataclass, or JSON-like data (a mapping or a
sequence) holding any of these, such as ``{'screen': context, 'selected': row.text}``.
"""

_EVENT_HOOK_KINDS: dict[str, str] = {
    'key': 'key',
    'mouse': 'mouse',
    'paste': 'paste',
    'resize': 'resize',
    'focus_gained': 'focus',
    'focus_lost': 'focus',
    'custom': 'custom',
}


@dataclasses.dataclass(frozen=True)
class Observation:
    """
    The canvas, or a part of it, as a model reads it.

    Made by [`observe`][xnano.ai.observe], and by every task model from the evidence it is
    given. ``to_json()`` is what a decision model is sent; ``to_prompt()`` is what a language
    model reads, with row numbers and a column ruler so that it can name cells.

    Attributes:
        text: The characters of the target's cells, one line per row.
        x: The column of the target, in its parent.
        y: The row of the target, in its parent.
        width: The width of the target in cells (in pixels for art).
        height: The height of the target in cells (in pixels for art).
        state: The canvas's state as JSON, or ``None`` for a canvas without state.
        event: What the hook heard: its ``kind`` (a [`HookKind`][xnano.hooks.HookKind]) and the
            details of the input, or ``None`` when nothing was heard.
        frame: The frame ``index``, the ``elapsed_seconds`` and the canvas's ``bpm``, or
            ``None`` for art.

    Examples:
        ```python
        import xnano
        from xnano.ai import observe

        with xnano.new(width=8, height=2) as canvas:
            label = canvas.screen.write('ok', x=2, y=1)
            observation = observe(label)
        assert (observation.text, observation.x, observation.y) == ('ok', 2, 1)
        assert observation.to_json()['width'] == 2
        ```
    """

    text: str
    x: int
    y: int
    width: int
    height: int
    state: JSONValue | None = None
    event: dict[str, JSONValue] | None = None
    frame: dict[str, JSONValue] | None = None

    def to_json(self) -> dict[str, JSONValue]:
        """The observation as JSON-like data, as a decision model is sent it."""
        value: dict[str, JSONValue] = {
            'text': self.text,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
        }
        for name in ('state', 'event', 'frame'):
            part = getattr(self, name)
            if part is not None:
                value[name] = part
        return value

    def to_prompt(self) -> str:
        """
        The observation as text for a language model.

        The cells come with a column ruler above them and a row number before each line, then
        the position, size, event, frame and state as plain lines.
        """
        lines = [_ruled(self.text, self.width, self.height)]
        lines.append(
            f'position: x={self.x}, y={self.y}; size: {self.width} by {self.height}'
        )
        if self.event is not None:
            lines.append(f'event: {json.dumps(self.event, sort_keys=True)}')
        if self.frame is not None:
            lines.append(f'frame: {json.dumps(self.frame, sort_keys=True)}')
        if self.state is not None:
            lines.append(f'state: {json.dumps(self.state, sort_keys=True)}')
        return '\n'.join(lines)


def _ruled(text: str, width: int, height: int = 0) -> str:
    """Cells with a ruler of column numbers above them and a number before each row."""
    rows = text.split('\n') if text else []
    rows += [''] * max(0, height - len(rows))
    columns = max([width, *(len(row) for row in rows)], default=0)
    margin = len(str(max(len(rows) - 1, 0))) + 1
    tens = ''.join(
        str(column // 10 % 10) if column % 10 == 0 else ' ' for column in range(columns)
    )
    units = ''.join(str(column % 10) for column in range(columns))
    ruled = []
    if columns >= 10:
        ruled.append(' ' * (margin + 1) + tens.rstrip())
    ruled.append(' ' * (margin + 1) + units)
    for index, row in enumerate(rows):
        ruled.append(f'{index:>{margin}} |{row.ljust(columns)}|')
    return '\n'.join(ruled)


def observe(target: object) -> Observation:
    """
    Read a canvas, a placement, a hook's context, a frame or a piece of art as a model would.

    Every task model reads its evidence this way; call it yourself to look at what a model is
    shown, to log it, or to combine several readings in one piece of evidence.

    The cells are what the target draws now. A [`Context`][xnano.hooks.Context] is read as
    the placement or canvas its hook is on, with the event it heard and the frame it ran in. A
    [`Frame`][xnano.hooks.Frame] from ``canvas.iter()`` is the whole canvas at that frame.
    [`Art`][xnano.art.Art] is its pixels, one letter per colour, with the colour each letter
    stands for after the rows.

    Args:
        target: A ``Canvas``, ``Placement``, ``Context``, ``Frame`` or ``Art``.

    Raises:
        TerminalError: ``target`` is the context of a ``writable`` or ``playable``
            component, which runs again on every frame it reads, so a model would be asked on
            every frame. Read the evidence in a hook instead, and keep the answer in state.
        TypeError: ``target`` is none of these.

    Examples:
        ```python
        import xnano
        from xnano.ai import observe

        with xnano.new(width=6, height=1) as canvas:
            canvas.screen.write('hello')
            observation = observe(canvas)
        assert observation.text == 'hello'
        assert observation.frame == {'index': 0, 'elapsed_seconds': 0.0, 'bpm': 120.0}
        ```
    """
    if isinstance(target, Observation):
        return target
    if isinstance(target, Context):
        return _observe_context(cast('Context[object, object]', target))
    if isinstance(target, Frame):
        return _observe_canvas(cast('Canvas[object, object]', target.canvas), event=None)
    if isinstance(target, Placement):
        return _observe_placement(cast('Placement[object, object]', target), event=None)
    if isinstance(target, Canvas):
        return _observe_canvas(cast('Canvas[object, object]', target), event=None)
    if isinstance(target, Art):
        return _observe_art(target)
    raise TypeError(
        f'observe() reads a Canvas, a Placement, a hook Context, a Frame or an Art, but got '
        f'{target!r} of type {type(target).__name__}. To give a model other facts, put them '
        f'beside the canvas in a dictionary, such as {{"screen": canvas, "score": 3}}.'
    )


def _observe_context(context: Context[object, object]) -> Observation:
    if context._log is not None:
        raise TerminalError(
            'observe() was given the context of a writable or playable component, which '
            'runs again whenever what it reads changes, so a model would be asked on every '
            'frame. Read the evidence in a hook instead, such as @canvas.hook(on="key"), and '
            'keep the answer in state for the component to read.',
            code='canvas.state',
        )
    event = _event_value(context)
    owner = context._owner
    if isinstance(owner, Placement):
        return _observe_placement(cast('Placement[object, object]', owner), event=event)
    return _observe_canvas(cast('Canvas[object, object]', owner), event=event)


def _observe_canvas(
    canvas: Canvas[object, object], *, event: dict[str, JSONValue] | None
) -> Observation:
    size = canvas.screen.size
    placement = canvas._parent_placement
    x, y = (0, 0) if placement is None else (placement.x, placement.y)
    return Observation(
        text=_trimmed(canvas.screen.render()),
        x=x,
        y=y,
        width=size.width,
        height=size.height,
        state=_state_value(canvas._canvas),
        event=event,
        frame=_frame_value(canvas._canvas),
    )


def _observe_placement(
    placement: Placement[object, object], *, event: dict[str, JSONValue] | None
) -> Observation:
    canvas = placement._canvas._canvas
    return Observation(
        text=_trimmed(placement.render()),
        x=placement.x,
        y=placement.y,
        width=placement.width,
        height=placement.height,
        state=_state_value(canvas),
        event=event,
        frame=_frame_value(canvas),
    )


def _observe_art(art: Art) -> Observation:
    pixels = art.pixels
    width, height = art.width, art.height
    letters: dict[tuple[int, int, int, int], str] = {}
    rows: list[str] = []
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    if pixels is not None:
        for row in range(height):
            line = []
            for column in range(width):
                start = (row * width + column) * 4
                red, green, blue, alpha = pixels[start : start + 4]
                if alpha == 0:
                    line.append('.')
                    continue
                key = (red, green, blue, alpha)
                if key not in letters:
                    letters[key] = alphabet[len(letters) % len(alphabet)]
                line.append(letters[key])
            rows.append(''.join(line))
    palette = [
        f'{letter} = #{red:02x}{green:02x}{blue:02x}'
        + ('' if alpha == 255 else f' at opacity {alpha / 255:.2f}')
        for (red, green, blue, alpha), letter in letters.items()
    ]
    text = '\n'.join(rows)
    if palette:
        text += '\n\n. = transparent\n' + '\n'.join(palette)
    return Observation(text=text, x=0, y=0, width=width, height=height)


def _trimmed(rendered: str) -> str:
    """Rendered rows without the spaces that end them."""
    return '\n'.join(line.rstrip() for line in rendered.split('\n')).rstrip('\n')


def _state_value(canvas: Canvas[object, object]) -> JSONValue | None:
    store = canvas._state_store
    if store is None:
        return None
    value = cast('dict[str, JSONValue]', store.snapshot().to_value())
    # The namespace xnano keeps its own bookkeeping in is not the program's state.
    return {key: part for key, part in value.items() if key != 'xnano'}


def _frame_value(canvas: Canvas[object, object]) -> dict[str, JSONValue]:
    clock = canvas._time_source
    return {
        'index': clock.frame,
        'elapsed_seconds': round(clock.elapsed_seconds, 6),
        'bpm': float(canvas.clock.bpm),
    }


def _event_value(context: Context[object, object]) -> dict[str, JSONValue] | None:
    event = context._event
    if event is None:
        return None
    if isinstance(event, Frame):
        return {'kind': 'frame'}
    if isinstance(event, Update):
        return {'kind': 'tick'}
    if isinstance(event, _core.TerminalStateChange):
        return {
            'kind': 'state',
            'paths': ['.'.join(str(part) for part in path) for path in event.paths],
        }
    if not isinstance(event, _core.Event):
        return None
    kind = _EVENT_HOOK_KINDS.get(str(event.kind))
    value: dict[str, JSONValue] = {'kind': kind}
    if kind == 'key':
        keyboard = context.keyboard
        value.update(
            {'key': keyboard.key, 'binding': keyboard.binding, 'type': keyboard.kind}
        )
    elif kind == 'mouse':
        mouse = context.mouse
        scroll = mouse.scroll
        if scroll.x or scroll.y:
            value = {'kind': 'scroll', 'x': scroll.x, 'y': scroll.y}
        else:
            position = mouse.position
            value.update(
                {
                    'type': mouse.kind,
                    'button': None if mouse.button is None else str(mouse.button),
                    'column': None if position is None else position.x,
                    'row': None if position is None else position.y,
                }
            )
    elif kind == 'paste':
        value['text'] = context.keyboard.pasted
    elif kind == 'focus':
        value['is_focused'] = str(event.kind) == 'focus_gained'
    elif kind == 'custom':
        value['name'] = event.custom_name
    return value


# -- evidence ---------------------------------------------------------------------------

_TARGETS = (Context, Canvas, Placement, Frame, Art, Observation)


def snapshot(evidence: object) -> object:
    """
    The evidence with every xnano target in it read now, as an observation.

    A blocking call reads its evidence with this before it waits on another thread, so the
    canvas is read on the thread that owns it and as it was when the call was made.
    """
    if isinstance(evidence, Observation):
        return evidence
    if isinstance(evidence, _TARGETS):
        return observe(evidence)
    if isinstance(evidence, BaseModel) or (
        dataclasses.is_dataclass(evidence) and not isinstance(evidence, type)
    ):
        return evidence_value(evidence)
    if isinstance(evidence, Mapping):
        return {
            key: snapshot(value)
            for key, value in cast('Mapping[object, object]', evidence).items()
        }
    if isinstance(evidence, (list, tuple)):
        return [snapshot(item) for item in cast('Sequence[object]', evidence)]
    return evidence


def evidence_value(evidence: object) -> JSONValue:
    """The evidence as JSON-like data, with every xnano target in it read as an observation."""
    if isinstance(evidence, _TARGETS):
        return cast('JSONValue', observe(evidence).to_json())
    if evidence is None or isinstance(evidence, (str, int, float, bool)):
        return evidence
    if isinstance(evidence, BaseModel):
        return cast('JSONValue', evidence.model_dump(mode='json'))
    if dataclasses.is_dataclass(evidence) and not isinstance(evidence, type):
        return evidence_value(
            {
                field.name: getattr(evidence, field.name)
                for field in dataclasses.fields(evidence)
            }
        )
    if isinstance(evidence, Mapping):
        return {
            str(key): evidence_value(value)
            for key, value in cast('Mapping[object, object]', evidence).items()
        }
    if isinstance(evidence, Sequence) and not isinstance(evidence, (bytes, bytearray)):
        return [evidence_value(item) for item in cast('Sequence[object]', evidence)]
    raise TypeError(
        f'Evidence is read as JSON, but {evidence!r} of type {type(evidence).__name__} is not '
        f'JSON-like and is not something observe() reads. Give a canvas, a placement, a '
        f'context, text, numbers, or a dictionary or list of them.'
    )


def evidence_prompt(evidence: object) -> str:
    """The evidence as text for a language model: observations as cells, the rest as JSON."""
    if isinstance(evidence, _TARGETS):
        return observe(evidence).to_prompt()
    if isinstance(evidence, str):
        return evidence
    if isinstance(evidence, Mapping) and any(
        isinstance(value, _TARGETS)
        for value in cast('Mapping[object, object]', evidence).values()
    ):
        parts = []
        for key, value in cast('Mapping[object, object]', evidence).items():
            body = (
                observe(value).to_prompt()
                if isinstance(value, _TARGETS)
                else json.dumps(evidence_value(value), indent=2, sort_keys=True)
            )
            parts.append(f'{key}:\n{body}')
        return '\n\n'.join(parts)
    return json.dumps(evidence_value(evidence), indent=2, sort_keys=True)


def evidence_for(evidence: object, *, is_decision_model: bool) -> str:
    """The evidence as the prompt of a request: JSON for a decision model, text otherwise."""
    if is_decision_model:
        value = evidence_value(evidence)
        return value if isinstance(value, str) else json.dumps(value, sort_keys=True)
    return evidence_prompt(evidence)
