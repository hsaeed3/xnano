"""
xnano.ai.testing

Models that answer from a script, so programs and tests that use `xnano.ai` run offline and give
the same answers every time.

[`ScriptedDecisionModel`][xnano.ai.testing.ScriptedDecisionModel] is a real pydantic-ai decision
model whose answers come from a mapping, so the questions, probabilities and margins a task model
works with are the ones a real decision backend would give.
[`scripted_model`][xnano.ai.testing.scripted_model] is a language model that answers each
request with the next step of a script.

[`replay`][xnano.ai.testing.replay] runs a file of cases through a
[`ChoiceModel`][xnano.ai.models.decisions.ChoiceModel] once, and reports how often it is right at each
threshold of probability, how well its probabilities are calibrated, and whether the order of
the options changes its answers: how a threshold for a program is chosen.
"""

from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import re
from collections.abc import AsyncIterator, Callable, Coroutine, Mapping, Sequence
from typing import TYPE_CHECKING, Any, TypeAlias

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models import override_allow_model_requests
from pydantic_ai.models.decision import (
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionAnswer,
    DecisionModel,
    DecisionModelSettings,
    DecisionQuestion,
    DecisionRequest,
    DecisionResponse,
    NoulAnswer,
    NoulQuestion,
    ScoreAnswer,
    ScoreQuestion,
)
from pydantic_ai.models.function import (
    AgentInfo,
    DeltaToolCall,
    DeltaToolCalls,
    FunctionModel,
)

if TYPE_CHECKING:
    from xnano.ai.models.decisions import ChoiceModel

__all__ = [
    'Coverage',
    'ReplayCase',
    'ReplayReport',
    'ScriptedDecisionModel',
    'ScriptedModel',
    'replay',
    'replay_async',
    'scripted_model',
]

ScriptedAnswer: TypeAlias = object
"""
One scripted answer: for a yes/no, ``True``, ``False`` or the probability of a yes; for a
pick-one, the label or a mapping from label to probability; for a rubric, the level or a
mapping from level to probability.
"""

AnswerFunction: TypeAlias = Callable[
    [str, DecisionQuestion, DecisionRequest], ScriptedAnswer
]
"""A function from the name of a question, the question and the request to its answer."""


def _choice_answer(question: ChoiceQuestion, value: ScriptedAnswer) -> ChoiceAnswer:
    labels = list(question.criteria)
    if isinstance(value, Mapping):
        probabilities = {
            str(label): float(probability) for label, probability in value.items()
        }
        for label in labels:
            probabilities.setdefault(label, 0.0)
        picked = max(probabilities, key=lambda label: probabilities[label])
    else:
        picked = labels[0] if value is None else str(value)
        if picked not in labels:
            raise ValueError(
                f'The scripted answer {picked!r} is not one of the options {labels}. Script '
                f'one of them, or a mapping from option to probability.'
            )
        rest = 0.1 / (len(labels) - 1) if len(labels) > 1 else 0.0
        probabilities = {label: 0.9 if label == picked else rest for label in labels}
        if len(labels) == 1:
            probabilities[picked] = 1.0
    return ChoiceAnswer(
        choice=picked, confidence=probabilities[picked], probabilities=probabilities
    )


def _score_answer(question: ScoreQuestion, value: ScriptedAnswer) -> ScoreAnswer:
    count = len(question.criteria)
    if isinstance(value, Mapping):
        probabilities = {
            int(level): float(probability) for level, probability in value.items()
        }
        score = sum(level * probability for level, probability in probabilities.items())
    else:
        level = int(value or 0)  # type: ignore[call-overload]
        probabilities = {index: 1.0 if index == level else 0.0 for index in range(count)}
        score = float(level)
    return ScoreAnswer(
        score=score,
        confidence=max(probabilities.values()),
        probabilities=probabilities,
        legend={},
    )


def _yes_or_no_answer(value: ScriptedAnswer) -> NoulAnswer:
    if value is None:
        probability = 0.75
    elif value is True:
        probability = 0.95
    elif value is False:
        probability = 0.05
    else:
        probability = float(value)  # type: ignore[arg-type]
    return NoulAnswer(noul=probability)


@dataclasses.dataclass(init=False)
class ScriptedDecisionModel(DecisionModel[None]):
    """
    A decision model that answers every question from a script, with no network.

    ``answers`` maps the name of a question to its answer: ``'response'`` for a single
    pick-one, a field name such as ``'answer'`` or ``'level'`` otherwise. A question with no
    scripted answer gets a yes with probability 0.75, the first option, or level 0.

    Args:
        answers: The answers by question name, or a function that returns the answer for a
            question; see [`ScriptedAnswer`][xnano.ai.testing.ScriptedAnswer].
        model_name: The name the model reports.

    Attributes:
        answers: The script.
        requests: Every request the model was sent, oldest first.
        last_state: What the latest request judged, parsed from JSON when it is JSON.

    Examples:
        ```python
        from xnano.ai.models.decisions import ChoiceModel
        from xnano.ai.testing import ScriptedDecisionModel

        model = ScriptedDecisionModel({'response': {'left': 0.6, 'right': 0.4}})
        decision = ChoiceModel(model).choose({'x': 3}, ['left', 'right'])
        assert decision.choice == 'left'
        assert model.last_state == {'x': 3}
        ```
    """

    max_choice_options = 255
    max_score_levels = 10

    answers: Mapping[str, ScriptedAnswer] | AnswerFunction
    requests: list[DecisionRequest]

    def __init__(
        self,
        answers: Mapping[str, ScriptedAnswer] | AnswerFunction | None = None,
        *,
        model_name: str = 'scripted',
    ) -> None:
        """Create the model with its script."""
        super().__init__()
        self.answers = {} if answers is None else answers
        self.requests = []
        self._name = model_name

    @property
    def model_name(self) -> str:
        """The name the model reports."""
        return self._name

    @property
    def system(self) -> str:
        """The provider the model reports: ``'scripted'``."""
        return 'scripted'

    async def request(self, *arguments: Any, **keywords: Any) -> ModelResponse:
        """Answer a request; a local model, so it is allowed when model requests are not."""
        with override_allow_model_requests(True):
            return await super().request(*arguments, **keywords)

    def _scripted(
        self, name: str, question: DecisionQuestion, request: DecisionRequest
    ) -> ScriptedAnswer:
        answers = self.answers
        if callable(answers):
            return answers(name, question, request)
        if name in answers:
            return answers[name]
        return answers.get(name.split('.', 1)[-1])

    async def decide(
        self, request: DecisionRequest, model_settings: DecisionModelSettings
    ) -> DecisionResponse:
        """Answer every question of the request from the script."""
        self.requests.append(request)
        answers: dict[str, DecisionAnswer] = {}
        for name, question in request.questions.items():
            value = self._scripted(name, question, request)
            if isinstance(question, NoulQuestion):
                answers[name] = _yes_or_no_answer(value)
            elif isinstance(question, ChoiceQuestion):
                answers[name] = _choice_answer(question, value)
            elif isinstance(question, ScoreQuestion):
                answers[name] = _score_answer(question, value)
        return DecisionResponse(answers=answers, model_name=self._name)

    @property
    def last_state(self) -> object:
        """What the latest request judged, parsed from JSON when it is JSON, or ``None``."""
        if not self.requests:
            return None
        state = self.requests[-1].state
        if isinstance(state, str):
            try:
                return json.loads(state)
            except ValueError:
                return state
        return state


@dataclasses.dataclass
class ScriptedModel:
    """
    What [`scripted_model`][xnano.ai.testing.scripted_model] returns: the model, and a record.

    Attributes:
        model: The pydantic-ai ``FunctionModel`` to give a task model.
        calls: What the agent offered at each request: its output tools and settings.
        messages: The messages of each request, oldest first.
    """

    model: FunctionModel
    calls: list[AgentInfo] = dataclasses.field(default_factory=list)
    messages: list[list[ModelMessage]] = dataclasses.field(default_factory=list)


def _step_response(step: object, info: AgentInfo) -> ModelResponse:
    if isinstance(step, ModelResponse):
        return step
    if isinstance(step, str):
        return ModelResponse(parts=[TextPart(step)])
    if isinstance(step, tuple) and len(step) == 2 and isinstance(step[0], str):
        name, arguments = step
        return ModelResponse(parts=[ToolCallPart(name, _arguments(arguments))])
    if isinstance(step, (BaseModel, Mapping)):
        tools = info.output_tools
        if not tools:
            raise AssertionError(
                'The script gave output arguments, but the request offers no output tool.'
            )
        return ModelResponse(parts=[ToolCallPart(tools[0].name, _arguments(step))])
    raise TypeError(
        f'A script step is text, a mapping of output arguments, a (tool name, arguments) '
        f'pair or a ModelResponse, but got {step!r}.'
    )


def _arguments(value: object) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode='json')
    return dict(value)  # type: ignore[call-overload]


def scripted_model(*steps: object, repeat_last: bool = False) -> ScriptedModel:
    """
    A language model that answers each request with the next step of a script.

    A step is text, a mapping of the arguments of the output (such as ``{'response':
    'left'}``), a ``(tool name, arguments)`` pair, a pydantic-ai ``ModelResponse``, or a function
    of the messages and the ``AgentInfo`` that returns one of these.

    Args:
        steps: The answers, in order.
        repeat_last: Whether the last step answers every request after it.

    Returns:
        The [`ScriptedModel`][xnano.ai.testing.ScriptedModel]: give its ``model`` to a task
        model.

    Examples:
        ```python
        from xnano.ai.models.text import TextModel
        from xnano.ai.testing import scripted_model

        script = scripted_model('The door creaks open.')
        writer = TextModel(script.model)
        assert writer.generate('Describe the door.') == 'The door creaks open.'
        ```
    """
    queue = list(steps)
    record = ScriptedModel(
        model=FunctionModel(lambda messages, info: _next(messages, info))
    )

    def _next(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        record.calls.append(info)
        record.messages.append(list(messages))
        if not queue:
            raise AssertionError('The scripted model has no step left for this request.')
        step = queue[0] if repeat_last and len(queue) == 1 else queue.pop(0)
        if callable(step) and not isinstance(step, (BaseModel, type)):
            step = step(messages, info)
        return _step_response(step, info)

    async def _stream(
        messages: list[ModelMessage], info: AgentInfo
    ) -> AsyncIterator[str | DeltaToolCalls]:
        response = _next(messages, info)
        for part in response.parts:
            if isinstance(part, TextPart):
                # Word by word, the way a model streams its text.
                for piece in re.findall(r'\S+\s*|\s+', part.content):
                    yield piece
            elif isinstance(part, ToolCallPart):
                yield {
                    0: DeltaToolCall(
                        name=part.tool_name, json_args=part.args_as_json_str()
                    )
                }

    record.model = FunctionModel(_next, stream_function=_stream, model_name='scripted')
    return record


# -- replaying cases -----------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class ReplayCase:
    """
    One case of a replay: the answer expected, and the one the model gave.

    Attributes:
        expected: The option the case expects.
        choice: The option the model picked.
        probability: The probability the model gave its pick, or ``None`` on a language model.
        reordered_choice: The option it picked with the options in the reverse order, or
            ``None`` when the order was not checked.
        is_correct: Whether the pick is the option expected.
    """

    expected: str
    choice: str
    probability: float | None
    reordered_choice: str | None

    @property
    def is_correct(self) -> bool:
        """Whether the pick is the option expected."""
        return self.choice == self.expected


@dataclasses.dataclass(frozen=True, slots=True)
class Coverage:
    """
    How a threshold of probability would work: how many cases it answers, how many correctly.

    Attributes:
        threshold: The least probability a pick needs to be acted on.
        coverage: The share of the cases whose pick reaches the threshold.
        accuracy: The share of those that are correct, or ``None`` when none reach it.
    """

    threshold: float
    coverage: float
    accuracy: float | None


@dataclasses.dataclass(frozen=True, slots=True)
class ReplayReport:
    """
    What a replay found: every case, and the figures that choose a threshold.

    Attributes:
        cases: Every case, in the order of the file.
        accuracy: The share of the cases the model got right.
        majority_baseline: The accuracy of always picking the option most cases expect: the
            figure the model has to beat.
        calibration_error: The expected calibration error over ten bins of probability: how
            far the probabilities are from how often the picks are right, from ``0.0`` (the
            same) up. ``None`` on a language model, which gives no probabilities.
        order_sensitivity: The share of the cases whose pick changed when the options were
            given in the reverse order, or ``None`` when that was not checked.

    Examples:
        ```python
        from xnano.ai.models.decisions import ChoiceModel
        from xnano.ai.testing import ScriptedDecisionModel, replay

        model = ScriptedDecisionModel({'response': {'left': 0.8, 'right': 0.2}})
        cases = [
            {'evidence': {'wall': 'right'}, 'options': ['left', 'right'], 'expected': 'left'},
            {'evidence': {'wall': 'left'}, 'options': ['left', 'right'], 'expected': 'right'},
        ]
        report = replay(ChoiceModel(model), cases, should_check_order=False)
        assert report.accuracy == 0.5
        assert report.at_threshold(0.7).coverage == 1.0
        ```
    """

    cases: tuple[ReplayCase, ...]

    @property
    def accuracy(self) -> float:
        """The share of the cases the model got right."""
        return _share(case.is_correct for case in self.cases)

    @property
    def majority_baseline(self) -> float:
        """The accuracy of always picking the option most cases expect."""
        counts: dict[str, int] = {}
        for case in self.cases:
            counts[case.expected] = counts.get(case.expected, 0) + 1
        return max(counts.values(), default=0) / len(self.cases) if self.cases else 0.0

    @property
    def calibration_error(self) -> float | None:
        """The expected calibration error over ten bins of probability, or ``None``."""
        rated = [case for case in self.cases if case.probability is not None]
        if not rated:
            return None
        error = 0.0
        for index in range(10):
            low, high = index / 10, (index + 1) / 10
            in_bin = [
                case
                for case in rated
                if low <= case.probability < high  # type: ignore[operator]
                or (index == 9 and case.probability == 1.0)
            ]
            if in_bin:
                confidence = sum(case.probability for case in in_bin) / len(in_bin)  # type: ignore[misc]
                accuracy = _share(case.is_correct for case in in_bin)
                error += abs(accuracy - confidence) * len(in_bin) / len(rated)
        return error

    @property
    def order_sensitivity(self) -> float | None:
        """The share of the cases whose pick changed with the options reversed, or ``None``."""
        checked = [case for case in self.cases if case.reordered_choice is not None]
        if not checked:
            return None
        return _share(case.reordered_choice != case.choice for case in checked)

    def at_threshold(self, threshold: float) -> Coverage:
        """
        How acting only on picks of at least ``threshold`` would have worked.

        Args:
            threshold: The least probability, from ``0.0`` to ``1.0``.

        Raises:
            ValueError: ``threshold`` is outside ``0.0`` to ``1.0``.
        """
        if isinstance(threshold, bool) or not 0.0 <= threshold <= 1.0:
            raise ValueError(f'threshold must be from 0.0 to 1.0, but was {threshold!r}.')
        reached = [
            case
            for case in self.cases
            if case.probability is not None and case.probability >= threshold
        ]
        return Coverage(
            threshold=threshold,
            coverage=len(reached) / len(self.cases) if self.cases else 0.0,
            accuracy=_share(case.is_correct for case in reached) if reached else None,
        )


def _share(flags: Any) -> float:
    values = list(flags)
    return sum(1 for value in values if value) / len(values) if values else 0.0


def replay_async(
    model: ChoiceModel,
    cases: str | os.PathLike[str] | Sequence[Mapping[str, Any]],
    *,
    should_check_order: bool = True,
) -> Coroutine[Any, Any, ReplayReport]:
    """
    Run cases through a choice model once, and report how it did, with ``await``.

    Each case is a mapping, or a line of a JSONL file, with ``evidence`` (what the model
    judges), ``options`` (a list of labels, or a mapping from label to what it means), the
    ``expected`` label and, when it differs from the model's, a ``question``. The model is
    asked once per case, and once more with the options in the reverse order unless
    ``should_check_order`` is false; every figure of the report comes from those answers, with
    no new requests.

    Args:
        model: The [`ChoiceModel`][xnano.ai.models.decisions.ChoiceModel] to replay.
        cases: The cases, or the path of a JSONL file of them.
        should_check_order: Whether to ask each case again with the options reversed.

    Returns:
        A coroutine that gives the [`ReplayReport`][xnano.ai.testing.ReplayReport].

    Raises:
        ValueError: A case has no ``evidence``, ``options`` or ``expected``, or expects a
            label that is not one of its options.
    """
    loaded = _load_cases(cases)
    return _replay(model, loaded, should_check_order)


def replay(
    model: ChoiceModel,
    cases: str | os.PathLike[str] | Sequence[Mapping[str, Any]],
    *,
    should_check_order: bool = True,
) -> ReplayReport:
    """
    Run cases through a choice model once, and report how it did, waiting for it.

    The same as [`replay_async`][xnano.ai.testing.replay_async].
    """
    from xnano.ai.models import _run_blocking

    return _run_blocking(
        replay_async(model, cases, should_check_order=should_check_order), 'replay'
    )


def _load_cases(
    cases: str | os.PathLike[str] | Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    if isinstance(cases, (str, os.PathLike)):
        text = pathlib.Path(cases).read_text(encoding='utf-8')
        loaded = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        loaded = list(cases)
    for index, case in enumerate(loaded):
        missing = [key for key in ('evidence', 'options', 'expected') if key not in case]
        if missing:
            raise ValueError(
                f'Case {index} has no {", ".join(missing)}. Each case needs evidence, options '
                f'and the expected label.'
            )
        labels = list(case['options'])
        if case['expected'] not in labels:
            raise ValueError(
                f'Case {index} expects {case["expected"]!r}, which is not one of its options '
                f'{labels}.'
            )
    return loaded


def _reversed_options(options: Any) -> Any:
    if isinstance(options, Mapping):
        return dict(reversed(list(options.items())))
    return list(reversed(list(options)))


async def _replay(
    model: ChoiceModel, cases: list[Mapping[str, Any]], should_check_order: bool
) -> ReplayReport:
    results = []
    for case in cases:
        question = case.get('question')
        decision = await model.choose_async(
            case['evidence'], case['options'], question=question, no_change=None
        )
        reordered = None
        if should_check_order:
            # Saved answers do not depend on the order of the options, so this one is asked.
            is_reusing = model._is_reusing_answers
            model._is_reusing_answers = False
            try:
                again = await model.choose_async(
                    case['evidence'],
                    _reversed_options(case['options']),
                    question=question,
                    no_change=None,
                )
            finally:
                model._is_reusing_answers = is_reusing
            reordered = again.choice
        probability = None
        if decision.probabilities is not None:
            probability = decision.probabilities.get(decision.choice)
        results.append(
            ReplayCase(
                expected=str(case['expected']),
                choice=decision.choice,
                probability=probability,
                reordered_choice=reordered,
            )
        )
    return ReplayReport(cases=tuple(results))
