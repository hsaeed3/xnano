"""
tests.test_ai_plugins

Background runs that finish as an event on the canvas, and the ``decide()`` and ``watch()``
plugins built on them, on scripted models.
"""

from __future__ import annotations

import asyncio
import threading

import pytest

pytest.importorskip('pydantic_ai')

from pydantic_ai import Choice  # noqa: E402

import xnano  # noqa: E402
import xnano_core as _core  # noqa: E402
from xnano.ai import background, decide, watch  # noqa: E402
from xnano.ai.models.decisions import ChoiceModel, JudgeModel  # noqa: E402
from xnano.ai.testing import ScriptedDecisionModel  # noqa: E402
from xnano.errors import TerminalError  # noqa: E402
from xnano.events import Event  # noqa: E402


def press(canvas: xnano.Canvas, key: str = 'enter') -> None:
    canvas.push(Event.key_press(key))
    canvas.clock.step()


class TestBackground:
    def test_a_manual_canvas_hears_the_answer_in_the_step_that_asked(self):
        pick = ChoiceModel(ScriptedDecisionModel({'response': 'jump'}))
        heard: list[str] = []
        with xnano.new(width=8, height=1) as canvas:
            runs = background(canvas)

            @canvas.hook(on='key', keys='enter')
            def ask(context: xnano.Context) -> None:
                runs.start(pick.choose_async(context, ['jump', 'duck']), name='move')

            @canvas.hook(on='ai.move')
            def moved(context: xnano.Context) -> None:
                heard.append(runs.result(context).choice)

            press(canvas)
            assert heard == ['jump']

    def test_the_same_canvas_has_the_same_runs(self):
        with xnano.new(width=8, height=1) as canvas:
            assert background(canvas) is background(canvas)

    def test_the_evidence_is_read_when_the_call_is_made(self):
        model = ScriptedDecisionModel({'response': 'a'})
        pick = ChoiceModel(model)
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.screen.write('before')
            call = pick.choose_async(canvas, ['a', 'b'])
            label.text = 'after'
            background(canvas).start(call, name='look')
        assert model.last_state['text'] == 'before'  # type: ignore[index]

    def test_an_error_is_raised_where_the_result_is_read(self):
        async def broken() -> None:
            raise RuntimeError('no answer')

        errors: list[str] = []
        with xnano.new(width=8, height=1) as canvas:
            runs = background(canvas)
            run = runs.start(broken(), name='broken')

            @canvas.hook(on='ai.broken')
            def read(context: xnano.Context) -> None:
                with pytest.raises(RuntimeError, match='no answer'):
                    runs.result(context)
                errors.append('read')

            canvas.clock.step()
        assert errors == ['read']
        assert isinstance(run.error, RuntimeError)

    def test_a_name_must_be_a_name(self):
        async def nothing() -> None:
            return None

        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(ValueError, match='letters, digits and underscores'):
                background(canvas).start(nothing(), name='not a name')

    def test_reading_a_result_from_another_event_is_explained(self):
        with xnano.new(width=8, height=1) as canvas:
            runs = background(canvas)
            caught: list[str] = []

            @canvas.hook(on='key')
            def read(context: xnano.Context) -> None:
                with pytest.raises(
                    TerminalError, match='not the event of a background run'
                ):
                    runs.result(context)
                caught.append('explained')

            press(canvas, 'a')
        assert caught == ['explained']

    def test_a_result_before_it_finished_is_explained(self):
        async def slow() -> int:
            await asyncio.sleep(10)
            return 1

        async def main() -> None:
            async with xnano.new(width=8, height=1) as canvas:
                run = background(canvas).start(slow(), name='slow')
                await asyncio.sleep(0)
                with pytest.raises(TerminalError, match='has not finished yet'):
                    run.result  # noqa: B018
                run.cancel()

        asyncio.run(main())

    def test_a_newer_run_replaces_the_older_one(self):
        async def answer(value: str, delay: float) -> str:
            await asyncio.sleep(delay)
            return value

        async def main() -> list[str]:
            async with xnano.new(width=8, height=1) as canvas:
                runs = background(canvas)
                heard: list[str] = []
                canvas.hook(
                    lambda context: heard.append(runs.result(context)), on='ai.answer'
                )
                first = runs.start(answer('first', 0.05), name='answer')
                await asyncio.sleep(0)
                runs.start(answer('second', 0.01), name='answer')
                await canvas.wait_for_tasks_async()
                canvas.clock.step()
                assert first.is_cancelled
                return heard

        assert asyncio.run(main()) == ['second']

    def test_queued_runs_finish_in_order(self):
        finished: list[str] = []

        async def answer(value: str, delay: float) -> str:
            await asyncio.sleep(delay)
            finished.append(value)
            return value

        async def main() -> None:
            async with xnano.new(width=8, height=1) as canvas:
                runs = background(canvas)
                runs.start(answer('first', 0.03), name='answer', if_running='queue')
                await asyncio.sleep(0)
                runs.start(answer('second', 0.0), name='answer', if_running='queue')
                await canvas.wait_for_tasks_async()

        asyncio.run(main())
        assert finished == ['first', 'second']

    def test_a_canvas_that_runs_by_itself_hears_the_answer(self):
        pick = ChoiceModel(ScriptedDecisionModel({'response': 'duck'}))
        heard: list[str] = []
        landed = threading.Event()
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            runs = background(canvas)

            @canvas.hook(on='ai.move')
            def moved(context: xnano.Context) -> None:
                heard.append(runs.result(context).choice)
                landed.set()

            runs.start(pick.choose_async({'x': 1}, ['jump', 'duck']), name='move')
            assert landed.wait(5)
        assert heard == ['duck']


class TestDecide:
    def test_a_decision_is_kept_and_its_style_applied(self):
        pick = ChoiceModel(
            ScriptedDecisionModel({'response': {'warn': 0.9, 'rest': 0.1}})
        )
        with xnano.new(width=20, height=1) as canvas:
            hero = canvas.screen.write('hero')
            hero | decide(
                pick,
                {'warn': Choice('danger', value=_core.Style('red')), 'rest': 'rest'},
                on='key',
                keys='enter',
            )
            press(canvas)
            canvas.clock.step()
            decision = hero.state.get('decision')
            assert decision['choice'] == 'warn'  # type: ignore[index]
            assert decision['margin'] == pytest.approx(0.8)  # type: ignore[index]
            cells = _core.Buffer.from_cell_grid(
                canvas.screen.output.render().to_cell_grid()
            )
            assert str(cells[0, 0].foreground) == "Color('red')"

    def test_a_pick_below_the_threshold_is_no_change(self):
        called: list[str] = []
        pick = ChoiceModel(
            ScriptedDecisionModel({'response': {'warn': 0.55, 'rest': 0.45}})
        )
        with xnano.new(width=20, height=1) as canvas:
            hero = canvas.screen.write('hero')
            hero | decide(
                pick,
                {
                    'warn': Choice('danger', value=lambda: called.append('warn')),
                    'rest': 'rest',
                },
                on='key',
                keys='enter',
                threshold=0.5,
            )
            press(canvas)
            canvas.clock.step()
            assert hero.state.get('decision')['choice'] == 'no_change'  # type: ignore[index]
        assert called == []

    def test_an_action_is_called_on_the_canvas_thread(self):
        pick = ChoiceModel(ScriptedDecisionModel({'response': 'wave'}))
        with xnano.new(width=20, height=1) as canvas:
            hero = canvas.screen.write('hero')

            def wave() -> None:
                hero.text = 'hero waves'

            hero | decide(
                pick, {'wave': Choice('greet', value=wave)}, on='key', keys='enter'
            )
            press(canvas)
            canvas.clock.step()
            assert canvas.screen.render() == 'hero waves'

    def test_each_target_gets_its_own_answer(self):
        model = ScriptedDecisionModel({'response': 'yes'})
        plugin = decide(
            ChoiceModel(model, cache=False), ['yes', 'no'], on='key', keys='enter'
        )
        with xnano.new(width=20, height=2) as canvas:
            first = canvas.screen.write('first')
            second = canvas.screen.write('second')
            first | plugin
            second | plugin
            press(canvas)
            canvas.clock.step()
            assert first.state.get('decision')['choice'] == 'yes'  # type: ignore[index]
            assert second.state.get('decision')['choice'] == 'yes'  # type: ignore[index]
        assert len(model.requests) == 2

    def test_removing_the_plugin_stops_it(self):
        model = ScriptedDecisionModel({'response': 'yes'})
        plugin = decide(ChoiceModel(model), ['yes', 'no'], on='key', keys='enter')
        with xnano.new(width=20, height=1) as canvas:
            hero = canvas.screen.write('hero')
            hero | plugin
            plugin.remove()  # type: ignore[attr-defined]
            press(canvas)
            canvas.clock.step()
        assert model.requests == []

    def test_on_is_needed(self):
        with pytest.raises(ValueError, match='needs on= to say when to ask the model'):
            decide(ChoiceModel(ScriptedDecisionModel()), ['a', 'b'])


class TestWatch:
    def test_a_verdict_is_kept_and_its_yes_applied(self):
        judge = JudgeModel(ScriptedDecisionModel({'answer': 0.9}))
        with xnano.new(width=20, height=1) as canvas:
            gauge = canvas.screen.write('CPU 97%')
            gauge | watch(
                judge,
                'Is the server under strain?',
                on='tick',
                every=1.0,
                yes=_core.Style('red'),
            )
            canvas.clock.step(delta_seconds=1.0)
            canvas.clock.step()
            verdict = gauge.state.get('verdict')
            assert verdict['answer'] is True  # type: ignore[index]
            assert verdict['probability'] == pytest.approx(0.9)  # type: ignore[index]

    def test_a_no_applies_no(self):
        judge = JudgeModel(ScriptedDecisionModel({'answer': 0.2}))
        changed: list[str] = []
        with xnano.new(width=20, height=1) as canvas:
            gauge = canvas.screen.write('CPU 12%')
            gauge | watch(
                judge,
                'Under strain?',
                on='key',
                keys='enter',
                no=lambda: changed.append('calm'),
            )
            press(canvas)
            canvas.clock.step()
        assert changed == ['calm']
