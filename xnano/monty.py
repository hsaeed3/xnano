"""
xnano.monty

Run untrusted Python, such as code written by a language model, against a canvas.

The code runs in [Monty](https://github.com/pydantic/monty), a sandboxed Python
interpreter, which cannot reach the files, the network or this program. Inside it, the code
imports a small ``xnano`` module that draws on the canvas you give it: ``canvas.write``,
``canvas.play``, ``canvas.step`` and ``draw``, with ``canvas`` and ``draw`` already defined.
[`SANDBOX_STUBS`][xnano.monty.SANDBOX_STUBS] is that module's whole interface, and every
program is type-checked against it before it runs.

This module needs the optional ``pydantic-monty`` package: ``pip install "xnano[monty]"``.
"""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Mapping
from types import ModuleType
from typing import TYPE_CHECKING, Literal, cast

from xnano._internal._optional import require
from xnano.art._worlds import Art, draw
from xnano.canvas import Canvas
from xnano.placement import Placement

if TYPE_CHECKING:
    from pydantic_monty import ResourceLimits
    from xnano_audio import InstrumentName

    from xnano.types import ColorValue, PlayOptions

__all__ = ['DEFAULT_LIMITS', 'SANDBOX_STUBS', 'Sandbox', 'run']

DEFAULT_LIMITS: ResourceLimits = {
    'max_feed_duration_secs': 10.0,
    'max_memory': 256 * 1024 * 1024,
    'max_suspensions': 1_000_000,
}
"""
The limits a sandbox starts from: ten seconds of running code per
[`Sandbox.run`][xnano.monty.Sandbox.run], 256 MiB of memory, and a million calls to the
canvas over the sandbox's life. Time spent waiting in ``time.sleep`` or inside the canvas does
not count toward the ten seconds.
"""

SANDBOX_STUBS = '''\
"""Draw on the canvas of the program that runs this code."""

from typing import Literal

Color = str | tuple[int, int, int]
"""A color name such as 'red', a '#rrggbb' string, or a (red, green, blue) tuple."""

Position = int | str
"""A number of cells, a percentage such as '50%', or 'left', 'center', 'right', 'top' or
'bottom'."""


class Time:
    """The canvas's clock."""

    @property
    def elapsed(self) -> float:
        """Seconds since the canvas started."""

    @property
    def frame(self) -> int:
        """How many frames the clock has counted."""


class Art:
    """Pixel art made with draw(). Show it with canvas.write(art)."""

    @property
    def width(self) -> int:
        """The width in pixels."""

    @property
    def height(self) -> int:
        """The height in pixels. A pixel is half a cell tall."""


class Placement:
    """
    Something written on the canvas.

    Read its attributes, and change it with its methods: assigning to an attribute is
    refused.
    """

    @property
    def x(self) -> int:
        """The column of the left edge."""

    @property
    def y(self) -> int:
        """The row of the top edge."""

    @property
    def width(self) -> int:
        """The width in cells."""

    @property
    def height(self) -> int:
        """The height in cells."""

    @property
    def text(self) -> str:
        """The text shown, line by line."""

    def move(self, x: int = 0, y: int = 0) -> None:
        """Move by a number of cells; negative numbers move left and up."""

    def set_position(self, x: Position | None = None, y: Position | None = None) -> None:
        """Move the left edge to x and the top edge to y; None keeps that one."""

    def set_text(self, text: str) -> None:
        """Show new text; the placement grows or shrinks to fit it."""

    def remove(self) -> None:
        """Take it off the canvas. Removing twice is harmless."""


class Canvas:
    """The canvas this code draws on."""

    @property
    def width(self) -> int:
        """The width in cells."""

    @property
    def height(self) -> int:
        """The height in cells."""

    @property
    def time(self) -> Time:
        """The canvas's clock."""

    def write(
        self,
        content: str | list[str] | Art,
        *,
        x: Position | None = None,
        y: Position | None = None,
        width: Position | None = None,
        height: Position | None = None,
        layer: int = 0,
        foreground: Color | None = None,
        background: Color | None = None,
        bold: bool = False,
        dim: bool = False,
        italic: bool = False,
        underline: bool = False,
        border: Literal['plain', 'rounded', 'double', 'thick'] | bool | None = None,
        title: str | None = None,
    ) -> Placement:
        """
        Put text (or a list of lines) or pixel art on the canvas, at the top-left corner
        unless x and y say otherwise. A higher layer is drawn over a lower one.
        """

    def step(self, delta_seconds: float | None = None) -> None:
        """
        Move the canvas's clock by delta_seconds (one frame when None) and draw a frame.

        A canvas on a screen moves by itself: wait with time.sleep(seconds) instead.
        """

    def play(
        self,
        music: str,
        *,
        instrument: str | None = None,
        beats: float | None = None,
        volume: float | None = None,
    ) -> None:
        """
        Play a note such as 'C4', a frequency such as '440hz', or melody text such as
        'C4 E4 G4:2 rest C5+E5'. Needs the program to have xnano's audio installed.
        """


canvas: Canvas
"""The canvas this code draws on."""


def draw(
    rows: str | list[str],
    palette: str | dict[str, Color],
    *,
    background: Color | None = None,
) -> Art:
    """
    Build pixel art, one character per pixel, without drawing it.

    rows is a multi-line string or a list of rows of equal length. palette says what each
    character means, as a dict or a string such as 'R=#e03040 G=green'; a character it does
    not name, such as '.', is a transparent pixel.
    """
'''
"""
The ``.pyi`` source of the ``xnano`` module that sandboxed code imports.

Every program is type-checked against it before it runs. Give it to whoever writes the
code, such as a language model, so that it knows what it can call.
"""

_PRELUDE = 'from xnano import canvas, draw'
_WRITTEN_CONTENT = 'text, a list of lines, or pixel art from draw()'


class _SandboxPlacement:
    """What sandboxed code holds for something written on the canvas."""

    def __init__(self, placement: Placement[object, object]) -> None:
        """
        Stand for a placement inside the sandbox.

        Args:
            placement: The placement that sandboxed code reads and changes.
        """
        self.placement = placement

    @property
    def x(self) -> int:
        return self.placement.x

    @property
    def y(self) -> int:
        return self.placement.y

    @property
    def width(self) -> int:
        return self.placement.width

    @property
    def height(self) -> int:
        return self.placement.height

    @property
    def text(self) -> str:
        return self.placement.text

    def move(self, x: int = 0, y: int = 0) -> None:
        self.placement.move(x=x, y=y)

    def set_position(
        self, x: int | str | None = None, y: int | str | None = None
    ) -> None:
        if x is not None:
            self.placement.x = x
        if y is not None:
            self.placement.y = y

    def set_text(self, text: str) -> None:
        self.placement.text = text

    def remove(self) -> None:
        self.placement.remove()


class _SandboxCanvas:
    """What sandboxed code holds for the canvas it draws on."""

    def __init__(self, canvas: Canvas[object, object], monty: ModuleType) -> None:
        """
        Stand for a canvas inside the sandbox.

        Args:
            canvas: The canvas that sandboxed code draws on.
            monty: The ``pydantic_monty`` module, which wraps what crosses into the sandbox.
        """
        self.canvas = canvas
        self._monty = monty

    @property
    def width(self) -> int:
        return self.canvas.width

    @property
    def height(self) -> int:
        return self.canvas.height

    @property
    def time(self) -> object:
        return self._monty.ClassInstance(
            self.canvas.time, lazy_attrs={'elapsed', 'frame'}
        )

    def write(
        self,
        content: object,
        *,
        x: int | str | None = None,
        y: int | str | None = None,
        width: int | str | None = None,
        height: int | str | None = None,
        layer: int = 0,
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
        bold: bool = False,
        dim: bool = False,
        italic: bool = False,
        underline: bool = False,
        border: Literal['plain', 'rounded', 'double', 'thick'] | bool | None = None,
        title: str | None = None,
    ) -> object:
        written: str | Art | list[str]
        if isinstance(content, (str, Art)):
            written = content
        elif isinstance(content, (list, tuple)) and all(
            isinstance(line, str) for line in content
        ):
            written = [str(line) for line in content]
        else:
            raise TypeError(
                f'canvas.write() takes {_WRITTEN_CONTENT}, but got '
                f'{type(content).__name__}. Pass a string such as "hello", or build pixel '
                f'art with draw(rows, palette) and write that.'
            )
        placement = self.canvas.write(
            written,
            x=x,
            y=y,
            width=width,
            height=height,
            layer=layer,
            foreground=foreground,
            background=background,
            bold=bold,
            dim=dim,
            italic=italic,
            underline=underline,
            border=border,
            title=title,
        )
        return _expose_placement(placement, self._monty)

    def step(self, delta_seconds: float | None = None) -> None:
        if self.canvas.time.is_realtime:
            raise RuntimeError(
                'canvas.step() moves the clock of a canvas that is not on a screen, but '
                'this canvas is on a screen and its clock moves by itself. Wait with '
                'time.sleep(seconds) instead; what you wrote is drawn while you wait.'
            )
        self.canvas.step(delta_seconds=delta_seconds)

    def play(
        self,
        music: str,
        *,
        instrument: str | None = None,
        beats: float | None = None,
        volume: float | None = None,
    ) -> None:
        if not isinstance(music, str):
            raise TypeError(
                f'canvas.play() takes music as text, but got {type(music).__name__}. '
                f'Pass a note such as "C4" or melody text such as "C4 E4 G4:2".'
            )
        options: PlayOptions = {}
        if instrument is not None:
            options['instrument'] = cast('InstrumentName', instrument)
        if beats is not None:
            options['beats'] = beats
        if volume is not None:
            options['volume'] = volume
        self.canvas.play(music, **options)


def _expose_placement(placement: Placement[object, object], monty: ModuleType) -> object:
    """Wrap a placement so that sandboxed code can read it and call its methods."""
    return monty.ClassInstance(
        _SandboxPlacement(placement),
        lazy_attrs={'x', 'y', 'width', 'height', 'text'},
        allowed_methods={'move', 'set_position', 'set_text', 'remove'},
    )


def _sandbox_module(canvas: Canvas[object, object], monty: ModuleType) -> object:
    """The ``xnano`` module that sandboxed code imports."""

    def draw_art(
        rows: str | list[str],
        palette: str | Mapping[str, ColorValue],
        *,
        background: ColorValue | None = None,
    ) -> object:
        if isinstance(rows, str) and '\n' not in rows:
            # A single row is a picture, never the name of art registered by this program.
            rows = [rows]
        art = draw(rows, palette, background=background)
        return monty.ClassInstance(art, lazy_attrs={'width', 'height'})

    sandbox_canvas = monty.ClassInstance(
        _SandboxCanvas(canvas, monty),
        lazy_attrs={'width', 'height', 'time'},
        allowed_methods={'write', 'step', 'play'},
    )
    return monty.ExternalModule(
        {'canvas': sandbox_canvas, 'draw': draw_art}, stubs=SANDBOX_STUBS
    )


def _host_value(value: object) -> object:
    """Turn what sandboxed code returned into the xnano objects it stands for."""
    if isinstance(value, _SandboxPlacement):
        return value.placement
    if isinstance(value, _SandboxCanvas):
        return value.canvas
    if isinstance(value, list):
        return [_host_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_host_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _host_value(item) for key, item in value.items()}
    return value


def _print(stream: Literal['stdout', 'stderr'], text: str) -> None:
    """Print what sandboxed code prints, where this program's own prints go."""
    (sys.stdout if stream == 'stdout' else sys.stderr).write(text)


class Sandbox:
    """
    A Monty sandbox that draws on a canvas and remembers what each program defined.

    Every [`run`][xnano.monty.Sandbox.run] continues the same session: names, functions and
    placements that one program made are there for the next, so a language model can build a
    picture over several turns. For a single program, [`run`][xnano.monty.run] is shorter.
    The sandbox starts a Monty worker process when it is created; close it, or use it in a
    ``with`` block, to stop that process.

    Args:
        canvas: The canvas the code draws on, from [`new`][xnano.new] or
            [`open`][xnano.open].
        limits: Monty's ``ResourceLimits``. The keys you give replace those of
            [`DEFAULT_LIMITS`][xnano.monty.DEFAULT_LIMITS]; a key set to ``None`` turns that
            limit off.

    Attributes:
        canvas: The canvas the code draws on.

    Raises:
        ImportError: ``pydantic-monty`` is not installed. Install it with
            ``pip install "xnano[monty]"``.
        TypeError: ``canvas`` is not a canvas.

    Examples:
        ```python
        import xnano
        from xnano.monty import Sandbox

        with xnano.new(width=12, height=2) as canvas, Sandbox(canvas) as sandbox:
            sandbox.run("label = canvas.write('hello')")
            sandbox.run("label.set_text('goodbye')")
            assert canvas.render().splitlines()[0] == 'goodbye'
        ```
    """

    def __init__(
        self, canvas: Canvas[object, object], *, limits: ResourceLimits | None = None
    ) -> None:
        """
        Start a Monty worker process whose code draws on ``canvas``.

        Args:
            canvas: The canvas the code draws on.
            limits: Monty's ``ResourceLimits``, over
                [`DEFAULT_LIMITS`][xnano.monty.DEFAULT_LIMITS].
        """
        monty = require('monty', needed_for='xnano.monty')
        if not isinstance(canvas, Canvas):
            raise TypeError(
                f'Sandbox() draws on a canvas, but got {type(canvas).__name__}. Create one '
                f'with xnano.new(width=40, height=10) or xnano.open() and pass it.'
            )
        self.canvas = canvas
        self._resources = contextlib.ExitStack()
        try:
            pool = self._resources.enter_context(
                monty.Monty(min_processes=1, max_processes=1)
            )
            self._session = self._resources.enter_context(
                pool.checkout(
                    script_name='sandbox.py',
                    limits={**DEFAULT_LIMITS, **(limits or {})},
                    type_check=True,
                    external_modules={'xnano': _sandbox_module(canvas, monty)},
                )
            )
            self._session.feed_run(_PRELUDE)
        except BaseException:
            self._resources.close()
            raise

    def run(self, code: str) -> object:
        """
        Type-check and run a program in the sandbox, and return its last expression.

        ``canvas`` and ``draw`` are defined, and ``import xnano`` gives the same module; see
        [`SANDBOX_STUBS`][xnano.monty.SANDBOX_STUBS]. What the program prints goes where
        this program's prints go, which a canvas on the screen holds back. A placement the
        program returns comes back as the [`Placement`][xnano.placement.Placement] itself.

        Args:
            code: The Python source to run.

        Returns:
            The value of the program's last line when it is an expression, else ``None``.

        Raises:
            pydantic_monty.MontyTypingError: The program does not fit the sandbox's
                interface, such as an unknown keyword or an assignment to a placement's
                attribute. Nothing ran, and the message points at the line.
            pydantic_monty.MontySyntaxError: The program is not valid Python.
            pydantic_monty.MontyRuntimeError: The program raised an error or went over a
                limit. Its ``display()`` is the sandbox's traceback. The sandbox stays usable.
            TypeError: ``code`` is not a string.
        """
        if not isinstance(code, str):
            raise TypeError(
                f'Sandbox.run() takes the program as a string, but got '
                f'{type(code).__name__}. Pass Python source such as "canvas.write(\'hi\')".'
            )
        return _host_value(self._session.feed_run(code, print_callback=_print))

    def close(self) -> None:
        """Stop the sandbox's worker process. Closing twice is harmless."""
        self._resources.close()

    def __enter__(self) -> Sandbox:
        return self

    def __exit__(self, *exception: object) -> None:
        self.close()


def run(
    code: str,
    canvas: Canvas[object, object],
    *,
    limits: ResourceLimits | None = None,
) -> object:
    """
    Type-check and run one program in a new Monty sandbox that draws on ``canvas``.

    This is ``Sandbox(canvas, limits=limits).run(code)`` with the sandbox closed afterwards;
    see [`Sandbox`][xnano.monty.Sandbox] to run several programs in one session.

    Args:
        code: The Python source to run. ``canvas`` and ``draw`` are defined in it.
        canvas: The canvas the code draws on.
        limits: Monty's ``ResourceLimits``, over [`DEFAULT_LIMITS`][xnano.monty.DEFAULT_LIMITS].

    Returns:
        The value of the program's last line when it is an expression, else ``None``.

    Raises:
        ImportError: ``pydantic-monty`` is not installed. Install it with
            ``pip install "xnano[monty]"``.
        pydantic_monty.MontyError: The program did not type-check, was not valid Python,
            raised an error or went over a limit; see
            [`Sandbox.run`][xnano.monty.Sandbox.run].

    Examples:
        ```python
        import xnano
        import xnano.monty

        with xnano.new(width=16, height=3) as canvas:
            xnano.monty.run(
                "canvas.write('sandboxed', x='center', y=1, foreground='green')", canvas
            )
            assert canvas.render().splitlines()[1] == '   sandboxed'
        ```
    """
    with Sandbox(canvas, limits=limits) as sandbox:
        return sandbox.run(code)
