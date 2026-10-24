"""
xnano.terminal._settings

The terminal settings a canvas asks for: their names, defaults, the ones hooks turn on, and how
new() and open() check them.
"""

from __future__ import annotations

import difflib
from collections.abc import Mapping
from typing import Final

from xnano._internal._axes import check_edges
from xnano._schema._generics import DepsT, StateT
from xnano.canvas import Canvas, _check_appearance, _check_bpm, _check_fps
from xnano.effects._registry import effect_sequence, normalize_effect
from xnano.errors import TerminalError
from xnano.styles._look import APPEARANCE_NAMES, check_border_kind

GATE_NAMES: Final = frozenset(
    {
        'mouse',
        'scroll',
        'keyboard',
        'paste',
        'focus',
        'interrupt',
        'capture',
        'clears_on_close',
        'alternate_screen',
    }
)
"""The terminal settings ``new()`` and ``open()`` accept."""

GATE_DEFAULTS: Final[Mapping[str, object]] = {
    'mouse': False,
    'scroll': False,
    'keyboard': True,
    'paste': True,
    'focus': True,
    'interrupt': True,
    'capture': True,
    'clears_on_close': True,
    'alternate_screen': True,
}
"""The value of every terminal setting that is left out."""

INFERRED_GATES: Final = ('mouse', 'scroll', 'paste')
"""The terminal settings a hook registered before the canvas is opened turns on, unless the caller gave them as ``False``."""

CANVAS_APPEARANCE_NAMES: Final = APPEARANCE_NAMES - {'title'}
"""The appearance keywords of ``new()`` and ``open()``: ``title`` is the window title there."""


def validate_gate_values(gates: Mapping[str, object]) -> None:
    """
    Check the values of the terminal settings and say which value is wrong and what is allowed.

    Args:
        gates: The terminal settings that were given, by name.

    Raises:
        ValueError: A terminal setting has a value it does not accept.
    """
    for name, value in gates.items():
        if name == 'mouse':
            if value == 'buttons':
                raise ValueError(
                    "mouse='buttons' is mouse=True: True reports button presses, releases "
                    "and drags. Pass mouse=True, or mouse='motion' to report every movement."
                )
            if value is not True and value is not False and value != 'motion':
                raise ValueError(
                    f"mouse must be True, False or 'motion', but was {value!r}. True reports "
                    f"button presses, releases and drags; 'motion' reports every movement too."
                )
        elif name == 'keyboard':
            if (
                value is not True
                and value is not False
                and value
                not in (
                    'disambiguated',
                    'release_events',
                )
            ):
                raise ValueError(
                    f"keyboard must be True, False, 'disambiguated' or 'release_events', but "
                    f'was {value!r}.'
                )
        elif value is not True and value is not False:
            raise ValueError(
                f'{name} must be True or False, but was {value!r}. Pass {name}=True or '
                f'{name}=False.'
            )


def split_settings(
    function_name: str, settings: Mapping[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    """
    Split the keyword settings of ``new()`` or ``open()`` into terminal settings and appearance.

    Args:
        function_name: ``'new'`` or ``'open'``, for the error messages.
        settings: The keyword settings that were given.

    Returns:
        The terminal settings and the appearance keywords, each by name.

    Raises:
        TypeError: A keyword is neither a terminal setting nor an appearance keyword.
        ValueError: A terminal setting has a value it does not accept.
    """
    gates: dict[str, object] = {}
    appearance: dict[str, object] = {}
    for name, value in settings.items():
        if name in GATE_NAMES:
            gates[name] = value
        elif name in CANVAS_APPEARANCE_NAMES:
            appearance[name] = value
        elif name == 'offscreen':
            raise TypeError(
                f'{function_name}() has no offscreen setting. A canvas from xnano.new() is '
                f'off the screen, and xnano.open() puts one on the screen: create the canvas '
                f'with xnano.new(...) and leave out offscreen.'
            )
        else:
            known = sorted(
                GATE_NAMES
                | CANVAS_APPEARANCE_NAMES
                | {
                    'width',
                    'height',
                    'fps',
                    'bpm',
                    'title',
                    'effects',
                    'deps',
                    'state',
                    'layout',
                    'edges',
                }
            )
            close = difflib.get_close_matches(name, known, n=2)
            hint = (
                f' Did you mean {" or ".join(repr(item) for item in close)}?'
                if close
                else ''
            )
            raise TypeError(
                f'{function_name}() has no setting called {name!r}.{hint} The settings are '
                f'the terminal settings ({", ".join(sorted(GATE_NAMES))}) and the look of the '
                f'canvas ({", ".join(sorted(CANVAS_APPEARANCE_NAMES))}).'
            )
    validate_gate_values(gates)
    check_border_kind(appearance.get('border'))
    return gates, appearance


def appearance_with_content_error(
    function_name: str, appearance: Mapping[str, object]
) -> TypeError:
    """The error for appearance keywords that were given together with content."""
    names = ', '.join(sorted(appearance))
    first = sorted(appearance)[0]
    return TypeError(
        f'These keywords style the canvas itself, not its content: {names}. Pass them to '
        f'canvas.screen.write(content, {first}=...) to style the content, or call {function_name}() '
        f'without content to style the canvas.'
    )


def is_gate_on(gate: str, resolved: Mapping[str, object]) -> bool:
    """Whether the input a hook needs reaches the canvas with the terminal settings ``resolved``."""
    if gate == 'keyboard_release':
        return resolved.get('keyboard') == 'release_events'
    value = resolved.get(gate)
    return value is not False and value is not None


def hook_label(function: object) -> str:
    """Name a hook for a message: ``hook name``, or ``component name`` for a component's."""
    component_name = getattr(function, '_component_name', None)
    if component_name is not None:
        return f'component {component_name}'
    return f'hook {getattr(function, "__name__", "hook")}'


def gate_message(
    label: str, gate: str, subject: str, resolved: Mapping[str, object]
) -> str:
    """Say which hook or component needs which terminal setting, what the setting is now, and how to turn it on."""
    key = 'keyboard' if gate == 'keyboard_release' else gate
    setting = (
        f'{key}={"release_events"!r}' if gate == 'keyboard_release' else f'{key}=True'
    )
    return (
        f'The {label} needs {setting}, but {subject} has {key}={resolved.get(key)!r}, '
        f'so that input would never arrive. Turn it on when the canvas is created or opened: '
        f'xnano.new({setting}), xnano.open({setting}) or canvas.open({setting}).'
    )


def parse_open_settings(
    canvas: Canvas[DepsT, StateT], settings: Mapping[str, object]
) -> dict[str, object]:
    """Check the keywords of ``open()`` for ``canvas``; return the ones to apply."""
    if 'realtime' in settings:
        raise TypeError(
            'open() takes no realtime: a canvas on the screen always runs on the wall '
            'clock. Remove realtime=..., or keep the canvas off the screen with '
            'xnano.new(realtime=True).'
        )
    for name in ('deps', 'state'):
        if name in settings and getattr(canvas, f'_{name}_given'):
            raise TypeError(
                f'{name} was already given to xnano.new(), and a canvas keeps the {name} '
                f'it was created with. Remove {name}= from open().'
            )
    if 'layout' in settings and settings['layout'] != canvas._layout:
        raise TypeError(
            f'A canvas keeps the layout it was created with, {canvas._layout!r}. Create it '
            f'with xnano.new(layout={settings["layout"]!r}) instead, or remove layout= '
            f'from open().'
        )
    own = {'fps', 'bpm', 'effects', 'deps', 'state', 'layout', 'edges'}
    gates, appearance = split_settings(
        'open', {name: value for name, value in settings.items() if name not in own}
    )
    parsed: dict[str, object] = {
        name: value for name, value in settings.items() if name in own
    }
    if 'fps' in parsed:
        parsed['fps'] = _check_fps(parsed['fps'])
    if 'bpm' in parsed:
        parsed['bpm'] = _check_bpm(parsed['bpm'])
    if 'edges' in parsed:
        parsed['edges'] = check_edges(parsed['edges'])
    if 'effects' in parsed:
        parsed['effects'] = [
            normalize_effect(specification, 'writable')
            for specification in effect_sequence(parsed['effects'], 'writable')
        ]
    if appearance:
        # A bad value is reported here, before the screen is claimed.
        _check_appearance(appearance)
    parsed['gates'] = gates
    parsed['appearance'] = appearance
    return parsed


def gates_for_screen(
    canvas: Canvas[DepsT, StateT], gates: Mapping[str, object]
) -> dict[str, object]:
    """The value of every terminal setting on the screen, with the inferred ones turned on by hooks."""
    needed: dict[str, list[str]] = {}
    # A hook joins its canvas on the canvas's loop, so the hooks are listed there, after
    # every hook registered before this call has joined.
    for handle in canvas._host.call(canvas._hook_handles):
        for gate in handle._needed_gates():
            needed.setdefault(gate, []).append(hook_label(handle.function))
    resolved = {name: gates.get(name, default) for name, default in GATE_DEFAULTS.items()}
    for gate, names in needed.items():
        if gate in gates or gate not in INFERRED_GATES:
            if not is_gate_on(gate, resolved):
                raise TerminalError(gate_message(names[0], gate, 'this canvas', resolved))
        elif gate in INFERRED_GATES:
            resolved[gate] = True
    return resolved
