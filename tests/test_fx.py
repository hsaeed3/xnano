"""Tests for typed customization, canvases, and operation piping."""

import dataclasses
import re
import typing

import pytest

import xnano
import xnano._customize as customize_module
import xnano.types
import xnano_core
from xnano._customize import (
    _CUSTOMIZATION_TYPES,
    CustomizationKind,
    FadeToEffectCustomization,
    normalize_effect,
)
from xnano._hooks import HookHandle
from xnano.context import Context
from xnano.operations import fx
from xnano_core import Event


def render_text(buffer) -> str:
    return buffer.render(format='text')


def test_customize_returns_a_dataclass_operation() -> None:
    fill = fx('fill', cell='.')
    assert dataclasses.is_dataclass(fill)
    assert fill.cell == '.'
    assert isinstance(fill, xnano.operations.Customization)


def test_customize_rejects_unknown_parameters() -> None:
    with pytest.raises(TypeError):
        fx('fill', character='.')  # type: ignore[call-arg]


def test_a_customization_is_a_live_handle_on_the_canvas() -> None:
    with xnano.new('hello', width=6, height=1) as canvas:
        dots = fx('fill', cell='.')
        canvas.update(dots)
        assert isinstance(dots, xnano.operations.Customization)
        dots.cell = '#'
        assert '#' in canvas.render()
        dots.cell = '+'
        assert '+' in canvas.render()


def test_appearance_keywords_style_the_canvas_and_never_its_content() -> None:
    with pytest.raises(
        TypeError, match='style the canvas itself, not its content: border'
    ):
        xnano.new('hi', border='rounded')
    with xnano.new(width=6, height=3, border='rounded') as canvas:
        assert canvas.render().split('\n')[0] == '╭────╮'
        canvas.write('hi')
        assert canvas.render().split('\n')[1] == '│hi  │', (
            'content lives inside the border'
        )


def test_a_placement_changes_its_look_after_it_is_written() -> None:
    with xnano.new(width=20, height=8) as canvas:
        label = canvas.write('hi', border='rounded', padding={'horizontal': 1})
        assert (label.width, label.height) == (6, 3)
        label.border = 'double'
        label.padding = 2
        label.text = 'hello'
        assert (label.width, label.height) == (11, 7)
        canvas.iter(count=1).__next__()
        assert '╔' in canvas.core_buffer.render(format='text')
        assert label.border.kind == 'double'


def test_margin_adds_space_outside_the_box() -> None:
    with xnano.new(width=12, height=6) as canvas:
        label = canvas.write('hi', border='plain', margin={'left': 2, 'top': 1})
        assert (label.width, label.height) == (6, 4)


def test_a_widget_takes_a_border_like_text_does() -> None:
    with xnano.new(width=12, height=5) as canvas:
        gauge = canvas.write(
            xnano_core.Gauge(ratio=0.5, width=10, height=1), border='plain'
        )
        assert (gauge.width, gauge.height) == (12, 3)
        assert canvas.render().split('\n')[0] == '┌──────────┐'
        gauge.border.color = 'red'
        gauge.border = False
        assert (gauge.width, gauge.height) == (10, 1)
        assert '┌' not in canvas.render()


def test_a_widget_can_take_a_look_after_it_was_written() -> None:
    with xnano.new(width=12, height=3) as canvas:
        gauge = canvas.write(xnano_core.Gauge(ratio=0.5, width=10, height=1))
        gauge.border = 'plain'
        assert (gauge.width, gauge.height) == (12, 3)
        assert canvas.render().split('\n')[0] == '┌──────────┐'


def test_an_effect_handle_restarts_the_effect_with_new_values() -> None:
    with xnano.new(width=10, height=1) as canvas:
        label = canvas.write('abc')
        effect = fx('effect.dissolve', duration_milliseconds=100)
        label.update(effect)
        key = effect.key
        assert key is not None
        effect.duration_milliseconds = 400
        assert effect.key == key
        assert effect.duration_milliseconds == 400


def test_canvas_pipes_a_customization() -> None:
    with xnano.new('x', width=4, height=1) as canvas:
        assert (canvas | fx('fill', cell='.')) is canvas
        assert isinstance(canvas, xnano.canvas.Canvas)
        assert '.' in canvas.render()


def test_open_explains_the_keywords_it_refuses_before_taking_the_screen() -> None:
    with xnano.new('hi', width=10, height=2, deps={'name': 'app'}) as canvas:
        with pytest.raises(TypeError, match='takes no realtime'):
            xnano.open(canvas, realtime=True)  # type: ignore[call-overload]
        with pytest.raises(TypeError, match='deps was already given to xnano.new'):
            xnano.open(canvas, deps={'name': 'other'})
        with pytest.raises(ValueError, match='needs a height too'):
            xnano.open(canvas, width=10)
        assert not isinstance(canvas, xnano.Terminal)
        assert xnano.terminal._live_terminal_open is False


def test_open_given_content_styles_the_canvas_only_without_content() -> None:
    with pytest.raises(TypeError, match='style the canvas itself'):
        xnano.open('text', border='rounded')
    assert xnano.terminal._live_terminal_open is False


def test_pipe_returns_the_canvas() -> None:
    with xnano.new(width=8, height=2) as canvas:
        assert (canvas | fx('fill', cell='.')) is canvas


class TestNamedEffects:
    def test_a_placement_starts_a_named_effect_at_once(self) -> None:
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.write('hi')
            fade = label.fx.fade_to(foreground='red', duration_milliseconds=100)
            assert fade.foreground == 'red'
            assert label.fx.active == (fade,)
            assert [entry[0] for entry in canvas._effects] == [fade]

    def test_a_key_hook_starts_an_effect_on_another_placement(self) -> None:
        with xnano.new(width=20, height=1) as canvas:
            content = canvas.write('Press e')

            @canvas.hook(on='key')
            def flash(context: Context) -> None:
                if context.keyboard.key == 'e':
                    content.fx.dissolve(duration_milliseconds=1000)

            press(canvas, 'x')
            assert content.fx.active == ()
            press(canvas, 'e')
            assert len(content.fx.active) == 1
            assert canvas._effects[0][1] is content

    def test_the_same_kind_again_replaces_the_earlier_effect(self) -> None:
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.write('hi')
            first = label.fx.fade_to(foreground='red', duration_milliseconds=1000)
            second = label.fx.fade_to(foreground='blue', duration_milliseconds=1000)
            assert label.fx.active == (second,)
            assert first is not second
            canvas.step()
            assert [entry[0] for entry in canvas._effects] == [second]

    def test_clear_and_remove_stop_the_effects(self) -> None:
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.write('hi')
            label.fx.fade_to(foreground='red', duration_milliseconds=1000)
            label.fx.clear()
            assert label.fx.active == ()
            label.fx.glitch(duration_milliseconds=1000)
            label.remove()
            assert label._renderable_effects.active == ()

    def test_a_removed_placement_refuses_an_effect(self) -> None:
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.write('hi')
            label.remove()
            with pytest.raises(xnano.errors.TerminalClosedError, match='was removed'):
                label.fx.fade_to(foreground='red')

    def test_the_canvas_has_its_own_effects(self) -> None:
        with xnano.new('hello', width=8, height=1) as canvas:
            dissolve = canvas.fx.dissolve(duration_milliseconds=300)
            assert canvas.fx.active == (dissolve,)
            assert canvas._effects[0][1] is canvas

    def test_visual_and_sound_effects_have_their_own_names(self) -> None:
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.write('hi')
            with pytest.raises(AttributeError, match='reverb is a sound effect'):
                label.fx.reverb  # noqa: B018
            with pytest.raises(AttributeError, match='fade_to is a visual effect'):
                canvas.audio.fx.fade_to  # noqa: B018
            with pytest.raises(AttributeError, match="no effect named 'fade'"):
                canvas.fx.fade  # noqa: B018

    def test_audio_effects_apply_to_every_sound_played_after_them(self) -> None:
        def late_peak(*, with_delay: bool) -> float:
            with xnano.new(width=8, height=1) as canvas:
                if with_delay:
                    echo = canvas.audio.fx.delay(
                        time_milliseconds=300.0, feedback=0.6, mix=0.8
                    )
                    assert canvas.audio.fx.active == (echo,)
                canvas.play(xnano.note('C4', beats=0.25))
                canvas.step(delta_seconds=1.5)
                samples = list(canvas.audio.render_sound().samples())
                return max(abs(value) for value in samples[len(samples) // 2 :])

        assert late_peak(with_delay=False) == 0.0
        assert late_peak(with_delay=True) > 0.01

    def test_clear_removes_the_audio_effects(self) -> None:
        with xnano.new(width=8, height=1) as canvas:
            canvas.audio.fx.reverb(mix=0.5)
            canvas.audio.fx.clear()
            assert canvas.audio.fx.active == ()


def test_nested_placement_follows_a_drag_hook() -> None:
    with xnano.new(width=20, height=3) as canvas:
        track = canvas.write(' ' * 10, y=1)
        thumb = track.write('█', x=(0, track.width - 1), y=0)

        @thumb.hook(on='drag')
        def slide(context: xnano.context.Context):
            while context.mouse.is_down:
                thumb.x = context.parent.local(context.mouse.position).x
                context = yield

        canvas.push(Event.mouse_event(column=0, row=1, kind='press', button='left'))
        canvas.push(Event.mouse_event(column=5, row=1, kind='drag', button='left'))
        canvas.deliver_events()
        assert thumb.x == 5


def test_expression_scopes_on_placements() -> None:
    with xnano.new(width=20, height=3) as canvas:
        ball = canvas.write('o')
        ball.x = (ball.parent.width - ball.width) * ((ball.root.time / 2.0) % 1.0)
        ball.x = (canvas.width - ball.width) * ((canvas.time / 2.0) % 1.0)


def test_a_frame_hook_runs_on_every_frame() -> None:
    calls: list[int] = []
    with xnano.new(width=8, height=2) as canvas:

        @canvas.hook(on='frame')
        def record(context: xnano.context.Context) -> None:
            calls.append(1)

        assert isinstance(record, HookHandle)
        for _ in canvas.iter(count=2):
            pass
    assert calls


def signature_parameters(callable_object: object) -> list[str]:
    """The parameter names of a native constructor, read from its text signature."""
    text = getattr(callable_object, '__text_signature__', None)
    assert text, f'{callable_object!r} has no text signature'
    names = []
    for part in text.strip('()').split(','):
        name = part.split('=')[0].strip().lstrip('*')
        if name and name not in ('$self', '/'):
            names.append(name)
    return names


def test_every_kind_has_a_dataclass_with_matching_defaults() -> None:
    from xnano._customize import _CUSTOMIZATION_TYPES

    assert set(_CUSTOMIZATION_TYPES) <= set(xnano_core.Customization.kinds())
    for kind, customization_class in _CUSTOMIZATION_TYPES.items():
        native = xnano_core.Customization.defaults(kind)
        fields = {
            field.name: field.default for field in dataclasses.fields(customization_class)
        }
        assert set(native) == set(fields), kind
        for name, default in native.items():
            assert fields[name] == default, (kind, name)


@pytest.mark.parametrize(
    ('kind', 'target', 'renamed'),
    [
        ('layout', xnano_core.Layout, {}),
        ('write', xnano_core.Write, {}),
        ('fill', xnano_core.Fill, {}),
        ('fuzz', xnano_core.Fuzz, {}),
        ('raster', xnano_core.Raster, {}),
        ('pixels', xnano_core.Pixels, {}),
    ],
)
def test_customize_reaches_every_parameter_of_the_core_constructor(
    kind: str, target: object, renamed: dict[str, str]
) -> None:
    reachable = set(xnano_core.Customization.defaults(kind))
    for name in signature_parameters(target):
        assert renamed.get(name, name) in reachable or name in reachable, (kind, name)


def test_customize_reaches_every_effect_constructor() -> None:
    combinators = {'consume_tick', 'term256_colors', 'parallel', 'sequence'}
    reachable = set(xnano_core.Customization.kinds())
    for name in dir(xnano_core.Effect):
        member = getattr(xnano_core.Effect, name)
        text = getattr(member, '__text_signature__', None)
        if name.startswith('_') or not text or '$self' in text or name in combinators:
            continue
        assert f'effect.{name}' in reachable, name
        parameters = xnano_core.Customization.defaults(f'effect.{name}')
        for parameter in signature_parameters(member):
            assert parameter in parameters, (name, parameter)


def test_customization_is_a_native_operation_that_sequences() -> None:
    fill = xnano_core.Customization('fill', cell='.')
    border = xnano_core.Customization('border', border_kind='rounded')
    buffer = xnano_core.Buffer(width=6, height=3)
    buffer.update(fill | border)
    text = buffer.render(format='text')
    assert '╭' in text
    assert '.' in text
    assert isinstance(fill | xnano_core.Style('red'), xnano_core.Operation)


def test_editing_a_field_changes_what_the_customization_does() -> None:
    fill = fx('fill', cell='.')
    fill.cell = '#'
    buffer = xnano_core.Buffer(width=3, height=1)
    buffer | fill
    assert buffer.text.startswith('###')


def test_customization_errors_say_how_to_recover() -> None:
    with pytest.raises(ValueError, match='Choose one of'):
        xnano_core.Customization('bogus').build()
    with pytest.raises(TypeError, match='Its parameters are'):
        xnano_core.Customization('style', bogus=1).build()
    with pytest.raises(AttributeError, match='provides: width, height, size'):
        xnano.expressions.Parent.depth  # noqa: B018


def test_mixed_operations_chain_in_order() -> None:
    shader = fx('pixels', shader=lambda column, row: (255, 0, 0))
    chained = shader | fx('fill', cell='.')
    assert isinstance(chained, xnano_core.OperationChain)
    buffer = xnano_core.Buffer(width=2, height=1)
    buffer.update(chained)


def test_triggers_decide_events_natively() -> None:
    press = xnano_core.Event.key_press('q')
    assert xnano_core.Trigger.key('q', 'escape').matches(press)
    assert not xnano_core.Trigger.key('x').matches(press)
    assert xnano_core.Trigger.key().matches(press)
    assert not xnano_core.Trigger.click().matches(press)
    assert xnano_core.Trigger.named('click') == xnano_core.Trigger.click()
    with pytest.raises(ValueError, match='Use one of'):
        xnano_core.Trigger.named('sometimes')
    with pytest.raises(ValueError, match='key binding'):
        xnano_core.Trigger.key('ctrl+')


def test_scopes_are_native_expressions() -> None:
    assert xnano.expressions.Parent.width is xnano_core.ParentWidth
    assert xnano.expressions.Root.time is xnano_core.TimeElapsed
    assert xnano.expressions.BufferExpressions.size is xnano_core.BufferSize


def test_audio_customization_chains_onto_sounds() -> None:
    pytest.importorskip('xnano_audio')
    from xnano_audio import TerminalSound

    sound = TerminalSound.from_samples([0.0, 0.5, -0.5, 0.25] * 64, sample_rate=8000)
    shaped = sound | fx('audio.reverb', mix=0.3)
    assert isinstance(shaped, TerminalSound)


def test_xnano_hook_makes_a_reusable_operation() -> None:
    ticks: list[float] = []

    @xnano.hook(on='tick', every=0.1)
    def tick(context: Context) -> None:
        ticks.append(round(context.time.elapsed, 1))

    assert isinstance(tick, xnano.operations.ContextualOperation)
    assert (tick.on, tick.every) == ('tick', 0.1)
    with xnano.new(width=8, height=1) as first, xnano.new(width=8, height=1) as second:
        first | tick
        second | tick
        first.step(delta_seconds=0.25)
        second.step(delta_seconds=0.15)
    assert len(ticks) == 3
    assert not hasattr(xnano, 'operation')


def test_a_hook_returning_an_operation_applies_it() -> None:
    with xnano.new(width=8, height=1) as canvas:
        label = canvas.write('hi')

        @label.hook(on='tick', after=0.0)
        def tint(context: Context) -> xnano_core.Operation:
            return xnano_core.Fill('x')

        canvas.step(delta_seconds=0.1)
        assert canvas.render().startswith('xx')


def test_a_hook_returning_content_is_refused() -> None:
    with pytest.raises(xnano.errors.TerminalError, match='cannot return content'):
        with xnano.new(width=8, height=1) as canvas:

            @canvas.hook(on='tick', after=0.0)
            def draw(context: Context) -> str:
                return 'text'

            canvas.step(delta_seconds=0.1)


# -- effect kinds, specifications and effects=[...] ---------------------------------------


def specification_kind(specification: type) -> str:
    """The ``kind`` a specification dictionary class is for, read from its annotation."""
    annotation = specification.__annotations__['kind']
    text = getattr(annotation, '__forward_arg__', str(annotation))
    match = re.search(r"Literal\['([a-z_.]+)'\]", text)
    assert match is not None, text
    return match.group(1)


RENDERABLE_SPECIFICATIONS = typing.get_args(xnano.types.RenderableEffectSpecification)
PLAYABLE_SPECIFICATIONS = typing.get_args(xnano.types.PlayableEffectSpecification)


def press(canvas: xnano.canvas.Canvas, key: str = 'a') -> None:
    canvas.push(Event.key_press(key))
    canvas.deliver_events()


class TestEffectKinds:
    def test_the_kinds_split_into_visual_and_sound(self) -> None:
        renderable = typing.get_args(xnano.types.RenderableEffectKind)
        playable = typing.get_args(xnano.types.PlayableEffectKind)
        assert len(renderable) == 21
        assert len(playable) == 7
        assert all(kind.startswith('effect.') for kind in renderable)
        assert all(kind.startswith('audio.') for kind in playable)
        assert set(renderable + playable) <= set(typing.get_args(CustomizationKind))
        assert len(RENDERABLE_SPECIFICATIONS) == 21
        assert len(PLAYABLE_SPECIFICATIONS) == 7

    def test_the_effect_unions_hold_every_customization_class(self) -> None:
        visual = set(typing.get_args(xnano.types.RenderableEffect))
        sound = set(typing.get_args(xnano.types.PlayableEffect))
        assert {customization.customization_kind for customization in visual} == set(
            typing.get_args(xnano.types.RenderableEffectKind)
        )
        assert {customization.customization_kind for customization in sound} == set(
            typing.get_args(xnano.types.PlayableEffectKind)
        )
        assert set(typing.get_args(xnano.types.EffectCustomization)) == visual | sound

    @pytest.mark.parametrize(
        'specification', RENDERABLE_SPECIFICATIONS + PLAYABLE_SPECIFICATIONS
    )
    def test_a_specification_is_its_arguments_plus_a_required_kind(
        self, specification: type
    ) -> None:
        kind = specification_kind(specification)
        customization_class = _CUSTOMIZATION_TYPES[kind]
        arguments = getattr(
            customize_module, specification.__name__.replace('Specification', 'Arguments')
        )
        assert 'kind' in specification.__required_keys__
        assert set(arguments.__annotations__) < set(specification.__annotations__)
        assert not set(arguments.__annotations__) & set(specification.__required_keys__)
        parameters = {field.name for field in dataclasses.fields(customization_class)}
        assert set(arguments.__annotations__) == parameters

    @pytest.mark.parametrize('specification', RENDERABLE_SPECIFICATIONS)
    def test_a_visual_specification_becomes_its_effect(self, specification: type) -> None:
        kind = specification_kind(specification)
        effect = normalize_effect({'kind': kind}, 'renderable')
        assert type(effect) is _CUSTOMIZATION_TYPES[kind]

    @pytest.mark.parametrize('specification', PLAYABLE_SPECIFICATIONS)
    def test_a_sound_specification_becomes_its_effect(self, specification: type) -> None:
        kind = specification_kind(specification)
        effect = normalize_effect({'kind': kind}, 'playable')
        assert type(effect) is _CUSTOMIZATION_TYPES[kind]

    def test_a_specification_carries_the_effects_keywords(self) -> None:
        effect = normalize_effect(
            {'kind': 'effect.fade_to', 'foreground': 'red', 'duration_milliseconds': 600},
            'renderable',
        )
        assert (effect.foreground, effect.duration_milliseconds) == ('red', 600)
        reverb = normalize_effect({'kind': 'audio.reverb', 'mix': 0.4}, 'playable')
        assert reverb.mix == 0.4

    def test_fx_is_not_exported_from_the_top_level(self) -> None:
        assert not hasattr(xnano, 'fx')
        assert 'fx' not in xnano.__all__
        assert xnano.operations.fx is fx


class TestEffectLists:
    @pytest.mark.parametrize(
        ('specification', 'expected', 'message'),
        [
            (
                fx('effect.dissolve'),
                'renderable',
                r"effects= takes dictionaries such as \{'kind': 'effect.fade_to'.*"
                r'placement \| fx',
            ),
            (
                fx('audio.reverb'),
                'playable',
                r"effects= takes dictionaries such as \{'kind': 'audio.reverb'.*"
                r'write the effect as a dictionary',
            ),
            ({'foreground': 'red'}, 'renderable', 'effects= takes dictionaries'),
            ('effect.fade_to', 'renderable', 'effects= takes dictionaries'),
            ({'kind': 3}, 'renderable', "The 'kind' of an effect is a string"),
            (
                {'kind': 'audio.reverb'},
                'renderable',
                "'audio.reverb' is a sound effect; pass it to play\\(effects=...\\)",
            ),
            (
                {'kind': 'effect.fade_to'},
                'playable',
                "'effect.fade_to' is a visual effect; pass it to write\\(effects=...\\)",
            ),
            ({'kind': 'fill'}, 'renderable', "'fill' is not a visual effect"),
            ({'kind': 'fill'}, 'playable', "'fill' is not a sound effect"),
        ],
    )
    def test_a_wrong_entry_says_what_the_list_takes(
        self, specification: object, expected: str, message: str
    ) -> None:
        with pytest.raises(TypeError, match=message):
            normalize_effect(specification, expected)  # type: ignore[arg-type]

    def test_an_unknown_effect_kind_lists_the_known_ones(self) -> None:
        with pytest.raises(
            ValueError, match="'effect.nope' is not a known visual effect"
        ):
            normalize_effect({'kind': 'effect.nope'}, 'renderable')

    def test_new_applies_effects_to_a_canvas_without_content(self) -> None:
        with xnano.new(
            width=6,
            height=1,
            effects=[{'kind': 'effect.fade_to', 'duration_milliseconds': 500}],
        ) as canvas:
            assert len(canvas._effects) == 1
            customization, target = canvas._effects[0]
            assert target is canvas
            assert customization.customization_kind == 'effect.fade_to'

    def test_a_sound_effect_in_a_visual_list_is_refused_everywhere(self) -> None:
        with pytest.raises(TypeError, match='is a sound effect'):
            xnano.new(width=6, height=1, effects=[{'kind': 'audio.reverb'}])  # type: ignore[list-item]
        with xnano.new(width=6, height=1) as canvas:
            with pytest.raises(TypeError, match='is a sound effect'):
                canvas.write('x', effects=[{'kind': 'audio.delay'}])  # type: ignore[list-item]
            label = canvas.write('x')
            with pytest.raises(TypeError, match='is a sound effect'):
                label.write('y', effects=[{'kind': 'audio.delay'}])  # type: ignore[list-item]

    def test_a_placement_write_starts_its_effects(self) -> None:
        with xnano.new(width=8, height=2) as canvas:
            outer = canvas.write('a')
            inner = outer.write(
                'b', effects=[{'kind': 'effect.dissolve', 'duration_milliseconds': 100}]
            )
            assert any(target is inner for _, target in canvas._effects)


class TestCancel:
    def test_cancel_stops_a_running_effect(self) -> None:
        with xnano.new(width=6, height=1) as canvas:
            label = canvas.write('hi')
            fade = fx('effect.fade_to', foreground='red', duration_milliseconds=1000)
            fade.apply_to(label)
            canvas.step(delta_seconds=0.25)
            canvas.step(delta_seconds=0.25)
            assert '38;2;' in canvas.render(format='ansi')
            fade.cancel()
            canvas.step(delta_seconds=0.1)
            assert '38;2;' not in canvas.render(format='ansi')
            assert canvas._effects == []

    def test_cancel_does_nothing_without_a_target_or_an_effect(self) -> None:
        fx('effect.fade_to').cancel()
        fill = fx('fill', cell='.')
        fill.cancel()
        with xnano.new(width=4, height=1) as canvas:
            canvas.update(fill)
            fill.cancel()
            fill.cancel()
            assert '.' in canvas.render()

    def test_cancel_twice_is_harmless(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:
            fade = fx('effect.dissolve', duration_milliseconds=1000)
            fade.apply_to(canvas)
            fade.cancel()
            fade.cancel()


class TestContextEffects:
    def test_a_visual_effect_runs_on_the_hooks_placement(self) -> None:
        with xnano.new(width=8, height=2) as canvas:
            label = canvas.write('hi')
            other = canvas.write('yo', y=1)
            applied: list[object] = []

            @label.hook(on='key')
            def tint(context: Context) -> None:
                applied.append(
                    context.fx.fade_to(foreground='red', duration_milliseconds=1000)
                )

            press(canvas)
            assert isinstance(applied[0], FadeToEffectCustomization)
            assert applied[0].foreground == 'red'
            assert [target for _, target in canvas._effects] == [label]
            canvas.step(delta_seconds=0.5)
            first, second = canvas.render(format='ansi').split('\n')[:2]
            assert '38;2;' in first
            assert '38;2;' not in second
            del other

    def test_a_hook_on_the_canvas_applies_to_the_canvas(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                context.fx.fade_to(foreground='red', duration_milliseconds=1000)

            press(canvas)
            assert [target for _, target in canvas._effects] == [canvas]
            for _ in range(3):
                canvas.step(delta_seconds=1.0)
            assert canvas._effects == []

    def test_the_effect_is_the_live_handle_fx_returns(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:
            kept: list[FadeToEffectCustomization] = []

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                kept.append(
                    context.fx.fade_to(foreground='red', duration_milliseconds=1000)
                )

            press(canvas)
            effect = kept[0]
            key = effect.key
            effect.duration_milliseconds = 400
            assert effect.key == key
            assert effect.duration_milliseconds == 400

    @pytest.mark.parametrize('name', ['nope', 'fill'])
    def test_an_unknown_name_lists_the_effects(self, name: str) -> None:
        with xnano.new(width=6, height=1) as canvas:
            errors: list[Exception] = []

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                try:
                    getattr(context.fx, name)
                except AttributeError as error:
                    errors.append(error)

            press(canvas)
            assert len(errors) == 1
            text = str(errors[0])
            assert f'context.fx has no effect named {name!r}' in text
            assert 'fade_to' in text
            assert 'tremolo' in text

    def test_a_wrong_keyword_is_refused_like_fx_refuses_it(self) -> None:
        with xnano.new(width=6, height=1) as canvas:
            errors: list[Exception] = []

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                try:
                    context.fx.fade_to(colour='red')  # type: ignore[call-overload]
                except TypeError as error:
                    errors.append(error)

            press(canvas)
            assert len(errors) == 1
            assert canvas._effects == []

    def test_the_same_kind_again_replaces_the_earlier_effect(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:
            seen: list[FadeToEffectCustomization] = []

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                seen.append(
                    context.fx.fade_to(foreground='red', duration_milliseconds=1000)
                )
                assert context.fx.active == (seen[-1],)

            press(canvas)
            press(canvas)
            assert len(seen) == 2
            assert seen[0] is not seen[1]
            assert [entry[0] for entry in canvas._effects] == [seen[1]]

    def test_different_kinds_stay_together(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:
            counts: list[int] = []

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                context.fx.fade_to(foreground='red', duration_milliseconds=1000)
                context.fx.dissolve(duration_milliseconds=1000)
                context.fx.reverb()
                counts.append(len(context.fx.active))

            press(canvas)
            assert counts == [3]
            assert len(canvas._effects) == 2

    def test_clear_ends_the_effects_of_the_hook(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:
            active: list[tuple[object, ...]] = []

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                if context.keyboard.key == 'a':
                    context.fx.fade_to(foreground='red', duration_milliseconds=1000)
                else:
                    context.fx.clear()
                    active.append(context.fx.active)

            press(canvas, 'a')
            canvas.step(delta_seconds=0.5)
            assert '38;2;' in canvas.render(format='ansi')
            press(canvas, 'b')
            canvas.step(delta_seconds=0.1)
            assert active == [()]
            assert '38;2;' not in canvas.render(format='ansi')
            assert canvas._effects == []

    def test_clear_with_no_effects_does_nothing(self) -> None:
        with xnano.new(width=6, height=1) as canvas:
            cleared: list[bool] = []

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                context.fx.clear()
                cleared.append(context.fx.active == ())

            press(canvas)
            assert cleared == [True]

    def test_clear_leaves_the_effects_of_other_hooks(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:

            @canvas.hook(on='key', keys='a')
            def first(context: Context) -> None:
                context.fx.fade_to(foreground='red', duration_milliseconds=1000)

            @canvas.hook(on='key', keys='b')
            def second(context: Context) -> None:
                context.fx.dissolve(duration_milliseconds=1000)

            @canvas.hook(on='key', keys='c')
            def third(context: Context) -> None:
                context.fx.clear()

            press(canvas, 'a')
            press(canvas, 'b')
            press(canvas, 'c')
            assert len(canvas._effects) == 2

    def test_removing_the_hook_ends_its_effects(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                context.fx.fade_to(foreground='red', duration_milliseconds=1000)

            press(canvas)
            canvas.step(delta_seconds=0.1)
            assert len(canvas._effects) == 1
            tint.remove()
            canvas.step(delta_seconds=0.1)
            assert canvas._effects == []

    def test_removing_the_placement_ends_its_effects(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:
            label = canvas.write('x')

            @label.hook(on='key')
            def tint(context: Context) -> None:
                context.fx.fade_to(foreground='red', duration_milliseconds=1000)

            press(canvas)
            label.remove()
            canvas.step(delta_seconds=0.1)
            assert canvas._effects == []

    def test_a_hook_that_removes_itself_leaves_no_effect_behind(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                context.hook.remove()
                effect = context.fx.fade_to(foreground='red', duration_milliseconds=1000)
                assert isinstance(effect, FadeToEffectCustomization)

            press(canvas)
            assert canvas._effects == []

    def test_closing_the_canvas_with_a_running_effect_is_clean(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                context.fx.fade_to(foreground='red', duration_milliseconds=1000)
                context.fx.reverb()

            press(canvas)
        assert tint._effect_state is None

    def test_a_frame_hook_keeps_one_effect_while_it_runs_every_frame(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:
            sizes: list[int] = []

            @canvas.hook(on='frame')
            def tint(context: Context) -> None:
                if not context.fx.active:
                    context.fx.fade_to(foreground='red', duration_milliseconds=1000)
                sizes.append(len(context.fx.active))

            for _ in canvas.iter(count=3):
                pass
            assert sizes and set(sizes) == {1}
            assert len(canvas._effects) == 1


class TestEffectSettings:
    def test_an_unknown_setting_names_the_kind_and_the_accepted_settings(self) -> None:
        with pytest.raises(
            TypeError, match="effect 'effect.dissolve' has no setting called 'color'"
        ):
            normalize_effect({'kind': 'effect.dissolve', 'color': 'red'}, 'renderable')
        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(TypeError, match='duration_milliseconds'):
                canvas.write(
                    'x',
                    effects=[{'kind': 'effect.dissolve', 'color': 'red'}],  # type: ignore[list-item]
                )

    def test_draw_checks_its_effects_at_the_call(self) -> None:
        with pytest.raises(ValueError, match='is not a known visual effect'):
            xnano.draw(['G'], {'G': 'red'}, effects=[{'kind': 'effect.nope'}])  # type: ignore[list-item]
        with pytest.raises(TypeError, match='sound effect'):
            xnano.draw(['G'], {'G': 'red'}, effects=[{'kind': 'audio.reverb'}])  # type: ignore[list-item]
