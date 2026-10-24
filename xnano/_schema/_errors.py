"""
xnano._schema._errors

The labels of the problems a terminal error reports.
"""

from __future__ import annotations

from typing import Literal, TypeAlias

TerminalErrorCode: TypeAlias = Literal[
    'validation.type',
    'validation.value',
    'validation.bounds',
    'validation.keyword',
    'canvas.closed',
    'canvas.state',
    'canvas.composition',
    'canvas.thread',
    'canvas.timeout',
    'canvas.callback',
    'canvas.loop',
    'screen.already_open',
    'screen.unavailable',
    'ai.model',
    'ai.generation',
    'ai.event_loop',
    'ai.asset',
]
"""
The label of a [`TerminalError`][xnano.errors.TerminalError]: what kind of problem it is.

- ``'validation.type'``: a value of the wrong type, such as text where a number belongs.
- ``'validation.value'``: a value of the right type that is not one of the accepted ones.
- ``'validation.bounds'``: a number outside the range it must be in, such as a size larger
  than a canvas can be.
- ``'validation.keyword'``: a keyword the call does not take.
- ``'canvas.closed'``: the canvas has been closed, or no canvas is running.
- ``'canvas.state'``: the canvas cannot do this in the state it is in.
- ``'canvas.composition'``: something cannot be written where it was asked to go.
- ``'canvas.thread'``: the canvas was used from a thread it does not belong to.
- ``'canvas.timeout'``: the canvas's loop did not answer in time.
- ``'canvas.callback'``: a hook or another callback raised on the canvas's loop.
- ``'canvas.loop'``: an ``async def`` hook has no event loop to run on.
- ``'screen.already_open'``: another canvas is already on the screen.
- ``'screen.unavailable'``: there is no terminal to draw on.
- ``'ai.model'``: a language or decision model could not be reached or did not answer.
- ``'ai.generation'``: a model answered, but its answer could not be made into what was
  asked for, even after the retries.
- ``'ai.event_loop'``: a blocking model call was made where waiting would freeze an event
  loop or the screen.
- ``'ai.asset'``: a library of examples is not installed, or could not be downloaded or
  installed.
"""
