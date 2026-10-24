"""
xnano.ai.models

Task models: each asks a model for one kind of thing and returns xnano values.

Every task model is a [`TaskModel`][xnano.ai.models.TaskModel], which owns one pydantic-ai agent
with its instructions and settings, and lives in a module named for what it makes:
[`decisions`][xnano.ai.models.decisions] (``ChoiceModel``, ``JudgeModel``),
[`state`][xnano.ai.models.state] (``StateModel``), [`text`][xnano.ai.models.text]
(``TextModel``), [`art`][xnano.ai.models.art] (``ArtModel``),
[`components`][xnano.ai.models.components] (``ComponentModel``) and
[`music`][xnano.ai.models.music] (``MusicModel``).
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
from collections.abc import Awaitable, Generator, Sequence
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from pydantic_ai import Agent
from pydantic_ai.exceptions import (
    AgentRunError,
    ModelAPIError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
    UserError,
)
from pydantic_ai.messages import ModelMessage, ModelResponse, UserContent
from pydantic_ai.models import KnownModelName, Model
from pydantic_ai.models.decision import DecisionModel
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.wrapper import WrapperModel

from xnano._runtime._loops import background_loop, is_canvas_loop_thread, running_loop
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from pydantic_ai.agent import AgentRunResult
    from pydantic_ai.capabilities import AbstractCapability
    from pydantic_ai.settings import ModelSettings, ThinkingLevel
    from pydantic_ai.usage import UsageLimits

__all__ = ['TaskModel', 'is_decision_model', 'run_to_completion']

ResultT = TypeVar('ResultT')

_DECISION_PROVIDERS: tuple[str, ...] = ('typesafe:', 'system-one:', 'openai-decisions:')
"""The prefixes of the model names whose backends are decision models."""


def is_decision_model(model: Model | KnownModelName | str | None) -> bool:
    """
    Whether a model answers typed questions with probabilities instead of writing text.

    A decision model (TypeSafe, OpenAI Decisions, System One) is sent the evidence as JSON and
    answers each question with a probability or a distribution, which task models report as
    ``probabilities`` and ``margin``. A language model writes its answer instead. A
    ``FallbackModel`` counts as the first model it tries.

    Args:
        model: A pydantic-ai ``Model``, a model name such as ``'typesafe:jev-1.14.0'``, or
            ``None``.

    Examples:
        ```python
        from xnano.ai.models import is_decision_model

        assert is_decision_model('typesafe:jev-1.14.0')
        assert not is_decision_model('openrouter:anthropic/claude-sonnet-5-5')
        ```
    """
    if model is None:
        return False
    if isinstance(model, str):
        return model.startswith(_DECISION_PROVIDERS)
    if isinstance(model, FallbackModel):
        return bool(model.models) and is_decision_model(model.models[0])
    if isinstance(model, WrapperModel):
        return is_decision_model(model.wrapped)
    return isinstance(model, DecisionModel)


def run_to_completion(awaitable: Awaitable[ResultT]) -> ResultT:
    """
    Run an awaitable from code that does not await, and return its result.

    It runs on an event loop of xnano's own on a background thread, which stays open between
    calls, so model clients that keep connections open work across calls. Every blocking method
    of a task model (``choose``, ``generate``, ...) runs its ``_async`` twin this way.

    Raises:
        TerminalError: Called inside a running event loop, which waiting would freeze (use
            ``await`` instead), or from a hook of a canvas that runs by itself, which waiting
            would freeze on the screen (use an ``async def`` hook or ``background()``).

    Examples:
        ```python
        import asyncio

        from xnano.ai.models import run_to_completion


        async def answer() -> int:
            await asyncio.sleep(0)
            return 42


        assert run_to_completion(answer()) == 42
        ```
    """
    return _run_blocking(awaitable, None)


def _run_blocking(awaitable: Awaitable[ResultT], operation: str | None) -> ResultT:
    """Run ``awaitable`` on the background loop for a blocking call named ``operation``."""
    called = 'run_to_completion()' if operation is None else f'{operation}()'
    awaited = 'the awaitable' if operation is None else f'{operation}_async(...)'
    if running_loop() is not None:
        _close(awaitable)
        raise TerminalError(
            f'{called} was called inside a running asyncio event loop, where waiting for the '
            f'answer would freeze the loop. Write await {awaited} instead.',
            code='ai.event_loop',
        )
    if is_canvas_loop_thread():
        _close(awaitable)
        raise TerminalError(
            f'{called} was called from a hook of a canvas that runs by itself, where waiting '
            f'for the answer would freeze the screen. Write the hook with async def and await '
            f'{awaited}, or start the call with xnano.ai.background(canvas).',
            code='ai.event_loop',
        )
    future = asyncio.run_coroutine_threadsafe(_as_coroutine(awaitable), background_loop())
    try:
        return future.result()
    except BaseException:
        # An interrupt while waiting cancels the call instead of leaving it running.
        future.cancel()
        raise


async def _as_coroutine(awaitable: Awaitable[ResultT]) -> ResultT:
    return await awaitable


def _close(awaitable: Awaitable[object]) -> None:
    """Close a coroutine that will never run, so that Python does not warn about it."""
    if inspect.iscoroutine(awaitable):
        awaitable.close()


class TaskModel:
    """
    A model with one job: an agent with its instructions and settings, behind methods that take
    xnano objects and return xnano objects.

    Every task model (``ChoiceModel``, ``ArtModel``, ...) is built on this. Each method that
    asks a model has two spellings: the plain one waits for the answer, and the ``_async`` one
    is a coroutine for code that awaits. A task model can be created without credentials; the
    model is reached at the first call.

    Args:
        model: The model to ask: a pydantic-ai ``Model``, one of pydantic-ai's known model
            names such as ``'typesafe:jev-latest'``, or any other name its providers take, such
            as ``'typesafe:jev-1.14.0'`` or ``'openrouter:anthropic/claude-sonnet-5-5'``.
        instructions: What the model is told before every request, after the task model's own
            instructions.
        model_settings: pydantic-ai settings for every request.
        capabilities: pydantic-ai capabilities for the agent.
        retries: How many times an answer that fails its checks is sent back to be fixed.
        usage_limits: Limits on the requests and tokens of one call.
        thinking: Whether the model reasons before answering. ``None``, the default, leaves
            that to the model; ``False`` turns it off where the model allows it, and some
            models cannot turn it off.
        cache: Whether the unchanging start of every prompt is cached by the provider.

    Attributes:
        model: The model the task model asks.
        agent: The pydantic-ai ``Agent``, for anything the task model does not expose.
        last_result: The result of the last call, or ``None`` before the first.
        is_decision_model: Whether ``model`` is a decision model.

    Examples:
        ```python
        from xnano.ai.models.decisions import ChoiceModel

        pick = ChoiceModel('typesafe:jev-1.14.0')
        assert pick.is_decision_model and pick.last_result is None
        ```
    """

    _task_instructions: ClassVar[str] = ''
    """The instructions every model of this kind is given, before the instance's own."""

    def __init__(
        self,
        model: Model | KnownModelName | str | None = None,
        *,
        instructions: str | None = None,
        model_settings: ModelSettings | None = None,
        capabilities: Sequence[AbstractCapability[Any]] = (),
        retries: int = 3,
        usage_limits: UsageLimits | None = None,
        thinking: ThinkingLevel | None = None,
        cache: bool = True,
    ) -> None:
        """
        Create the task model and its agent; nothing is sent until the first call.

        Raises:
            ValueError: ``retries`` is not a whole number of 0 or more.
        """
        if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
            raise ValueError(
                f'retries must be a whole number of 0 or more, but was {retries!r}. It is how '
                f'many times an answer that fails its checks is sent back, such as retries=3.'
            )
        self.model: Model | KnownModelName | str | None = model
        self._instructions = instructions
        settings: dict[str, object] = dict(model_settings or {})
        if thinking is not None:
            settings.setdefault('thinking', thinking)
        if cache:
            settings.setdefault('cache', True)
        self._model_settings = settings
        self._usage_limits = usage_limits
        self.agent: Agent[None, Any] = Agent(
            model,
            instructions=self._joined_instructions() or None,
            model_settings=settings,  # type: ignore[arg-type]
            capabilities=list(capabilities),
            retries={'output': retries},
            defer_model_check=True,
        )
        self.last_result: AgentRunResult[Any] | None = None

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self._model_name()!r})'

    def _model_name(self) -> str:
        """The model as messages name it: its name, or the provider and name of a ``Model``."""
        model = self.model
        if model is None or isinstance(model, str):
            return str(model)
        return f'{model.system}:{model.model_name}'

    @property
    def is_decision_model(self) -> bool:
        """Whether ``model`` is a decision model, which answers with probabilities."""
        return is_decision_model(self.model)

    def _joined_instructions(self) -> str:
        parts = [
            type(self)._task_instructions.strip(),
            (self._instructions or '').strip(),
        ]
        return '\n\n'.join(part for part in parts if part)

    @contextlib.contextmanager
    def override(
        self, *, model: Model | KnownModelName | str
    ) -> Generator[None, None, None]:
        """
        Ask another model inside a ``with`` block: a test double, or a cheaper draft model.

        Args:
            model: The model to ask instead.

        Examples:
            ```python
            from xnano.ai.models.decisions import ChoiceModel
            from xnano.ai.testing import ScriptedDecisionModel

            pick = ChoiceModel('typesafe:jev-1.14.0')
            with pick.override(model=ScriptedDecisionModel({'response': 'left'})):
                assert pick.choose('the hero', ['left', 'right']).choice == 'left'
            ```
        """
        previous = self.model
        self.model = model
        try:
            with self.agent.override(model=model):
                yield
        finally:
            self.model = previous

    # -- what the last answer reported ----------------------------------------------------

    def details(self) -> dict[str, Any]:
        """
        What the backend reported about its last answer, as pydantic-ai's ``provider_details``.

        Empty before the first call, and for a backend that reports nothing.
        """
        response = self._last_response()
        if response is None or response.provider_details is None:
            return {}
        return dict(response.provider_details)

    def probabilities(self, field: str) -> dict[str, float] | None:
        """
        The distribution a decision model gave a pick-one or rubric field in its last answer.

        Args:
            field: The name of the field, such as ``'response'`` for a single pick-one.

        Returns:
            The probability of each option, or ``None`` on a language model or for a field it
            did not report.
        """
        distribution = self.details().get('probabilities', {}).get(field)
        if distribution is None:
            return None
        return {str(option): float(value) for option, value in distribution.items()}

    def confidence(self, field: str) -> float | None:
        """
        The confidence a decision model reported for a field of its last answer, or ``None``.

        The confidence is the backend's own figure; it is not how often the answer is right.
        """
        value = self.details().get('confidence', {}).get(field)
        return None if value is None else float(value)

    def _last_response(self) -> ModelResponse | None:
        result = self.last_result
        if result is None:
            return None
        for message in reversed(result.all_messages()):
            if isinstance(message, ModelResponse):
                return message
        return None

    # -- asking ---------------------------------------------------------------------------

    def _require_model(self, operation: str) -> Model | KnownModelName | str:
        """The model to ask for ``operation``, or the error that says one is needed."""
        model = self.model
        if model is None:
            name = type(self).__name__
            raise TerminalError(
                f'{name}.{operation}() has no model to ask. Give one when you create it, '
                f"such as {name}('typesafe:jev-1.14.0') or "
                f"{name}('openrouter:anthropic/claude-sonnet-5-5').",
                code='ai.model',
            )
        return model

    def _model_error(self, error: Exception, operation: str) -> TerminalError:
        """The error to raise when the model could not answer ``operation``."""
        name = f'{type(self).__name__}.{operation}()'
        detail = f'{type(error).__name__}: {str(error).rstrip(".")}'
        if isinstance(error, UnexpectedModelBehavior) and 'retries' in str(error):
            failure = TerminalError(
                f'{name} got no usable answer from {self._model_name()!r}: every answer failed its '
                f'checks ({detail}). Ask for something more specific, allow more retries, or '
                f'try another model.',
                code='ai.generation',
            )
            failure.__cause__ = error
            return failure
        if isinstance(
            error, (ModelAPIError, UnexpectedModelBehavior, UsageLimitExceeded)
        ):
            message = (
                f'{name} could not get an answer from {self._model_name()!r}: {detail}. Check the '
                f'model name, the API key in the environment and the network, or ask another '
                f'model.'
            )
            if 'reasoning' in detail.lower() and 'thinking' in self._model_settings:
                message = (
                    f'{name} could not get an answer from {self._model_name()!r}: {detail}. '
                    f'This model decides its own reasoning, so leave thinking=None instead of '
                    f'thinking={self._model_settings["thinking"]!r}.'
                )
        else:
            message = f'{name} could not ask {self._model_name()!r}: {detail}.'
        failure = TerminalError(message, code='ai.model')
        failure.__cause__ = error
        return failure

    async def _ask(
        self,
        prompt: str | Sequence[UserContent],
        output_type: object,
        *,
        operation: str,
        instructions: str | None = None,
        message_history: Sequence[ModelMessage] | None = None,
        model: Model | KnownModelName | str | None = None,
    ) -> AgentRunResult[Any]:
        """Run the agent once for ``operation`` and keep the result; ``model`` asks another."""
        self._require_model(operation)
        try:
            result = await self.agent.run(
                prompt,
                output_type=output_type,  # type: ignore[arg-type]
                usage_limits=self._usage_limits,
                instructions=instructions,
                message_history=None
                if message_history is None
                else list(message_history),
                model=model,
            )
        except (AgentRunError, UserError) as error:
            raise self._model_error(error, operation) from error
        self.last_result = result
        return result
