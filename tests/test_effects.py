"""
tests.test_effects

Tests for effects, Dynamic operations, canvases and operation piping.
"""

import dataclasses
import inspect
import re
import typing

import pytest

import xnano
import xnano._schema._effects as effects_schema
import xnano.effects
import xnano.terminal._screen
import xnano_core
from xnano.effects import FadeToEffectParameters, effect
from xnano.effects._registry import EFFECT_PARAMETERS_BY_KIND, normalize_effect
from xnano.hooks import Context, HookHandle
from xnano.operations import (
    DynamicFill,
    DynamicFuzz,
    DynamicLayout,
    DynamicPixels,
    DynamicRaster,
    DynamicWrite,
)
from xnano_core import Event


def render_text(buffer) -> str:
    return buffer.render(format='text')


def test_a_dynamic_operation_is_a_dataclass_operation() -> None:
    fill = DynamicFill(cell='.')
    assert dataclasses.is_dataclass(fill)
    assert fill.cell == '.'
    assert isinstance(fill, xnano_core.Customization)
    assert isinstance(fill, xnano_core.Operation)


@pytest.mark.parametrize(
    'parameters_class',
    [
        *EFFECT_PARAMETERS_BY_KIND.values(),
        DynamicFill,
        DynamicWrite,
        DynamicLayout,
        DynamicFuzz,
        DynamicPixels,
        DynamicRaster,
    ],
    ids=lambda parameters_class: parameters_class.__name__,
)
def test_every_parameters_class_rejects_a_setting_it_does_not_have(
    parameters_class: type,
) -> None:
    settings = ', '.join(
        field.name for field in dataclasses.fields(parameters_class) if field.init
    )
    with pytest.raises(
        TypeError,
        match=re.escape(
            f"{parameters_class.__name__} has no setting called 'not_a_setting'. "
            f'Its settings are: {settings}.'
        ),
    ):
        parameters_class(not_a_setting=1)


def test_effect_refuses_the_kind_of_a_dynamic_operation() -> None:
    with pytest.raises(ValueError, match='DynamicFill'):
        effect('fill')  # type: ignore[call-overload]
    with pytest.raises(ValueError, match='DynamicPixels'):
        effect('pixels')  # type: ignore[call-overload]


def test_effect_refuses_an_unknown_kind() -> None:
    with pytest.raises(ValueError, match='is not a known effect kind'):
        effect('effect.nope')  # type: ignore[call-overload]


def test_effect_refuses_a_setting_the_kind_does_not_have() -> None:
    with pytest.raises(TypeError, match="has no setting called 'color'"):
        effect('effect.fade_to', color='red')  # type: ignore[call-overload]


def test_a_dynamic_operation_is_a_live_handle_on_the_canvas() -> None:
    with xnano.new('hello', width=6, height=1) as canvas:
        dots = DynamicFill(cell='.')
        canvas.screen.update(dots)
        assert isinstance(dots, DynamicFill)
        dots.cell = '#'
        assert '#' in canvas.screen.render()
        dots.cell = '+'
        assert '+' in canvas.screen.render()


def test_appearance_keywords_style_the_canvas_and_never_its_content() -> None:
    with pytest.raises(
        TypeError, match='style the canvas itself, not its content: border'
    ):
        xnano.new('hi', border='rounded')
    with xnano.new(width=6, height=3, border='rounded') as canvas:
        assert canvas.screen.render().split('\n')[0] == '╭────╮'
        canvas.screen.write('hi')
        assert canvas.screen.render().split('\n')[1] == '│hi  │', (
            'content lives inside the border'
        )


def test_a_placement_changes_its_look_after_it_is_written() -> None:
    with xnano.new(width=20, height=8) as canvas:
        label = canvas.screen.write('hi', border='rounded', padding={'horizontal': 1})
        assert (label.width, label.height) == (6, 3)
        label.border = 'double'
        label.padding = 2
        label.text = 'hello'
        assert (label.width, label.height) == (11, 7)
        canvas.iter(frames=1).__next__()
        assert '╔' in canvas.screen.core_buffer.render(format='text')
        assert label.border.kind == 'double'


def test_margin_adds_space_outside_the_box() -> None:
    with xnano.new(width=12, height=6) as canvas:
        label = canvas.screen.write('hi', border='plain', margin={'left': 2, 'top': 1})
        assert (label.width, label.height) == (6, 4)


def test_a_widget_takes_a_border_like_text_does() -> None:
    with xnano.new(width=12, height=5) as canvas:
        gauge = canvas.screen.write(
            xnano_core.Gauge(ratio=0.5, width=10, height=1), border='plain'
        )
        assert (gauge.width, gauge.height) == (12, 3)
        assert canvas.screen.render().split('\n')[0] == '┌──────────┐'
        gauge.border.color = 'red'
        gauge.border = False
        assert (gauge.width, gauge.height) == (10, 1)
        assert '┌' not in canvas.screen.render()


def test_a_widget_can_take_a_look_after_it_was_written() -> None:
    with xnano.new(width=12, height=3) as canvas:
        gauge = canvas.screen.write(xnano_core.Gauge(ratio=0.5, width=10, height=1))
        gauge.border = 'plain'
        assert (gauge.width, gauge.height) == (12, 3)
        assert canvas.screen.render().split('\n')[0] == '┌──────────┐'


def test_an_effect_handle_restarts_the_effect_with_new_values() -> None:
    with xnano.new(width=10, height=1) as canvas:
        label = canvas.screen.write('abc')
        dissolve = effect('effect.dissolve', duration_milliseconds=100)
        label.update(dissolve)
        key = dissolve.key
        assert key is not None
        dissolve.duration_milliseconds = 400
        assert dissolve.key == key
        assert dissolve.duration_milliseconds == 400


def test_canvas_pipes_a_dynamic_operation() -> None:
    with xnano.new('x', width=4, height=1) as canvas:
        assert (canvas.screen | DynamicFill(cell='.')) is canvas.screen
        assert isinstance(canvas, xnano.canvas.Canvas)
        assert '.' in canvas.screen.render()


def test_open_explains_the_keywords_it_refuses_before_taking_the_screen() -> None:
    with xnano.new('hi', width=10, height=2, deps={'name': 'app'}) as canvas:
        with pytest.raises(TypeError, match='takes no realtime'):
            xnano.open(canvas, realtime=True)  # type: ignore[call-overload]
        with pytest.raises(TypeError, match='deps was already given to xnano.new'):
            xnano.open(canvas, deps={'name': 'other'})
        with pytest.raises(ValueError, match='needs a height too'):
            xnano.open(canvas, width=10)
        assert not isinstance(canvas, xnano.Terminal)
        assert xnano.terminal._screen.is_screen_claimed is False


def test_open_given_content_styles_the_canvas_only_without_content() -> None:
    with pytest.raises(TypeError, match='style the canvas itself'):
        xnano.open('text', border='rounded')
    assert xnano.terminal._screen.is_screen_claimed is False


def test_pipe_returns_the_screen() -> None:
    with xnano.new(width=8, height=2) as canvas:
        assert (canvas.screen | DynamicFill(cell='.')) is canvas.screen


class TestNamedEffects:
    def test_a_placement_starts_a_named_effect_at_once(self) -> None:
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.screen.write('hi')
            fade = label.fx.fade_to(foreground='red', duration_milliseconds=100)
            assert fade.foreground == 'red'
            assert label.fx.active == (fade,)
            assert [entry[0] for entry in canvas._effects] == [fade]

    def test_a_key_hook_starts_an_effect_on_another_placement(self) -> None:
        with xnano.new(width=20, height=1) as canvas:
            content = canvas.screen.write('Press e')

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
            label = canvas.screen.write('hi')
            first = label.fx.fade_to(foreground='red', duration_milliseconds=1000)
            second = label.fx.fade_to(foreground='blue', duration_milliseconds=1000)
            assert label.fx.active == (second,)
            assert first is not second
            canvas.clock.step()
            assert [entry[0] for entry in canvas._effects] == [second]

    def test_clear_and_remove_stop_the_effects(self) -> None:
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.screen.write('hi')
            label.fx.fade_to(foreground='red', duration_milliseconds=1000)
            label.fx.clear()
            assert label.fx.active == ()
            label.fx.glitch(duration_milliseconds=1000)
            label.remove()
            assert label._writable_effects.active == ()

    def test_a_removed_placement_refuses_an_effect(self) -> None:
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.screen.write('hi')
            label.remove()
            with pytest.raises(xnano.errors.TerminalClosedError, match='was removed'):
                label.fx.fade_to(foreground='red')

    def test_the_canvas_has_its_own_effects(self) -> None:
        with xnano.new('hello', width=8, height=1) as canvas:
            dissolve = canvas.screen.fx.dissolve(duration_milliseconds=300)
            assert canvas.screen.fx.active == (dissolve,)
            assert canvas._effects[0][1] is canvas

    def test_visual_and_sound_effects_have_their_own_names(self) -> None:
        with xnano.new(width=8, height=1) as canvas:
            label = canvas.screen.write('hi')
            with pytest.raises(AttributeError, match='reverb is a sound effect'):
                label.fx.reverb  # noqa: B018
            with pytest.raises(AttributeError, match='fade_to is a visual effect'):
                canvas.speaker.fx.fade_to  # noqa: B018
            with pytest.raises(AttributeError, match="no effect named 'fade'"):
                canvas.screen.fx.fade  # noqa: B018

    def test_audio_effects_apply_to_every_sound_played_after_them(self) -> None:
        def late_peak(*, with_delay: bool) -> float:
            with xnano.new(width=8, height=1) as canvas:
                if with_delay:
                    echo = canvas.speaker.fx.delay(
                        time_milliseconds=300.0, feedback=0.6, mix=0.8
                    )
                    assert canvas.speaker.fx.active == (echo,)
                canvas.speaker.play(xnano.note('C4', beats=0.25))
                canvas.clock.step(delta_seconds=1.5)
                samples = list(canvas.speaker.render().samples())
                return max(abs(value) for value in samples[len(samples) // 2 :])

        assert late_peak(with_delay=False) == 0.0
        assert late_peak(with_delay=True) > 0.01

    def test_clear_removes_the_audio_effects(self) -> None:
        with xnano.new(width=8, height=1) as canvas:
            canvas.speaker.fx.reverb(mix=0.5)
            canvas.speaker.fx.clear()
            assert canvas.speaker.fx.active == ()


def test_nested_placement_follows_a_drag_hook() -> None:
    with xnano.new(width=20, height=3) as canvas:
        track = canvas.screen.write(' ' * 10, y=1)
        thumb = track.write('█', x=(0, track.width - 1), y=0)

        @thumb.hook(on='drag')
        def slide(context: xnano.hooks.Context):
            while context.mouse.is_down:
                thumb.x = context.parent.local(context.mouse.position).x
                context = yield

        canvas.push(Event.mouse_event(column=0, row=1, kind='press', button='left'))
        canvas.push(Event.mouse_event(column=5, row=1, kind='drag', button='left'))
        canvas.deliver_events()
        assert thumb.x == 5


def test_expression_scopes_on_placements() -> None:
    with xnano.new(width=20, height=3) as canvas:
        ball = canvas.screen.write('o')
        ball.x = (ball.parent.width - ball.width) * ((ball.root.time / 2.0) % 1.0)
        ball.x = (canvas.screen.width - ball.width) * ((canvas.clock / 2.0) % 1.0)


def test_a_frame_hook_runs_on_every_frame() -> None:
    calls: list[int] = []
    with xnano.new(width=8, height=2) as canvas:

        @canvas.hook(on='frame')
        def record(context: xnano.hooks.Context) -> None:
            calls.append(1)

        assert isinstance(record, HookHandle)
        for _ in canvas.iter(frames=2):
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


DYNAMIC_OPERATION_CLASSES = (
    DynamicFill,
    DynamicWrite,
    DynamicLayout,
    DynamicFuzz,
    DynamicPixels,
    DynamicRaster,
)


def test_every_kind_has_a_dataclass_with_matching_defaults() -> None:
    parameter_classes = {
        **EFFECT_PARAMETERS_BY_KIND,
        **{cls.customization_kind: cls for cls in DYNAMIC_OPERATION_CLASSES},
    }
    assert len(parameter_classes) == 28 + 6
    assert set(parameter_classes) <= set(xnano_core.Customization.kinds())
    for kind, parameters_class in parameter_classes.items():
        native = xnano_core.Customization.defaults(kind)
        fields = {
            field.name: field.default for field in dataclasses.fields(parameters_class)
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
def test_dynamic_operations_reach_every_parameter_of_the_core_constructor(
    kind: str, target: object, renamed: dict[str, str]
) -> None:
    reachable = set(xnano_core.Customization.defaults(kind))
    for name in signature_parameters(target):
        assert renamed.get(name, name) in reachable or name in reachable, (kind, name)


def test_effect_kinds_reach_every_effect_constructor() -> None:
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


def test_editing_a_field_changes_what_the_dynamic_operation_does() -> None:
    fill = DynamicFill(cell='.')
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
    shader = DynamicPixels(shader=lambda column, row: (255, 0, 0))
    chained = shader | DynamicFill(cell='.')
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


def test_a_sound_effect_chains_onto_sounds() -> None:
    pytest.importorskip('xnano_audio')
    from xnano_audio import TerminalSound

    sound = TerminalSound.from_samples([0.0, 0.5, -0.5, 0.25] * 64, sample_rate=8000)
    shaped = sound | effect('audio.reverb', mix=0.3)
    assert isinstance(shaped, TerminalSound)


def test_xnano_hook_makes_a_reusable_operation() -> None:
    ticks: list[float] = []

    @xnano.hook(on='tick', every=0.1)
    def tick(context: Context) -> None:
        ticks.append(round(context.clock.elapsed, 1))

    assert isinstance(tick, xnano.operations.ContextualOperation)
    assert (tick.on, tick.every) == ('tick', 0.1)
    with xnano.new(width=8, height=1) as first:
        first | tick
        first.clock.step(delta_seconds=0.25)
    with xnano.new(width=8, height=1) as second:
        second | tick
        second.clock.step(delta_seconds=0.15)
    assert len(ticks) == 3
    assert not hasattr(xnano, 'operation')


def test_a_hook_returning_an_operation_applies_it() -> None:
    with xnano.new(width=8, height=1) as canvas:
        label = canvas.screen.write('hi')

        @label.hook(on='tick', after=0.0)
        def tint(context: Context) -> xnano_core.Operation:
            return xnano_core.Fill('x')

        canvas.clock.step(delta_seconds=0.1)
        assert canvas.screen.render().startswith('xx')


def test_a_hook_returning_content_is_refused() -> None:
    with pytest.raises(xnano.errors.TerminalError, match='cannot return content'):
        with xnano.new(width=8, height=1) as canvas:

            @canvas.hook(on='tick', after=0.0)
            def draw(context: Context) -> str:
                return 'text'

            canvas.clock.step(delta_seconds=0.1)


# -- effect kinds, specifications and effects=[...] ---------------------------------------


def specification_kind(specification: type) -> str:
    """The ``kind`` a specification dictionary class is for, read from its annotation."""
    annotation = specification.__annotations__['kind']
    text = getattr(annotation, '__forward_arg__', str(annotation))
    match = re.search(r"Literal\['([a-z_.]+)'\]", text)
    assert match is not None, text
    return match.group(1)


RENDERABLE_SPECIFICATIONS = typing.get_args(xnano.effects.WritableEffectSpecification)
PLAYABLE_SPECIFICATIONS = typing.get_args(xnano.effects.PlayableEffectSpecification)


def public_annotated_members(name: str) -> dict[str, object]:
    """``xnano.effects.<name>`` and, for a class, the function of each public member of it."""
    owner = getattr(xnano.effects, name)
    if not (inspect.isclass(owner) or inspect.isroutine(owner)):
        # A type alias such as a ``Literal`` carries no annotations of its own to resolve.
        return {}
    members: dict[str, object] = {name: owner}
    if not inspect.isclass(owner):
        return members
    for attribute in dir(owner):
        if attribute.startswith('_'):
            continue
        member = inspect.getattr_static(owner, attribute)
        if isinstance(member, property):
            member = member.fget
        elif isinstance(member, (staticmethod, classmethod)):
            member = member.__func__
        # Methods a schema inherits from ``dict``, such as ``fromkeys``, have no annotations.
        if inspect.isfunction(member) or inspect.isclass(member):
            members[f'{name}.{attribute}'] = member
    return members


def type_hints_failure(member: object) -> str:
    """Why ``typing.get_type_hints`` refuses ``member``, or an empty string when it resolves."""
    try:
        typing.get_type_hints(member, include_extras=True)
    except (NameError, TypeError) as error:
        return f'{type(error).__name__}: {error}'
    return ''


def press(canvas: xnano.canvas.Canvas, key: str = 'a') -> None:
    canvas.push(Event.key_press(key))
    canvas.deliver_events()


class TestEffectKinds:
    def test_the_kinds_split_into_visual_and_sound(self) -> None:
        writable = typing.get_args(xnano.effects.WritableEffectKind)
        playable = typing.get_args(xnano.effects.PlayableEffectKind)
        assert len(writable) == 21
        assert len(playable) == 7
        assert all(kind.startswith('effect.') for kind in writable)
        assert all(kind.startswith('audio.') for kind in playable)
        assert set(writable + playable) == set(typing.get_args(xnano.effects.EffectKind))
        assert len(RENDERABLE_SPECIFICATIONS) == 21
        assert len(PLAYABLE_SPECIFICATIONS) == 7

    def test_the_effect_unions_hold_every_parameters_class(self) -> None:
        visual = set(typing.get_args(xnano.effects.WritableEffect))
        sound = set(typing.get_args(xnano.effects.PlayableEffect))
        assert {parameters.customization_kind for parameters in visual} == set(
            typing.get_args(xnano.effects.WritableEffectKind)
        )
        assert {parameters.customization_kind for parameters in sound} == set(
            typing.get_args(xnano.effects.PlayableEffectKind)
        )
        assert visual | sound == set(EFFECT_PARAMETERS_BY_KIND.values())
        assert set(typing.get_args(xnano.effects.EffectSpecification)) == visual | sound

    def test_the_effect_unions_work_with_isinstance(self) -> None:
        fade = effect('effect.fade_to')
        reverb = effect('audio.reverb')
        assert isinstance(fade, xnano.effects.WritableEffect)
        assert not isinstance(fade, xnano.effects.PlayableEffect)
        assert isinstance(reverb, xnano.effects.PlayableEffect)
        assert not isinstance(reverb, xnano.effects.WritableEffect)
        assert isinstance(fade, xnano.effects.EffectSpecification)
        assert isinstance(reverb, xnano.effects.EffectSpecification)
        assert not isinstance(object(), xnano.effects.EffectSpecification)

    def test_the_effect_unions_are_the_same_objects_everywhere_they_are_read(
        self,
    ) -> None:
        for name in ('WritableEffect', 'PlayableEffect', 'EffectSpecification'):
            assert getattr(xnano.effects, name) is getattr(effects_schema, name)
            assert name in dir(effects_schema)

    def test_an_unknown_name_of_the_effect_schema_is_refused(self) -> None:
        with pytest.raises(AttributeError, match='NoSuchName'):
            effects_schema.NoSuchName  # noqa: B018

    def test_annotations_that_use_the_effect_unions_resolve(self) -> None:
        def describe(
            effect: 'xnano.effects.WritableEffect',
        ) -> 'tuple[xnano.effects.EffectSpecification, ...]':
            return (effect,)

        hints = typing.get_type_hints(describe)
        assert hints['effect'] == xnano.effects.WritableEffect
        assert hints['return'] == tuple[xnano.effects.EffectSpecification, ...]
        controller_hints = typing.get_type_hints(
            xnano.effects.EffectController.active.fget
        )
        assert controller_hints['return'] == tuple[xnano.effects.EffectSpecification, ...]

    @pytest.mark.parametrize('name', xnano.effects.__all__)
    def test_the_annotations_of_every_public_effect_member_resolve(
        self, name: str
    ) -> None:
        failures = {
            label: type_hints_failure(member)
            for label, member in public_annotated_members(name).items()
        }
        assert {label: why for label, why in failures.items() if why} == {}

    def test_the_active_effects_of_a_property_are_a_tuple_of_its_effect_union(
        self,
    ) -> None:
        writable_hints = typing.get_type_hints(
            xnano.effects.WritableEffectProperties.active.fget
        )
        assert writable_hints['return'] == tuple[xnano.effects.WritableEffect, ...]
        playable_hints = typing.get_type_hints(
            xnano.effects.PlayableEffectProperties.active.fget
        )
        assert playable_hints['return'] == tuple[xnano.effects.PlayableEffect, ...]

    def test_the_kinds_of_the_parameters_classes_match_the_kind_aliases(self) -> None:
        assert {
            kind for kind in EFFECT_PARAMETERS_BY_KIND if kind.startswith('effect.')
        } == set(typing.get_args(xnano.effects.WritableEffectKind))
        assert {
            kind for kind in EFFECT_PARAMETERS_BY_KIND if kind.startswith('audio.')
        } == set(typing.get_args(xnano.effects.PlayableEffectKind))

    @pytest.mark.parametrize(
        'specification', RENDERABLE_SPECIFICATIONS + PLAYABLE_SPECIFICATIONS
    )
    def test_a_specification_is_its_arguments_plus_a_required_kind(
        self, specification: type
    ) -> None:
        kind = specification_kind(specification)
        parameters_class = EFFECT_PARAMETERS_BY_KIND[kind]
        schema = getattr(
            effects_schema,
            specification.__name__.replace('Specification', 'ParametersSchema'),
        )
        assert 'kind' in specification.__required_keys__
        assert set(schema.__annotations__) < set(specification.__annotations__)
        assert not set(schema.__annotations__) & set(specification.__required_keys__)
        parameters = {field.name for field in dataclasses.fields(parameters_class)}
        assert set(schema.__annotations__) == parameters

    @pytest.mark.parametrize('specification', RENDERABLE_SPECIFICATIONS)
    def test_a_visual_specification_becomes_its_effect(self, specification: type) -> None:
        kind = specification_kind(specification)
        started = normalize_effect({'kind': kind}, 'writable')
        assert type(started) is EFFECT_PARAMETERS_BY_KIND[kind]

    @pytest.mark.parametrize('specification', PLAYABLE_SPECIFICATIONS)
    def test_a_sound_specification_becomes_its_effect(self, specification: type) -> None:
        kind = specification_kind(specification)
        started = normalize_effect({'kind': kind}, 'playable')
        assert type(started) is EFFECT_PARAMETERS_BY_KIND[kind]

    def test_a_specification_carries_the_effects_keywords(self) -> None:
        fade = normalize_effect(
            {'kind': 'effect.fade_to', 'foreground': 'red', 'duration_milliseconds': 600},
            'writable',
        )
        assert isinstance(fade, FadeToEffectParameters)
        assert (fade.foreground, fade.duration_milliseconds) == ('red', 600)
        reverb = normalize_effect({'kind': 'audio.reverb', 'mix': 0.4}, 'playable')
        assert reverb.mix == 0.4

    def test_effect_is_exported_from_the_top_level(self) -> None:
        assert xnano.effect is xnano.effects.effect
        assert 'effect' in xnano.__all__
        assert not hasattr(xnano, 'fx')
        assert not hasattr(xnano.operations, 'fx')


class TestEffectLists:
    @pytest.mark.parametrize(
        ('specification', 'expected', 'message'),
        [
            (
                effect('effect.dissolve'),
                'writable',
                r"effects= takes dictionaries such as \{'kind': 'effect.fade_to'.*"
                r'placement \| effect',
            ),
            (
                effect('audio.reverb'),
                'playable',
                r"effects= takes dictionaries such as \{'kind': 'audio.reverb'.*"
                r'write the effect as a dictionary',
            ),
            ({'foreground': 'red'}, 'writable', 'effects= takes dictionaries'),
            ('effect.fade_to', 'writable', 'effects= takes dictionaries'),
            ({'kind': 3}, 'writable', "The 'kind' of an effect is a string"),
            (
                {'kind': 'audio.reverb'},
                'writable',
                "'audio.reverb' is a sound effect; pass it to play\\(effects=...\\)",
            ),
            (
                {'kind': 'effect.fade_to'},
                'playable',
                "'effect.fade_to' is a visual effect; pass it to write\\(effects=...\\)",
            ),
            ({'kind': 'fill'}, 'writable', "'fill' is not a visual effect"),
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
            normalize_effect({'kind': 'effect.nope'}, 'writable')

    def test_new_applies_effects_to_a_canvas_without_content(self) -> None:
        with xnano.new(
            width=6,
            height=1,
            effects=[{'kind': 'effect.fade_to', 'duration_milliseconds': 500}],
        ) as canvas:
            assert len(canvas._effects) == 1
            running, target = canvas._effects[0]
            assert target is canvas
            assert running.customization_kind == 'effect.fade_to'

    def test_a_sound_effect_in_a_visual_list_is_refused_everywhere(self) -> None:
        with pytest.raises(TypeError, match='is a sound effect'):
            xnano.new(width=6, height=1, effects=[{'kind': 'audio.reverb'}])  # type: ignore[list-item]
        with xnano.new(width=6, height=1) as canvas:
            with pytest.raises(TypeError, match='is a sound effect'):
                canvas.screen.write('x', effects=[{'kind': 'audio.delay'}])  # type: ignore[list-item]
            label = canvas.screen.write('x')
            with pytest.raises(TypeError, match='is a sound effect'):
                label.write('y', effects=[{'kind': 'audio.delay'}])  # type: ignore[list-item]

    def test_a_placement_write_starts_its_effects(self) -> None:
        with xnano.new(width=8, height=2) as canvas:
            outer = canvas.screen.write('a')
            inner = outer.write(
                'b', effects=[{'kind': 'effect.dissolve', 'duration_milliseconds': 100}]
            )
            assert any(target is inner for _, target in canvas._effects)


class TestCancel:
    def test_cancel_stops_a_running_effect(self) -> None:
        with xnano.new(width=6, height=1) as canvas:
            label = canvas.screen.write('hi')
            fade = effect('effect.fade_to', foreground='red', duration_milliseconds=1000)
            fade.apply_to(label)
            canvas.clock.step(delta_seconds=0.25)
            canvas.clock.step(delta_seconds=0.25)
            assert '38;2;' in canvas.screen.render(format='ansi')
            fade.cancel()
            canvas.clock.step(delta_seconds=0.1)
            assert '38;2;' not in canvas.screen.render(format='ansi')
            assert canvas._effects == []

    def test_cancel_does_nothing_without_a_target(self) -> None:
        effect('effect.fade_to').cancel()

    def test_a_dynamic_operation_has_nothing_to_cancel(self) -> None:
        assert not hasattr(DynamicFill(), 'cancel')

    def test_cancel_twice_is_harmless(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:
            fade = effect('effect.dissolve', duration_milliseconds=1000)
            fade.apply_to(canvas)
            fade.cancel()
            fade.cancel()


class TestContextEffects:
    def test_a_visual_effect_runs_on_the_hooks_placement(self) -> None:
        with xnano.new(width=8, height=2) as canvas:
            label = canvas.screen.write('hi')
            other = canvas.screen.write('yo', y=1)
            applied: list[object] = []

            @label.hook(on='key')
            def tint(context: Context) -> None:
                applied.append(
                    context.fx.fade_to(foreground='red', duration_milliseconds=1000)
                )

            press(canvas)
            assert isinstance(applied[0], FadeToEffectParameters)
            assert applied[0].foreground == 'red'
            assert [target for _, target in canvas._effects] == [label]
            canvas.clock.step(delta_seconds=0.5)
            first, second = canvas.screen.render(format='ansi').split('\n')[:2]
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
                canvas.clock.step(delta_seconds=1.0)
            assert canvas._effects == []

    def test_the_effect_is_the_live_handle_the_hook_returns(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:
            kept: list[FadeToEffectParameters] = []

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                kept.append(
                    context.fx.fade_to(foreground='red', duration_milliseconds=1000)
                )

            press(canvas)
            fade = kept[0]
            key = fade.key
            fade.duration_milliseconds = 400
            assert fade.key == key
            assert fade.duration_milliseconds == 400

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

    def test_a_wrong_keyword_is_refused_like_effect_refuses_it(self) -> None:
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
            seen: list[FadeToEffectParameters] = []

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
            canvas.clock.step(delta_seconds=0.5)
            assert '38;2;' in canvas.screen.render(format='ansi')
            press(canvas, 'b')
            canvas.clock.step(delta_seconds=0.1)
            assert active == [()]
            assert '38;2;' not in canvas.screen.render(format='ansi')
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
            canvas.clock.step(delta_seconds=0.1)
            assert len(canvas._effects) == 1
            tint.remove()
            canvas.clock.step(delta_seconds=0.1)
            assert canvas._effects == []

    def test_removing_the_placement_ends_its_effects(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:
            label = canvas.screen.write('x')

            @label.hook(on='key')
            def tint(context: Context) -> None:
                context.fx.fade_to(foreground='red', duration_milliseconds=1000)

            press(canvas)
            label.remove()
            canvas.clock.step(delta_seconds=0.1)
            assert canvas._effects == []

    def test_a_hook_that_removes_itself_leaves_no_effect_behind(self) -> None:
        with xnano.new('hi', width=6, height=1) as canvas:

            @canvas.hook(on='key')
            def tint(context: Context) -> None:
                context.hook.remove()
                fade = context.fx.fade_to(foreground='red', duration_milliseconds=1000)
                assert isinstance(fade, FadeToEffectParameters)

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

            for _ in canvas.iter(frames=3):
                pass
            assert sizes and set(sizes) == {1}
            assert len(canvas._effects) == 1


class TestEffectSettings:
    def test_an_unknown_setting_names_the_kind_and_the_accepted_settings(self) -> None:
        with pytest.raises(
            TypeError, match="effect 'effect.dissolve' has no setting called 'color'"
        ):
            normalize_effect({'kind': 'effect.dissolve', 'color': 'red'}, 'writable')
        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(TypeError, match='duration_milliseconds'):
                canvas.screen.write(
                    'x',
                    effects=[{'kind': 'effect.dissolve', 'color': 'red'}],  # type: ignore[list-item]
                )

    def test_draw_checks_its_effects_at_the_call(self) -> None:
        with pytest.raises(ValueError, match='is not a known visual effect'):
            xnano.draw(['G'], {'G': 'red'}, effects=[{'kind': 'effect.nope'}])  # type: ignore[list-item]
        with pytest.raises(TypeError, match='sound effect'):
            xnano.draw(['G'], {'G': 'red'}, effects=[{'kind': 'audio.reverb'}])  # type: ignore[list-item]


class TestSuggestedValues:
    def test_every_interpolation_is_one_the_engine_accepts(self) -> None:
        names = typing.get_args(xnano.effects.Interpolation)
        assert typing.get_args(xnano_core.Interpolation) == names
        with xnano.new('hi', width=4, height=1) as canvas:
            for name in names:
                canvas.screen.fx.fade_to(foreground='red', interpolation=name)
                canvas.clock.step(delta_seconds=0.01)

    def test_every_motion_direction_is_one_the_engine_accepts(self) -> None:
        with xnano.new('hi', width=4, height=1) as canvas:
            for direction in typing.get_args(xnano.effects.MotionDirection):
                canvas.screen.fx.sweep_in(direction=direction, duration_milliseconds=10)
                canvas.screen.fx.stretch(direction=direction, duration_milliseconds=10)
                canvas.clock.step(delta_seconds=0.01)

    def test_percentages_are_suggested_in_steps_of_five(self) -> None:
        steps = typing.get_args(xnano.layout.Percentage)
        assert steps == tuple(f'{share}%' for share in range(5, 101, 5))
