"""
xnano.ai.capabilities

Capabilities for any pydantic-ai ``Agent``: tools that let it see and change a canvas, draw
pixel art and play melodies.

Give them to an agent and it *is* the agent of a terminal program: no session class is needed.

```python
from pydantic_ai import Agent
from xnano.ai.capabilities import ArtCapability, CanvasCapability, MusicCapability

agent = Agent(
    'openrouter:anthropic/claude-sonnet-5-5',
    capabilities=[CanvasCapability(terminal, keyboard=True), ArtCapability(), MusicCapability()],
)
```

Every tool checks its arguments the way the task models check their answers: a fault goes back
to the agent with what is wrong, so it can fix it in the same run. The tools run on the event
loop of the agent's run: run the agent with ``run_sync`` or ``await agent.run(...)`` from the
thread of a canvas from ``new()``; a canvas on the screen can be used from any thread.

Examples:
    ```python
    import xnano
    from pydantic_ai import Agent
    from xnano.ai.capabilities import CanvasCapability
    from xnano.ai.testing import scripted_model

    script = scripted_model(
        ('write_component', {'program': "canvas.screen.write('hello')", 'width': 8, 'height': 1}),
        'Done.',
    )
    with xnano.new(width=20, height=3) as canvas:
        agent = Agent(script.model, capabilities=[CanvasCapability(canvas)])
        assert agent.run_sync('Say hello.').output == 'Done.'
        assert canvas.screen.render().splitlines()[0] == 'hello'
    ```
"""

from __future__ import annotations

import asyncio
import dataclasses
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal

from pydantic_ai import ModelRetry
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import FunctionToolset

from xnano import symbols
from xnano.ai._generations import _Attempts
from xnano.ai._observe import _ruled
from xnano.ai.models.art import ArtText, _Checker, _Color, _EditChecker, _Run
from xnano.ai.models.components import _run_component
from xnano.art import Art
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.layout._placement import Placement

__all__ = ['ArtCapability', 'CanvasCapability', 'MusicCapability']

_SETTLE_SECONDS = 0.5
"""The longest an action waits for a canvas on the screen to draw what it changed."""


def _refusal(error: Exception) -> ModelRetry:
    """A fault of a tool's arguments, sent back to the agent to fix."""
    return ModelRetry(str(error))


@dataclasses.dataclass
class CanvasCapability(AbstractCapability[Any]):
    """
    Let an agent see a canvas and change it: write widgets and art, and, when allowed, press
    keys and use the mouse.

    The agent's tools are ``observe`` (the canvas as text, under a column ruler with row
    numbers), ``write_component`` (a small program that draws a widget, written on the next
    free line unless it says where), ``update_component`` and ``show_art``. With
    ``keyboard=True`` it also has ``press_key``, ``type_text`` and ``paste``; with
    ``mouse=True``, ``click``, ``drag`` and ``scroll`` at cell coordinates. Every action lets
    the canvas draw what changed and returns what the canvas then shows. The agent cannot
    press ``ctrl+c`` or a key that ``run(quit_on=...)`` ends the program with.

    Args:
        canvas: The canvas the agent sees and changes.
        keyboard: Whether the agent can press keys, type and paste.
        mouse: Whether the agent can click, drag and scroll.

    Attributes:
        canvas: The canvas the agent sees and changes.
        keyboard: Whether the agent can press keys, type and paste.
        mouse: Whether the agent can click, drag and scroll.
        components: What the agent wrote, by the name it gave.
    """

    canvas: Canvas[Any, Any]
    keyboard: bool = False
    mouse: bool = False
    components: dict[str, Placement[Any, Any]] = dataclasses.field(default_factory=dict)
    _repairs: list[str] = dataclasses.field(default_factory=list, repr=False)

    @classmethod
    def get_serialization_name(cls) -> str | None:
        """A canvas cannot be written in an agent spec, so this capability has no name there."""
        return None

    def get_instructions(self) -> str:
        """Tell the agent what it can see and do."""
        size = self.canvas.screen.size
        parts = [
            f'You can see and change a terminal canvas of {size.width} by {size.height} '
            f'cells. Call observe to see it. write_component runs a small Python program '
            f'that draws a widget with canvas.screen.write(text, x=..., y=..., border=...); '
            f'show_art shows pixel art.'
        ]
        if self.keyboard:
            parts.append(
                'press_key, type_text and paste act as the person at the keyboard.'
            )
        if self.mouse:
            parts.append('click, drag and scroll act as the mouse, at cell coordinates.')
        return ' '.join(parts)

    def get_toolset(self) -> FunctionToolset[Any]:
        """The tools of the canvas."""
        tools: list[Any] = [
            self.observe,
            self.write_component,
            self.update_component,
            self.show_art,
        ]
        if self.keyboard:
            tools.extend((self.press_key, self.type_text, self.paste))
        if self.mouse:
            tools.extend((self.click, self.drag, self.scroll))
        return FunctionToolset(tools)

    # -- seeing -------------------------------------------------------------------------

    async def observe(self) -> str:
        """See the canvas: its text under a column ruler, with the row numbers."""
        screen = self.canvas.screen
        return _ruled(screen.render(), screen.width)

    async def _settled(self) -> str:
        """Let the canvas draw what an action changed, then see it, with any fixes made."""
        canvas = self.canvas
        if canvas.clock.is_realtime:
            output = canvas.screen.output
            revision = output.revision
            deadline = time.monotonic() + _SETTLE_SECONDS
            while output.revision == revision and time.monotonic() < deadline:
                await asyncio.sleep(0.01)
        else:
            canvas.deliver_events()
            canvas.clock.step()
        observation = await self.observe()
        repairs, self._repairs[:] = list(self._repairs), []
        if not repairs:
            return observation
        fixed = '\n'.join(f'- {repair}' for repair in repairs)
        return f'Fixed in the program:\n{fixed}\n\n{observation}'

    # -- writing ------------------------------------------------------------------------

    async def write_component(
        self,
        program: str,
        width: int,
        height: int,
        name: str | None = None,
        x: int | None = None,
        y: int | None = None,
    ) -> str:
        """
        Draw a widget: a Python program that writes on a canvas of width by height cells.

        Args:
            program: The program; it draws with canvas.screen.write(...).
            width: The width of the widget, in cells.
            height: The height of the widget, in rows.
            name: A name to change it by later with update_component.
            x: The column of its left edge; on the next free line when x and y are left out.
            y: The row of its top edge.
        """
        component = self._component(program, width, height)
        placement = self.canvas.screen.write(
            component, x='next' if x is None else x, y='next' if y is None else y
        )
        if name is not None:
            previous = self.components.pop(name, None)
            if previous is not None:
                previous.remove()
            self.components[name] = placement
        return await self._settled()

    async def update_component(self, name: str, program: str) -> str:
        """
        Draw a widget written with write_component again, with a new program, in its place.

        Args:
            name: The name it was written with.
            program: The new program.
        """
        placement = self.components.get(name)
        if placement is None or placement._removed:
            known = ', '.join(sorted(self.components)) or 'none yet'
            raise ModelRetry(
                f'There is no widget called {name!r}. The widgets are: {known}. Write it with '
                f'write_component first.'
            )
        component = self._component(program, placement.width, placement.height)
        x, y = placement.x, placement.y
        placement.remove()
        self.components[name] = self.canvas.screen.write(component, x=x, y=y)
        return await self._settled()

    def _component(self, program: str, width: int, height: int) -> Any:
        screen = self.canvas.screen
        if not (1 <= width <= screen.width and 1 <= height <= screen.height):
            raise ModelRetry(
                f'A widget of {width} by {height} does not fit the canvas, which is '
                f'{screen.width} by {screen.height}. Make it smaller.'
            )
        component, problems = _run_component('', program, width, height, self._repairs)
        if problems:
            listed = '\n'.join(f'- {problem}' for problem in problems)
            raise ModelRetry(
                f'The program could not be used:\n{listed}\nSend it again, fixed.'
            )
        return component

    async def show_art(
        self,
        name: str,
        palette: list[_Color],
        width: int,
        height: int,
        program: str,
        x: int | None = None,
        y: int | None = None,
    ) -> str:
        """
        Show pixel art: a palette of letters with roles, a size, and a program that paints them.

        The program paints W by H transparent pixels with pixel(x, y, letter), rect(x, y,
        width, height, letter), ellipse(x, y, width, height, letter), line(x1, y1, x2, y2,
        letter), polygon(points, letter), fill(x, y, letter), mirror_x(), mirror_y() and
        outline(letter). A pixel is half a cell tall. The art is kept under the name, so the
        program finds it with xnano.symbols.lookup(name).

        Args:
            name: The name to keep the art under.
            palette: Each letter, what its colour is for, and the colour as #rrggbb.
            width: The width in pixels.
            height: The height in pixels.
            program: The program that paints the palette's letters.
            x: The column of its left edge; on the next free line when x and y are left out.
            y: The row of its top edge.
        """
        art = _checked_art(palette, width, height, program, name=name)
        self.canvas.screen.write(
            art, x='next' if x is None else x, y='next' if y is None else y
        )
        return await self._settled()

    # -- the keyboard -------------------------------------------------------------------

    async def press_key(self, key: str) -> str:
        """
        Press a key, such as 'enter', 'tab', 'a' or a binding such as 'ctrl+s'.

        Args:
            key: The key, or the key binding.
        """
        normalized = key.strip().lower()
        if normalized == 'ctrl+c' or normalized in self.canvas._quit_keys:
            raise ModelRetry(
                f'{key!r} ends the program, so it cannot be pressed from here. Press another '
                f'key.'
            )
        try:
            self.canvas.keyboard.press(key)
        except (TypeError, ValueError) as error:
            raise _refusal(error) from None
        return await self._settled()

    async def type_text(self, text: str) -> str:
        """
        Type text, one key per character, as the person at the keyboard would.

        Args:
            text: The text to type.
        """
        for character in text:
            name = {' ': 'space', '\n': 'enter', '\t': 'tab'}.get(character, character)
            try:
                self.canvas.keyboard.press(name)
            except (TypeError, ValueError) as error:
                raise _refusal(error) from None
        return await self._settled()

    async def paste(self, text: str) -> str:
        """
        Paste text, which arrives whole, as a paste from the clipboard does.

        Args:
            text: The text to paste.
        """
        self.canvas.keyboard.paste(text)
        return await self._settled()

    # -- the mouse ----------------------------------------------------------------------

    async def click(
        self, x: int, y: int, button: Literal['left', 'right', 'middle'] = 'left'
    ) -> str:
        """
        Click a cell.

        Args:
            x: The column, from 0 at the left.
            y: The row, from 0 at the top.
            button: The mouse button.
        """
        self._check_cell(x, y)
        self.canvas.mouse.click(button, x=x, y=y)
        return await self._settled()

    async def drag(self, from_x: int, from_y: int, to_x: int, to_y: int) -> str:
        """
        Drag with the left button held, from one cell to another.

        Args:
            from_x: The column to start at.
            from_y: The row to start at.
            to_x: The column to end at.
            to_y: The row to end at.
        """
        self._check_cell(from_x, from_y)
        self._check_cell(to_x, to_y)
        with self.canvas.mouse.press('left', x=from_x, y=from_y) as held:
            held.move(to_x - from_x, to_y - from_y)
        return await self._settled()

    async def scroll(self, x: int, y: int, rows: int) -> str:
        """
        Turn the mouse wheel over a cell.

        Args:
            x: The column of the pointer.
            y: The row of the pointer.
            rows: How far: a positive number scrolls down, a negative one up.
        """
        self._check_cell(x, y)
        mouse = self.canvas.mouse
        mouse.pointer = (x, y)
        mouse.scroll.turn(y=rows)
        return await self._settled()

    def _check_cell(self, x: int, y: int) -> None:
        screen = self.canvas.screen
        if not (0 <= x < screen.width and 0 <= y < screen.height):
            raise ModelRetry(
                f'The cell ({x}, {y}) is outside the canvas, which is {screen.width} by '
                f'{screen.height}: x is from 0 to {screen.width - 1} and y from 0 to '
                f'{screen.height - 1}.'
            )


@dataclasses.dataclass
class ArtCapability(AbstractCapability[Any]):
    """
    Let an agent draw and edit pixel art, kept by name in [`symbols`][xnano.symbols].

    The agent's tools are ``draw_art`` (a palette of letters with roles, a size, and a short
    program of drawing calls that paints the letters) and ``edit_art`` (runs of letters that
    change pixels of a piece it drew).
    The program finds each piece with ``xnano.symbols.lookup(name, kind=xnano.art.Art)`` and
    writes it where it wants.

    Args:
        max_colors: The most colours a piece may have.

    Attributes:
        max_colors: The most colours a piece may have.
    """

    max_colors: int = 16

    @classmethod
    def get_serialization_name(cls) -> str | None:
        """This capability has no name in an agent spec."""
        return None

    def get_instructions(self) -> str:
        """Tell the agent how to draw."""
        return (
            'draw_art draws pixel art: name the colours by role (outline, base, shadow, '
            'highlight, accent, skin, detail) under single lowercase letters, then write a '
            'short program that paints them on W by H transparent pixels with pixel(x, y, '
            'letter), rect(x, y, width, height, letter), ellipse(x, y, width, height, '
            'letter), line(x1, y1, x2, y2, letter), polygon(points, letter), fill(x, y, '
            'letter), mirror_x(), mirror_y() and outline(letter). Light comes from the top '
            f'left; use one outline colour and at most {self.max_colors} colours. edit_art '
            'changes pixels of a piece already drawn.'
        )

    def get_toolset(self) -> FunctionToolset[Any]:
        """The tools of pixel art."""
        return FunctionToolset([self.draw_art, self.edit_art])

    async def draw_art(
        self, name: str, palette: list[_Color], width: int, height: int, program: str
    ) -> str:
        """
        Draw pixel art and keep it under a name.

        Args:
            name: The name to keep the art under.
            palette: Each letter, what its colour is for, and the colour as #rrggbb.
            width: The width in pixels.
            height: The height in pixels.
            program: The program that paints the palette's letters onto W by H pixels.
        """
        art = _checked_art(
            palette, width, height, program, name=name, max_colors=self.max_colors
        )
        return f'Drew {name!r}, {art.width} by {art.height} pixels.'

    async def edit_art(
        self, name: str, runs: list[_Run], new_colors: list[_Color]
    ) -> str:
        """
        Change pixels of a piece drawn with draw_art: runs of letters along rows.

        Args:
            name: The name of the piece.
            runs: Each run's row, its first column, and its letters.
            new_colors: Colours the runs use that the palette does not have yet.
        """
        try:
            art = symbols.lookup(name, kind=Art)
        except (KeyError, LookupError, TypeError, ValueError) as error:
            raise _refusal(error) from None
        text = ArtText.from_art(art)
        checker = _EditChecker(_Attempts(), text, frozenset(), True, 1.0, 'patch')
        edited = checker.patch(runs, new_colors)
        edited.to_art(symbol=name)
        return f'Changed {name!r}.\n{edited.labelled()}'


@dataclasses.dataclass
class MusicCapability(AbstractCapability[Any]):
    """
    Let an agent play melodies on a canvas's speaker, and keep them by name.

    The agent's tools are ``play_melody`` and ``compose_melody``, both in xnano's melody text
    (``'C4 E4 G4:2 | rest C5+E5+G5'``). A melody kept by name plays with ``play(name)``. Needs
    the ``audio`` extra.

    Args:
        canvas: The canvas whose speaker plays; ``None`` plays with [`play`][xnano.play].

    Attributes:
        canvas: The canvas whose speaker plays.
    """

    canvas: Canvas[Any, Any] | None = None

    @classmethod
    def get_serialization_name(cls) -> str | None:
        """This capability has no name in an agent spec."""
        return None

    def get_instructions(self) -> str:
        """Tell the agent how to write melodies."""
        from xnano.ai.models.music import _GRAMMAR

        return f'play_melody plays a melody and compose_melody keeps one by name.\n{_GRAMMAR}'

    def get_toolset(self) -> FunctionToolset[Any]:
        """The tools of music."""
        return FunctionToolset([self.play_melody, self.compose_melody])

    async def play_melody(self, text: str, bpm: float = 120.0) -> str:
        """
        Play a melody now.

        Args:
            text: The melody text.
            bpm: The tempo, in beats per minute.
        """
        melody = _checked_melody(text, bpm, symbol=None)
        if self.canvas is None:
            from xnano.audio import play

            play(melody)
        else:
            self.canvas.speaker.play(melody)
        return f'Playing {melody.length_beats:g} beats.'

    async def compose_melody(self, name: str, text: str, bpm: float = 120.0) -> str:
        """
        Keep a melody under a name, so the program plays it with play(name).

        Args:
            name: The name to keep the melody under.
            text: The melody text.
            bpm: The tempo, in beats per minute.
        """
        melody = _checked_melody(text, bpm, symbol=name)
        return f'Kept {name!r}, {melody.length_beats:g} beats.'


def _checked_art(
    palette: Sequence[_Color],
    width: int,
    height: int,
    program: str,
    *,
    name: str,
    max_colors: int = 25,
) -> Art:
    """Pixel art from a tool's arguments, kept under ``name``, or the fault sent back."""
    checker = _Checker(_Attempts(), (1, 64), (1, 64), max_colors)
    text = checker.program(palette, width, height, program)
    try:
        return text.to_art(symbol=name)
    except ValueError as error:
        raise _refusal(error) from None


def _checked_melody(text: str, bpm: float, *, symbol: str | None) -> Any:
    """A melody from a tool's arguments, or the fault sent back."""
    from xnano.audio import Melody

    try:
        return Melody(text, bpm=bpm, symbol=symbol)
    except (TypeError, ValueError, TerminalError) as error:
        raise _refusal(error) from None
