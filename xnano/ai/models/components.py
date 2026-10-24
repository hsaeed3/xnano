"""
xnano.ai.models.components

Widgets from a language model: a small program that draws on a canvas of its own size, run in
the sandbox of [`xnano.sandbox`][xnano.sandbox] and written like any other content.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Coroutine, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Final

from pydantic_ai import ToolOutput

from xnano.ai import assets
from xnano.ai._generations import GenerationReport, _Attempts, _generation_error
from xnano.ai._observe import _ruled, evidence_prompt, snapshot
from xnano.ai.models import TaskModel, _run_blocking
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from pydantic_ai.capabilities import AbstractCapability
    from pydantic_ai.models import KnownModelName, Model
    from pydantic_ai.settings import ModelSettings, ThinkingLevel
    from pydantic_ai.usage import UsageLimits

    from xnano.hooks._context import Context
    from xnano.layout._region import Region

__all__ = ['Component', 'ComponentModel']

_PROGRAM_SECONDS: Final = 2.0
"""The longest a component's program may run."""

_BUILT_IN_EXAMPLES: Final = (
    {
        'request': 'a status card for a server: CPU 73% and memory 41%, a bar for each',
        'width': 30,
        'height': 4,
        'program': (
            '# A rounded card with a title, and one labelled bar per line inside it.\n'
            "rows = [('CPU', 0.73), ('Memory', 0.41)]\n"
            'lines = []\n'
            'for label, share in rows:\n'
            '    filled = round(share * 10)\n'
            "    lines.append(f'{label:<7}' + '█' * filled + '░' * (10 - filled) + f' {share:.0%}')\n"
            "canvas.screen.write(lines, border='rounded', title='server')"
        ),
    },
    {
        'request': 'a main menu with three items, the second one chosen',
        'width': 24,
        'height': 4,
        'program': (
            '# A bold heading, then one line per item; the chosen item is highlighted.\n'
            "canvas.screen.write('Main menu', bold=True)\n"
            "for index, item in enumerate(['New game', 'Continue', 'Quit']):\n"
            '    chosen = index == 1\n'
            '    canvas.screen.write(\n'
            "        ('> ' if chosen else '  ') + item,\n"
            "        foreground='black' if chosen else None,\n"
            "        background='yellow' if chosen else None,\n"
            '    )'
        ),
    },
)


@dataclasses.dataclass(frozen=True, slots=True)
class Component:
    """
    A widget a model wrote: a small program that draws on a canvas of its own size.

    Write it like other content, with ``canvas.screen.write(component)``: it takes its
    ``width`` and ``height``, and a border or a title given to the write goes around it. Its
    ``code`` runs in the sandbox of [`xnano.sandbox`][xnano.sandbox], so it can only draw.

    Attributes:
        request: What was asked for.
        code: The program, in Python.
        width: The width it draws at, in cells.
        height: The height it draws at, in rows.
        text: What it draws, as text.

    Examples:
        ```python
        import xnano
        from xnano.ai.models.components import ComponentModel
        from xnano.ai.testing import scripted_model

        answer = {'layout': 'One bold line.', 'program': "canvas.screen.write('Ready', bold=True)"}
        components = ComponentModel(scripted_model(answer).model)
        badge = components.generate('a ready badge', width=8, height=1)
        assert badge.text == 'Ready'
        with xnano.new(width=12, height=3) as canvas:
            canvas.screen.write(badge, border='rounded')
            assert canvas.screen.render().splitlines()[1] == '│Ready   │'
        ```
    """

    request: str
    code: str
    width: int
    height: int
    text: str
    _cells: Region[int] = dataclasses.field(compare=False, repr=False)

    def __xnano_write__(self, context: Context[object, object]) -> Region[int]:
        """The cells the program drew."""
        return self._cells


class ComponentModel(TaskModel):
    """
    Generate widgets: a status card, a menu, a table, as a small program that draws them.

    The model is given the drawing API of the sandbox and worked examples, each with what it
    draws, and writes a program at the size asked for. The program is run in the sandbox of
    [`xnano.sandbox`][xnano.sandbox] as it arrives. What can be fixed safely is fixed and reported
    in ``last_generation.notes``: a near-miss border or colour name, a keyword the API does not
    take, a cell outside the canvas, a line too long for it. An error, something else drawn
    outside the size, or nothing drawn at all goes back to the model with what it drew so far,
    under a column ruler. When the ``'component-examples'`` library of [`xnano.ai.assets`][xnano.ai.assets]
    is installed, the examples closest to each request are shown too.

    Args:
        model: The language model to ask.
        max_width: The widest component a call may ask for, in cells.
        max_height: The tallest component a call may ask for, in rows.
        instructions: What the model is told before every request.
        model_settings: pydantic-ai settings for every request.
        capabilities: pydantic-ai capabilities for the agent.
        retries: How many times a program that fails is sent back.
        usage_limits: Limits on the requests and tokens of one call.
        thinking: Whether the model reasons before answering. ``None``, the default, leaves
            that to the model; ``False`` turns it off where the model allows it, and some
            models cannot turn it off.
        cache: Whether the unchanging start of every prompt is cached by the provider.

    Attributes:
        last_generation: How the last call went, or ``None`` before the first.
    """

    def __init__(
        self,
        model: Model | KnownModelName | str | None = None,
        *,
        max_width: int = 48,
        max_height: int = 12,
        instructions: str | None = None,
        model_settings: ModelSettings | None = None,
        capabilities: Sequence[AbstractCapability[Any]] = (),
        retries: int = 2,
        usage_limits: UsageLimits | None = None,
        thinking: ThinkingLevel | None = None,
        cache: bool = True,
    ) -> None:
        """
        Create the component model; nothing is sent until the first call.

        Raises:
            ValueError: ``max_width`` or ``max_height`` is not a whole number of 1 or more.
        """
        for name, value in (('max_width', max_width), ('max_height', max_height)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(
                    f'{name} must be a whole number of 1 or more, but was {value!r}.'
                )
        super().__init__(
            model,
            instructions='\n\n'.join(
                part for part in (_instructions(), instructions) if part
            ),
            model_settings=model_settings,
            capabilities=capabilities,
            retries=retries,
            usage_limits=usage_limits,
            thinking=thinking,
            cache=cache,
        )
        self.max_width = max_width
        self.max_height = max_height
        self.last_generation: GenerationReport | None = None

    def generate_async(
        self,
        request: str,
        evidence: object = None,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> Coroutine[Any, Any, Component]:
        """
        Write a widget from a description, with ``await``.

        Args:
            request: What to draw, such as ``'a status card: CPU 73%, memory 41%'``.
            evidence: What the widget shows, such as the hook's context; see
                [`Evidence`][xnano.ai.Evidence].
            width: The width in cells; ``None`` is ``max_width``.
            height: The height in rows; ``None`` is ``max_height``.

        Returns:
            A coroutine that gives the [`Component`][xnano.ai.models.components.Component].

        Raises:
            ValueError: A size is not a whole number from 1 to the model's most.
            GenerationError: No program drew the widget, even after the retries, when
                awaited.
        """
        size = (self._check_size(width, 'width'), self._check_size(height, 'height'))
        return self._write(request, snapshot(evidence), size, None)

    def generate(
        self,
        request: str,
        evidence: object = None,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> Component:
        """
        Write a widget from a description, waiting for it.

        The same as [`generate_async`][xnano.ai.models.components.ComponentModel.generate_async].
        """
        return _run_blocking(
            self.generate_async(request, evidence, width=width, height=height), 'generate'
        )

    def edit_async(
        self, component: Component, request: str
    ) -> Coroutine[Any, Any, Component]:
        """
        Change a widget as asked, at the same size, with ``await``.

        Args:
            component: The widget to change.
            request: The change, such as ``'turn the CPU bar red'``.

        Returns:
            A coroutine that gives the new [`Component`][xnano.ai.models.components.Component]; the one given
            is not changed.
        """
        return self._write(request, None, (component.width, component.height), component)

    def edit(self, component: Component, request: str) -> Component:
        """
        Change a widget as asked, waiting for it.

        The same as [`edit_async`][xnano.ai.models.components.ComponentModel.edit_async].
        """
        return _run_blocking(self.edit_async(component, request), 'edit')

    def _check_size(self, value: int | None, axis: str) -> int:
        most = self.max_width if axis == 'width' else self.max_height
        if value is None:
            return most
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= most
        ):
            raise ValueError(
                f'The {axis} of a component must be a whole number from 1 to {most}, but was '
                f'{value!r}. Pass a smaller size, or create the model with a larger '
                f'max_{axis}.'
            )
        return value

    async def _write(
        self,
        request: str,
        evidence: object,
        size: tuple[int, int],
        earlier: Component | None,
    ) -> Component:
        attempts = _Attempts()
        width, height = size
        drawn: list[Component] = []

        def write_program(layout: str, program: str) -> str:
            """Give the layout in one sentence, then the whole program."""
            attempts.begin()
            repairs: list[str] = []
            component, problems = _run_component(request, program, width, height, repairs)
            if problems:
                raise attempts.refuse(
                    problems, then='Send the whole program again, fixed.'
                )
            attempts.notes.extend(repairs)
            drawn.append(component)
            return program

        lines = []
        if earlier is None:
            lines.append(f'Draw: {request}')
        else:
            lines.append(f'Change the widget: {request}')
            lines.append(f'Its program:\n{earlier.code}')
            lines.append(f'What it draws:\n{_ruled(earlier.text, width)}')
        lines.append(
            f'The canvas is {width} cells wide and {height} rows tall; everything, borders '
            f'included, must fit inside it.'
        )
        examples = assets._closest(
            assets._entries('component-examples'),
            request,
            fields=('request', 'tags'),
            count=2,
        )
        lines.extend(_example_text(example) for example in examples)
        if evidence is not None:
            lines.append(f'What the widget shows:\n{evidence_prompt(evidence)}')
        try:
            result = await self._ask(
                '\n\n'.join(lines),
                ToolOutput(write_program, name='write_program'),
                operation='edit' if earlier else 'generate',
            )
        except TerminalError as error:
            self.last_generation = attempts.report('program')
            if error.code == 'ai.generation':
                called = f'ComponentModel.{"edit" if earlier else "generate"}()'
                raise _generation_error(
                    called, 'program', self._model_name(), self.last_generation
                ) from error
            raise
        self.last_generation = attempts.report('program')
        return next(component for component in drawn if component.code == result.output)


def _run_component(
    request: str, program: str, width: int, height: int, repairs: list[str] | None = None
) -> tuple[Component, list[str]]:
    """
    Run a program on a canvas of the size; return the component and what is wrong.

    What can be fixed safely (a near-miss name, a keyword it does not take, a cell outside the
    canvas, a line too long) is fixed and noted in ``repairs`` instead of being wrong.
    """
    if repairs is None:
        repairs = []
    from xnano.canvas import _create
    from xnano.layout._region import Region, _composed
    from xnano.sandbox import Sandbox

    problems: list[str] = []
    # A canvas of its own, not one inside the canvas that is running.
    with _create(None, width=width, height=height) as canvas:
        sandbox = Sandbox._repairing(
            canvas, repairs, limits={'max_feed_duration_secs': _PROGRAM_SECONDS}
        )
        try:
            sandbox.run(program)
        except Exception as error:
            message = getattr(error, 'display', None)
            detail = message('msg') if callable(message) else str(error)
            problems.append(f'the program failed: {detail}')
        finally:
            sandbox.close()
        canvas.clock.step()
        text = canvas.screen.render()
        right = max(
            (p.x + p.width for p in canvas._placements if not p._removed), default=0
        )
        bottom = max(
            (p.y + p.height for p in canvas._placements if not p._removed), default=0
        )
        if right > width:
            problems.append(
                f'it draws {right - width} cells past the right edge (to column {right})'
            )
        if bottom > height:
            problems.append(
                f'it draws {bottom - height} rows past the bottom (to row {bottom})'
            )
        if not problems and not text.strip():
            problems.append('it draws nothing')
        if problems:
            problems.append(f'what it drew, under a column ruler:\n{_ruled(text, width)}')
        # The cells with what was written on them, so the component draws without its canvas.
        cells = Region._from_buffer(_composed(canvas._content))
    return Component(request, program, width, height, text, cells), problems


def _example_text(example: Mapping[str, object]) -> str:
    width = int(example.get('width', 0))  # type: ignore[call-overload]
    output = str(example.get('output', ''))
    return (
        f'An example: {example.get("request")}, at {width} by {example.get("height")}.\n'
        f'{example.get("program")}\nIt draws:\n{_ruled(output, width) if output else ""}'
    )


_instructions_text: str | None = None


def _instructions() -> str:
    """The instructions of every component model: the sandbox's API and worked examples."""
    global _instructions_text
    if _instructions_text is None:
        from xnano.sandbox import SANDBOX_STUBS

        examples = []
        for example in _BUILT_IN_EXAMPLES:
            repairs: list[str] = []
            component, problems = _run_component(
                str(example['request']),
                str(example['program']),
                int(example['width']),  # type: ignore[call-overload]
                int(example['height']),  # type: ignore[call-overload]
                repairs,
            )
            assert not problems and not repairs, (problems, repairs)
            examples.append(_example_text({**example, 'output': component.text}))
        _instructions_text = (
            'You write small Python programs that draw widgets in a terminal program. A '
            'program draws only through the API below, on a canvas of a size it is told. Let '
            "the engine place things: write lines that follow each other, use x='center', "
            'percentages and canvas.screen.width rather than counting columns. Start the '
            'program with a one-line comment that says the layout.\n\n'
            f'The API:\n```python\n{SANDBOX_STUBS}\n```\n\n' + '\n\n'.join(examples)
        )
    return _instructions_text
