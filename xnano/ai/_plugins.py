"""
xnano.ai._plugins

``decide()`` and ``watch()``: a decision or a judgement attached to a placement with ``|``, the
way a hook from ``xnano.hook()`` is.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Final, cast

import xnano_core as _core
from xnano._internal._dynamic_operations import DynamicOperation
from xnano.ai._background import background
from xnano.ai.models.decisions import (
    NO_CHANGE,
    ChoiceModel,
    Decision,
    JudgeModel,
    Options,
    Verdict,
    _check_threshold,
    _offered,
    _resolve_blocking,
)
from xnano.hooks._handles import _check_if_running
from xnano.operations import ContextualOperation

if TYPE_CHECKING:
    from xnano._schema._hooks import HookTrigger, IfRunning, KeyName
    from xnano.canvas import Canvas
    from xnano.hooks._context import Context
    from xnano.hooks._handles import HookHandle
    from xnano.layout._placement import Placement
    from xnano_core import JSONValue

__all__ = ['decide', 'watch']

_ATTACHMENTS: Final = itertools.count(1)
"""Numbers the attachments of plugins, so that each one finishes with its own event."""


class _ModelPlugin(ContextualOperation[Any, Any]):
    """
    Two hooks attached together: one that starts a model call, one that applies its answer.

    Each target it is applied to gets its own pair, with its own event, because custom events
    reach every hook that listens for their name.
    """

    def __init__(
        self,
        *,
        kind: str,
        start: Callable[[Context[Any, Any]], object],
        receive: Callable[[Context[Any, Any], object], object],
        on: HookTrigger[Any, Any] | None,
        every: float | None,
        after: float | None,
        keys: KeyName | tuple[KeyName, ...] | None,
        if_running: IfRunning,
    ) -> None:
        super().__init__(
            on=on,
            every=every,
            after=after,
            keys=()
            if keys is None
            else ((keys,) if isinstance(keys, str) else tuple(keys)),
        )
        self._kind = kind
        self._start = start
        self._receive = receive
        self._start_keys = keys
        self._if_running: IfRunning = if_running
        self._handles: list[HookHandle[Any, Any]] = []

    def apply_to(
        self, target: Canvas[Any, Any] | Placement[Any, Any] | _core.Surface
    ) -> None:
        """
        Attach the plugin's two hooks to a canvas or a placement.

        Raises:
            TypeError: ``target`` is a core surface, which cannot hold hooks.
        """
        if isinstance(target, _core.Surface):
            raise TypeError(
                f'{self._kind}() attaches hooks, so it goes on a canvas or a placement, such as '
                f'placement | {self._kind}(...), not on a core buffer.'
            )
        runs = background(target._canvas)
        name = f'{self._kind}.attachment_{next(_ATTACHMENTS)}'
        start, receive = self._start, self._receive

        def start_run(context: Context[Any, Any]) -> None:
            runs.start(
                cast('Any', start(context)), name=name, if_running=self._if_running
            )

        def apply_answer(context: Context[Any, Any]) -> object:
            return receive(context, runs.result(context))

        start_run.__name__ = f'{self._kind}_start'
        apply_answer.__name__ = f'{self._kind}_answer'
        self._handles.append(
            target.hook(
                start_run,
                on=self._hook_on,
                every=self._every,
                after=self._after,
                keys=self._start_keys,
            )
        )
        self._handles.append(target.hook(apply_answer, on=f'ai.{name}'))

    def remove(self) -> None:
        """Detach the plugin from every target it was attached to."""
        handles, self._handles = self._handles, []
        for handle in handles:
            handle.remove()


def _applicable(value: object) -> object:
    """``value`` when a hook that returns it changes its target, else ``None``."""
    if isinstance(value, (_core.Operation, _core.Style, DynamicOperation)):
        return value
    return None


def _check_when(function: str, on: object) -> None:
    if on is None:
        raise ValueError(
            f'{function}() needs on= to say when to ask the model, as hook() takes it: such '
            f"as on='key', keys='enter' or on='tick', every=2.0. Asking on every event would "
            f'call the model on every movement of the mouse.'
        )


def decide(
    model: ChoiceModel,
    options: Options,
    *,
    question: str | None = None,
    on: HookTrigger[Any, Any] | None = None,
    keys: KeyName | tuple[KeyName, ...] | None = None,
    every: float | None = None,
    after: float | None = None,
    threshold: float = 0.0,
    no_change: str | None = 'nothing needs to change now',
    if_running: IfRunning = 'replace',
) -> ContextualOperation[Any, Any]:
    """
    Let a choice model decide what a placement does, when something happens to it.

    Attach the result with ``placement | decide(...)``. When the hook's event comes (``on``,
    ``keys``, ``every`` and ``after`` are the ones ``hook()`` takes), the model is asked in the
    background with the hook's context as evidence, so the canvas goes on drawing. When the
    answer lands, a pick whose margin is below ``threshold`` counts as ``no_change``; then the
    decision is kept in the target's state under ``'decision'`` (its ``choice``, ``margin``
    and ``probabilities``), a callable value of the option picked is called, and a value that
    is an operation, a style or an effect is applied to the target, as a hook's return value is.

    Args:
        model: The [`ChoiceModel`][xnano.ai.models.decisions.ChoiceModel] that decides.
        options: The options; see [`Options`][xnano.ai.models.decisions.Options].
        question: What is being decided, such as ``'How should the hero react?'``.
        on: When to decide, as ``hook()`` takes it, such as ``on='key'``.
        keys: The keys that decide, such as ``keys='enter'``.
        every: Decide every this many seconds.
        after: Decide once after this many seconds.
        threshold: How far the pick must lead the next option, from 0 to 1; below it the
            decision is ``no_change``. Set it by what a wrong action costs.
        no_change: What the ``no_change`` option means, or ``None`` to offer only yours.
        if_running: What a new decision does to one that has not landed; ``'replace'``, so
            the latest input wins. See [`IfRunning`][xnano.hooks.IfRunning].

    Returns:
        The plugin: ``placement | plugin`` attaches it, and ``plugin.remove()`` detaches it.

    Raises:
        ValueError: ``on`` was not given, an option or ``threshold`` is not valid, or
            ``if_running`` is not one of its words.

    Examples:
        ```python
        import xnano
        from pydantic_ai import Choice
        from xnano.ai.models.decisions import ChoiceModel
        from xnano.ai import decide
        from xnano.ai.testing import ScriptedDecisionModel
        from xnano.events import Event
        from xnano_core import Style

        pick = ChoiceModel(ScriptedDecisionModel({'response': {'warn': 0.9, 'rest': 0.1}}))

        with xnano.new(width=20, height=1) as canvas:
            hero = canvas.screen.write('hero')
            hero | decide(
                pick,
                {'warn': Choice('the hero is in danger', value=Style('red')), 'rest': 'rest'},
                on='key',
                keys='enter',
                threshold=0.5,
            )
            canvas.push(Event.key_press('enter'))
            canvas.clock.step()
            canvas.clock.step()
            assert hero.state.get('decision')['choice'] == 'warn'
        ```
    """
    offered = _offered(options, no_change)
    _check_threshold(threshold)
    _check_if_running(if_running)
    _check_when('decide', on)
    meanings = {label: meaning or label for label, (meaning, _) in offered.items()}
    plain = {label: meaning for label, meaning in meanings.items() if label != NO_CHANGE}

    def start(context: Context[Any, Any]) -> object:
        return model.choose_async(context, plain, question=question, no_change=no_change)

    def receive(context: Context[Any, Any], answer: object) -> object:
        decision = cast('Decision', answer)
        margin = decision.margin
        if decision.choice != NO_CHANGE and margin is not None and margin < threshold:
            decision = Decision(
                choice=NO_CHANGE,
                value=NO_CHANGE,
                probabilities=decision.probabilities,
                confidence=decision.confidence,
            )
        kept: dict[str, JSONValue] = {
            'choice': decision.choice,
            'margin': decision.margin,
            'probabilities': cast('JSONValue', decision.probabilities),
        }
        context.buffer.state.push('decision', kept)
        if decision.choice == NO_CHANGE:
            return None
        value = _resolve_blocking(offered[decision.choice][1], decision.choice, 'decide')
        return _applicable(value)

    return _ModelPlugin(
        kind='decide',
        start=start,
        receive=receive,
        on=on,
        every=every,
        after=after,
        keys=keys,
        if_running=if_running,
    )


def watch(
    model: JudgeModel,
    question: str,
    *,
    on: HookTrigger[Any, Any] | None = None,
    keys: KeyName | tuple[KeyName, ...] | None = None,
    every: float | None = None,
    after: float | None = None,
    threshold: float = 0.5,
    yes: _core.Operation | _core.Style | Callable[[], object] | None = None,
    no: _core.Operation | _core.Style | Callable[[], object] | None = None,
    if_running: IfRunning = 'replace',
) -> ContextualOperation[Any, Any]:
    """
    Let a judge model keep answering a yes/no question about a placement.

    Attach the result with ``placement | watch(...)``. When the hook's event comes, the model
    is asked in the background with the hook's context as evidence; when the answer lands, the
    verdict is kept in the target's state under ``'verdict'`` (its ``answer`` and
    ``probability``), so a ``writable`` that reads it runs again, and ``yes`` or ``no`` is
    applied to the target when it is an operation, a style or an effect, or called when it is a
    function.

    Args:
        model: The [`JudgeModel`][xnano.ai.models.decisions.JudgeModel] that answers.
        question: The question, such as ``'Is the server under strain?'``.
        on: When to ask, as ``hook()`` takes it.
        keys: The keys that ask, such as ``keys='enter'``.
        every: Ask every this many seconds.
        after: Ask once after this many seconds.
        threshold: How likely a yes has to be, on a decision model.
        yes: What to apply or call when the answer is yes.
        no: What to apply or call when the answer is no.
        if_running: What a new question does to one that has not been answered.

    Returns:
        The plugin: ``placement | plugin`` attaches it, and ``plugin.remove()`` detaches it.

    Raises:
        ValueError: ``on`` was not given, ``threshold`` is not from 0 to 1, or ``if_running``
            is not one of its words.

    Examples:
        ```python
        import xnano
        from xnano.ai.models.decisions import JudgeModel
        from xnano.ai import watch
        from xnano.ai.testing import ScriptedDecisionModel
        from xnano_core import Style

        judge = JudgeModel(ScriptedDecisionModel({'answer': 0.8}))

        with xnano.new(width=20, height=1) as canvas:
            gauge = canvas.screen.write('CPU 97%')
            gauge | watch(
                judge, 'Is the server under strain?', on='tick', every=1.0, yes=Style('red')
            )
            canvas.clock.step(delta_seconds=1.0)
            canvas.clock.step()
            assert gauge.state.get('verdict')['answer'] is True
        ```
    """
    _check_threshold(threshold)
    _check_if_running(if_running)
    _check_when('watch', on)

    def start(context: Context[Any, Any]) -> object:
        return model.ask_async(context, question, threshold=threshold)

    def receive(context: Context[Any, Any], answer: object) -> object:
        verdict = cast('Verdict', answer)
        kept: dict[str, JSONValue] = {
            'question': verdict.question,
            'answer': verdict.answer,
            'probability': verdict.probability,
        }
        context.buffer.state.push('verdict', kept)
        value = yes if verdict.answer else no
        if value is None:
            return None
        return _applicable(
            _resolve_blocking(value, '', 'watch') if callable(value) else value
        )

    return _ModelPlugin(
        kind='watch',
        start=start,
        receive=receive,
        on=on,
        every=every,
        after=after,
        keys=keys,
        if_running=if_running,
    )
