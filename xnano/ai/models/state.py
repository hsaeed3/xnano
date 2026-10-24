"""
xnano.ai.models.state

A model that keeps a small state up to date as things happen: a character's mood, a door's
lock, the phase of a game.
"""

from __future__ import annotations

import dataclasses
import itertools
import json
import math
import typing
from collections.abc import Callable, Coroutine, Sequence
from typing import TYPE_CHECKING, Any, Generic, Literal, cast

from pydantic import BaseModel, Field, create_model
from pydantic_ai import Choices

from xnano._schema._generics import StateT
from xnano.ai._observe import evidence_prompt, evidence_value, snapshot
from xnano.ai.models import TaskModel, _run_blocking
from xnano.ai.models.decisions import MOST_OPTIONS
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from pydantic_ai.capabilities import AbstractCapability
    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.models import KnownModelName, Model
    from pydantic_ai.settings import ModelSettings, ThinkingLevel
    from pydantic_ai.usage import UsageLimits

__all__ = ['StateModel', 'StateTransition']

Invariant = Callable[[Any], bool]
"""A rule every state must keep: a function of the state that returns whether it holds."""


@dataclasses.dataclass(frozen=True)
class StateTransition(Generic[StateT]):
    """
    How a [`StateModel`][xnano.ai.models.state.StateModel] changed a state.

    Attributes:
        before: The state as it was.
        after: The state as it is now; ``before`` itself when nothing changed.
        changes: Each field that changed, with its old and its new value.
        confidence: How likely the new value of each field is, on a decision model, or
            ``None`` on a language model.
        reason: Why the state changed, as a language model wrote it, or ``None``.
    """

    before: StateT
    after: StateT
    changes: dict[str, tuple[object, object]]
    confidence: dict[str, float] | None = None
    reason: str | None = None

    @property
    def is_changed(self) -> bool:
        """Whether any field changed."""
        return bool(self.changes)


def _field_types(state_type: type[Any]) -> dict[str, Any]:
    """The fields of a dataclass or Pydantic model, with their types."""
    if isinstance(state_type, type) and issubclass(state_type, BaseModel):
        return {name: field.annotation for name, field in state_type.model_fields.items()}
    if dataclasses.is_dataclass(state_type):
        types: dict[str, Any] = {}
        hints: dict[str, Any] | None = None
        for field in dataclasses.fields(state_type):
            annotation = field.type
            if isinstance(annotation, str):
                # Written with `from __future__ import annotations`: resolved in its module.
                if hints is None:
                    hints = typing.get_type_hints(state_type)
                annotation = hints[field.name]
            types[field.name] = annotation
        return types
    raise TypeError(
        f'StateModel keeps a dataclass or a Pydantic model, but got {state_type!r}. Describe '
        f'the state as a dataclass, such as @dataclass class Mood: mood: Literal["calm", '
        f'"angry"] = "calm".'
    )


def _values(state: object, fields: dict[str, Any]) -> dict[str, object]:
    return {name: getattr(state, name) for name in fields}


def _rebuilt(state: StateT, changes: dict[str, object]) -> StateT:
    """The state with some fields changed."""
    if not changes:
        return state
    if isinstance(state, BaseModel):
        return cast(
            'StateT', type(state).model_validate({**state.model_dump(), **changes})
        )
    return cast('StateT', dataclasses.replace(cast('Any', state), **changes))


def _closed_values(annotation: object) -> tuple[object, ...] | None:
    """The values a field can take when there are few of them: a ``bool`` or a ``Literal``."""
    if annotation is bool:
        return (False, True)
    if typing.get_origin(annotation) is Literal:
        return typing.get_args(annotation)
    return None


def _value_text(value: object) -> str:
    return json.dumps(value) if not isinstance(value, str) else value


class StateModel(TaskModel, Generic[StateT]):
    """
    Keep a small state up to date as things happen.

    The state is a dataclass or a Pydantic model. On a decision model, the fields with a few
    values (``bool`` and ``Literal``) are decided: when the combinations of them are 255 or
    fewer, the model picks the whole next state among the ones that keep every invariant, so
    fields that depend on each other change together; with more, each field is asked on its own
    among the values that keep the invariants. Other fields keep their values. On a language
    model, the model writes the fields that change and why, and an answer that breaks an
    invariant is sent back to be fixed.

    Args:
        state_type: The dataclass or Pydantic model of the state.
        model: The model to ask.
        invariants: Rules every state must keep, as functions of the state that return
            whether they hold.
        instructions: What the model is told before every request.
        model_settings: pydantic-ai settings for every request.
        capabilities: pydantic-ai capabilities for the agent.
        retries: How many times an answer that breaks an invariant is sent back.
        usage_limits: Limits on the requests and tokens of one call.
        thinking: Whether the model reasons before answering. ``None``, the default, leaves
            that to the model; ``False`` turns it off where the model allows it, and some
            models cannot turn it off.
        cache: Whether the unchanging start of every prompt is cached by the provider.

    Examples:
        ```python
        from dataclasses import dataclass
        from typing import Literal

        from xnano.ai.models.state import StateModel
        from xnano.ai.testing import ScriptedDecisionModel


        @dataclass
        class Goblin:
            mood: Literal['calm', 'wary', 'angry'] = 'calm'
            is_hostile: bool = False


        moods = StateModel(
            Goblin,
            ScriptedDecisionModel({'response': 'mood=angry, is_hostile=true'}),
            invariants=[lambda goblin: goblin.mood == 'angry' or not goblin.is_hostile],
        )
        transition = moods.update(Goblin(), 'The hero stole its lunch.')
        assert transition.after == Goblin(mood='angry', is_hostile=True)
        assert transition.changes['mood'] == ('calm', 'angry')
        ```
    """

    _task_instructions = (
        'You keep the state of something in a program up to date. Change only what the '
        'evidence says has changed, and keep everything else as it is.'
    )

    def __init__(
        self,
        state_type: type[StateT],
        model: Model | KnownModelName | str | None = None,
        *,
        invariants: Sequence[Invariant] = (),
        instructions: str | None = None,
        model_settings: ModelSettings | None = None,
        capabilities: Sequence[AbstractCapability[Any]] = (),
        retries: int = 3,
        usage_limits: UsageLimits | None = None,
        thinking: ThinkingLevel | None = None,
        cache: bool = True,
    ) -> None:
        """
        Create the state model; nothing is sent until the first update.

        Raises:
            TypeError: ``state_type`` is not a dataclass or a Pydantic model, or an invariant
                is not a function.
        """
        self._fields = _field_types(state_type)
        for rule in invariants:
            if not callable(rule):
                raise TypeError(
                    f'An invariant is a function of the state that returns whether it holds, '
                    f'such as lambda state: state.health >= 0, but got {rule!r}.'
                )
        super().__init__(
            model,
            instructions=instructions,
            model_settings=model_settings,
            capabilities=capabilities,
            retries=retries,
            usage_limits=usage_limits,
            thinking=thinking,
            cache=cache,
        )
        self.state_type = state_type
        self.invariants = tuple(invariants)
        self._retries = retries

    def _keeps_invariants(self, state: object) -> bool:
        return all(rule(state) for rule in self.invariants)

    def _broken_invariants(self, state: object) -> list[str]:
        return [
            getattr(rule, '__name__', repr(rule))
            for rule in self.invariants
            if not rule(state)
        ]

    def update_async(
        self, current: StateT, evidence: object
    ) -> Coroutine[Any, Any, StateTransition[StateT]]:
        """
        Work out the state after what the evidence says happened, with ``await``.

        The evidence is read, and the current state checked, when this is called; await the
        result for the transition.

        Args:
            current: The state now.
            evidence: What happened, such as ``'The hero stole its lunch.'`` or the hook's
                context; see [`Evidence`][xnano.ai.Evidence].

        Returns:
            A coroutine that gives the [`StateTransition`][xnano.ai.models.state.StateTransition].

        Raises:
            ValueError: ``current`` breaks an invariant, or on a decision model the state has
                no ``bool`` or ``Literal`` field to decide.
            TerminalError: The model could not be reached (``ai.model``), or a language model
                kept breaking an invariant (``ai.generation``), when awaited.
        """
        if not self._keeps_invariants(current):
            raise ValueError(
                f'The current state {current!r} breaks the invariants '
                f'{", ".join(self._broken_invariants(current))}, so no update can start from '
                f'it. Fix the state, or the invariants.'
            )
        if self.is_decision_model:
            return self._decide(current, snapshot(evidence))
        return self._patch(current, snapshot(evidence))

    def update(self, current: StateT, evidence: object) -> StateTransition[StateT]:
        """
        Work out the state after what the evidence says happened, waiting for the answer.

        The same as [`update_async`][xnano.ai.models.state.StateModel.update_async], for code that does not
        await.
        """
        return _run_blocking(self.update_async(current, evidence), 'update')

    def _transition(
        self,
        current: StateT,
        after: StateT,
        *,
        confidence: dict[str, float] | None = None,
        reason: str | None = None,
    ) -> StateTransition[StateT]:
        before_values = _values(current, self._fields)
        after_values = _values(after, self._fields)
        changes = {
            name: (before_values[name], after_values[name])
            for name in self._fields
            if before_values[name] != after_values[name]
        }
        return StateTransition(
            before=current,
            after=after if changes else current,
            changes=changes,
            confidence=confidence,
            reason=reason,
        )

    # -- on a decision model -------------------------------------------------------------

    async def _decide(self, current: StateT, evidence: object) -> StateTransition[StateT]:
        closed = {
            name: values
            for name, annotation in self._fields.items()
            if (values := _closed_values(annotation)) is not None
        }
        if not closed:
            raise ValueError(
                f'{self.state_type.__name__} has no bool or Literal field, which is what a '
                f'decision model decides. Add one, such as mood: Literal["calm", "angry"], or '
                f'use a language model.'
            )
        values = _values(current, self._fields)
        prompt = json.dumps(
            {'state': evidence_value(values), 'evidence': evidence_value(evidence)},
            sort_keys=True,
        )
        if math.prod(len(options) for options in closed.values()) <= MOST_OPTIONS:
            return await self._decide_whole(current, closed, values, prompt)
        return await self._decide_fields(current, closed, values, prompt)

    async def _decide_whole(
        self,
        current: StateT,
        closed: dict[str, tuple[object, ...]],
        values: dict[str, object],
        prompt: str,
    ) -> StateTransition[StateT]:
        names = list(closed)
        candidates: dict[str, StateT] = {}
        now = tuple(values[name] for name in names)
        combinations = [
            now,
            *(
                combination
                for combination in itertools.product(*closed.values())
                if combination != now
            ),
        ]
        for combination in combinations:
            candidate = _rebuilt(current, dict(zip(names, combination, strict=True)))
            if self._keeps_invariants(candidate):
                label = ', '.join(
                    f'{name}={_value_text(value)}'
                    for name, value in zip(names, combination, strict=True)
                )
                candidates[label] = candidate
        meanings = {
            label: (
                'the state as it is now' if index == 0 else f'the state becomes {label}'
            )
            for index, label in enumerate(candidates)
        }
        choices = Choices(
            meanings,
            name='next_state',
            description='What is the state after what the evidence says happened?',
        )
        result = await self._ask(prompt, choices, operation='update')
        label = str(result.output)
        after = candidates[label]
        distribution = self.probabilities('response')
        confidence = None
        if distribution is not None:
            confidence = {}
            for name in names:
                picked = getattr(after, name)
                confidence[name] = sum(
                    probability
                    for option, probability in distribution.items()
                    if option in candidates
                    and getattr(candidates[option], name) == picked
                )
        return self._transition(current, after, confidence=confidence)

    async def _decide_fields(
        self,
        current: StateT,
        closed: dict[str, tuple[object, ...]],
        values: dict[str, object],
        prompt: str,
    ) -> StateTransition[StateT]:
        fields: dict[str, Any] = {}
        for name, options in closed.items():
            allowed = tuple(
                option
                for option in options
                if self._keeps_invariants(_rebuilt(current, {name: option}))
            )
            if len(allowed) < 2:
                continue
            question = f'What is {name} now? It was {_value_text(values[name])}.'
            annotation = bool if allowed == (False, True) else Literal[allowed]  # type: ignore[valid-type]
            fields[name] = (annotation, Field(description=question))
        if not fields:
            return self._transition(current, current)
        output_type = create_model(
            'NextState', __doc__='The state after the evidence.', **fields
        )
        result = await self._ask(prompt, output_type, operation='update')
        changes = {name: getattr(result.output, name) for name in fields}
        after = _rebuilt(current, changes)
        if not self._keeps_invariants(after):
            # The fields were decided one at a time, and together they break a rule.
            after = current
        confidence = {
            name: value for name in fields if (value := self.confidence(name)) is not None
        }
        return self._transition(current, after, confidence=confidence or None)

    # -- on a language model ---------------------------------------------------------------

    async def _patch(self, current: StateT, evidence: object) -> StateTransition[StateT]:
        values = _values(current, self._fields)
        fields: dict[str, Any] = {
            name: (
                annotation | None,
                Field(
                    default=None,
                    description=f'The new value of {name}, or null to keep {_value_text(values[name])}.',
                ),
            )
            for name, annotation in self._fields.items()
        }
        fields['reason'] = (
            str,
            Field(description='Why the state changes, in one sentence.'),
        )
        output_type = create_model(
            'StateChanges', __doc__='The fields that change.', **fields
        )
        prompt = (
            f'The state now: {json.dumps(evidence_value(values), sort_keys=True)}\n\n'
            f'What happened:\n{evidence_prompt(evidence)}\n\n'
            f'Give the new value of each field that changes, and null for the rest.'
        )
        history: list[ModelMessage] | None = None
        for _ in range(self._retries + 1):
            result = await self._ask(
                prompt, output_type, operation='update', message_history=history
            )
            changes = {
                name: value
                for name in self._fields
                if (value := getattr(result.output, name)) is not None
                and value != values[name]
            }
            after = _rebuilt(current, changes)
            broken = self._broken_invariants(after)
            if not broken:
                return self._transition(current, after, reason=result.output.reason)
            history = result.all_messages()
            prompt = (
                f'That state breaks the rules {", ".join(broken)}. Give the changes again so '
                f'that every rule holds.'
            )
        raise TerminalError(
            f'StateModel.update() kept getting states that break the invariants from '
            f'{self._model_name()!r}, after {self._retries + 1} answers. Say in the instructions what '
            f'the rules mean, or use a decision model, which only picks among valid states.',
            code='ai.generation',
        )
