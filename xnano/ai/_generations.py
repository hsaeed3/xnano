"""
xnano.ai._generations

What every generating model reports: the answers it sent back to be fixed, the repairs it
made, and the error when no answer could be used.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

from pydantic_ai import ModelRetry

from xnano.errors import TerminalError

__all__ = ['Critique', 'GenerationError', 'GenerationReport']

_MOST_LISTED = 16
"""The most problems of one answer that are listed when it is sent back."""
_MOST_QUOTED = 600
"""The most characters of the last answer's problems that an error message quotes."""


@dataclasses.dataclass(frozen=True, slots=True)
class Critique:
    """
    What a critic saw in a piece: a score, and each problem it would fix.

    Attributes:
        score: From 1 (unreadable) to 10 (nothing to fix).
        problems: Each problem, in a sentence; none when there is nothing to fix.
    """

    score: int
    problems: tuple[str, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class GenerationReport:
    """
    How a generation went: the answers sent back to be fixed, and the repairs made.

    ``last_generation`` of [`ArtModel`][xnano.ai.models.art.ArtModel],
    [`ComponentModel`][xnano.ai.models.components.ComponentModel] and [`MusicModel`][xnano.ai.models.music.MusicModel] is one.

    Attributes:
        strategy: How the model wrote its answer: ``'program'`` or ``'svg'`` for art,
            ``'program'`` for a component, or ``'melody'``.
        attempts: How many answers the model gave.
        problems: What was wrong with each answer that was sent back, in order.
        notes: The safe repairs that were made instead of a retry, such as a colour written
            ``'#f8c'``.
        critiques: What the critic said in each round of ``critique``, in order; the piece
            kept is the one with the best score.
        sketch: For art larger than 12 pixels, the sketch the piece was drawn from: one letter
            per block of 2 by 2 pixels, ``'.'`` for an empty block; empty otherwise.
    """

    strategy: str
    attempts: int
    problems: tuple[str, ...]
    notes: tuple[str, ...]
    critiques: tuple[Critique, ...] = ()
    sketch: tuple[str, ...] = ()


class GenerationError(TerminalError):
    """
    Raised when no answer of the model could be made into what was asked for.

    Attributes:
        generation: How the generation went: each problem that was sent back to be fixed.
    """

    generation: GenerationReport

    def __init__(self, message: str, generation: GenerationReport) -> None:
        """Create the error with the report of the generation."""
        super().__init__(message, code='ai.generation')
        self.generation = generation


def _generation_error(
    called: str, made: str, model_name: str, report: GenerationReport
) -> GenerationError:
    """The error for a call that got no usable answer, quoting the problems of the last one."""
    last = report.problems[-1] if report.problems else 'every answer failed its checks'
    if len(last) > _MOST_QUOTED:
        last = last[:_MOST_QUOTED].rsplit('; ', 1)[0] + '; and more'
    return GenerationError(
        f'{called} got no usable {made} from {model_name!r} after {report.attempts} answers. '
        f'The problems of the last answer were: {last}. Ask for something simpler or smaller, '
        f'allow more retries, or try another model; error.generation has the problems of '
        f'every answer.',
        report,
    )


class _Attempts:
    """What one call saw: each answer's problems, and the repairs made."""

    __slots__ = ('attempts', 'notes', 'problems')

    def __init__(self) -> None:
        self.attempts = 0
        self.problems: list[str] = []
        self.notes: list[str] = []

    def begin(self) -> None:
        """Start checking another answer: only the repairs of the accepted one are reported."""
        self.attempts += 1
        self.notes.clear()

    def refuse(self, problems: Sequence[str], *, then: str) -> ModelRetry:
        self.problems.append('; '.join(problems))
        listed = '\n'.join(f'- {problem}' for problem in problems[:_MOST_LISTED])
        if len(problems) > _MOST_LISTED:
            listed += f'\n- and {len(problems) - _MOST_LISTED} more like these'
        return ModelRetry(f'The answer could not be used:\n{listed}\n{then}')

    def report(self, strategy: str, *, sketch: object = None) -> GenerationReport:
        rows = getattr(sketch, 'rows', ())
        return GenerationReport(
            strategy=strategy,
            attempts=self.attempts,
            problems=tuple(self.problems),
            notes=tuple(self.notes),
            sketch=tuple(rows),
        )
