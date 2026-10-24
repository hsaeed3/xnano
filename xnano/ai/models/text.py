"""
xnano.ai.models.text

Prose from a language model, written whole or streamed into a placement as it arrives.
"""

from __future__ import annotations

import asyncio
import queue
import re
import threading
import time
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Coroutine,
    Iterable,
    Iterator,
    Sequence,
)
from typing import TYPE_CHECKING, Any, Final

from pydantic_ai.exceptions import AgentRunError, UserError

from xnano.ai._observe import evidence_prompt, snapshot
from xnano.ai.models import TaskModel, _run_blocking
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from pydantic_ai.capabilities import AbstractCapability
    from pydantic_ai.models import KnownModelName, Model
    from pydantic_ai.settings import ModelSettings, ThinkingLevel
    from pydantic_ai.usage import UsageLimits

    from xnano.layout._placement import Placement

__all__ = ['TextModel', 'stream_into', 'stream_into_async']

_SENTENCE_END: Final = re.compile(r'(?<=[.!?])\s+')

_FINISHED: Final = object()
"""What the pump of a blocking stream puts on its queue after the last piece."""


def _first_sentences(text: str, count: int | None) -> str:
    """The text cut after ``count`` sentences, or the whole text."""
    if count is None:
        return text
    sentences = _SENTENCE_END.split(text.strip())
    return ' '.join(sentences[:count])


class TextModel(TaskModel):
    """
    Write prose for the canvas: a description, a narration, a line of dialogue.

    ``generate`` returns the whole text; ``stream`` gives it piece by piece as the model writes
    it, which [`stream_into`][xnano.ai.models.text.stream_into] shows in a placement as it arrives.

    Args:
        model: The language model to ask.
        style: How the text should read, such as ``'wry, second person'``.
        max_sentences: The most sentences an answer keeps; a longer answer is cut after them.
        instructions: What the model is told before every request.
        model_settings: pydantic-ai settings for every request.
        capabilities: pydantic-ai capabilities for the agent.
        retries: How many times an empty answer is asked again.
        usage_limits: Limits on the requests and tokens of one call.
        thinking: Whether the model reasons before answering. ``None``, the default, leaves
            that to the model; ``False`` turns it off where the model allows it, and some
            models cannot turn it off.
        cache: Whether the unchanging start of every prompt is cached by the provider.

    Examples:
        ```python
        from xnano.ai.models.text import TextModel
        from xnano.ai.testing import scripted_model

        writer = TextModel(scripted_model('A door. A key. A choice.').model, max_sentences=2)
        assert writer.generate('Describe the room.') == 'A door. A key.'
        ```
    """

    _task_instructions = (
        'You write short prose that is shown in a terminal program. Write plain text only: '
        'no markdown, no headings, no lists and no quotation marks around the answer.'
    )

    def __init__(
        self,
        model: Model | KnownModelName | str | None = None,
        *,
        style: str | None = None,
        max_sentences: int | None = None,
        instructions: str | None = None,
        model_settings: ModelSettings | None = None,
        capabilities: Sequence[AbstractCapability[Any]] = (),
        retries: int = 3,
        usage_limits: UsageLimits | None = None,
        thinking: ThinkingLevel | None = None,
        cache: bool = True,
    ) -> None:
        """
        Create the text model; nothing is sent until the first call.

        Raises:
            ValueError: ``max_sentences`` is not a whole number of 1 or more.
        """
        if max_sentences is not None and (
            isinstance(max_sentences, bool)
            or not isinstance(max_sentences, int)
            or max_sentences < 1
        ):
            raise ValueError(
                f'max_sentences must be a whole number of 1 or more, or None, but was '
                f'{max_sentences!r}.'
            )
        parts = [instructions or '']
        if style:
            parts.append(f'Write in this style: {style}.')
        if max_sentences is not None:
            parts.append(f'Write at most {max_sentences} sentences.')
        super().__init__(
            model,
            instructions=' '.join(part for part in parts if part) or None,
            model_settings=model_settings,
            capabilities=capabilities,
            retries=retries,
            usage_limits=usage_limits,
            thinking=thinking,
            cache=cache,
        )
        self.style = style
        self.max_sentences = max_sentences
        self._retries = retries

    def _prompt(self, request: str, evidence: object) -> str:
        if evidence is None:
            return request
        return f'{request}\n\nWhat is on the screen:\n{evidence_prompt(evidence)}'

    def generate_async(
        self, request: str, evidence: object = None
    ) -> Coroutine[Any, Any, str]:
        """
        Write the text asked for, with ``await``.

        The evidence is read when this is called; await the result for the text.

        Args:
            request: What to write, such as ``'Describe the room the hero just entered.'``.
            evidence: What the text is about, such as the hook's context; see
                [`Evidence`][xnano.ai.Evidence]. ``None`` sends the request alone.

        Returns:
            A coroutine that gives the text, cut after ``max_sentences`` sentences.

        Raises:
            TerminalError: The model could not be reached (``ai.model``), or wrote nothing,
                even when asked again (``ai.generation``), when awaited.
        """
        return self._generate(self._prompt(request, snapshot(evidence)))

    async def _generate(self, prompt: str) -> str:
        for _ in range(self._retries + 1):
            result = await self._ask(prompt, str, operation='generate')
            text = str(result.output).strip()
            if text:
                return _first_sentences(text, self.max_sentences)
        raise TerminalError(
            f'TextModel.generate() got no text from {self._model_name()!r}, even after asking '
            f'{self._retries + 1} times. Ask for something more specific, or try another model.',
            code='ai.generation',
        )

    def generate(self, request: str, evidence: object = None) -> str:
        """
        Write the text asked for, waiting for the whole answer.

        The same as [`generate_async`][xnano.ai.models.text.TextModel.generate_async], for code that does
        not await.
        """
        return _run_blocking(self.generate_async(request, evidence), 'generate')

    def stream_async(self, request: str, evidence: object = None) -> AsyncIterator[str]:
        """
        Write the text asked for, giving each new piece as the model writes it, with
        ``async for``.

        The evidence is read when this is called.

        Args:
            request: What to write.
            evidence: What the text is about; see [`Evidence`][xnano.ai.Evidence].

        Yields:
            The pieces of the text, in order: joined, they are the whole text.

        Raises:
            TerminalError: The model could not be reached (``ai.model``).

        Examples:
            ```python
            import asyncio

            from xnano.ai.models.text import TextModel
            from xnano.ai.testing import scripted_model

            writer = TextModel(scripted_model('Once upon a time.').model)


            async def main() -> str:
                return ''.join([piece async for piece in writer.stream_async('Begin.')])


            assert asyncio.run(main()) == 'Once upon a time.'
            ```
        """
        self._require_model('stream')
        return self._stream(self._prompt(request, snapshot(evidence)))

    async def _stream(self, prompt: str) -> AsyncIterator[str]:
        try:
            async with self.agent.run_stream(
                prompt, output_type=str, usage_limits=self._usage_limits
            ) as response:
                async for piece in response.stream_text(delta=True, debounce_by=None):
                    if piece:
                        yield piece
        except (AgentRunError, UserError) as error:
            raise self._model_error(error, 'stream') from error

    def stream(self, request: str, evidence: object = None) -> Iterator[str]:
        """
        Write the text asked for, giving each piece as it is written, for code that does not
        await.

        The same as [`stream_async`][xnano.ai.models.text.TextModel.stream_async]. Stopping the loop
        early cancels the request.
        """
        return _blocking_pieces(self.stream_async(request, evidence), 'stream')


def _blocking_pieces(pieces: AsyncIterator[str], operation: str) -> Iterator[str]:
    """Iterate over an async stream from code that does not await, on xnano's own loop."""
    waiting: queue.Queue[object] = queue.Queue()
    is_stopped = threading.Event()

    async def pump() -> None:
        try:
            async for piece in pieces:
                if is_stopped.is_set():
                    break
                waiting.put(piece)
        except BaseException as error:
            waiting.put(error)
            if isinstance(error, asyncio.CancelledError):
                raise
        finally:
            waiting.put(_FINISHED)

    task = _run_blocking(_start(pump()), operation)
    try:
        while True:
            item = waiting.get()
            if item is _FINISHED:
                return
            if isinstance(item, BaseException):
                raise item
            yield str(item)
    finally:
        is_stopped.set()
        loop = task.get_loop()
        if not loop.is_closed():
            loop.call_soon_threadsafe(task.cancel)


async def _start(coroutine: Any) -> asyncio.Task[None]:
    """Start a coroutine as a task on the running loop, and return the task at once."""
    return asyncio.get_running_loop().create_task(coroutine)


async def stream_into_async(
    placement: Placement[Any, Any],
    pieces: AsyncIterable[str],
    *,
    debounce_seconds: float = 1 / 30,
) -> str:
    """
    Show text in a placement as its pieces arrive, and return the whole text.

    The placement's text is replaced at most every ``debounce_seconds`` with everything that
    arrived so far, so a fast stream costs a few redraws, not one per piece. When the stream ends
    or is cancelled, the placement keeps all the text that arrived.

    Args:
        placement: Where to show the text; it grows with it, unless it was given a size.
        pieces: The pieces, such as ``TextModel.stream_async(...)``.
        debounce_seconds: The least time between two redraws.

    Returns:
        The whole text.

    Examples:
        ```python
        import asyncio

        import xnano
        from xnano.ai.models.text import TextModel, stream_into_async
        from xnano.ai.testing import scripted_model

        writer = TextModel(scripted_model('The rain stops.').model)


        async def main() -> str:
            async with xnano.new(width=20, height=1) as canvas:
                label = canvas.screen.write('')
                await stream_into_async(label, writer.stream_async('Narrate.'))
                return canvas.screen.render()


        assert asyncio.run(main()) == 'The rain stops.'
        ```
    """
    _check_debounce(debounce_seconds)
    text: list[str] = []
    shown = ''
    last = 0.0
    try:
        async for piece in pieces:
            text.append(piece)
            now = time.monotonic()
            if now - last >= debounce_seconds:
                shown = ''.join(text)
                placement.text = shown
                last = now
    finally:
        whole = ''.join(text)
        if whole != shown and not placement._removed:
            placement.text = whole
    return whole


def stream_into(
    placement: Placement[Any, Any],
    pieces: Iterable[str],
    *,
    debounce_seconds: float = 1 / 30,
) -> str:
    """
    Show text in a placement as its pieces arrive, for code that does not await.

    The same as [`stream_into_async`][xnano.ai.models.text.stream_into_async], with pieces such as
    ``TextModel.stream(...)``.

    Examples:
        ```python
        import xnano
        from xnano.ai.models.text import TextModel, stream_into
        from xnano.ai.testing import scripted_model

        writer = TextModel(scripted_model('Thunder rolls.').model)
        with xnano.new(width=20, height=1) as canvas:
            label = canvas.screen.write('')
            assert stream_into(label, writer.stream('Narrate.')) == 'Thunder rolls.'
            assert canvas.screen.render() == 'Thunder rolls.'
        ```
    """
    _check_debounce(debounce_seconds)
    text: list[str] = []
    shown = ''
    last = 0.0
    try:
        for piece in pieces:
            text.append(piece)
            now = time.monotonic()
            if now - last >= debounce_seconds:
                shown = ''.join(text)
                placement.text = shown
                last = now
    finally:
        whole = ''.join(text)
        if whole != shown and not placement._removed:
            placement.text = whole
    return whole


def _check_debounce(debounce_seconds: float) -> None:
    if isinstance(debounce_seconds, bool) or not debounce_seconds >= 0:
        raise ValueError(
            f'debounce_seconds must be 0 or more, but was {debounce_seconds!r}. It is the '
            f'least time between two redraws, such as 1 / 30.'
        )
