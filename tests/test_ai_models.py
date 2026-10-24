"""
tests.test_ai_models

The task models of `xnano.ai` on scripted models: what they send, what they return, and how
their blocking and awaited spellings behave on and off a canvas.
"""

from __future__ import annotations

import asyncio
import dataclasses
import importlib
import inspect
import random
import threading
from typing import Literal

import pytest

pytest.importorskip('pydantic_ai')

from pydantic import BaseModel  # noqa: E402
from pydantic_ai import Choice  # noqa: E402
from pydantic_ai.models.decision import NoulCriteria  # noqa: E402
from pydantic_ai.models.fallback import FallbackModel  # noqa: E402

import xnano  # noqa: E402
from xnano.ai import Observation, observe  # noqa: E402
from xnano.ai._observe import evidence_value  # noqa: E402
from xnano.ai.models import TaskModel, is_decision_model, run_to_completion  # noqa: E402
from xnano.ai.models.decisions import ChoiceModel, Decision, JudgeModel  # noqa: E402
from xnano.ai.models.state import StateModel  # noqa: E402
from xnano.ai.models.text import TextModel, stream_into, stream_into_async  # noqa: E402
from xnano.ai.testing import ScriptedDecisionModel, scripted_model  # noqa: E402
from xnano.errors import TerminalError  # noqa: E402
from xnano.events import Event  # noqa: E402


class TestModels:
    def test_every_model_is_exported_from_xnano_ai(self):
        import xnano.ai

        for module_name in ('art', 'components', 'decisions', 'music', 'state', 'text'):
            module = importlib.import_module(f'xnano.ai.models.{module_name}')
            for name in module.__all__:
                assert name in xnano.ai.__all__, name
                assert getattr(xnano.ai, name) is getattr(module, name), name
        assert xnano.ai.TaskModel is TaskModel

    def test_decision_models_are_known_by_name_and_by_kind(self):
        assert is_decision_model('typesafe:jev-1.14.0')
        assert is_decision_model('openai-decisions:gpt-6-luna')
        assert not is_decision_model('openrouter:anthropic/claude-sonnet-5-5')
        assert is_decision_model(ScriptedDecisionModel())
        assert not is_decision_model(scripted_model('x').model)
        assert not is_decision_model(None)

    def test_a_fallback_counts_as_its_first_model(self):
        decision_first = FallbackModel(ScriptedDecisionModel(), scripted_model('x').model)
        language_first = FallbackModel(scripted_model('x').model, ScriptedDecisionModel())
        assert is_decision_model(decision_first)
        assert not is_decision_model(language_first)

    def test_a_task_model_needs_no_credentials_until_it_is_asked(self):
        pick = ChoiceModel('typesafe:jev-1.14.0')
        assert pick.is_decision_model
        assert pick.last_result is None
        assert pick.details() == {}
        assert repr(pick) == "ChoiceModel('typesafe:jev-1.14.0')"

    def test_without_a_model_the_error_says_how_to_give_one(self):
        with pytest.raises(
            TerminalError, match=r'ChoiceModel\.choose\(\) has no model'
        ) as caught:
            ChoiceModel().choose('x', ['a', 'b'])
        assert caught.value.code == 'ai.model'

    def test_retries_must_be_a_whole_number(self):
        with pytest.raises(ValueError, match='retries must be a whole number'):
            ChoiceModel('typesafe:jev-1.14.0', retries=-1)

    def test_override_asks_another_model_inside_the_block(self):
        pick = ChoiceModel('typesafe:jev-1.14.0')
        with pick.override(model=ScriptedDecisionModel({'response': 'b'})):
            assert pick.choose('x', ['a', 'b']).choice == 'b'
        assert pick.model == 'typesafe:jev-1.14.0'

    def test_the_details_of_the_last_answer_are_kept(self):
        pick = ChoiceModel(ScriptedDecisionModel({'response': {'a': 0.3, 'b': 0.7}}))
        pick.choose('x', ['a', 'b'])
        assert pick.probabilities('response') == {'a': 0.3, 'b': 0.7, 'no_change': 0.0}
        assert pick.confidence('response') == 0.7
        assert pick.last_result is not None

    def test_a_model_that_cannot_answer_is_an_ai_model_error(self):
        def broken(messages, info):
            raise RuntimeError('unreachable')

        script = scripted_model(broken)
        with pytest.raises(RuntimeError, match='unreachable'):
            TextModel(script.model).generate('x')


class TestTwins:
    CLASSES = (ChoiceModel, JudgeModel, StateModel, TextModel)

    def test_every_async_method_has_a_blocking_twin_with_the_same_parameters(self):
        twins = []
        for cls in self.CLASSES:
            for name, method in inspect.getmembers(cls, inspect.isfunction):
                if not name.endswith('_async') or name.startswith('_'):
                    continue
                blocking = getattr(cls, name.removesuffix('_async'))
                assert inspect.signature(blocking).parameters.keys() == (
                    inspect.signature(method).parameters.keys()
                ), f'{cls.__name__}.{name}'
                twins.append(f'{cls.__name__}.{name}')
        assert len(twins) >= 6

    def test_the_stream_has_a_blocking_twin_too(self):
        assert inspect.signature(TextModel.stream).parameters.keys() == (
            inspect.signature(TextModel.stream_async).parameters.keys()
        )

    def test_run_to_completion_returns_the_result(self):
        async def answer() -> int:
            await asyncio.sleep(0)
            return 42

        assert run_to_completion(answer()) == 42

    def test_a_blocking_call_inside_an_event_loop_is_refused(self):
        pick = ChoiceModel(ScriptedDecisionModel())

        async def main() -> None:
            pick.choose('x', ['a', 'b'])

        with pytest.raises(
            TerminalError, match=r'await choose_async\(\.\.\.\)'
        ) as caught:
            asyncio.run(main())
        assert caught.value.code == 'ai.event_loop'

    def test_a_blocking_call_in_a_hook_of_a_live_canvas_is_refused(self):
        pick = ChoiceModel(ScriptedDecisionModel())
        failures: list[str] = []
        heard = threading.Event()
        with xnano.new(realtime=True, width=8, height=1) as canvas:

            @canvas.hook(on='key')
            def react(context: xnano.Context) -> None:
                try:
                    pick.choose(context, ['a', 'b'])
                except TerminalError as error:
                    # Only the text: the error's frames belong to the canvas's thread.
                    failures.append(str(error))
                heard.set()

            canvas.push(Event.key_press('a'))
            assert heard.wait(5)
        assert 'freeze the screen' in failures[0]

    def test_the_awaited_spelling_works_inside_an_event_loop(self):
        pick = ChoiceModel(ScriptedDecisionModel({'response': 'b'}))

        async def main() -> str:
            return (await pick.choose_async('x', ['a', 'b'])).choice

        assert asyncio.run(main()) == 'b'


class TestObserve:
    def test_a_canvas_is_its_cells_size_and_frame(self):
        with xnano.new(width=6, height=2) as canvas:
            canvas.screen.write('hello')
            observation = observe(canvas)
        assert observation.text == 'hello'
        assert (observation.width, observation.height) == (6, 2)
        assert observation.frame == {'index': 0, 'elapsed_seconds': 0.0, 'bpm': 120.0}
        assert observation.state is None and observation.event is None

    def test_a_placement_is_its_own_cells_and_position(self):
        with xnano.new(width=10, height=3) as canvas:
            card = canvas.screen.write('hi', x=3, y=1, border='rounded')
            observation = observe(card)
        assert observation.text == '╭──╮\n│hi│\n╰──╯'
        assert (observation.x, observation.y, observation.width, observation.height) == (
            3,
            1,
            4,
            3,
        )

    def test_a_context_is_its_placement_with_the_event(self):
        observations: list[Observation] = []
        with xnano.new(width=10, height=2) as canvas:
            label = canvas.screen.write('ok')

            @label.hook(on='key')
            def read(context: xnano.Context) -> None:
                observations.append(observe(context))

            canvas.push(Event.key_press('ctrl+s'))
            canvas.clock.step()
        assert observations[0].text == 'ok'
        assert observations[0].event == {
            'kind': 'key',
            'key': 's',
            'binding': 'ctrl+s',
            'type': 'press',
        }

    def test_a_custom_event_names_itself(self):
        observations: list[Observation] = []
        with xnano.new(width=10, height=2) as canvas:

            @canvas.hook(on='app.ping')
            def read(context: xnano.Context) -> None:
                observations.append(observe(context))

            canvas.push(Event.custom('app.ping'))
            canvas.clock.step()
        assert observations[0].event == {'kind': 'custom', 'name': 'app.ping'}

    def test_state_is_read_as_json(self):
        @dataclasses.dataclass
        class Score:
            points: int = 3

        with xnano.new(width=4, height=1, state=Score()) as canvas:
            assert observe(canvas).state == {'points': 3}

    def test_art_is_letters_with_their_colours(self):
        art = xnano.pixel_art(['RB', '.R'], {'R': '#ff0000', 'B': '#0000ff'})
        observation = observe(art)
        assert observation.text.splitlines()[:2] == ['AB', '.A']
        assert 'A = #ff0000' in observation.text and 'B = #0000ff' in observation.text
        assert (observation.width, observation.height) == (2, 2)

    def test_a_component_context_is_refused(self):
        @xnano.writable
        def badge(context: xnano.Context) -> str:
            observe(context)
            return 'x'

        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(TerminalError, match='writable or playable'):
                canvas.screen.write(badge())
                canvas.screen.render()

    def test_other_values_are_refused_with_the_way_to_give_them(self):
        with pytest.raises(TypeError, match='put them beside the canvas in a dictionary'):
            observe(42)

    def test_the_prompt_has_a_ruler_and_row_numbers(self):
        observation = Observation(text='ab\ncd', x=0, y=0, width=12, height=2)
        lines = observation.to_prompt().splitlines()
        assert lines[0].strip() == '0         1'
        assert lines[1].strip() == '012345678901'
        assert lines[2] == ' 0 |ab          |'
        assert lines[3] == ' 1 |cd          |'

    def test_evidence_reads_targets_inside_mappings_and_models(self):
        class Facts(BaseModel):
            score: int

        @dataclasses.dataclass
        class Player:
            name: str

        with xnano.new(width=4, height=1) as canvas:
            canvas.screen.write('hi')
            value = evidence_value(
                {
                    'screen': canvas,
                    'facts': Facts(score=2),
                    'player': Player('Ada'),
                    'tags': ('a',),
                }
            )
        assert value['screen']['text'] == 'hi'  # type: ignore[index]
        assert value['facts'] == {'score': 2}  # type: ignore[index]
        assert value['player'] == {'name': 'Ada'}  # type: ignore[index]
        assert value['tags'] == ['a']  # type: ignore[index]
        with pytest.raises(TypeError, match='is not JSON-like'):
            evidence_value({'when': object()})


class TestChoiceModel:
    def test_no_change_is_offered_first_and_the_options_after_it(self):
        model = ScriptedDecisionModel({'response': 'right'})
        decision = ChoiceModel(model).choose(
            {'x': 1}, {'left': 'step left', 'right': 'step right'}, question='Where?'
        )
        criteria = model.requests[-1].questions['response'].criteria
        assert list(criteria) == ['no_change', 'left', 'right']
        assert decision.choice == 'right' and decision.value == 'right'
        assert list(decision.probabilities or {}) == ['no_change', 'left', 'right']
        assert model.last_state == {'x': 1}

    def test_no_change_can_be_left_out(self):
        model = ScriptedDecisionModel()
        ChoiceModel(model).choose('x', ['a', 'b'], no_change=None)
        assert list(model.requests[-1].questions['response'].criteria) == ['a', 'b']

    def test_a_callable_value_is_called_when_picked(self):
        calls: list[str] = []
        options = {
            'cheer': Choice(
                'the player won', value=lambda: calls.append('cheer') or 'cheered'
            ),
            'warn': Choice('the player is in danger', value=lambda: calls.append('warn')),
        }
        decision = ChoiceModel(ScriptedDecisionModel({'response': 'cheer'})).choose(
            'x', options
        )
        assert decision.value == 'cheered'
        assert calls == ['cheer']

    def test_an_async_callable_value_is_awaited(self):
        async def fetch() -> str:
            await asyncio.sleep(0)
            return 'fetched'

        options = {'go': Choice('go', value=fetch), 'stay': 'stay'}
        decision = ChoiceModel(ScriptedDecisionModel({'response': 'go'})).choose(
            'x', options
        )
        assert decision.value == 'fetched'

    def test_the_same_evidence_is_answered_without_a_request(self):
        model = ScriptedDecisionModel({'response': 'a'})
        calls: list[int] = []
        pick = ChoiceModel(model)
        options = {'a': Choice('a', value=lambda: calls.append(1)), 'b': 'b'}
        first = pick.choose({'x': 1}, options)
        second = pick.choose({'x': 1}, options)
        assert len(model.requests) == 1
        assert first.probabilities == second.probabilities
        assert calls == [1, 1]
        pick.choose({'x': 2}, options)
        assert len(model.requests) == 2

    def test_reusing_answers_can_be_turned_off(self):
        model = ScriptedDecisionModel({'response': 'a'})
        pick = ChoiceModel(model, cache=False)
        pick.choose('x', ['a', 'b'])
        pick.choose('x', ['a', 'b'])
        assert len(model.requests) == 2

    def test_too_many_options_are_refused_before_a_request(self):
        with pytest.raises(ValueError, match='at most 255 options'):
            ChoiceModel(ScriptedDecisionModel()).choose(
                'x', [str(index) for index in range(300)]
            )

    def test_a_single_string_is_not_a_list_of_options(self):
        with pytest.raises(TypeError, match='single string'):
            ChoiceModel(ScriptedDecisionModel()).choose('x', 'left')  # type: ignore[arg-type]

    def test_a_language_model_picks_without_probabilities(self):
        script = scripted_model({'response': 'b'})
        decision = ChoiceModel(script.model).choose('x', ['a', 'b'], question='Which?')
        assert decision.choice == 'b'
        assert decision.probabilities is None and decision.margin is None


class TestDecision:
    def test_margin_is_the_lead_of_the_pick(self):
        decision = Decision('a', 'a', {'a': 0.6, 'b': 0.3, 'c': 0.1})
        assert round(decision.margin or 0, 6) == 0.3

    def test_sampling_follows_the_distribution_and_a_seed_repeats_it(self):
        decision = Decision('a', 'a', {'a': 0.6, 'b': 0.4})
        first = [decision.sample(random.Random(5)) for _ in range(5)]
        second = [decision.sample(random.Random(5)) for _ in range(5)]
        assert first == second
        draws = [decision.sample(random.Random(seed)) for seed in range(400)]
        assert 0.5 < draws.count('a') / len(draws) < 0.7

    def test_a_floor_keeps_unlikely_options_out(self):
        decision = Decision('a', 'a', {'a': 0.97, 'b': 0.03})
        assert {
            decision.sample(random.Random(seed), floor=0.05) for seed in range(50)
        } == {'a'}

    def test_temperature_must_be_above_zero(self):
        with pytest.raises(ValueError, match='temperature must be above 0'):
            Decision('a', 'a', {'a': 1.0}).sample(temperature=0)


class TestJudgeModel:
    def test_a_yes_needs_the_threshold(self):
        judge = JudgeModel(ScriptedDecisionModel({'answer': 0.6}))
        assert judge.ask('x', 'Is it done?').answer
        assert not judge.ask('x', 'Is it done?', threshold=0.7).answer

    def test_what_a_yes_and_a_no_mean_is_sent(self):
        model = ScriptedDecisionModel({'answer': True})
        JudgeModel(model).ask(
            'x', 'Is it full?', yes='every cell is filled', no='a cell is empty'
        )
        assert model.requests[-1].questions['answer'].criteria == NoulCriteria(
            true='every cell is filled', false='a cell is empty'
        )

    def test_several_questions_go_in_one_request(self):
        model = ScriptedDecisionModel({'is_full': 0.9, 'has_winner': 0.2})
        verdicts = JudgeModel(model).ask_many(
            'x', {'is_full': 'Is the board full?', 'has_winner': 'Did someone win?'}
        )
        assert len(model.requests) == 1
        assert verdicts['is_full'].answer and not verdicts['has_winner'].answer
        listed = JudgeModel(ScriptedDecisionModel()).ask_many('x', ['One?', 'Two?'])
        assert list(listed) == ['One?', 'Two?']

    def test_a_name_must_be_an_identifier(self):
        with pytest.raises(ValueError, match='must be a Python identifier'):
            JudgeModel(ScriptedDecisionModel()).ask_many('x', {'is full': 'Is it full?'})

    def test_a_rubric_gives_the_level_and_its_distribution(self):
        model = ScriptedDecisionModel({'level': {0: 0.1, 1: 0.6, 2: 0.3}})
        score = JudgeModel(model).score('x', ['empty', 'sparse', 'busy'])
        assert (score.level, score.label) == (1, 'sparse')
        assert score.probabilities == {'empty': 0.1, 'sparse': 0.6, 'busy': 0.3}
        assert round(score.expected or 0, 6) == 1.2

    def test_a_rubric_needs_two_levels(self):
        with pytest.raises(ValueError, match='at least two levels'):
            JudgeModel(ScriptedDecisionModel()).score('x', ['only'])

    def test_a_verdict_is_true_when_the_answer_is_yes(self):
        assert JudgeModel(ScriptedDecisionModel({'answer': 0.9})).ask('x', 'Done?')


@dataclasses.dataclass
class Goblin:
    mood: Literal['calm', 'wary', 'angry'] = 'calm'
    is_hostile: bool = False
    name: str = 'Grub'


def only_angry_goblins_attack(goblin: Goblin) -> bool:
    return goblin.mood == 'angry' or not goblin.is_hostile


class TestStateModel:
    def test_a_decision_model_picks_among_the_states_that_keep_the_rules(self):
        model = ScriptedDecisionModel({'response': 'mood=angry, is_hostile=true'})
        moods = StateModel(Goblin, model, invariants=[only_angry_goblins_attack])
        transition = moods.update(Goblin(), 'The hero stole its lunch.')
        offered = list(model.requests[-1].questions['response'].criteria)
        assert offered[0] == 'mood=calm, is_hostile=false'
        assert 'mood=calm, is_hostile=true' not in offered
        assert transition.after == Goblin(mood='angry', is_hostile=True)
        assert transition.changes == {
            'mood': ('calm', 'angry'),
            'is_hostile': (False, True),
        }
        assert (
            transition.confidence is not None
            and transition.confidence['is_hostile'] == 0.9
        )

    def test_keeping_the_state_is_no_change(self):
        model = ScriptedDecisionModel({'response': 'mood=calm, is_hostile=false'})
        transition = StateModel(Goblin, model).update(Goblin(), 'Nothing happened.')
        assert not transition.is_changed and transition.after is transition.before

    def test_many_combinations_are_asked_field_by_field(self):
        @dataclasses.dataclass
        class Switches:
            first: Literal['a', 'b', 'c', 'd', 'e', 'f', 'g'] = 'a'
            second: Literal['a', 'b', 'c', 'd', 'e', 'f', 'g'] = 'a'
            third: Literal['a', 'b', 'c', 'd', 'e', 'f', 'g'] = 'a'

        model = ScriptedDecisionModel({'first': 'c', 'second': 'a', 'third': 'g'})
        transition = StateModel(Switches, model).update(Switches(), 'flip')
        assert set(model.requests[-1].questions) == {'first', 'second', 'third'}
        assert transition.after == Switches(first='c', second='a', third='g')

    def test_a_language_model_is_sent_back_when_it_breaks_a_rule(self):
        script = scripted_model(
            {'mood': 'wary', 'is_hostile': True, 'reason': 'hmm'},
            {'mood': 'angry', 'is_hostile': True, 'reason': 'It is furious.'},
        )
        moods = StateModel(Goblin, script.model, invariants=[only_angry_goblins_attack])
        transition = moods.update(Goblin(), 'The hero stole its lunch.')
        assert transition.after == Goblin(mood='angry', is_hostile=True)
        assert transition.reason == 'It is furious.'
        assert len(script.calls) == 2

    def test_a_language_model_that_keeps_breaking_a_rule_is_an_error(self):
        script = scripted_model(
            {'mood': 'wary', 'is_hostile': True, 'reason': 'no'}, repeat_last=True
        )
        moods = StateModel(
            Goblin, script.model, invariants=[only_angry_goblins_attack], retries=1
        )
        with pytest.raises(TerminalError, match='break the invariants') as caught:
            moods.update(Goblin(), 'x')
        assert caught.value.code == 'ai.generation'

    def test_a_current_state_that_breaks_a_rule_is_refused(self):
        moods = StateModel(
            Goblin, ScriptedDecisionModel(), invariants=[only_angry_goblins_attack]
        )
        with pytest.raises(ValueError, match='only_angry_goblins_attack'):
            moods.update(Goblin(is_hostile=True), 'x')

    def test_a_decision_model_needs_a_field_with_few_values(self):
        @dataclasses.dataclass
        class Note:
            text: str = ''

        with pytest.raises(ValueError, match='no bool or Literal field'):
            StateModel(Note, ScriptedDecisionModel()).update(Note(), 'x')

    def test_the_state_must_be_a_dataclass_or_a_model(self):
        with pytest.raises(TypeError, match='dataclass or a Pydantic model'):
            StateModel(dict, ScriptedDecisionModel())  # type: ignore[arg-type]


class TestTextModel:
    def test_the_text_is_cut_after_the_sentences_it_may_have(self):
        writer = TextModel(scripted_model('One. Two! Three?').model, max_sentences=2)
        assert writer.generate('Write.') == 'One. Two!'

    def test_style_and_length_are_in_the_instructions(self):
        script = scripted_model('ok')
        TextModel(script.model, style='wry', max_sentences=1).generate('Write.')
        sent = str(script.messages[0])
        assert 'Write in this style: wry.' in sent and 'at most 1 sentences' in sent

    def test_an_empty_answer_is_asked_again(self):
        script = scripted_model('  ', 'Now something.')
        assert TextModel(script.model).generate('Write.') == 'Now something.'

    def test_no_text_after_the_retries_is_an_error(self):
        script = scripted_model('', repeat_last=True)
        with pytest.raises(TerminalError, match='no usable answer') as caught:
            TextModel(script.model, retries=1).generate('Write.')
        assert caught.value.code == 'ai.generation'

    def test_the_evidence_is_shown_with_the_request(self):
        script = scripted_model('ok')
        with xnano.new(width=8, height=1) as canvas:
            canvas.screen.write('door')
            TextModel(script.model).generate('Describe it.', canvas)
        assert 'door' in str(script.messages[0])

    def test_a_stream_gives_the_text_piece_by_piece(self):
        pieces = list(
            TextModel(scripted_model('Once upon a time.').model).stream('Begin.')
        )
        assert len(pieces) > 1 and ''.join(pieces) == 'Once upon a time.'

    def test_breaking_out_of_a_stream_stops_it(self):
        stream = TextModel(scripted_model('a b c d e f').model).stream('Begin.')
        assert next(iter(stream)) == 'a '
        stream.close()  # type: ignore[attr-defined]

    def test_stream_into_shows_the_text_in_a_placement(self):
        writer = TextModel(scripted_model('Thunder rolls.').model)
        with xnano.new(width=20, height=1) as canvas:
            label = canvas.screen.write('')
            assert stream_into(label, writer.stream('Narrate.')) == 'Thunder rolls.'
            assert canvas.screen.render() == 'Thunder rolls.'

    def test_a_cancelled_stream_keeps_what_arrived(self):
        async def pieces():
            yield 'kept '
            await asyncio.sleep(10)
            yield 'lost'

        async def main() -> str:
            async with xnano.new(width=20, height=1) as canvas:
                label = canvas.screen.write('')
                task = asyncio.ensure_future(
                    stream_into_async(label, pieces(), debounce_seconds=60)
                )
                await asyncio.sleep(0.01)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
                return canvas.screen.render()

        assert asyncio.run(main()) == 'kept'

    def test_debounce_must_not_be_negative(self):
        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(ValueError, match='debounce_seconds must be 0 or more'):
                stream_into(canvas.screen.write(''), ['a'], debounce_seconds=-1)


def test_a_task_model_subclass_can_add_its_instructions():
    class Narrator(TaskModel):
        _task_instructions = 'Narrate.'

    assert (
        Narrator('x', instructions='Be brief.')._joined_instructions()
        == 'Narrate.\n\nBe brief.'
    )
