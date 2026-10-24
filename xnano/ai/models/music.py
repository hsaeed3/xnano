"""
xnano.ai.models.music

Melodies from a language model, written in xnano's melody text and parsed into a
[`Melody`][xnano.audio.Melody].
"""

from __future__ import annotations

from collections.abc import Coroutine, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Final, Literal, TypeAlias

from pydantic_ai import ToolOutput

from xnano._internal._optional import require
from xnano.ai import assets
from xnano.ai._generations import GenerationReport, _Attempts, _generation_error
from xnano.ai._observe import evidence_prompt, snapshot
from xnano.ai.models import TaskModel, _run_blocking
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from pydantic_ai.capabilities import AbstractCapability
    from pydantic_ai.models import KnownModelName, Model
    from pydantic_ai.settings import ModelSettings, ThinkingLevel
    from pydantic_ai.usage import UsageLimits

    from xnano.audio import Melody

__all__ = ['Meter', 'MusicModel']

Meter: TypeAlias = Literal['4/4', '3/4', '2/4']
"""How many beats a bar holds: ``'4/4'``, ``'3/4'`` or ``'2/4'``."""

_BEATS_PER_BAR: Final[dict[str, float]] = {'4/4': 4.0, '3/4': 3.0, '2/4': 2.0}
_LOWEST_PITCH: Final = 36
"""C2: the lowest pitch a melody may reach."""
_HIGHEST_PITCH: Final = 96
"""C7: the highest pitch a melody may reach."""

_GRAMMAR: Final = """Write melodies in this melody text:
- A note is a letter A to G, an optional # or b, and an octave 0 to 8: C4, F#3, Bb4. C4 is middle C.
- :beats after a note gives its length in beats; without it a note lasts 1 beat: C4:0.5, G4:2.
- C4+E4+G4 is a chord, all notes at once; :beats goes after its last note: C4+E4+G4:2.
- rest (or -) is a silence, which takes :beats the same way: rest:2.
- | is a bar line between bars.
Every bar holds exactly the beats of the meter.

An example, a calm loop in G major, 4/4, 2 bars:
G4 B4 D5:2 | C5:0.5 B4:0.5 A4 G4:2"""


class MusicModel(TaskModel):
    """
    Compose melodies: [`Melody`][xnano.audio.Melody] in xnano's own melody text.

    The model writes the melody as text, which is parsed as it arrives: a parse error, a wrong
    number of bars, a bar that does not hold the beats of the meter, or a pitch outside C2 to
    C7 goes back to the model with the fault. When the ``'melodies'`` library of
    [`xnano.ai.assets`][xnano.ai.assets] is installed, the melodies closest to each request are
    shown as examples. Playing a melody needs the ``audio`` extra:
    ``pip install "xnano[audio]"``.

    Args:
        model: The language model to ask.
        meter: The meter of what ``compose`` writes, unless a call gives its own.
        style: How the music should sound, such as ``'chiptune, bouncy'``.
        instructions: What the model is told before every request.
        model_settings: pydantic-ai settings for every request.
        capabilities: pydantic-ai capabilities for the agent.
        retries: How many times a melody that fails its checks is sent back.
        usage_limits: Limits on the requests and tokens of one call.
        thinking: Whether the model reasons before answering. ``None``, the default, leaves
            that to the model; ``False`` turns it off where the model allows it, and some
            models cannot turn it off.
        cache: Whether the unchanging start of every prompt is cached by the provider.

    Attributes:
        meter: The meter of what ``compose`` writes.
        last_generation: How the last call went, or ``None`` before the first.

    Examples:
        ```python
        from xnano.ai.models.music import MusicModel
        from xnano.ai.testing import scripted_model

        composer = MusicModel(scripted_model({'text': 'C4 E4 G4:2 | F4 D4 C4:2'}).model)
        theme = composer.compose('a cheerful march in C', bars=2, bpm=120)
        assert theme.length_beats == 8.0
        ```
    """

    def __init__(
        self,
        model: Model | KnownModelName | str | None = None,
        *,
        meter: Meter = '4/4',
        style: str | None = None,
        instructions: str | None = None,
        model_settings: ModelSettings | None = None,
        capabilities: Sequence[AbstractCapability[Any]] = (),
        retries: int = 3,
        usage_limits: UsageLimits | None = None,
        thinking: ThinkingLevel | None = None,
        cache: bool = True,
    ) -> None:
        """
        Create the music model; nothing is sent until the first call.

        Raises:
            ValueError: ``meter`` is not one of the meters.
        """
        _check_meter(meter)
        parts = [
            'You compose short melodies for a terminal program.',
            _GRAMMAR,
            instructions or '',
        ]
        if style:
            parts.append(f'Compose in this style: {style}.')
        super().__init__(
            model,
            instructions='\n\n'.join(part for part in parts if part),
            model_settings=model_settings,
            capabilities=capabilities,
            retries=retries,
            usage_limits=usage_limits,
            thinking=thinking,
            cache=cache,
        )
        self.meter: Meter = meter
        self.style = style
        self.last_generation: GenerationReport | None = None

    def compose_async(
        self,
        request: str,
        evidence: object = None,
        *,
        bars: int = 4,
        meter: Meter | None = None,
        bpm: float | None = None,
        symbol: str | None = None,
    ) -> Coroutine[Any, Any, Melody]:
        """
        Compose a melody from a description, with ``await``.

        Args:
            request: What to compose, such as ``'a cheerful four-bar march in C'``.
            evidence: What the music is for, such as the hook's context; see
                [`Evidence`][xnano.ai.Evidence].
            bars: How many bars.
            meter: The meter; ``None`` uses the model's.
            bpm: The tempo of the melody; ``None`` takes the active canvas's, or 120.
            symbol: A name to register the melody under in [`symbols`][xnano.symbols], so
                ``play(name)`` plays it.

        Returns:
            A coroutine that gives the [`Melody`][xnano.audio.Melody].

        Raises:
            ImportError: ``xnano-audio`` is not installed.
            ValueError: ``bars`` is not a whole number from 1 to 32, or ``meter`` is not one
                of the meters.
            GenerationError: No answer was a melody that passes the checks, when awaited.
        """
        require('audio', needed_for='MusicModel.compose()')
        if isinstance(bars, bool) or not isinstance(bars, int) or not 1 <= bars <= 32:
            raise ValueError(
                f'bars must be a whole number from 1 to 32, but was {bars!r}.'
            )
        chosen_meter = self.meter if meter is None else _check_meter(meter)
        return self._compose(
            request, snapshot(evidence), bars, chosen_meter, _tempo(bpm), symbol, None
        )

    def compose(
        self,
        request: str,
        evidence: object = None,
        *,
        bars: int = 4,
        meter: Meter | None = None,
        bpm: float | None = None,
        symbol: str | None = None,
    ) -> Melody:
        """
        Compose a melody from a description, waiting for it.

        The same as [`compose_async`][xnano.ai.models.music.MusicModel.compose_async].
        """
        return _run_blocking(
            self.compose_async(
                request, evidence, bars=bars, meter=meter, bpm=bpm, symbol=symbol
            ),
            'compose',
        )

    def vary_async(
        self, melody: Melody, request: str, *, symbol: str | None = None
    ) -> Coroutine[Any, Any, Melody]:
        """
        Write a variation of a melody, with the same bars, meter and tempo, with ``await``.

        Args:
            melody: The melody to vary; it must have bar lines, as composed melodies do.
            request: The change, such as ``'make the last bar end on the tonic'``.
            symbol: A name to register the variation under in [`symbols`][xnano.symbols].

        Returns:
            A coroutine that gives the new [`Melody`][xnano.audio.Melody].

        Raises:
            ValueError: The melody's bars do not all hold the beats of one meter.
        """
        bars = melody.text.split('|')
        beats = melody.length_beats / len(bars)
        meter = next(
            (name for name, count in _BEATS_PER_BAR.items() if count == beats), None
        )
        if meter is None:
            raise ValueError(
                f'vary() needs a melody whose bars hold 2, 3 or 4 beats each, but this one '
                f'has {len(bars)} bars over {melody.length_beats:g} beats. Write it with a '
                f'bar line, |, between bars.'
            )
        return self._compose(
            request,
            None,
            len(bars),
            _check_meter(meter),
            melody.bpm,
            symbol,
            melody.text,
        )

    def vary(self, melody: Melody, request: str, *, symbol: str | None = None) -> Melody:
        """
        Write a variation of a melody, waiting for it.

        The same as [`vary_async`][xnano.ai.models.music.MusicModel.vary_async].
        """
        return _run_blocking(self.vary_async(melody, request, symbol=symbol), 'vary')

    async def _compose(
        self,
        request: str,
        evidence: object,
        bars: int,
        meter: Meter,
        bpm: float,
        symbol: str | None,
        earlier: str | None,
    ) -> Melody:
        from xnano.audio import Melody

        attempts = _Attempts()

        def write_melody(text: str) -> str:
            """Give the melody text, with a bar line between bars."""
            attempts.begin()
            problems = _melody_problems(text, bars, meter, bpm)
            if problems:
                raise attempts.refuse(
                    problems, then='Send the whole melody again, fixed.'
                )
            return text.strip()

        if earlier is None:
            lines = [f'Compose: {request}']
        else:
            lines = [
                f'Write a variation of this melody: {request}',
                f'The melody:\n{earlier}',
            ]
        lines.append(f'It has {bars} bars in {meter}, at {bpm:g} beats per minute.')
        examples = assets._closest(
            assets._entries('melodies'), request, fields=('description', 'tags'), count=2
        )
        lines.extend(_example_text(example) for example in examples)
        if evidence is not None:
            lines.append(f'What the music is for:\n{evidence_prompt(evidence)}')
        operation = 'compose' if earlier is None else 'vary'
        try:
            result = await self._ask(
                '\n\n'.join(lines),
                ToolOutput(write_melody, name='write_melody'),
                operation=operation,
            )
        except TerminalError as error:
            self.last_generation = attempts.report('melody')
            if error.code == 'ai.generation':
                raise _generation_error(
                    f'MusicModel.{operation}()',
                    'melody',
                    self._model_name(),
                    self.last_generation,
                ) from error
            raise
        self.last_generation = attempts.report('melody')
        return Melody(result.output, bpm=bpm, symbol=symbol)


def _melody_problems(text: str, bars: int, meter: Meter, bpm: float) -> list[str]:
    """What is wrong with a melody: its parse, its bars and its pitches."""
    from xnano.audio import Melody

    try:
        melody = Melody(text, bpm=bpm)
    except (TypeError, ValueError) as error:
        return [f'the text does not parse: {error}']
    problems = []
    written = text.split('|')
    if len(written) != bars:
        problems.append(f'it has {len(written)} bars, but {bars} were asked for')
    expected = _BEATS_PER_BAR[meter]
    for index, bar in enumerate(written, start=1):
        try:
            beats = Melody(bar, bpm=bpm).length_beats if bar.strip() else 0.0
        except (TypeError, ValueError):
            continue
        if abs(beats - expected) > 1e-9:
            problems.append(
                f'bar {index} holds {beats:g} beats, but a bar of {meter} holds {expected:g}'
            )
    region = melody.region
    lowest, highest = region.y, region.y + region.height - 1
    if lowest < _LOWEST_PITCH or highest > _HIGHEST_PITCH:
        problems.append(
            f'its pitches reach MIDI {lowest} to {highest}; keep them from C2 (36) to C7 (96)'
        )
    return problems


def _example_text(example: Mapping[str, object]) -> str:
    return (
        f'An example: {example.get("description")} ({example.get("meter")}, '
        f'{example.get("bars")} bars):\n{example.get("text")}'
    )


def _check_meter(meter: object) -> Meter:
    if meter not in _BEATS_PER_BAR:
        raise ValueError(f"meter must be '4/4', '3/4' or '2/4', but was {meter!r}.")
    return meter  # type: ignore[return-value]


def _tempo(bpm: float | None) -> float:
    """The tempo given, or the active canvas's, or 120."""
    if bpm is not None:
        if isinstance(bpm, bool) or not bpm > 0:
            raise ValueError(f'bpm must be above 0, such as 120, but was {bpm!r}.')
        return float(bpm)
    from xnano.canvas import active

    canvas = active(is_required=False)
    return 120.0 if canvas is None else float(canvas.clock.bpm)
