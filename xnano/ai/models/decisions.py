"""
xnano.ai.models.decisions

Picking one of a few options, and answering yes/no questions and rubrics, about evidence.
"""

from __future__ import annotations

import collections
import dataclasses
import hashlib
import inspect
import json
import random
from collections.abc import Coroutine, Mapping, Sequence
from typing import Annotated, Any, Final, cast

from pydantic import Field, WithJsonSchema, create_model
from pydantic_ai import BoolCriteria, Choice, Choices

from xnano.ai._observe import evidence_for, snapshot
from xnano.ai.models import TaskModel, _run_blocking

__all__ = ['ChoiceModel', 'Decision', 'JudgeModel', 'Options', 'Score', 'Verdict']

NO_CHANGE: Final = 'no_change'
"""The label of the option that keeps things as they are."""

MOST_OPTIONS: Final = 255
"""The most options one decision can offer, which is what decision backends accept."""

_UNSET: Final = Choice().value
"""What a ``Choice`` built without a ``value`` holds, so that its key is its value."""

_SAVED_ANSWERS: Final = 256
"""How many answers a task model keeps for evidence it is asked about again."""

Options = Sequence[str] | Mapping[str, 'str | Choice[Any]']
"""
The options of a decision: labels, a mapping from label to what it means, or a mapping from
label to a pydantic-ai ``Choice`` whose ``value`` is what the label stands for. A callable
``value`` is called when its option is picked, and the decision's ``value`` is what it returned.
"""


@dataclasses.dataclass(frozen=True)
class Decision:
    """
    The option a [`ChoiceModel`][xnano.ai.models.decisions.ChoiceModel] picked, and how sure it was.

    Attributes:
        choice: The label that was picked, such as ``'left'``, or ``'no_change'``.
        value: What the label stands for: the ``Choice`` value, what a callable value returned,
            or the label itself.
        probabilities: The probability of every option on a decision model, in the order the
            options were offered, or ``None`` on a language model.
        confidence: The backend's own confidence in the pick, or ``None``. It is not how often
            the pick is right; threshold on ``margin`` instead.

    Examples:
        ```python
        import random

        from xnano.ai.models.decisions import Decision

        decision = Decision(
            choice='left', value='left', probabilities={'left': 0.7, 'right': 0.3}
        )
        assert round(decision.margin, 2) == 0.4
        assert decision.sample(random.Random(3)) in ('left', 'right')
        ```
    """

    choice: str
    value: object
    probabilities: dict[str, float] | None = None
    confidence: float | None = None

    @property
    def margin(self) -> float | None:
        """
        How far the pick is ahead: its probability minus the next one's, or ``None``.

        A margin near ``0`` means two options were nearly tied. Below the margin an action is
        worth taking for, keep things as they are.
        """
        probabilities = self.probabilities
        if not probabilities:
            return None
        ordered = sorted(probabilities.values(), reverse=True)
        return ordered[0] - (ordered[1] if len(ordered) > 1 else 0.0)

    def sample(
        self,
        source: random.Random | None = None,
        *,
        temperature: float = 1.0,
        floor: float = 0.0,
    ) -> str:
        """
        Draw an option from the distribution instead of always taking the likeliest.

        Use it for variety that still follows what the model thought likely: a character that
        mostly, but not always, does the expected thing.

        Args:
            source: Where the random numbers come from, such as ``random.Random(7)`` for the
                same draws on every run; Python's shared generator when ``None``.
            temperature: Above ``1`` the options are drawn more evenly, below ``1`` the
                likeliest is drawn more often; it must be above ``0``.
            floor: Options less likely than this are never drawn.

        Returns:
            The label drawn, or ``choice`` on a language model, which gives no distribution.

        Raises:
            ValueError: ``temperature`` is not above ``0``.
        """
        if not temperature > 0:
            raise ValueError(
                f'temperature must be above 0, but was {temperature!r}. Use 1.0 to draw as '
                f'the model gave the odds, more to draw more evenly, less to favour the '
                f'likeliest option.'
            )
        probabilities = self.probabilities
        if not probabilities:
            return self.choice
        kept = {
            label: probability ** (1.0 / temperature)
            for label, probability in probabilities.items()
            if probability >= floor and probability > 0
        }
        if not kept:
            return self.choice
        draw = (source or random).random() * sum(kept.values())
        for label, weight in kept.items():
            draw -= weight
            if draw <= 0:
                return label
        return next(reversed(kept))


@dataclasses.dataclass(frozen=True)
class Verdict:
    """
    The answer of a [`JudgeModel`][xnano.ai.models.decisions.JudgeModel] to a yes/no question.

    Attributes:
        question: The question that was asked.
        answer: Whether the answer is yes: on a decision model, whether ``probability`` is at
            least ``threshold``.
        probability: How likely a yes is on a decision model, or ``None`` on a language model.
        threshold: The probability a yes needed.
    """

    question: str
    answer: bool
    probability: float | None = None
    threshold: float = 0.5

    def __bool__(self) -> bool:
        return self.answer


@dataclasses.dataclass(frozen=True)
class Score:
    """
    The level of a rubric a [`JudgeModel`][xnano.ai.models.decisions.JudgeModel] placed the evidence at.

    Attributes:
        level: The position of the level in the rubric, from ``0``.
        label: The level as it was written in the rubric.
        probabilities: The probability of each level, by its label, on a decision model, or
            ``None`` on a language model.
        expected: The probability-weighted mean level on a decision model, between two levels
            when the model hesitated, or ``None``.
    """

    level: int
    label: str
    probabilities: dict[str, float] | None = None
    expected: float | None = None


def _offered(
    options: Options, no_change: str | None
) -> dict[str, tuple[str | None, object]]:
    """Each option's label with what it means and what it stands for, ``no_change`` first."""
    if isinstance(options, str):
        raise TypeError(
            f'options takes a list of labels or a mapping from label to its meaning, but got '
            f'the single string {options!r}. Write options=[{options!r}, ...] instead.'
        )
    offered: dict[str, tuple[str | None, object]] = {}
    if no_change is not None:
        offered[NO_CHANGE] = (no_change, _UNSET)
    if isinstance(options, Mapping):
        for label, option in options.items():
            if isinstance(option, Choice):
                offered[str(label)] = (option.description, option.value)
            else:
                offered[str(label)] = (str(option), _UNSET)
    else:
        for label in options:
            offered[str(label)] = (None, _UNSET)
    if len(offered) - (no_change is not None) < 1:
        raise ValueError(
            'A decision needs at least one option besides no_change, such as '
            "options=['left', 'right'] or options={'left': 'step left'}."
        )
    if len(offered) > MOST_OPTIONS:
        raise ValueError(
            f'A decision can offer at most {MOST_OPTIONS} options, but {len(offered)} were '
            f'given. Shortlist them in code first: models pick best among about 12 to 20.'
        )
    return offered


async def _resolve(value: object, label: str) -> object:
    """What a picked label stands for: its value, or what its callable value returned."""
    if value is _UNSET:
        return label
    if callable(value):
        result = value()
        if inspect.isawaitable(result):
            result = await result
        return result
    return value


def _resolve_blocking(value: object, label: str, operation: str) -> object:
    """``_resolve`` for a blocking call: the callable runs on the calling thread."""
    if value is _UNSET:
        return label
    if callable(value):
        result = value()
        if inspect.isawaitable(result):
            result = _run_blocking(result, operation)
        return result
    return value


class _SavedAnswers:
    """The answers a task model got, by the evidence and the question they were for."""

    __slots__ = ('_answers',)

    def __init__(self) -> None:
        self._answers: collections.OrderedDict[str, object] = collections.OrderedDict()

    def get(self, key: str) -> object | None:
        answer = self._answers.get(key)
        if answer is not None:
            self._answers.move_to_end(key)
        return answer

    def put(self, key: str, answer: object) -> None:
        self._answers[key] = answer
        self._answers.move_to_end(key)
        while len(self._answers) > _SAVED_ANSWERS:
            self._answers.popitem(last=False)


def _answer_key(*parts: object) -> str:
    text = json.dumps(parts, sort_keys=True, default=repr)
    return hashlib.sha256(text.encode()).hexdigest()


class _AskingModel(TaskModel):
    """A task model that keeps its answers, so the same question costs one request."""

    def __init__(self, *arguments: Any, **keywords: Any) -> None:
        super().__init__(*arguments, **keywords)
        self._is_reusing_answers = keywords.get('cache', True)
        self._saved = _SavedAnswers()

    def _save(self, key: str, answer: object) -> None:
        """Keep an answer for the same question later, unless answers are not reused."""
        if self._is_reusing_answers:
            self._saved.put(key, answer)

    def _saved_answer(self, *parts: object) -> tuple[str, object | None]:
        model = self.model
        name = (
            model
            if isinstance(model, str) or model is None
            else (f'{model.system}:{model.model_name}')
        )
        key = _answer_key(name, *parts)
        return key, (self._saved.get(key) if self._is_reusing_answers else None)

    def _distribution(self) -> dict[str, float] | None:
        """The one pick-one distribution of the last answer, whatever its field is called."""
        distributions = self.details().get('probabilities', {})
        distribution = distributions.get('response')
        if distribution is None and len(distributions) == 1:
            distribution = next(iter(distributions.values()))
        if distribution is None:
            return None
        return {str(option): float(value) for option, value in distribution.items()}


class ChoiceModel(_AskingModel):
    """
    Pick one of a few options for what is on the canvas.

    On a decision model (``'typesafe:jev-1.14.0'``) the answer comes with the probability of
    every option, so a program can act only when the pick is clear. A named ``no_change``
    option is always offered first, because "keep things as they are" is a better answer than a
    forced guess. Identical evidence and options are answered from the saved answer, with no
    request.

    Examples:
        ```python
        from xnano.ai.models.decisions import ChoiceModel
        from xnano.ai.testing import ScriptedDecisionModel

        pick = ChoiceModel(ScriptedDecisionModel({'response': {'left': 0.8, 'right': 0.2}}))
        decision = pick.choose(
            {'hero': 'at the right wall'},
            {'left': 'the hero should step left', 'right': 'the hero should step right'},
            question='Where should the hero go?',
        )
        assert decision.choice == 'left' and decision.margin > 0.5
        ```
    """

    def choose_async(
        self,
        evidence: object,
        options: Options,
        *,
        question: str | None = None,
        no_change: str | None = 'nothing needs to change now',
    ) -> Coroutine[Any, Any, Decision]:
        """
        Pick one of the options for the evidence, with ``await``.

        The evidence is read when this is called, so the model judges the canvas as it was
        then, and the options are checked then too; await the result for the decision.

        Args:
            evidence: What to decide about: a context, canvas or placement, or a mapping of
                them with the facts your program knows; see [`Evidence`][xnano.ai.Evidence].
            options: The labels to pick from, with what each means; see
                [`Options`][xnano.ai.models.decisions.Options].
            question: What is being decided, such as ``'What should the hero do now?'``.
            no_change: What the ``no_change`` option means, or ``None`` to offer only your
                options.

        Returns:
            A coroutine that gives the [`Decision`][xnano.ai.models.decisions.Decision].

        Raises:
            ValueError: No option was given besides ``no_change``, or more than 255.
            TerminalError: The model could not be reached (``ai.model``), when awaited.
        """
        offered = _offered(options, no_change)
        return self._choose(snapshot(evidence), offered, question)

    def choose(
        self,
        evidence: object,
        options: Options,
        *,
        question: str | None = None,
        no_change: str | None = 'nothing needs to change now',
    ) -> Decision:
        """
        Pick one of the options for the evidence, waiting for the answer.

        The same as [`choose_async`][xnano.ai.models.decisions.ChoiceModel.choose_async], for code that does not
        await. A callable value of the option picked is called on the calling thread, so it
        may change the canvas.
        """
        offered = _offered(options, no_change)
        label, probabilities, confidence = _run_blocking(
            self._pick(snapshot(evidence), offered, question), 'choose'
        )
        value = _resolve_blocking(offered[label][1], label, 'choose')
        return Decision(
            choice=label, value=value, probabilities=probabilities, confidence=confidence
        )

    async def _choose(
        self,
        evidence: object,
        offered: dict[str, tuple[str | None, object]],
        question: str | None,
    ) -> Decision:
        label, probabilities, confidence = await self._pick(evidence, offered, question)
        value = await _resolve(offered[label][1], label)
        return Decision(
            choice=label, value=value, probabilities=probabilities, confidence=confidence
        )

    async def _pick(
        self,
        evidence: object,
        offered: dict[str, tuple[str | None, object]],
        question: str | None,
    ) -> tuple[str, dict[str, float] | None, float | None]:
        """The label the model picked, with the distribution and the confidence."""
        prompt = evidence_for(evidence, is_decision_model=self.is_decision_model)
        meanings = {label: meaning for label, (meaning, _) in offered.items()}
        key, saved = self._saved_answer('choose', prompt, question, meanings)
        if isinstance(saved, tuple):
            return cast('tuple[str, dict[str, float] | None, float | None]', saved)
        choices = Choices(
            {label: meaning or label for label, meaning in meanings.items()},
            name='choice',
            description=question,
        )
        asked = (
            prompt
            if self.is_decision_model or question is None
            else f'{question}\n\n{prompt}'
        )
        result = await self._ask(asked, choices, operation='choose')
        label = str(result.output)
        distribution = self._distribution()
        probabilities = (
            None
            if distribution is None
            else {option: distribution.get(option, 0.0) for option in offered}
        )
        answer = (label, probabilities, self.confidence('response'))
        self._save(key, answer)
        return answer


def _probability_of_yes(confidence: float | None, answer: bool) -> float | None:
    """A yes/no's probability of yes from the confidence a decision model reports for it."""
    if confidence is None:
        return None
    return (1.0 + confidence) / 2.0 if answer else (1.0 - confidence) / 2.0


def _yes_or_no(question: str, yes: str | None, no: str | None) -> Any:
    """The annotated ``bool`` that asks ``question``, with what a yes and a no mean."""
    if yes is None and no is None:
        return Annotated[bool, Field(description=question)]
    return Annotated[
        bool,
        BoolCriteria(true=yes or f'Yes: {question}', false=no or f'No: {question}'),
        Field(description=question),
    ]


def _check_threshold(threshold: float) -> None:
    if isinstance(threshold, bool) or not 0.0 <= threshold <= 1.0:
        raise ValueError(
            f'threshold must be a probability from 0 to 1, but was {threshold!r}. 0.5 takes '
            f'the likelier answer; 0.7 asks for a clearer yes.'
        )


class JudgeModel(_AskingModel):
    """
    Answer yes/no questions, and place evidence on a rubric.

    On a decision model each answer comes with the probability of a yes, and ``threshold``
    sets how sure a yes has to be. Ask one question per thing you want to know, with "yes"
    meaning that it is true; several questions about the same evidence go in one request with
    [`ask_many`][xnano.ai.models.decisions.JudgeModel.ask_many].

    Examples:
        ```python
        from xnano.ai.models.decisions import JudgeModel
        from xnano.ai.testing import ScriptedDecisionModel

        judge = JudgeModel(ScriptedDecisionModel({'answer': 0.9}))
        verdict = judge.ask('Ada typed: "Ada"', 'Has the user finished typing their name?')
        assert verdict.answer and verdict.probability > 0.8
        ```
    """

    def ask_async(
        self,
        evidence: object,
        question: str,
        *,
        threshold: float = 0.5,
        yes: str | None = None,
        no: str | None = None,
    ) -> Coroutine[Any, Any, Verdict]:
        """
        Answer a yes/no question about the evidence, with ``await``.

        The evidence is read when this is called; await the result for the verdict.

        Args:
            evidence: What the question is about; see [`Evidence`][xnano.ai.Evidence].
            question: The question, such as ``'Is the board full?'``.
            threshold: How likely a yes has to be to count, on a decision model.
            yes: What a yes means, when the question alone leaves it open.
            no: What a no means.

        Returns:
            A coroutine that gives the [`Verdict`][xnano.ai.models.decisions.Verdict].

        Raises:
            ValueError: ``threshold`` is not from 0 to 1.
            TerminalError: The model could not be reached (``ai.model``), when awaited.
        """
        _check_threshold(threshold)
        return self._ask_one(snapshot(evidence), (question, yes, no), threshold)

    async def _ask_one(
        self,
        evidence: object,
        question: tuple[str, str | None, str | None],
        threshold: float,
    ) -> Verdict:
        verdicts = await self._judge(evidence, {'answer': question}, threshold)
        return verdicts['answer']

    def ask(
        self,
        evidence: object,
        question: str,
        *,
        threshold: float = 0.5,
        yes: str | None = None,
        no: str | None = None,
    ) -> Verdict:
        """
        Answer a yes/no question about the evidence, waiting for the answer.

        The same as [`ask_async`][xnano.ai.models.decisions.JudgeModel.ask_async], for code that does not await.
        """
        return _run_blocking(
            self.ask_async(evidence, question, threshold=threshold, yes=yes, no=no), 'ask'
        )

    def ask_many_async(
        self,
        evidence: object,
        questions: Sequence[str] | Mapping[str, str],
        *,
        threshold: float = 0.5,
    ) -> Coroutine[Any, Any, dict[str, Verdict]]:
        """
        Answer several yes/no questions about the same evidence in one request, with ``await``.

        The evidence is read when this is called; await the result for the verdicts.

        Args:
            evidence: What the questions are about; see [`Evidence`][xnano.ai.Evidence].
            questions: The questions, or a mapping from a name of your own to each question.
            threshold: How likely a yes has to be to count, on a decision model.

        Returns:
            A coroutine that gives each [`Verdict`][xnano.ai.models.decisions.Verdict], by its question, or by
            its name when a mapping was given.

        Raises:
            ValueError: No question was given, a name is not a Python identifier, or
                ``threshold`` is not from 0 to 1.
            TerminalError: The model could not be reached (``ai.model``).
        """
        _check_threshold(threshold)
        if isinstance(questions, str):
            raise TypeError(
                f'ask_many() takes a list of questions, but got the single string '
                f'{questions!r}. Use ask() for one question.'
            )
        if isinstance(questions, Mapping):
            named = {str(name): question for name, question in questions.items()}
            for name in named:
                if not name.isidentifier():
                    raise ValueError(
                        f'The name {name!r} of a question must be a Python identifier, such '
                        f"as 'is_full', because it names the answer."
                    )
        else:
            named = {
                f'question_{index}': question
                for index, question in enumerate(questions, 1)
            }
        if not named:
            raise ValueError('ask_many() needs at least one question.')
        return self._ask_several(
            snapshot(evidence), named, threshold, is_named=isinstance(questions, Mapping)
        )

    async def _ask_several(
        self, evidence: object, named: dict[str, str], threshold: float, *, is_named: bool
    ) -> dict[str, Verdict]:
        verdicts = await self._judge(
            evidence,
            {name: (question, None, None) for name, question in named.items()},
            threshold,
        )
        if is_named:
            return verdicts
        return {verdict.question: verdict for verdict in verdicts.values()}

    def ask_many(
        self,
        evidence: object,
        questions: Sequence[str] | Mapping[str, str],
        *,
        threshold: float = 0.5,
    ) -> dict[str, Verdict]:
        """
        Answer several yes/no questions about the same evidence in one request, waiting.

        The same as [`ask_many_async`][xnano.ai.models.decisions.JudgeModel.ask_many_async], for code that does
        not await.
        """
        return _run_blocking(
            self.ask_many_async(evidence, questions, threshold=threshold),
            'ask_many',
        )

    async def _judge(
        self,
        evidence: object,
        questions: dict[str, tuple[str, str | None, str | None]],
        threshold: float,
    ) -> dict[str, Verdict]:
        prompt = evidence_for(evidence, is_decision_model=self.is_decision_model)
        key, saved = self._saved_answer('ask', prompt, questions)
        if isinstance(saved, dict):
            probabilities_and_answers: dict[str, tuple[bool, float | None]] = saved
        else:
            fields: dict[str, Any] = {
                name: (_yes_or_no(question, yes, no), ...)
                for name, (question, yes, no) in questions.items()
            }
            output_type = create_model(
                'Answers', __doc__='Questions about the evidence.', **fields
            )
            asked = prompt
            if not self.is_decision_model:
                listed = '\n'.join(
                    f'- {name}: {question}'
                    for name, (question, _, _) in questions.items()
                )
                asked = f'Answer each question about the evidence.\n{listed}\n\n{prompt}'
            result = await self._ask(asked, output_type, operation='ask')
            probabilities_and_answers = {}
            for name in questions:
                answer = bool(getattr(result.output, name))
                probabilities_and_answers[name] = (
                    answer,
                    _probability_of_yes(self.confidence(name), answer),
                )
            self._save(key, probabilities_and_answers)
        verdicts = {}
        for name, (question, _, _) in questions.items():
            answer, probability = probabilities_and_answers[name]
            verdicts[name] = Verdict(
                question=question,
                answer=answer if probability is None else probability >= threshold,
                probability=probability,
                threshold=threshold,
            )
        return verdicts

    def score_async(
        self, evidence: object, levels: Sequence[str], *, question: str | None = None
    ) -> Coroutine[Any, Any, Score]:
        """
        Place the evidence on a rubric of levels, with ``await``.

        The evidence is read when this is called; await the result for the score.

        Describe each level as a situation (``'two or three items on the screen'``), not as a
        degree (``'somewhat busy'``). A rubric is the least reliable kind of answer on current
        decision models: for anything that matters, ask a yes/no or pick one option instead.

        Args:
            evidence: What to score; see [`Evidence`][xnano.ai.Evidence].
            levels: The levels in order, from lowest to highest; at least two.
            question: What the rubric measures, such as ``'How busy is the screen?'``.

        Returns:
            A coroutine that gives the [`Score`][xnano.ai.models.decisions.Score].

        Raises:
            ValueError: Fewer than two levels were given.
            TerminalError: The model could not be reached (``ai.model``), when awaited.
        """
        if isinstance(levels, str) or len(levels) < 2:
            raise ValueError(
                f'score() takes at least two levels, from lowest to highest, such as '
                f"['empty', 'sparse', 'busy'], but got {levels!r}."
            )
        labels = [str(level) for level in levels]
        return self._score(
            snapshot(evidence), labels, question or 'Which level describes the evidence?'
        )

    async def _score(
        self, evidence: object, labels: list[str], asked_question: str
    ) -> Score:
        prompt = evidence_for(evidence, is_decision_model=self.is_decision_model)
        key, saved = self._saved_answer('score', prompt, asked_question, labels)
        if isinstance(saved, tuple):
            level, probabilities = saved
        else:
            rubric = Annotated[
                int,
                Field(ge=0, le=len(labels) - 1, description=asked_question),
                WithJsonSchema(
                    {
                        'type': 'integer',
                        'description': asked_question,
                        'anyOf': [
                            {'const': index, 'description': label}
                            for index, label in enumerate(labels)
                        ],
                    }
                ),
            ]
            output_type = create_model(
                'Rubric', __doc__=asked_question, level=(rubric, ...)
            )
            asked = prompt
            if not self.is_decision_model:
                listed = '\n'.join(
                    f'{index}: {label}' for index, label in enumerate(labels)
                )
                asked = f'{asked_question} Answer with the number of the level.\n{listed}\n\n{prompt}'
            result = await self._ask(asked, output_type, operation='score')
            level = int(result.output.level)
            distribution = self.details().get('probabilities', {}).get('level')
            probabilities = (
                None
                if distribution is None
                else {
                    labels[int(option)]: float(value)
                    for option, value in distribution.items()
                    if str(option).isdigit() and int(option) < len(labels)
                }
            )
            self._save(key, (level, probabilities))
        expected = (
            None
            if probabilities is None
            else sum(
                labels.index(label) * value for label, value in probabilities.items()
            )
        )
        return Score(
            level=level,
            label=labels[level],
            probabilities=probabilities,
            expected=expected,
        )

    def score(
        self, evidence: object, levels: Sequence[str], *, question: str | None = None
    ) -> Score:
        """
        Place the evidence on a rubric of levels, waiting for the answer.

        The same as [`score_async`][xnano.ai.models.decisions.JudgeModel.score_async], for code that does not
        await.
        """
        return _run_blocking(
            self.score_async(evidence, levels, question=question), 'score'
        )
